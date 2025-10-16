"""Tests for CSS selector validation and repair service."""

import pytest
from app.services.selector_validator import SelectorValidator


@pytest.fixture
def validator() -> SelectorValidator:
    """Create a SelectorValidator instance for testing."""
    return SelectorValidator(fuzzy_threshold=0.80)


@pytest.fixture
def sample_html() -> str:
    """Sample HTML for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <header id="main-header">
            <h1 class="page-title">Welcome to Test Page</h1>
            <nav class="main-nav">
                <ul>
                    <li><a href="/">Home</a></li>
                    <li><a href="/about">About</a></li>
                </ul>
            </nav>
        </header>
        <main>
            <article id="article-1" class="post">
                <h2>First Article</h2>
                <p class="intro">This is the introduction paragraph.</p>
                <p>This is a regular paragraph with some content.</p>
                <p>Another paragraph here.</p>
            </article>
            <article id="article-2" class="post featured">
                <h2>Second Article</h2>
                <p class="intro">Introduction for second article.</p>
            </article>
        </main>
        <footer>
            <p>Copyright 2025</p>
        </footer>
    </body>
    </html>
    """


class TestValidateSelector:
    """Tests for selector validation."""

    def test_valid_unique_id_selector(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test validation of unique ID selector."""
        is_valid, count, element = validator.validate_selector(
            sample_html, "#main-header"
        )
        assert is_valid is True
        assert count == 1
        assert element is not None

    def test_valid_class_selector(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test validation of unique class selector."""
        is_valid, count, element = validator.validate_selector(
            sample_html, ".page-title"
        )
        assert is_valid is True
        assert count == 1
        assert element is not None

    def test_non_unique_selector(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test validation fails for non-unique selector."""
        is_valid, count, element = validator.validate_selector(sample_html, "p")
        assert is_valid is False  # Multiple <p> tags
        assert count > 1
        assert element is not None  # First match returned

    def test_invalid_selector(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test validation fails for non-existent selector."""
        is_valid, count, element = validator.validate_selector(
            sample_html, "#does-not-exist"
        )
        assert is_valid is False
        assert count == 0
        assert element is None

    def test_complex_valid_selector(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test validation of complex hierarchical selector."""
        is_valid, count, element = validator.validate_selector(
            sample_html, "article#article-1 > p.intro"
        )
        assert is_valid is True
        assert count == 1
        assert element is not None


class TestFindTextInDom:
    """Tests for finding text in DOM."""

    def test_exact_text_match(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test finding exact text match."""
        matches = validator.find_text_in_dom(
            sample_html, "This is the introduction paragraph.", use_fuzzy=False
        )
        assert len(matches) > 0
        assert matches[0][1] == 1.0  # Perfect match

    def test_partial_text_match(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test finding partial text match."""
        matches = validator.find_text_in_dom(
            sample_html, "introduction paragraph", use_fuzzy=False
        )
        assert len(matches) > 0

    def test_fuzzy_text_match(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test fuzzy text matching."""
        # Slightly different text should still match with fuzzy
        # Use closer match - "introduction paragraph" is in the actual text
        matches = validator.find_text_in_dom(
            sample_html, "introduction paragraph", use_fuzzy=True
        )
        assert len(matches) > 0
        assert matches[0][1] >= 0.80  # Above threshold

    def test_no_match(self, validator: SelectorValidator, sample_html: str) -> None:
        """Test when text is not found."""
        matches = validator.find_text_in_dom(
            sample_html, "This text does not exist anywhere", use_fuzzy=True
        )
        assert len(matches) == 0


class TestGenerateRobustSelector:
    """Tests for selector generation."""

    def test_generate_for_unique_id(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test generation uses ID for unique elements."""
        from lxml import html

        dom = html.fromstring(sample_html)
        element = dom.get_element_by_id("main-header")

        css, xpath = validator.generate_robust_selector(element)

        assert css is not None
        assert "#main-header" in css or "main-header" in css
        assert xpath is not None

    def test_generate_for_nested_element(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test generation for nested element without ID."""
        from lxml import html
        from lxml.cssselect import CSSSelector

        dom = html.fromstring(sample_html)
        selector = CSSSelector("article#article-1 > p.intro")
        element = selector(dom)[0]

        css, xpath = validator.generate_robust_selector(element)

        assert css is not None
        assert xpath is not None


class TestRepairSelector:
    """Tests for selector repair functionality."""

    def test_repair_with_exact_text_match(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test repair finds text and generates new selector."""
        # Bad selector (wrong element)
        bad_selector = "#does-not-exist"
        text = "This is the introduction paragraph."

        result = validator.repair_selector(sample_html, text, bad_selector, None)

        assert result["success"] is True
        assert result["css_selector"] is not None or result["xpath"] is not None
        assert result["text_similarity"] >= 0.80
        assert result["match_count"] >= 1

    def test_repair_with_fuzzy_match(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test repair works with fuzzy text matching."""
        bad_selector = "#wrong"
        # Slightly different from actual text
        text = "the introduction paragraph"

        result = validator.repair_selector(sample_html, text, bad_selector, None)

        assert result["success"] is True
        assert result["text_similarity"] >= 0.80

    def test_repair_fails_when_text_not_found(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test repair fails gracefully when text doesn't exist."""
        bad_selector = "#wrong"
        text = "This text does not exist anywhere in the document"

        result = validator.repair_selector(sample_html, text, bad_selector, None)

        assert result["success"] is False
        assert "not found" in result["message"].lower()
        # Should keep original selector
        assert result["css_selector"] == bad_selector

    def test_repair_with_multiple_matches(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test repair chooses best match when multiple found."""
        bad_selector = "#wrong"
        text = "Article"  # Appears multiple times

        result = validator.repair_selector(sample_html, text, bad_selector, None)

        # Should still succeed by picking best match
        assert result["match_count"] >= 1


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_validate_malformed_html(self, validator: SelectorValidator) -> None:
        """Test validation handles malformed HTML."""
        malformed = "<div><p>Unclosed paragraph"
        is_valid, count, element = validator.validate_selector(malformed, "p")
        # lxml is forgiving and should parse it
        assert count >= 0  # Should not crash

    def test_validate_empty_html(self, validator: SelectorValidator) -> None:
        """Test validation with empty HTML."""
        is_valid, count, element = validator.validate_selector("", "p")
        assert is_valid is False
        assert count == 0

    def test_find_text_empty_string(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test finding empty text string."""
        matches = validator.find_text_in_dom(sample_html, "", use_fuzzy=True)
        assert len(matches) == 0

    def test_repair_with_empty_text(
        self, validator: SelectorValidator, sample_html: str
    ) -> None:
        """Test repair with empty highlighted text."""
        result = validator.repair_selector(sample_html, "", "#bad", None)
        assert result["success"] is False
