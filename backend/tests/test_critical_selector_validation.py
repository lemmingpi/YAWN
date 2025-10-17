"""
Critical tests proving CSS selector validation issue with chunked DOM.
These tests MUST pass before the implementation is complete.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from app.services.auto_note_service import AutoNoteService
from app.services.selector_validator import SelectorValidator


class TestCriticalSelectorValidation:
    """Prove that selector validation must use full DOM, not chunk DOM."""

    @pytest.fixture
    def full_dom(self):
        """Complete DOM as it exists on the page."""
        return """
        <html>
        <body class="article-page">
            <header id="site-header">
                <h1>Site Title</h1>
            </header>
            <main>
                <article class="content">
                    <section id="intro" class="section-1">
                        <h2>Introduction</h2>
                        <p id="p1">First paragraph in intro.</p>
                        <p id="p2">Second paragraph.</p>
                    </section>
                    <section id="main" class="section-2">
                        <h2>Main Content</h2>
                        <p id="p3">Target paragraph to annotate.</p>
                        <p id="p4">Another paragraph.</p>
                    </section>
                    <section id="conclusion" class="section-3">
                        <h2>Conclusion</h2>
                        <p id="p5">Final thoughts.</p>
                    </section>
                </article>
            </main>
        </body>
        </html>
        """

    @pytest.fixture
    def chunk_2_dom(self):
        """Chunk 2: Just the main section (missing all parent context)."""
        return """
        <section id="main" class="section-2">
            <h2>Main Content</h2>
            <p id="p3">Target paragraph to annotate.</p>
            <p id="p4">Another paragraph.</p>
        </section>
        """

    def test_problem_selectors_fail_with_chunk_dom(self, chunk_2_dom):
        """
        CURRENT STATE (FAILS): Selectors fail validation with chunk DOM only.
        This test documents the problem we're fixing.
        """
        selectors_from_llm = [
            "body > main > article > section:nth-child(2) > p#p3",
            "article.content > section#main > p:first-of-type",
            "main > article > section:nth-child(2) > p:nth-child(2)",
        ]

        validator = SelectorValidator()
        for selector in selectors_from_llm:
            is_valid = validator.validate_selector(chunk_2_dom, selector)[0]
            assert is_valid == False, f"Selector '{selector}' fails with chunk DOM"

    def test_solution_selectors_work_with_full_dom(self, full_dom):
        """
        DESIRED STATE (MUST PASS): Same selectors work with full DOM.
        This is what we're implementing.
        """
        selectors_from_llm = [
            "body > main > article > section:nth-child(2) > p#p3",
            "article.content > section#main > p:first-of-type",
            "main > article > section:nth-child(2) > p:nth-child(2)",
        ]

        validator = SelectorValidator()
        for selector in selectors_from_llm:
            is_valid, match_count, _ = validator.validate_selector(full_dom, selector)
            assert is_valid == True, f"Selector '{selector}' must work with full DOM"
            assert match_count > 0, f"Selector '{selector}' must find matches"

    @pytest.mark.asyncio
    async def test_service_validates_with_full_dom(self, full_dom, chunk_2_dom):
        """
        Integration test: Service method uses full DOM for validation.
        """
        mock_db = AsyncMock()
        service = AutoNoteService(mock_db)

        # Mock the new method we'll implement
        with patch.object(service, "process_chunk_with_full_dom") as mock_process:
            mock_process.return_value = {
                "validation_success": True,
                "notes": [
                    {
                        "content": "Test note",
                        "css_selector": "section#main > p#p3",
                        "highlighted_text": "Target paragraph to annotate.",
                    }
                ],
            }

            # This is the NEW method we'll implement
            result = await service.process_chunk_with_full_dom(
                chunk_dom=chunk_2_dom,  # For LLM prompt
                full_dom=full_dom,  # For validation (KEY!)
                chunk_index=1,
                total_chunks=3,
            )

            assert result["validation_success"] == True
            assert len(result["notes"]) > 0
