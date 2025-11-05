"""Tests for context builder service."""

from unittest.mock import MagicMock

import pytest

from backend.app.services.context_builder import (
    ARTIFACT_TEMPLATES,
    ArtifactType,
    ContextBuilder,
)


@pytest.fixture
def context_builder():
    """Create a context builder instance."""
    return ContextBuilder(max_context_length=32000)


@pytest.fixture
def mock_note():
    """Create a mock note object."""
    note = MagicMock()
    note.id = 1
    note.content = "This is a test note about Python programming."
    note.highlighted_text = "Python programming"
    note.page_section_html = "<p>Learn Python basics</p>"
    return note


@pytest.fixture
def mock_page():
    """Create a mock page object."""
    page = MagicMock()
    page.id = 1
    page.title = "Python Tutorial"
    page.url = "https://example.com/python"
    page.page_summary = "A comprehensive Python tutorial"
    page.user_context = "Learning Python for data science"
    return page


@pytest.fixture
def mock_site():
    """Create a mock site object."""
    site = MagicMock()
    site.id = 1
    site.domain = "example.com"
    site.user_context = "Educational website for programming"
    return site


class TestContextBuilder:
    """Tests for ContextBuilder class."""

    def test_init(self):
        """Test initialization."""
        builder = ContextBuilder(max_context_length=10000)
        assert builder.max_context_length == 10000

    def test_default_max_length(self, context_builder):
        """Test default max context length."""
        assert context_builder.max_context_length == 32000


