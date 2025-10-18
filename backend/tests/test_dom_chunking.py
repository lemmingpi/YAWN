"""Test the DOM chunking algorithm ported from JavaScript."""

from app.services.dom_chunker import DOMChunker


class TestDOMChunking:

    def test_small_dom_single_chunk(self) -> None:
        """DOM < 40KB returns single chunk."""
        small_dom = "<body>" + "<p>Text</p>" * 100 + "</body>"  # ~2KB
        chunker = DOMChunker()
        chunks = chunker.chunk_html(small_dom)

        assert len(chunks) == 1
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["total_chunks"] == 1

    def test_large_dom_multiple_chunks(self) -> None:
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

    def test_semantic_boundaries_respected(self) -> None:
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

    def test_chunk_metadata_correct(self) -> None:
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

    def test_parent_context_extraction(self) -> None:
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
        assert context["main_container"] is True
        assert context["document_title"] == "Test Page"

    def test_merging_small_chunks(self) -> None:
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

    def test_handles_deeply_nested_content(self) -> None:
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

    def test_preserves_html_structure(self) -> None:
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

    def test_filters_navigation_elements(self) -> None:
        """Navigation elements are filtered out."""
        dom = """
        <body>
            <nav class="navbar">
                <a href="/">Home</a>
                <a href="/about">About</a>
            </nav>
            <section id="main-content">
                <h1>Article Title</h1>
                <p>Article content here.</p>
            </section>
            <aside class="sidebar">
                <ul>
                    <li>Link 1</li>
                    <li>Link 2</li>
                </ul>
            </aside>
        </body>
        """

        chunker = DOMChunker(filter_non_content=True)
        chunks = chunker.chunk_html(dom)

        chunk_dom = chunks[0]["chunk_dom"]
        # Navigation should be removed
        assert "<nav" not in chunk_dom
        assert "navbar" not in chunk_dom
        # Main content should be preserved
        assert "Article Title" in chunk_dom
        assert "Article content here" in chunk_dom
        # Sidebar should be removed
        assert "sidebar" not in chunk_dom

    def test_filters_header_and_footer(self) -> None:
        """Header and footer elements are filtered out."""
        dom = """
        <body>
            <header class="site-header">
                <h1>Site Name</h1>
                <div class="logo">Logo</div>
            </header>
            <main>
                <article>
                    <h2>Article Title</h2>
                    <p>Important article content.</p>
                </article>
            </main>
            <footer class="site-footer">
                <p>Copyright 2024</p>
                <div class="footer-links">Links</div>
            </footer>
        </body>
        """

        chunker = DOMChunker(filter_non_content=True)
        chunks = chunker.chunk_html(dom)

        chunk_dom = chunks[0]["chunk_dom"]
        # Header should be removed
        assert "<header" not in chunk_dom
        assert "Site Name" not in chunk_dom
        # Footer should be removed
        assert "<footer" not in chunk_dom
        assert "Copyright 2024" not in chunk_dom
        # Article content should be preserved
        assert "Article Title" in chunk_dom
        assert "Important article content" in chunk_dom

    def test_filters_advertisements(self) -> None:
        """Advertisement elements are filtered out."""
        dom = """
        <body>
            <div class="ad-banner">
                <img src="ad.jpg" />
            </div>
            <section class="content">
                <p>Real content here.</p>
            </section>
            <div class="advertisement">
                <p>Buy this product!</p>
            </div>
            <div data-ad-slot="12345">
                <p>Sponsored content</p>
            </div>
        </body>
        """

        chunker = DOMChunker(filter_non_content=True)
        chunks = chunker.chunk_html(dom)

        chunk_dom = chunks[0]["chunk_dom"]
        # Ads should be removed
        assert "ad-banner" not in chunk_dom
        assert "advertisement" not in chunk_dom
        assert "Buy this product" not in chunk_dom
        assert "Sponsored content" not in chunk_dom
        # Real content should be preserved
        assert "Real content here" in chunk_dom

    def test_filters_cookie_and_modal_elements(self) -> None:
        """Cookie banners and modals are filtered out."""
        dom = """
        <body>
            <div class="cookie-banner">
                <p>We use cookies!</p>
            </div>
            <div class="modal hidden">
                <p>Sign up now!</p>
            </div>
            <article>
                <h1>Article Title</h1>
                <p>Article content.</p>
            </article>
            <div class="gdpr-banner">
                <p>Privacy notice</p>
            </div>
        </body>
        """

        chunker = DOMChunker(filter_non_content=True)
        chunks = chunker.chunk_html(dom)

        chunk_dom = chunks[0]["chunk_dom"]
        # Cookie banner should be removed
        assert "cookie-banner" not in chunk_dom
        assert "We use cookies" not in chunk_dom
        # Modal should be removed
        assert "modal" not in chunk_dom
        assert "Sign up now" not in chunk_dom
        # GDPR banner should be removed
        assert "gdpr-banner" not in chunk_dom
        assert "Privacy notice" not in chunk_dom
        # Article should be preserved
        assert "Article Title" in chunk_dom
        assert "Article content" in chunk_dom

    def test_filtering_can_be_disabled(self) -> None:
        """Filtering can be toggled off."""
        dom = """
        <body>
            <nav class="navbar">
                <a href="/">Home</a>
            </nav>
            <section>
                <p>Content</p>
            </section>
        </body>
        """

        # With filtering disabled
        chunker = DOMChunker(filter_non_content=False)
        chunks = chunker.chunk_html(dom)
        chunk_dom = chunks[0]["chunk_dom"]

        # Navigation should be present
        assert "<nav" in chunk_dom or "navbar" in chunk_dom

    def test_filter_stats_in_parent_context(self) -> None:
        """Filter statistics are included in parent context."""
        dom = """
        <body>
            <nav>Nav</nav>
            <header>Header</header>
            <footer>Footer</footer>
            <div class="ad">Ad</div>
            <section>
                <p>Content</p>
            </section>
        </body>
        """

        chunker = DOMChunker(filter_non_content=True)
        chunks = chunker.chunk_html(dom)

        # Large DOM that requires chunking to get filter stats
        large_dom = "<body>"
        large_dom += "<nav>Nav</nav>"
        large_dom += "<header>Header</header>"
        for i in range(50):
            large_dom += f'<section id="s{i}">' + "<p>Text</p>" * 100 + "</section>"
        large_dom += "<footer>Footer</footer>"
        large_dom += "</body>"

        chunks = chunker.chunk_html(large_dom, max_chars=40000)

        # Check that filter stats are present
        parent_context = chunks[0]["parent_context"]
        assert "filter_stats" in parent_context
        stats = parent_context["filter_stats"]
        assert stats["total"] > 0
        assert stats["nav"] >= 1
        assert stats["header"] >= 1
        assert stats["footer"] >= 1

    def test_preserves_main_content_with_filtering(self) -> None:
        """Real-world HTML with filtering preserves main content."""
        dom = """
        <html>
        <head><title>News Article</title></head>
        <body>
            <header class="site-header">
                <nav class="main-nav">
                    <a href="/">Home</a>
                    <a href="/news">News</a>
                </nav>
            </header>
            <div class="cookie-notice">Accept cookies?</div>
            <main>
                <article>
                    <h1>Breaking News: Important Event</h1>
                    <p class="byline">By John Doe</p>
                    <section class="article-content">
                        <p>This is the first paragraph of important news.</p>
                        <p>This is the second paragraph with more details.</p>
                    </section>
                </article>
                <aside class="related-articles">
                    <h3>Related</h3>
                    <ul>
                        <li>Link 1</li>
                    </ul>
                </aside>
            </main>
            <div class="ad-container">
                <div class="advertisement">Buy now!</div>
            </div>
            <footer class="site-footer">
                <p>Copyright</p>
            </footer>
        </body>
        </html>
        """

        chunker = DOMChunker(filter_non_content=True)
        chunks = chunker.chunk_html(dom)

        chunk_dom = chunks[0]["chunk_dom"]

        # Main article content should be preserved
        assert "Breaking News: Important Event" in chunk_dom
        assert "By John Doe" in chunk_dom
        assert "first paragraph of important news" in chunk_dom
        assert "second paragraph with more details" in chunk_dom

        # Non-content should be removed
        assert "site-header" not in chunk_dom
        assert "main-nav" not in chunk_dom
        assert "cookie-notice" not in chunk_dom
        assert "Accept cookies" not in chunk_dom
        assert "ad-container" not in chunk_dom
        assert "Buy now" not in chunk_dom
        assert "site-footer" not in chunk_dom
        assert "Copyright" not in chunk_dom.split("Breaking News")[0]  # Not in header
