"""Context assembly service for building LLM prompts from notes."""

import logging
from enum import Enum
from typing import Dict, Optional, Union

from ..models import Note, Page, Site

logger = logging.getLogger(__name__)


class ArtifactType(str, Enum):
    """Supported artifact generation types."""

    SUMMARY = "summary"
    ANALYSIS = "analysis"
    QUESTIONS = "questions"
    ACTION_ITEMS = "action_items"
    CODE_SNIPPET = "code_snippet"
    EXPLANATION = "explanation"
    OUTLINE = "outline"
    CUSTOM = "custom"


# Prompt templates for different artifact types
ARTIFACT_TEMPLATES = {
    ArtifactType.SUMMARY: """Generate a concise summary of the following content.

{context}

Requirements:
- Be clear and concise
- Capture key points
- Use bullet points if appropriate
{user_instructions}

Summary:""",
    ArtifactType.ANALYSIS: """Provide a detailed analysis of the following content.

{context}

Requirements:
- Identify key themes and patterns
- Provide insights and observations
- Consider implications and significance
{user_instructions}

Analysis:""",
    ArtifactType.QUESTIONS: """Generate thoughtful questions about the following content.

{context}

Requirements:
- Ask clarifying questions
- Explore deeper implications
- Identify areas for further investigation
{user_instructions}

Questions:""",
    ArtifactType.ACTION_ITEMS: """Extract actionable items from the following content.

{context}

Requirements:
- List specific, actionable tasks
- Include context for each item
- Prioritize if possible
{user_instructions}

Action Items:""",
    ArtifactType.CODE_SNIPPET: """Generate a code snippet based on the following content.

{context}

Requirements:
- Write clean, readable code
- Include comments where helpful
- Follow best practices
{user_instructions}

Code:""",
    ArtifactType.EXPLANATION: """Explain the following content in clear, simple terms.

{context}

Requirements:
- Use plain language
- Break down complex concepts
- Provide examples if helpful
{user_instructions}

Explanation:""",
    ArtifactType.OUTLINE: """Create a structured outline of the following content.

{context}

Requirements:
- Use hierarchical structure
- Include main topics and subtopics
- Be comprehensive yet concise
{user_instructions}

Outline:""",
    ArtifactType.CUSTOM: """{context}

{user_instructions}""",
}