class TestBuildPrompt:
    """Tests for build_prompt method."""

    def test_build_prompt_basic(self, context_builder, mock_note):
        """Test building a basic prompt."""
        prompt = context_builder.build_prompt(
            note=mock_note,
            artifact_type=ArtifactType.SUMMARY,
        )

        assert "This is a test note about Python programming" in prompt
        assert "Python programming" in prompt
        assert "Learn Python basics" in prompt
        assert "Summary:" in prompt

    def test_build_prompt_with_instructions(self, context_builder, mock_note):
        """Test building prompt with user instructions."""
        prompt = context_builder.build_prompt(
            note=mock_note,
            artifact_type=ArtifactType.SUMMARY,
            user_instructions="Focus on beginner concepts",
        )

        assert "Focus on beginner concepts" in prompt
        assert "Additional Instructions:" in prompt

    def test_build_prompt_with_page_context(
        self, context_builder, mock_note, mock_page
    ):
        """Test building prompt with page context."""
        mock_note.page = mock_page

        prompt = context_builder.build_prompt(
            note=mock_note,
            artifact_type=ArtifactType.SUMMARY,
        )

        assert "Python Tutorial" in prompt
        assert "https://example.com/python" in prompt
        assert "A comprehensive Python tutorial" in prompt

    def test_build_prompt_with_site_context(
        self, context_builder, mock_note, mock_page, mock_site
    ):
        """Test building prompt with site context."""
        mock_page.site = mock_site
        mock_note.page = mock_page

        prompt = context_builder.build_prompt(
            note=mock_note,
            artifact_type=ArtifactType.SUMMARY,
        )

        assert "example.com" in prompt
        assert "Educational website for programming" in prompt

    def test_build_prompt_unsupported_type(self, context_builder, mock_note):
        """Test error with unsupported artifact type."""
        with pytest.raises(ValueError, match="Unsupported artifact type"):
            context_builder.build_prompt(
                note=mock_note,
                artifact_type="invalid_type",
            )

    def test_build_prompt_analysis(self, context_builder, mock_note):
        """Test building prompt for analysis artifact."""
        prompt = context_builder.build_prompt(
            note=mock_note,
            artifact_type=ArtifactType.ANALYSIS,
            user_instructions="My Usr Context",
        )

        assert mock_note.content in prompt
        assert "My Usr Context" in prompt

    def test_build_prompt_questions(self, context_builder, mock_note):
        """Test building prompt for questions artifact."""
        prompt = context_builder.build_prompt(
            note=mock_note,
            artifact_type=ArtifactType.QUESTIONS,
        )

        assert "Questions:" in prompt
        assert "thoughtful questions" in prompt

    def test_build_prompt_action_items(self, context_builder, mock_note):
        """Test building prompt for action items artifact."""
        prompt = context_builder.build_prompt(
            note=mock_note,
            artifact_type=ArtifactType.ACTION_ITEMS,
            user_instructions="My Usr Context",
        )

        assert mock_note.content in prompt
        assert "My Usr Context" in prompt

    def test_build_prompt_code_snippet(self, context_builder, mock_note):
        """Test building prompt for code snippet artifact."""
        prompt = context_builder.build_prompt(
            note=mock_note,
            artifact_type=ArtifactType.CODE_SNIPPET,
        )

        assert "Code:" in prompt
        assert "code snippet" in prompt

    def test_build_prompt_explanation(self, context_builder, mock_note):
        """Test building prompt for explanation artifact."""
        prompt = context_builder.build_prompt(
            note=mock_note,
            artifact_type=ArtifactType.EXPLANATION,
        )

        assert "Explanation:" in prompt
        assert "Explain" in prompt

    def test_build_prompt_outline(self, context_builder, mock_note):
        """Test building prompt for outline artifact."""
        prompt = context_builder.build_prompt(
            note=mock_note,
            artifact_type=ArtifactType.OUTLINE,
        )

        assert "Outline:" in prompt
        assert "structured outline" in prompt

    def test_build_prompt_truncates_long_context(self, context_builder, mock_note):
        """Test that very long context is truncated."""
        # Create a note with very long content
        mock_note.page_section_html = "x" * 50000

        builder = ContextBuilder(max_context_length=1000)
        prompt = builder.build_prompt(
            note=mock_note,
            artifact_type=ArtifactType.SUMMARY,
        )

        assert len(prompt) <= 2000  # Allow some overhead for template
        assert "[truncated]" in prompt

    def test_build_prompt_with_minimal_note(self, context_builder):
        """Test with minimal note (only content)."""
        minimal_note = MagicMock()
        minimal_note.content = "Simple note"
        minimal_note.highlighted_text = None
        minimal_note.page_section_html = None

        prompt = context_builder.build_prompt(
            note=minimal_note,
            artifact_type=ArtifactType.SUMMARY,
        )

        assert "Simple note" in prompt
        assert "Summary:" in prompt


class TestBuildPageContext:
    """Tests for _build_page_context method."""

    def test_build_page_context_full(self, context_builder, mock_page):
        """Test building full page context."""
        context = context_builder._build_page_context(mock_page)

        assert "Python Tutorial" in context
        assert "https://example.com/python" in context
        assert "A comprehensive Python tutorial" in context
        assert "Learning Python for data science" in context

    def test_build_page_context_minimal(self, context_builder):
        """Test building minimal page context."""
        page = MagicMock()
        page.title = "Test Page"
        page.url = None
        page.page_summary = None
        page.user_context = None

        context = context_builder._build_page_context(page)

        assert "Test Page" in context
        assert context.strip()  # Should not be empty

    def test_build_page_context_empty(self, context_builder):
        """Test building context for page with no data."""
        page = MagicMock()
        page.title = None
        page.url = None
        page.page_summary = None
        page.user_context = None

        context = context_builder._build_page_context(page)

        assert context == ""


class TestBuildSiteContext:
    """Tests for _build_site_context method."""

    def test_build_site_context_full(self, context_builder, mock_site):
        """Test building full site context."""
        context = context_builder._build_site_context(mock_site)

        assert "example.com" in context
        assert "Educational website for programming" in context

    def test_build_site_context_minimal(self, context_builder):
        """Test building minimal site context."""
        site = MagicMock()
        site.domain = "test.com"
        site.user_context = None

        context = context_builder._build_site_context(site)

        assert "test.com" in context

    def test_build_site_context_empty(self, context_builder):
        """Test building context for site with no data."""
        site = MagicMock()
        site.domain = None
        site.user_context = None

        context = context_builder._build_site_context(site)

        assert context == ""


