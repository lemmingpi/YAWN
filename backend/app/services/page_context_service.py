"""Service for generating AI-powered page context summaries."""

import logging
import time
from pathlib import Path
from typing import Dict, Optional

import jinja2
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Note, Page
from .gemini_provider import create_gemini_provider

logger = logging.getLogger(__name__)


class PageContextService:
    """
    Service for generating LLM-powered context summaries for pages.

    This service analyzes page content and notes to create structured context
    summaries optimized for LLM consumption. The context captures genre-specific
    information like writing style, technical details, or scholarly metadata.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the page context service.

        Args:
            db: Database session for querying pages and notes
        """
        self.db = db
        self._template = None

    def _load_prompt_template(self) -> jinja2.Template:
        """
        Load the Jinja2 template for page context generation.

        Returns:
            Compiled Jinja2 template

        Raises:
            FileNotFoundError: If template file not found
        """
        if self._template is not None:
            return self._template

        # Find template file relative to this module
        template_path = (
            Path(__file__).parent.parent.parent
            / "prompts"
            / "page_context"
            / "page_context_generation.jinja2"
        )

        if not template_path.exists():
            raise FileNotFoundError(
                f"Page context template not found at: {template_path}"
            )

        logger.info(f"Loading page context template from: {template_path}")

        # Load template
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # Create Jinja2 environment and compile template
        env = jinja2.Environment(
            autoescape=False,  # Don't escape - we want raw text
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._template = env.from_string(template_content)

        return self._template

    async def _build_context_prompt(
        self,
        page: Page,
        notes: list[Note],
        custom_instructions: Optional[str] = None,
        page_source: Optional[str] = None,
    ) -> str:
        """
        Build the prompt for page context generation.

        Args:
            page: Page object with metadata
            notes: List of notes on this page
            custom_instructions: Optional user-provided instructions
            page_source: Optional alternate page source (for paywalled content)

        Returns:
            Formatted prompt string ready for LLM
        """
        # Concatenate all note content
        notes_content = "\n\n---\n\n".join(
            [f"Note {i + 1}:\n{note.content}" for i, note in enumerate(notes)]
        )

        # Load and render template
        template = self._load_prompt_template()
        prompt: str = template.render(
            page_url=page.url,  # Always from database
            page_title=page.title or "Untitled",
            page_summary=page.page_summary,
            notes_content=notes_content if notes_content else None,
            custom_instructions=custom_instructions,
            page_source=page_source,  # Optional alternate source
        )

        return prompt

    async def generate_page_context(
        self,
        page_id: int,
        llm_provider_id: int,
        custom_instructions: Optional[str] = None,
        page_source: Optional[str] = None,
    ) -> Dict:
        """
        Generate AI-powered context summary for a page.

        Args:
            page_id: ID of page to generate context for
            llm_provider_id: LLM provider to use (currently unused, uses Gemini)
            custom_instructions: Optional user instructions for customization
            page_source: Optional alternate page source (for paywalled content)

        Returns:
            Dictionary with:
                - user_context: Generated context string
                - detected_content_type: Content type detected by LLM
                - tokens_used: Total tokens consumed
                - cost_usd: Cost in USD
                - generation_time_ms: Generation time in milliseconds
                - input_tokens: Input token count
                - output_tokens: Output token count

        Raises:
            ValueError: If page not found
            GeminiProviderError: If LLM generation fails
        """
        start_time = time.time()

        logger.info(f"Starting page context generation for page_id={page_id}")

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

        # Fetch all notes for this page
        notes_result = await self.db.execute(
            select(Note)
            .where(Note.page_id == page_id)
            .where(Note.is_active.is_(True))
            .order_by(Note.created_at)
        )
        notes = list(notes_result.scalars().all())

        logger.info(f"Found {len(notes)} active notes for this page")

        # Build prompt
        prompt = await self._build_context_prompt(
            page, notes, custom_instructions, page_source
        )
        logger.info(f"Built prompt: {len(prompt)} characters")

        # Generate using Gemini
        provider = await create_gemini_provider()
        logger.info("Calling Gemini API for context generation")

        generation_result = await provider.generate_content_large(prompt=prompt)

        logger.info(
            f"Generation complete: {generation_result['input_tokens']} input tokens, "
            f"{generation_result['output_tokens']} output tokens, "
            f"${generation_result['cost']:.6f} cost"
        )

        if generation_result.get("token_limit_reached"):
            logger.warning(
                f"⚠️  Token limit reached! Response may be incomplete. "
                f"Output: {generation_result['output_tokens']} tokens. "
                f"Consider increasing max_output_tokens in generate_content() call."
            )

        # Extract generated context
        generated_context = generation_result["content"]

        # Try to extract detected content type from first line
        detected_content_type = "Unknown"
        if generated_context.startswith("Content Type:"):
            first_line = generated_context.split("\n", 1)[0]
            detected_content_type = first_line.replace("Content Type:", "").strip()
            logger.info(f"Detected content type: {detected_content_type}")

        # Update page with generated context
        page.user_context = generated_context
        await self.db.commit()
        await self.db.refresh(page)

        logger.info(f"Updated page.user_context for page_id={page_id}")

        # Calculate generation time
        generation_time_ms = int((time.time() - start_time) * 1000)

        return {
            "user_context": generated_context,
            "detected_content_type": detected_content_type,
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
        custom_instructions: Optional[str] = None,
        page_source: Optional[str] = None,
    ) -> str:
        """
        Preview the prompt that would be sent to the LLM without actually calling it.

        This method uses the same _build_context_prompt function as generate_page_context,
        ensuring the preview exactly matches what will be sent to the LLM.

        Args:
            page_id: ID of page to preview prompt for
            custom_instructions: Optional user instructions for customization
            page_source: Optional alternate page source (for paywalled content)

        Returns:
            The fully rendered prompt string

        Raises:
            ValueError: If page not found
        """
        logger.info(f"Previewing prompt for page_id={page_id}")

        # Fetch page with site relationship
        result = await self.db.execute(
            select(Page).options(selectinload(Page.site)).where(Page.id == page_id)
        )
        page = result.scalar_one_or_none()

        if not page:
            raise ValueError(f"Page with ID {page_id} not found")

        # Fetch all notes for this page (same logic as generate_page_context)
        notes_result = await self.db.execute(
            select(Note)
            .where(Note.page_id == page_id)
            .where(Note.is_active.is_(True))
            .order_by(Note.created_at)
        )
        notes = list(notes_result.scalars().all())

        # Build prompt using the SAME function as generate_page_context
        prompt = await self._build_context_prompt(
            page, notes, custom_instructions, page_source
        )

        logger.info(f"Preview generated: {len(prompt)} characters")
        return prompt