class ContextBuilder:
    """
    Service for assembling context from notes, pages, and sites into LLM prompts.

    Builds structured prompts by combining:
    - Note content and metadata
    - Highlighted text from the page
    - Page section HTML context
    - Page title and summary
    - Site domain and context
    - User instructions and artifact type
    """

    def __init__(self, max_context_length: int = 32000):
        """
        Initialize context builder.

        Args:
            max_context_length: Maximum characters in assembled context
        """
        self.max_context_length = max_context_length

    def build_prompt(
        self,
        note: Note,
        artifact_type: ArtifactType,
        user_instructions: Optional[str] = None,
    ) -> str:
        """
        Build a complete prompt for artifact generation.

        Args:
            note: Note object with relationships loaded (page, page.site)
            artifact_type: Type of artifact to generate
            user_instructions: Optional additional instructions from user

        Returns:
            Formatted prompt string ready for LLM

        Raises:
            ValueError: If artifact_type is not supported
        """
        if artifact_type not in ARTIFACT_TEMPLATES:
            raise ValueError(
                f"Unsupported artifact type: {artifact_type}. "
                f"Supported types: {list(ARTIFACT_TEMPLATES.keys())}"
            )

        # For CUSTOM type, user_instructions is required
        if artifact_type == ArtifactType.CUSTOM and not user_instructions:
            raise ValueError(
                "Custom artifact type requires user_instructions (custom_prompt)"
            )

        # Assemble context from note and related objects
        context_parts = []

        # Add note content
        if note.content:
            context_parts.append(f"Note:\n{note.content}\n")

        # Add highlighted text if available
        if note.highlighted_text:
            context_parts.append(f"Highlighted Text:\n{note.highlighted_text}\n")

        # Add page section HTML if available (truncate if too long)
        if note.page_section_html:
            section_html = self._truncate_text(note.page_section_html, max_length=8000)
            context_parts.append(f"Page Context:\n{section_html}\n")

        # Add page metadata if available
        if hasattr(note, "page") and note.page:
            page_info = self._build_page_context(note.page)
            if page_info:
                context_parts.append(page_info)

        # Add site context if available
        if hasattr(note, "page") and note.page and hasattr(note.page, "site"):
            site_info = self._build_site_context(note.page.site)
            if site_info:
                context_parts.append(site_info)

        # Combine all context
        full_context = "\n".join(context_parts)

        # Truncate if necessary
        if len(full_context) > self.max_context_length:
            logger.warning(
                f"Context length {len(full_context)} exceeds maximum "
                f"{self.max_context_length}, truncating"
            )
            full_context = self._truncate_text(
                full_context, max_length=self.max_context_length
            )

        # Format user instructions
        instructions_text = ""
        if user_instructions:
            instructions_text = f"\n\nAdditional Instructions:\n{user_instructions}"

        # Get template and format
        template = ARTIFACT_TEMPLATES[artifact_type]
        prompt = template.format(
            context=full_context,
            user_instructions=instructions_text,
        )

        return prompt

    def _build_page_context(self, page: Page) -> str:
        """
        Build context string from page metadata.

        Args:
            page: Page object

        Returns:
            Formatted page context string
        """
        parts = []

        if page.title:
            parts.append(f"Page Title: {page.title}")

        if page.url:
            parts.append(f"Page URL: {page.url}")

        if page.page_summary:
            summary = self._truncate_text(page.page_summary, max_length=1000)
            parts.append(f"Page Summary: {summary}")

        if page.user_context:
            context = self._truncate_text(page.user_context, max_length=500)
            parts.append(f"User Context: {context}")

        return "\n".join(parts) + "\n" if parts else ""

    def _build_site_context(self, site: Site) -> str:
        """
        Build context string from site metadata.

        Args:
            site: Site object

        Returns:
            Formatted site context string
        """
        parts = []

        if site.domain:
            parts.append(f"Site Domain: {site.domain}")

        if site.user_context:
            context = self._truncate_text(site.user_context, max_length=500)
            parts.append(f"Site Context: {context}")

        return "\n".join(parts) + "\n" if parts else ""

    def _truncate_text(
        self, text: str, max_length: int, suffix: str = "... [truncated]"
    ) -> str:
        """
        Truncate text to maximum length, adding suffix.

        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add when truncated

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix

    def estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for a text string.

        Uses rough heuristic: 1 token ≈ 4 characters.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def build_context_summary(self, note: Note) -> Dict[str, Union[bool, int]]:
        """
        Build a summary of available context for a note.

        Useful for displaying to users before generation.

        Args:
            note: Note object with relationships loaded

        Returns:
            Dictionary with context information:
                - has_note_content: bool
                - has_highlighted_text: bool
                - has_page_section: bool
                - has_page_metadata: bool
                - has_site_context: bool
                - estimated_input_tokens: int
        """
        summary: Dict[str, Union[bool, int]] = {
            "has_note_content": bool(note.content),
            "has_highlighted_text": bool(note.highlighted_text),
            "has_page_section": bool(note.page_section_html),
            "has_page_metadata": False,
            "has_site_context": False,
            "estimated_input_tokens": 0,
        }

        # Check page metadata
        if hasattr(note, "page") and note.page:
            summary["has_page_metadata"] = bool(
                note.page.title or note.page.page_summary or note.page.user_context
            )

            # Check site context
            if hasattr(note.page, "site") and note.page.site:
                summary["has_site_context"] = bool(note.page.site.user_context)

        # Build a sample prompt to estimate tokens
        # Use SUMMARY type as it's representative
        try:
            sample_prompt = self.build_prompt(
                note=note,
                artifact_type=ArtifactType.SUMMARY,
                user_instructions=None,
            )
            summary["estimated_input_tokens"] = self.estimate_token_count(sample_prompt)
        except Exception as e:
            logger.warning(f"Error estimating tokens: {e}")
            summary["estimated_input_tokens"] = 0

        return summary