class TestTruncateText:
    """Tests for _truncate_text method."""

    def test_no_truncation_needed(self, context_builder):
        """Test when text is within limit."""
        text = "Short text"
        result = context_builder._truncate_text(text, max_length=100)
        assert result == text

    def test_truncation_applied(self, context_builder):
        """Test when text exceeds limit."""
        text = "x" * 1000
        result = context_builder._truncate_text(text, max_length=100)

        assert len(result) == 100
        assert result.endswith("... [truncated]")

    def test_custom_suffix(self, context_builder):
        """Test truncation with custom suffix."""
        text = "x" * 1000
        result = context_builder._truncate_text(text, max_length=100, suffix="...")

        assert len(result) == 100
        assert result.endswith("...")


class TestEstimateTokenCount:
    """Tests for estimate_token_count method."""

    def test_estimate_tokens(self, context_builder):
        """Test token estimation."""
        text = "x" * 400  # Should be ~100 tokens
        tokens = context_builder.estimate_token_count(text)
        assert tokens == 100

    def test_estimate_tokens_short(self, context_builder):
        """Test token estimation for short text."""
        text = "Hello world"
        tokens = context_builder.estimate_token_count(text)
        assert tokens > 0

    def test_estimate_tokens_empty(self, context_builder):
        """Test token estimation for empty text."""
        tokens = context_builder.estimate_token_count("")
        assert tokens == 0


class TestBuildContextSummary:
    """Tests for build_context_summary method."""

    def test_summary_full_context(
        self, context_builder, mock_note, mock_page, mock_site
    ):
        """Test summary with full context available."""
        mock_page.site = mock_site
        mock_note.page = mock_page

        summary = context_builder.build_context_summary(mock_note)

        assert summary["has_note_content"] is True
        assert summary["has_highlighted_text"] is True
        assert summary["has_page_section"] is True
        assert summary["has_page_metadata"] is True
        assert summary["has_site_context"] is True
        assert summary["estimated_input_tokens"] > 0

    def test_summary_minimal_context(self, context_builder):
        """Test summary with minimal context."""
        note = MagicMock()
        note.content = "Test"
        note.highlighted_text = None
        note.page_section_html = None

        summary = context_builder.build_context_summary(note)

        assert summary["has_note_content"] is True
        assert summary["has_highlighted_text"] is False
        assert summary["has_page_section"] is False

    def test_summary_no_context(self, context_builder):
        """Test summary with no context."""
        note = MagicMock()
        note.content = None
        note.highlighted_text = None
        note.page_section_html = None

        summary = context_builder.build_context_summary(note)

        assert summary["has_note_content"] is False
        assert summary["has_highlighted_text"] is False
        assert summary["has_page_section"] is False


class TestArtifactTemplates:
    """Tests for artifact templates."""

    def test_all_templates_exist(self):
        """Test that templates exist for all artifact types."""
        # Visualization types use Jinja2 templates, not ARTIFACT_TEMPLATES
        visualization_types = {
            ArtifactType.SCENE_ILLUSTRATION,
            ArtifactType.DATA_CHART,
            ArtifactType.SCIENTIFIC_VISUALIZATION,
        }

        for artifact_type in ArtifactType:
            if artifact_type not in visualization_types:
                assert artifact_type in ARTIFACT_TEMPLATES

    def test_templates_have_placeholders(self):
        """Test that templates have required placeholders."""
        for template in ARTIFACT_TEMPLATES.values():
            assert "{context}" in template
            assert "{user_instructions}" in template

    def test_templates_are_strings(self):
        """Test that all templates are strings."""
        for template in ARTIFACT_TEMPLATES.values():
            assert isinstance(template, str)
            assert len(template) > 0
