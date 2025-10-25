"""Service for generating AI-powered page context summaries."""

import logging
import time
from pathlib import Path
from typing import Dict, Optional

import jinja2
from bs4 import BeautifulSoup
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

    def _clean_dom(self, html: str) -> BeautifulSoup:
        """
        Clean the DOM by removing unnecessary elements.

        Args:
            html: Raw HTML string

        Returns:
            Cleaned BeautifulSoup object
        """
        soup = BeautifulSoup(html, "lxml")

        # Remove script, style, and other non-content elements
        for tag in soup(
            [
                "script",
                "style",
                "meta",
                "link",
                "noscript",
                "iframe",
                "nav",
                "header",
                "footer",
            ]
        ):
            tag.decompose()

        return soup

    def _find_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Find the main content area of the page.

        Args:
            soup: BeautifulSoup object

        Returns:
            Main content section or full body
        """
        # Try to find main content area
        main_content = soup.find(["main", "article"]) or soup.find(
            attrs={"role": "main"}
        )

        if not main_content:
            # If no main content found, use body
            main_content = soup.body if soup.body else soup

        return main_content

    def _extract_text_from_dom(self, html: str, max_tokens: int = 30000) -> str:
        """
        Extract and clean text from HTML DOM.

        Args:
            html: Raw HTML string
            max_tokens: Maximum tokens to extract (default 30000)

        Returns:
            Extracted text content
        """
        # Clean the DOM
        soup = self._clean_dom(html)

        # Find main content
        main_content = self._find_main_content(soup)

        # Extract text with explicit type annotation for mypy
        text: str = main_content.get_text(separator="\n", strip=True)

        # Estimate tokens (1 token ≈ 4 characters)
        estimated_tokens = len(text) / 4

        # If within limits, return as is
        if estimated_tokens <= max_tokens:
            return text

        # Calculate target character count (reserve 20% for prompt overhead)
        usable_tokens = max_tokens * 0.8
        target_chars = int(usable_tokens * 4)

        # Try to break at sentence boundaries
        if len(text) > target_chars:
            # Find last period before target
            last_period = text.rfind(". ", 0, target_chars)
            if (
                last_period > target_chars * 0.5
            ):  # Only use if we're not cutting too much
                text = text[: last_period + 1]
            else:
                # Just cut at target
                text = text[:target_chars]

        logger.info(
            f"Extracted {len(text)} characters from DOM (approx {len(text) / 4:.0f} tokens)"
        )
        return text

    async def _build_context_prompt(
        self,
        page: Page,
        notes: list[Note],
        custom_instructions: Optional[str] = None,
        page_source: Optional[str] = None,
        page_dom: Optional[str] = None,
    ) -> str:
        """
        Build the prompt for page context generation.

        Args:
            page: Page object with metadata
            notes: List of notes on this page
            custom_instructions: Optional user-provided instructions
            page_source: Optional alternate page source (for paywalled content)
            page_dom: Optional page DOM for content extraction

        Returns:
            Formatted prompt string ready for LLM
        """
        # Extract content from DOM if provided
        extracted_content = None
        if page_dom:
            logger.info(
                f"Attempting to extract content from page_dom ({len(page_dom)} chars)"
            )
            try:
                extracted_content = self._extract_text_from_dom(page_dom)
                logger.info(
                    f"Successfully extracted {len(extracted_content)} characters from DOM"
                )
            except Exception as e:
                logger.error(f"Failed to extract content from DOM: {e}", exc_info=True)
                # Fall back to page_source if available
                extracted_content = None
        else:
            logger.info("No page_dom provided, skipping DOM extraction")

        # Use extracted content or fall back to page_source
        content_to_use = extracted_content or page_source

        if content_to_use:
            logger.info(f"Using content for prompt: {len(content_to_use)} characters")
        else:
            logger.info("No content available (neither extracted nor provided)")

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
            page_source=content_to_use,  # Use extracted content or alternate source
        )

        return prompt

    async def generate_page_context(
        self,
        page_id: int,
        llm_provider_id: int,
        custom_instructions: Optional[str] = None,
        page_source: Optional[str] = None,
        page_dom: Optional[str] = None,
    ) -> Dict:
        """
        Generate AI-powered context summary for a page.

        Args:
            page_id: ID of page to generate context for
            llm_provider_id: LLM provider to use (currently unused, uses Gemini)
            custom_instructions: Optional user instructions for customization
            page_source: Optional alternate page source (for paywalled content)
            page_dom: Optional page DOM for content extraction

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

        # Build prompt with DOM support
        prompt = await self._build_context_prompt(
            page, notes, custom_instructions, page_source, page_dom
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
        page_dom: Optional[str] = None,
    ) -> str:
        """
        Preview the prompt that would be sent to the LLM without actually calling it.

        This method uses the same _build_context_prompt function as generate_page_context,
        ensuring the preview exactly matches what will be sent to the LLM.

        Args:
            page_id: ID of page to preview prompt for
            custom_instructions: Optional user instructions for customization
            page_source: Optional alternate page source (for paywalled content)
            page_dom: Optional page DOM for content extraction

        Returns:
            The fully rendered prompt string

        Raises:
            ValueError: If page not found
        """
        logger.info(f"Previewing prompt for page_id={page_id}")
        logger.info(
            f"Input lengths - page_dom: {len(page_dom) if page_dom else 0}, "
            f"page_source: {len(page_source) if page_source else 0}, "
            f"custom_instructions: {len(custom_instructions) if custom_instructions else 0}"
        )

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
            page, notes, custom_instructions, page_source, page_dom
        )

        logger.info(f"Preview generated: {len(prompt)} characters")
        logger.info(prompt)
        return prompt
