"""Service for generating AI-powered auto-notes from page content."""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import jinja2
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Note, Page
from .gemini_provider import create_gemini_provider
from .selector_validator import SelectorValidator

logger = logging.getLogger(__name__)


def detect_selector_type(position_string: str) -> tuple[str | None, str | None]:
    """
    Auto-detect whether a position string is a CSS selector or XPath.

    Args:
        position_string: The position string from LLM (could be CSS, XPath, or text)

    Returns:
        Tuple of (css_selector, xpath) where one will be the string and the other None
    """
    if not position_string or not isinstance(position_string, str):
        return (None, None)

    position_string = position_string.strip()

    # XPath indicators
    xpath_indicators = [
        position_string.startswith("/"),  # Absolute XPath
        position_string.startswith("//"),  # Relative XPath
        position_string.startswith("("),  # XPath expression
        "//" in position_string and "[" in position_string,  # Contains XPath syntax
        "ancestor::" in position_string,  # XPath axis
        "descendant::" in position_string,
        "following::" in position_string,
        "preceding::" in position_string,
    ]

    if any(xpath_indicators):
        return (None, position_string)

    # CSS selector indicators (if it has CSS-specific syntax)
    css_indicators = [
        ">" in position_string,  # Direct child combinator
        "+" in position_string,  # Adjacent sibling
        "~" in position_string,  # General sibling
        ":nth-child" in position_string,
        ":first-child" in position_string,
        ":last-child" in position_string,
        "::before" in position_string,
        "::after" in position_string,
        position_string.startswith("#"),  # ID selector
        position_string.startswith("."),  # Class selector
        "[" in position_string and "]" in position_string,  # Attribute selector
    ]

    if any(css_indicators):
        return (position_string, None)

    # If it looks like a simple tag or class/id combo, treat as CSS
    if (
        position_string.replace(".", "").replace("#", "").replace(" ", "").isalnum()
        or " " in position_string
    ):
        return (position_string, None)

    # Default to None for ambiguous cases (plain text descriptions)
    return (None, None)


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
        self._validator = SelectorValidator(fuzzy_threshold=0.80)

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
        page_dom: Optional[str] = None,
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
            page_dom=page_dom,  # Optional DOM from extension
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
        page_dom: Optional[str] = None,
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

        # Validate that page is not paywalled
        if page.is_paywalled:
            raise ValueError(
                "Cannot generate auto-notes for paywalled pages. "
                "The LLM cannot accurately position notes without access "
                "to the original page content. "
                "You can still use the preview feature to see what "
                "would be generated."
            )

        logger.info(
            f"Found page: title='{page.title}', url='{page.url}', "
            f"site_id={page.site_id}, is_paywalled={page.is_paywalled}"
        )

        # Build prompt
        prompt = await self._build_prompt(
            page, template_type, custom_instructions, page_source, page_dom
        )
        logger.info(f"Built prompt: {len(prompt)} characters")

        # Echo the full prompt to console for debugging
        logger.info("=" * 80)
        logger.info("FULL PROMPT BEING SENT TO LLM:")
        logger.info("=" * 80)
        logger.info(prompt)
        logger.info("=" * 80)
        logger.info(
            f"DOM included: {bool(page_dom)}, DOM size: {len(page_dom) if page_dom else 0} chars"
        )
        logger.info("=" * 80)

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

        # Track validation statistics
        validation_stats = {
            "total": len(notes_data),
            "validated": 0,
            "repaired": 0,
            "failed_validation": 0,
        }

        # Create Note records
        created_notes = []
        for idx, note_data in enumerate(notes_data):
            # Extract selectors from LLM response
            # New format: css_selector and xpath fields directly provided
            css_selector = note_data.get("css_selector")
            xpath = note_data.get("xpath")

            # Fallback to old format for backward compatibility
            if not css_selector and not xpath:
                position = note_data.get("position") or note_data.get("position_hint")
                if position:
                    css_selector, xpath = detect_selector_type(position)

            # Validate and repair selectors if page_dom is available
            validation_metadata = None
            if page_dom and css_selector:
                highlighted_text = note_data.get("highlighted_text", "")

                # Try to validate the CSS selector
                is_valid, match_count, _ = self._validator.validate_selector(
                    page_dom, css_selector
                )

                if is_valid:
                    validation_stats["validated"] += 1
                    logger.debug(
                        f"Note {idx + 1}: Selector valid - '{css_selector[:50]}...'"
                    )
                else:
                    validation_stats["failed_validation"] += 1
                    logger.info(
                        f"Note {idx + 1}: Selector invalid (matched {match_count} elements), "
                        f"attempting repair - '{css_selector[:50]}...'"
                    )

                    # Attempt to repair the selector
                    repair_result = self._validator.repair_selector(
                        page_dom, highlighted_text, css_selector, xpath
                    )

                    if repair_result["success"]:
                        validation_stats["repaired"] += 1
                        # Replace with repaired selectors
                        old_css = css_selector
                        css_selector = repair_result["css_selector"]
                        xpath = repair_result["xpath"]

                        new_selector_preview = (
                            css_selector[:30] if css_selector else xpath[:30]
                        )
                        logger.info(
                            f"Note {idx + 1}: Repaired selector "
                            f"(similarity={repair_result['text_similarity']:.2f}, "
                            f"matches={repair_result['match_count']}) - "
                            f"old: '{old_css[:30]}...', "
                            f"new: '{new_selector_preview}...'"
                        )

                        # Store validation metadata for debugging
                        validation_metadata = {
                            "original_selector": old_css,
                            "was_repaired": True,
                            "match_count": repair_result["match_count"],
                            "text_similarity": repair_result["text_similarity"],
                            "repair_message": repair_result["message"],
                        }
                    else:
                        logger.warning(
                            f"Note {idx + 1}: Failed to repair selector - "
                            f"{repair_result['message']}"
                        )
                        validation_metadata = {
                            "original_selector": css_selector,
                            "was_repaired": False,
                            "repair_failed": True,
                            "repair_message": repair_result["message"],
                        }

            # Build anchor_data with selectors
            anchor_data: Dict[str, Any] = {
                "auto_generated": True,
            }

            # Add validation metadata if available
            if validation_metadata:
                anchor_data["validation"] = validation_metadata

            if css_selector:
                anchor_data["elementSelector"] = css_selector
            if xpath:
                anchor_data["elementXPath"] = xpath

            # Build selectionData for the extension to properly highlight text
            # The extension needs this structure to restore text highlighting
            highlighted_text = note_data.get("highlighted_text", "")
            if highlighted_text and (css_selector or xpath):
                # Use the best available selector (prefer CSS)
                selector = css_selector or xpath
                anchor_data["selectionData"] = {
                    "selectedText": highlighted_text,
                    "startSelector": selector,
                    "endSelector": selector,
                    "startOffset": 0,  # LLM doesn't provide exact offsets
                    "endOffset": len(highlighted_text),
                    "startContainerType": 3,  # TEXT_NODE
                    "endContainerType": 3,  # TEXT_NODE
                    "commonAncestorSelector": selector,
                }

            # Create unique server_link_id using batch ID + index
            # This prevents duplicates during sync while allowing extension display
            server_link_id = f"{generation_batch_id}_{idx}"

            note = Note(
                content=note_data.get("commentary", ""),
                highlighted_text=highlighted_text,
                page_section_html=None,  # We don't have section HTML from LLM
                position_x=100 + (idx * 20),  # Stagger notes slightly
                position_y=100 + (idx * 20),
                anchor_data=anchor_data,
                page_id=page_id,
                user_id=user_id,
                generation_batch_id=generation_batch_id,
                server_link_id=server_link_id,
                is_active=True,
            )
            self.db.add(note)
            created_notes.append(note)

        await self.db.commit()

        # Refresh to get IDs
        for note in created_notes:
            await self.db.refresh(note)

        logger.info(f"Created {len(created_notes)} auto-generated notes")

        # Log validation statistics if page_dom was provided
        if page_dom and validation_stats["total"] > 0:
            success_rate = (
                (validation_stats["validated"] + validation_stats["repaired"])
                / validation_stats["total"]
                * 100
            )
            logger.info(
                f"Selector validation stats: {validation_stats['validated']} valid, "
                f"{validation_stats['repaired']} repaired, "
                f"{validation_stats['failed_validation'] - validation_stats['repaired']} failed "
                f"({success_rate:.1f}% success rate)"
            )

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

    async def generate_auto_notes_chunked(
        self,
        page_id: int,
        user_id: int,
        llm_provider_id: int,
        chunk_index: int,
        total_chunks: int,
        chunk_dom: str,
        batch_id: str,
        position_offset: int = 0,
        template_type: str = "study_guide",
        parent_context: Optional[Dict[str, Any]] = None,
        custom_instructions: Optional[str] = None,
    ) -> Dict:
        """
        Generate AI-powered study notes from a DOM chunk (stateless).

        Each chunk is processed independently with no backend session management.
        Frontend-generated batch_id links all notes together.

        This enables:
        - Complete page coverage by processing chunks in parallel (3 at a time)
        - Simpler backend with no session state
        - Better scalability for large pages

        Args:
            page_id: ID of page to generate notes for (already registered)
            user_id: ID of user creating the notes
            llm_provider_id: LLM provider to use
            chunk_index: Index of current chunk (0-based)
            total_chunks: Total number of chunks
            chunk_dom: DOM content for this chunk
            batch_id: Frontend-generated batch ID (shared across all chunks)
            position_offset: Position offset for notes in this chunk
            template_type: Type of template ('study_guide' or 'content_review')
            parent_context: Parent document context for selectors
            custom_instructions: Optional user instructions

        Returns:
            Dictionary with notes and metadata for this chunk only

        Raises:
            ValueError: If page not found or JSON parsing fails
        """
        start_time = time.time()

        logger.info(
            f"Processing chunk {chunk_index + 1}/{total_chunks}, "
            f"batch_id={batch_id}, page_id={page_id}"
        )

        # Fetch page with site relationship
        result = await self.db.execute(
            select(Page).options(selectinload(Page.site)).where(Page.id == page_id)
        )
        page = result.scalar_one_or_none()

        if not page:
            raise ValueError(f"Page with ID {page_id} not found")

        # Build prompt with chunk context
        chunk_instructions = (
            f"Processing chunk {chunk_index + 1} of {total_chunks}. "
            f"Generate notes only for content in this chunk. "
        )
        if custom_instructions:
            chunk_instructions += custom_instructions

        prompt = await self._build_prompt(
            page,
            template_type,
            chunk_instructions,
            page_source=None,
            page_dom=chunk_dom,
        )

        logger.info(
            f"Chunk {chunk_index + 1}/{total_chunks}: Prompt built, {len(prompt)} chars"
        )

        # Generate using Gemini
        provider = await create_gemini_provider()
        generation_result = await provider.generate_content_large(prompt=prompt)

        logger.info(
            f"Chunk {chunk_index + 1}/{total_chunks}: Generation complete, "
            f"{generation_result['input_tokens']} in, {generation_result['output_tokens']} out"
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
            logger.error(
                f"Failed to parse JSON response for chunk {chunk_index + 1}: {e}"
            )
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

        # Create Note records for this chunk
        created_notes = []
        if notes_data:
            for idx, note_data in enumerate(notes_data):
                # Extract selectors
                css_selector = note_data.get("css_selector")
                xpath = note_data.get("xpath")

                # Fallback to old format
                if not css_selector and not xpath:
                    position = note_data.get("position") or note_data.get(
                        "position_hint"
                    )
                    if position:
                        css_selector, xpath = detect_selector_type(position)

                # Validate and repair selectors if chunk_dom available
                validation_metadata = None
                if chunk_dom and css_selector:
                    highlighted_text = note_data.get("highlighted_text", "")

                    is_valid, match_count, _ = self._validator.validate_selector(
                        chunk_dom, css_selector
                    )

                    if not is_valid:
                        repair_result = self._validator.repair_selector(
                            chunk_dom, highlighted_text, css_selector, xpath
                        )

                        if repair_result["success"]:
                            css_selector = repair_result["css_selector"]
                            xpath = repair_result["xpath"]
                            validation_metadata = {
                                "original_selector": note_data.get("css_selector"),
                                "was_repaired": True,
                                "match_count": repair_result["match_count"],
                                "text_similarity": repair_result["text_similarity"],
                            }

                # Build anchor_data
                anchor_data: Dict[str, Any] = {
                    "auto_generated": True,
                    "chunk_index": chunk_index,
                }

                if validation_metadata:
                    anchor_data["validation"] = validation_metadata

                if css_selector:
                    anchor_data["elementSelector"] = css_selector
                if xpath:
                    anchor_data["elementXPath"] = xpath

                # Build selectionData
                highlighted_text = note_data.get("highlighted_text", "")
                if highlighted_text and (css_selector or xpath):
                    selector = css_selector or xpath
                    anchor_data["selectionData"] = {
                        "selectedText": highlighted_text,
                        "startSelector": selector,
                        "endSelector": selector,
                        "startOffset": 0,
                        "endOffset": len(highlighted_text),
                        "startContainerType": 3,
                        "endContainerType": 3,
                        "commonAncestorSelector": selector,
                    }

                # Create unique server_link_id using batch_id + chunk_index + idx
                server_link_id = f"{batch_id}_{chunk_index}_{idx}"

                note = Note(
                    content=note_data.get("commentary", ""),
                    highlighted_text=highlighted_text,
                    page_section_html=None,
                    position_x=100 + position_offset + (idx * 20),
                    position_y=100 + position_offset + (idx * 20),
                    anchor_data=anchor_data,
                    page_id=page_id,
                    user_id=user_id,
                    generation_batch_id=batch_id,  # Use frontend-provided batch_id
                    server_link_id=server_link_id,
                    is_active=True,
                )
                self.db.add(note)
                created_notes.append(note)

            await self.db.commit()

            # Refresh to get IDs
            for note in created_notes:
                await self.db.refresh(note)

            logger.info(
                f"Chunk {chunk_index + 1}/{total_chunks}: Created {len(created_notes)} notes"
            )

        # Calculate generation time for this chunk
        generation_time_ms = int((time.time() - start_time) * 1000)

        # Return results for this chunk only (stateless)
        return {
            "notes": created_notes,
            "tokens_used": generation_result["input_tokens"]
            + generation_result["output_tokens"],
            "cost_usd": generation_result["cost"],
            "input_tokens": generation_result["input_tokens"],
            "output_tokens": generation_result["output_tokens"],
            "generation_time_ms": generation_time_ms,
        }

    async def preview_prompt(
        self,
        page_id: int,
        template_type: str = "study_guide",
        custom_instructions: Optional[str] = None,
        page_source: Optional[str] = None,
        page_dom: Optional[str] = None,
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
            page, template_type, custom_instructions, page_source, page_dom
        )

        logger.info(f"Preview generated: {len(prompt)} characters")
        return prompt

    async def delete_batch(self, generation_batch_id: str, user_id: int) -> int:
        """
        Archive all notes with a given generation_batch_id.

        Args:
            generation_batch_id: Batch ID to archive
            user_id: User ID for authorization

        Returns:
            Number of notes archived

        Raises:
            ValueError: If batch not found or user doesn't own the notes
        """
        logger.info(
            f"Archiving notes with generation_batch_id={generation_batch_id} "
            f"for user_id={user_id}"
        )

        # Fetch notes with this batch ID
        result = await self.db.execute(
            select(Note)
            .where(Note.generation_batch_id == generation_batch_id)
            .where(Note.user_id == user_id)
            .where(Note.is_archived == False)  # noqa: E712
        )
        notes_to_archive = list(result.scalars().all())

        if not notes_to_archive:
            raise ValueError(
                f"No active notes found with batch ID {generation_batch_id} for this user"
            )

        # Archive the notes (soft delete)
        for note in notes_to_archive:
            note.is_archived = True

        await self.db.commit()

        logger.info(f"Archived {len(notes_to_archive)} notes")

        return len(notes_to_archive)
