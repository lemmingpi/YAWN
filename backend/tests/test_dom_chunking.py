"""Test the DOM chunking algorithm ported from JavaScript."""

import pytest
from app.services.dom_chunker import DOMChunker


class TestDOMChunking:

    def test_small_dom_single_chunk(self):
        """DOM < 40KB returns single chunk."""
        small_dom = "<body>" + "<p>Text</p>" * 100 + "</body>"  # ~2KB
        chunker = DOMChunker()
        chunks = chunker.chunk_html(small_dom)

        assert len(chunks) == 1
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["total_chunks"] == 1

    def test_large_dom_multiple_chunks(self):
        """Large DOM splits into multiple chunks."""
        # Create 200KB DOM
        large_dom = "<body>"
        for i in range(50):
            large_dom += f'<section id="s{i}">' + "<p>Text</p>" * 100 + "</section>"
        large_dom += "</body>"

        chunker = DOMChunker()
        chunks = chunker.chunk_html(large_dom, max_chars=40000)

        assert len(chunks) > 1
        assert all(len(c["chunk_dom"]) <= 40000 for c in chunks)

    def test_semantic_boundaries_respected(self):
        """Chunks split at semantic boundaries (sections/articles)."""
        dom_with_sections = """
        <body>
            <section id="intro">
                <p>Intro content</p>
            </section>
            <section id="main">
                <p>Main content</p>
            </section>
            <section id="conclusion">
                <p>Conclusion content</p>
            </section>
        </body>
        """

        chunker = DOMChunker()
        chunks = chunker.chunk_html(dom_with_sections, max_chars=500)

        # Each chunk should contain complete sections
        for chunk in chunks:
            assert "<section" in chunk["chunk_dom"]
            assert "</section>" in chunk["chunk_dom"]

    def test_chunk_metadata_correct(self):
        """Each chunk has correct metadata."""
        dom = "<body>"
        for i in range(10):
            dom += f'<section id="section-{i}">' + "<p>Content</p>" * 200 + "</section>"
        dom += "</body>"

        chunker = DOMChunker()
        chunks = chunker.chunk_html(dom, max_chars=10000)

        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i
            assert chunk["total_chunks"] == len(chunks)
            assert "parent_context" in chunk
            assert isinstance(chunk["parent_context"], dict)

    def test_parent_context_extraction(self):
        """Parent context is correctly extracted."""
        dom = """
        <html>
        <head><title>Test Page</title></head>
        <body class="article main-content" id="page-body">
            <main role="main">
                <p>Content</p>
            </main>
        </body>
        </html>
        """

        chunker = DOMChunker()
        chunks = chunker.chunk_html(dom)

        context = chunks[0]["parent_context"]
        assert "article" in context["body_classes"]
        assert "main-content" in context["body_classes"]
        assert context["body_id"] == "page-body"
        assert context["main_container"] == True
        assert context["document_title"] == "Test Page"

    def test_merging_small_chunks(self):
        """Small chunks are merged to avoid tiny fragments."""
        dom = "<body>"
        for i in range(20):
            # Create very small sections
            dom += f'<section id="s{i}"><p>Small</p></section>'
        dom += "</body>"

        chunker = DOMChunker(max_chars=1000, min_chars=500)
        chunks = chunker.chunk_html(dom)

        # Should merge small sections
        for chunk in chunks:
            # Each chunk should be at least min_chars unless it's the last one
            if chunk["chunk_index"] < len(chunks) - 1:
                assert len(chunk["chunk_dom"]) >= 500 or len(chunks) == 1

    def test_handles_deeply_nested_content(self):
        """Handles deeply nested HTML structures."""
        dom = """
        <body>
            <div class="wrapper">
                <div class="container">
                    <article>
                        <section>
                            <div class="content">
                                <p>Deeply nested content</p>
                            </div>
                        </section>
                    </article>
                </div>
            </div>
        </body>
        """

        chunker = DOMChunker()
        chunks = chunker.chunk_html(dom)

        assert len(chunks) == 1
        assert "Deeply nested content" in chunks[0]["chunk_dom"]

    def test_preserves_html_structure(self):
        """HTML structure is preserved in chunks."""
        dom = """
        <body>
            <section id="test">
                <h2>Title</h2>
                <p class="intro">Introduction paragraph</p>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                </ul>
            </section>
        </body>
        """

        chunker = DOMChunker()
        chunks = chunker.chunk_html(dom)

        chunk_dom = chunks[0]["chunk_dom"]
        assert "<h2>Title</h2>" in chunk_dom
        assert '<p class="intro">Introduction paragraph</p>' in chunk_dom
        assert "<ul>" in chunk_dom
        assert "<li>Item 1</li>" in chunk_dom
