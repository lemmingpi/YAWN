"""Service for generating AI-powered auto-notes from page content."""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

import jinja2
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Note, Page
from .gemini_provider import create_gemini_provider

logger = logging.getLogger(__name__)


class AutoNoteService:
    """
    Service for generating LLM-powered study notes from page content.

    This service analyzes page content and automatically creates structured notes
    with highlighted text and commentary, similar to a study guide or editorial review.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the auto note service.

        Args:
            db: Database session for querying pages and creating notes
        """
        self.db = db
        self._study_guide_template = None
        self._content_review_template = None

    def _load_prompt_template(self, template_name: str) -> jinja2.Template:
        """
        Load a Jinja2 template for auto note generation.

        Args:
            template_name: Name of template ('study_guide' or 'content_review')

        Returns:
            Compiled Jinja2 template

        Raises:
            FileNotFoundError: If template file not found
            ValueError: If template_name is invalid
        """
        # Map template names to files
        template_files = {
            "study_guide": "study_guide_generation.jinja2",
            "content_review": "content_review_expansion.jinja2",
        }

        if template_name not in template_files:
            raise ValueError(
                f"Invalid template name: {template_name}. "
                f"Must be one of: {list(template_files.keys())}"
            )

        # Check cache
        if template_name == "study_guide" and self._study_guide_template is not None:
            return self._study_guide_template
        if (
            template_name == "content_review"
            and self._content_review_template is not None
        ):
            return self._content_review_template

        # Find template file relative to this module
        template_path = (
            Path(__file__).parent.parent.parent
            / "prompts"
            / "auto_notes"
            / template_files[template_name]
        )

        if not template_path.exists():
            raise FileNotFoundError(f"Auto note template not found at: {template_path}")

        logger.info(f"Loading auto note template from: {template_path}")

        # Load template
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # Create Jinja2 environment and compile template
        env = jinja2.Environment(
            autoescape=False,  # Don't escape - we want raw text
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = env.from_string(template_content)

        # Cache the template
        if template_name == "study_guide":
            self._study_guide_template = template
        else:
            self._content_review_template = template

        return template

    async def _build_prompt(
        self,
        page: Page,
        template_type: str,
        custom_instructions: Optional[str] = None,
        page_source: Optional[str] = None,
    ) -> str:
        """
        Build the prompt for auto note generation.

        Args:
            page: Page object with metadata
            template_type: Type of template ('study_guide' or 'content_review')
            custom_instructions: Optional user-provided instructions
            page_source: Optional alternate page source (for paywalled content)

        Returns:
            Formatted prompt string ready for LLM
        """
        # Load and render template
        template = self._load_prompt_template(template_type)
        prompt: str = template.render(
            page_url=page.url,  # Always from database
            page_title=page.title or "Untitled",
            page_summary=page.page_summary,
            user_context=page.user_context,
            custom_instructions=custom_instructions,
            page_source=page_source,  # Optional alternate source
        )

        return prompt

    async def generate_auto_notes(
        self,
        page_id: int,
        user_id: int,
        llm_provider_id: int,
        template_type: str = "study_guide",
        custom_instructions: Optional[str] = None,
        page_source: Optional[str] = None,
    ) -> Dict:
        """
        Generate AI-powered study notes for a page.

        Args:
            page_id: ID of page to generate notes for
            user_id: ID of user creating the notes
            llm_provider_id: LLM provider to use (currently unused, uses Gemini)
            template_type: Type of template ('study_guide' or 'content_review')
            custom_instructions: Optional user instructions for customization
            page_source: Optional alternate page source (for paywalled content)

        Returns:
            Dictionary with:
                - notes: List of created Note objects
                - generation_batch_id: Batch ID for deletion
                - tokens_used: Total tokens consumed
                - cost_usd: Cost in USD
                - generation_time_ms: Generation time in milliseconds
                - input_tokens: Input token count
                - output_tokens: Output token count

        Raises:
            ValueError: If page not found or JSON parsing fails
            GeminiProviderError: If LLM generation fails
        """
        start_time = time.time()

        logger.info(
            f"Starting auto note generation for page_id={page_id}, "
            f"template_type={template_type}"
        )

        # Fetch page with site relationship
        result = await self.db.execute(
            select(Page).options(selectinload(Page.site)).where(Page.id == page_id)
        )
        page = result.scalar_one_or_none()

        if not page:
            raise ValueError(f"Page with ID {page_id} not found")

        logger.info(
            f"Found page: title='{page.title}', url='{page.url}', site_id={page.site_id}"
        )

        # Build prompt
        prompt = await self._build_prompt(
            page, template_type, custom_instructions, page_source
        )
        logger.info(f"Built prompt: {len(prompt)} characters")

        # Generate using Gemini
        provider = await create_gemini_provider()
        logger.info("Calling Gemini API for auto note generation")

        generation_result = await provider.generate_content_large(prompt=prompt)

        logger.info(
            f"Generation complete: {generation_result['input_tokens']} input tokens, "
            f"{generation_result['output_tokens']} output tokens, "
            f"${generation_result['cost']:.6f} cost"
        )

        if generation_result.get("token_limit_reached"):
            logger.warning(
                f"⚠️  Token limit reached! Response may be incomplete. "
                f"Output: {generation_result['output_tokens']} tokens."
            )

        # Parse JSON response
        generated_content = generation_result["content"]

        # Remove markdown code blocks if present
        if generated_content.startswith("```json"):
            generated_content = generated_content.replace("```json", "", 1)
        if generated_content.startswith("```"):
            generated_content = generated_content.replace("```", "", 1)
        if generated_content.endswith("```"):
            generated_content = generated_content.rsplit("```", 1)[0]

        generated_content = generated_content.strip()

        try:
            parsed_data = json.loads(generated_content)
            notes_data = parsed_data.get("notes", [])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {generated_content[:500]}...")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

        if not notes_data:
            logger.warning("No notes generated from LLM response")
            return {
                "notes": [],
                "generation_batch_id": None,
                "tokens_used": generation_result["input_tokens"]
                + generation_result["output_tokens"],
                "cost_usd": generation_result["cost"],
                "generation_time_ms": int((time.time() - start_time) * 1000),
                "input_tokens": generation_result["input_tokens"],
                "output_tokens": generation_result["output_tokens"],
            }

        # Generate batch ID for this set of notes
        generation_batch_id = f"auto_{uuid.uuid4().hex[:12]}"
        logger.info(
            f"Creating {len(notes_data)} notes with batch_id={generation_batch_id}"
        )

        # Create Note records
        created_notes = []
        for idx, note_data in enumerate(notes_data):
            note = Note(
                content=note_data.get("commentary", ""),
                highlighted_text=note_data.get("highlighted_text"),
                page_section_html=None,  # We don't have section HTML from LLM
                position_x=100 + (idx * 20),  # Stagger notes slightly
                position_y=100 + (idx * 20),
                anchor_data={
                    "position_hint": note_data.get("position_hint"),
                    "auto_generated": True,
                },
                page_id=page_id,
                user_id=user_id,
                generation_batch_id=generation_batch_id,
                is_active=True,
            )
            self.db.add(note)
            created_notes.append(note)

        await self.db.commit()

        # Refresh to get IDs
        for note in created_notes:
            await self.db.refresh(note)

        logger.info(f"Created {len(created_notes)} auto-generated notes")

        # Calculate generation time
        generation_time_ms = int((time.time() - start_time) * 1000)

        return {
            "notes": created_notes,
            "generation_batch_id": generation_batch_id,
            "tokens_used": generation_result["input_tokens"]
            + generation_result["output_tokens"],
            "cost_usd": generation_result["cost"],
            "generation_time_ms": generation_time_ms,
            "input_tokens": generation_result["input_tokens"],
            "output_tokens": generation_result["output_tokens"],
        }

    async def preview_prompt(
        self,
        page_id: int,
        template_type: str = "study_guide",
        custom_instructions: Optional[str] = None,
        page_source: Optional[str] = None,
    ) -> str:
        """
        Preview the prompt that would be sent to the LLM without actually calling it.

        Args:
            page_id: ID of page to preview prompt for
            template_type: Type of template ('study_guide' or 'content_review')
            custom_instructions: Optional user instructions for customization
            page_source: Optional alternate page source (for paywalled content)

        Returns:
            The fully rendered prompt string

        Raises:
            ValueError: If page not found
        """
        logger.info(f"Previewing auto note prompt for page_id={page_id}")

        # Fetch page with site relationship
        result = await self.db.execute(
            select(Page).options(selectinload(Page.site)).where(Page.id == page_id)
        )
        page = result.scalar_one_or_none()

        if not page:
            raise ValueError(f"Page with ID {page_id} not found")

        # Build prompt
        prompt = await self._build_prompt(
            page, template_type, custom_instructions, page_source
        )

        logger.info(f"Preview generated: {len(prompt)} characters")
        return prompt

    async def delete_batch(self, generation_batch_id: str, user_id: int) -> int:
        """
        Delete all notes with a given generation_batch_id.

        Args:
            generation_batch_id: Batch ID to delete
            user_id: User ID for authorization

        Returns:
            Number of notes deleted

        Raises:
            ValueError: If batch not found or user doesn't own the notes
        """
        logger.info(
            f"Deleting notes with generation_batch_id={generation_batch_id} "
            f"for user_id={user_id}"
        )

        # Fetch notes with this batch ID
        result = await self.db.execute(
            select(Note)
            .where(Note.generation_batch_id == generation_batch_id)
            .where(Note.user_id == user_id)
        )
        notes_to_delete = list(result.scalars().all())

        if not notes_to_delete:
            raise ValueError(
                f"No notes found with batch ID {generation_batch_id} for this user"
            )

        # Mark as inactive rather than hard delete
        for note in notes_to_delete:
            note.is_active = False

        await self.db.commit()

        logger.info(f"Deleted {len(notes_to_delete)} notes")

        return len(notes_to_delete)
