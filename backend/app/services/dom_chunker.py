"""
DOM chunking service ported from JavaScript.
Splits large HTML into semantic chunks for LLM processing.
"""

import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup


class DOMChunker:
    """Handles semantic chunking of HTML content."""

    # Semantic boundaries in priority order
    BOUNDARY_SELECTORS = [
        "section[id], section[class]",
        "article",
        "div.content, div.main, div.article",
        "div[id]",
        "h1, h2",
    ]

    # Elements to exclude from chunking (non-content elements)
    EXCLUSION_PATTERNS = {
        # Navigation elements
        "nav_elements": ["nav", 'aside[role="navigation"]', 'div[role="navigation"]'],
        "nav_classes": [
            "navbar",
            "nav-menu",
            "navigation",
            "sidebar",
            "menu",
            "nav-bar",
            "site-nav",
            "main-nav",
        ],
        "nav_ids": ["nav", "navigation", "menu", "sidebar"],
        # Header elements
        "header_elements": ["header", 'div[role="banner"]'],
        "header_classes": [
            "header",
            "site-header",
            "page-header",
            "masthead",
            "top-bar",
        ],
        "header_ids": ["header", "site-header", "masthead"],
        # Footer elements
        "footer_elements": ["footer", 'div[role="contentinfo"]'],
        "footer_classes": ["footer", "site-footer", "page-footer", "bottom"],
        "footer_ids": ["footer", "site-footer"],
        # Advertisement elements
        "ad_classes": [
            "ad",
            "ads",
            "advertisement",
            "adsense",
            "adsbygoogle",
            "ad-banner",
            "ad-container",
            "sponsored",
            "promo",
            "promotion",
        ],
        "ad_ids": ["ad", "ads", "advertisement"],
        # Cookie/GDPR banners
        "cookie_classes": [
            "cookie-banner",
            "cookie-notice",
            "gdpr-banner",
            "privacy-notice",
            "consent-banner",
        ],
        # Social media widgets
        "social_classes": [
            "social-share",
            "social-links",
            "share-buttons",
            "fb-like",
            "twitter-follow",
            "social-widget",
        ],
        # Modals and popups
        "modal_classes": ["modal", "popup", "overlay", "dialog", "lightbox"],
    }

    def __init__(
        self,
        max_chars: int = 40000,
        min_chars: int = 10000,
        filter_non_content: bool = True,
    ):
        """
        Initialize chunker with size constraints.

        Args:
            max_chars: Maximum characters per chunk (~10k tokens)
            min_chars: Minimum characters to avoid tiny chunks
            filter_non_content: Whether to filter out non-content elements
        """
        self.max_chars = max_chars
        self.min_chars = min_chars
        self.filter_non_content = filter_non_content

    def _should_exclude_element(self, element: Any) -> bool:
        """
        Check if an element should be excluded based on exclusion patterns.

        Args:
            element: BeautifulSoup element to check

        Returns:
            True if element should be excluded, False otherwise
        """
        if not hasattr(element, "name"):
            return False

        # Check element tags
        for pattern_list in [
            self.EXCLUSION_PATTERNS["nav_elements"],
            self.EXCLUSION_PATTERNS["header_elements"],
            self.EXCLUSION_PATTERNS["footer_elements"],
        ]:
            for pattern in pattern_list:
                # Handle role attributes
                if "[role=" in pattern:
                    tag = pattern.split("[")[0]
                    role_match = re.search(r'role="([^"]+)"', pattern)
                    if role_match:
                        role_value = role_match.group(1)
                        if element.name == tag and element.get("role") == role_value:
                            return True
                # Simple tag match
                elif element.name == pattern:
                    return True

        # Check classes
        element_classes = element.get("class", [])
        if isinstance(element_classes, str):
            element_classes = [element_classes]

        for class_list_key in [
            "nav_classes",
            "header_classes",
            "footer_classes",
            "ad_classes",
            "cookie_classes",
            "social_classes",
            "modal_classes",
        ]:
            exclusion_classes = self.EXCLUSION_PATTERNS[class_list_key]
            for excluded_class in exclusion_classes:
                # Check for exact match or partial match
                for elem_class in element_classes:
                    if excluded_class in elem_class.lower():
                        return True

        # Check IDs
        element_id = element.get("id", "")
        if element_id:
            for id_list_key in ["nav_ids", "header_ids", "footer_ids", "ad_ids"]:
                exclusion_ids = self.EXCLUSION_PATTERNS[id_list_key]
                for excluded_id in exclusion_ids:
                    if excluded_id in element_id.lower():
                        return True

        # Check for ad-related data attributes
        for attr in element.attrs:
            if attr.startswith("data-ad") or attr.startswith("data-google"):
                return True

        return False

    def _remove_non_content_elements(self, soup: BeautifulSoup) -> Dict[str, int]:
        """
        Remove non-content elements from the DOM.

        Args:
            soup: BeautifulSoup object to filter

        Returns:
            Dictionary with statistics about removed elements
        """
        stats = {
            "nav": 0,
            "header": 0,
            "footer": 0,
            "ads": 0,
            "cookies": 0,
            "social": 0,
            "modals": 0,
            "total": 0,
        }

        # Find all elements to remove (traverse from bottom up to avoid issues)
        elements_to_remove = []
        for element in soup.find_all():
            if self._should_exclude_element(element):
                elements_to_remove.append(element)

        # Remove elements and track stats
        for element in elements_to_remove:
            # Skip if element was already removed (as child of another removed element)
            if element.parent is None:
                continue

            # Categorize for stats
            element_classes = element.get("class", [])
            if isinstance(element_classes, str):
                element_classes = [element_classes]
            element_classes_str = " ".join(element_classes).lower()

            if element.name in ["nav", "aside"] or "nav" in element_classes_str:
                stats["nav"] += 1
            elif element.name == "header" or "header" in element_classes_str:
                stats["header"] += 1
            elif element.name == "footer" or "footer" in element_classes_str:
                stats["footer"] += 1
            elif any(
                ad_class in element_classes_str
                for ad_class in ["ad", "advertisement", "sponsor"]
            ):
                stats["ads"] += 1
            elif any(
                cookie_class in element_classes_str
                for cookie_class in ["cookie", "gdpr", "consent"]
            ):
                stats["cookies"] += 1
            elif "social" in element_classes_str or "share" in element_classes_str:
                stats["social"] += 1
            elif any(
                modal_class in element_classes_str
                for modal_class in ["modal", "popup", "overlay"]
            ):
                stats["modals"] += 1

            stats["total"] += 1
            element.decompose()  # Remove from tree

        return stats

    def chunk_html(
        self, html_content: str, max_chars: Optional[int] = None
    ) -> List[Dict]:
        """
        Split HTML into semantic chunks.

        Args:
            html_content: Full HTML content to chunk
            max_chars: Override default max_chars if provided

        Returns:
            List of chunk dictionaries with metadata
        """
        if max_chars is not None:
            max_chars_to_use = max_chars
        else:
            max_chars_to_use = self.max_chars

        # Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")
        body = soup.body if soup.body else soup

        # Extract parent context once (before filtering)
        parent_context = self._extract_parent_context(html_content)

        # Filter non-content elements if enabled
        if self.filter_non_content:
            filter_stats = self._remove_non_content_elements(body)
            # Add filter stats to parent context for debugging
            parent_context["filter_stats"] = filter_stats

        # Get filtered HTML
        filtered_html = str(body)

        # Small enough for single chunk?
        if len(filtered_html) <= max_chars_to_use:
            return [
                {
                    "chunk_index": 0,
                    "total_chunks": 1,
                    "chunk_dom": filtered_html,
                    "parent_context": parent_context,
                }
            ]

        # Find semantic boundaries
        boundaries = self._find_semantic_boundaries(body)

        # Group into chunks
        raw_chunks = self._group_boundaries_into_chunks(boundaries, max_chars_to_use)

        # Merge small chunks
        merged_chunks = self._merge_small_chunks(raw_chunks, max_chars_to_use)

        # Build final chunk objects
        chunk_objects = self._build_chunk_objects(merged_chunks, parent_context)

        # Filter out chunks with minimal content
        content_rich_chunks = self._filter_content_poor_chunks(chunk_objects)

        # Re-index chunks after filtering
        for i, chunk in enumerate(content_rich_chunks):
            chunk["chunk_index"] = i
            chunk["total_chunks"] = len(content_rich_chunks)

        return content_rich_chunks

    def _extract_parent_context(self, html: str) -> Dict:
        """Extract document metadata for selector accuracy."""
        soup = BeautifulSoup(html, "html.parser")
        body = soup.body if soup.body else soup

        # Get body classes and id
        body_classes = []
        body_id = ""

        if hasattr(body, "get"):
            body_classes = body.get("class", [])
            if isinstance(body_classes, str):
                body_classes = [body_classes]
            body_id = body.get("id", "")

        # Check for main container
        main_container = bool(soup.select_one('main, [role="main"]'))

        # Get document title
        title_element = soup.find("title")
        document_title = title_element.string if title_element else ""

        return {
            "body_classes": body_classes,
            "body_id": body_id,
            "main_container": main_container,
            "document_title": document_title,
        }

    def _find_semantic_boundaries(self, element: Any) -> List[Any]:
        """Find elements to use as chunk boundaries."""
        # Try CSS selectors in priority order
        for selector in self.BOUNDARY_SELECTORS:
            try:
                # Handle complex selectors by splitting on commas
                boundaries = []
                for sub_selector in selector.split(","):
                    sub_selector = sub_selector.strip()

                    # Handle attribute selectors
                    if "[" in sub_selector and "]" in sub_selector:
                        # Extract tag and attribute
                        tag_match = re.match(r"^(\w+)\[(\w+)\]", sub_selector)
                        if tag_match:
                            tag = tag_match.group(1)
                            attr = tag_match.group(2)
                            # Find all elements with that tag and attribute
                            found = element.find_all(tag, attrs={attr: True})
                            boundaries.extend(found)
                    # Handle class selectors with wildcards
                    elif "*=" in sub_selector:
                        # Parse div[class*="content"] style selectors
                        match = re.match(r'(\w+)\[class\*="([^"]+)"\]', sub_selector)
                        if match:
                            tag = match.group(1)
                            class_pattern = match.group(2)
                            # Find divs with classes containing the pattern
                            for elem in element.find_all(tag):
                                classes = elem.get("class", [])
                                if isinstance(classes, str):
                                    classes = [classes]
                                if any(class_pattern in cls for cls in classes):
                                    boundaries.append(elem)
                    # Handle regular CSS selectors
                    else:
                        found = element.select(sub_selector)
                        boundaries.extend(found)

                # If we found multiple boundaries, use them
                if len(boundaries) > 1:
                    return boundaries
            except Exception:
                # If selector parsing fails, continue to next
                continue

        # IMPROVED FALLBACK: Only use content-rich paragraphs, not every div/p
        # This prevents creating hundreds of tiny non-content chunks
        content_boundaries = []

        # Look for paragraphs with substantial text content
        for p in element.find_all("p"):
            text = p.get_text(strip=True)
            # Only use paragraphs with at least 50 characters of content
            if len(text) > 50:
                content_boundaries.append(p)

        # If we found content paragraphs, use those as boundaries
        if content_boundaries:
            return content_boundaries

        # Last resort: treat entire body as single chunk
        # Better to have one large chunk than many empty ones
        return [element]

    def _group_boundaries_into_chunks(
        self, boundaries: List, max_chars: int
    ) -> List[List]:
        """Group boundary elements into size-appropriate chunks."""
        chunks: List[List[Any]] = []
        current_chunk: List[Any] = []
        current_size = 0

        for element in boundaries:
            element_html = str(element)
            element_size = len(element_html)

            # Start new chunk if adding would exceed limit
            if current_size + element_size > max_chars and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [element]
                current_size = element_size
            else:
                current_chunk.append(element)
                current_size += element_size

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _merge_small_chunks(self, chunks: List[List], max_chars: int) -> List[List]:
        """Merge chunks smaller than minimum size."""
        merged: List[List[Any]] = []
        current_merged: List[Any] = []
        current_size = 0

        for chunk in chunks:
            chunk_size = sum(len(str(el)) for el in chunk)

            if not current_merged:
                current_merged = chunk
                current_size = chunk_size
            elif (
                current_size < self.min_chars and current_size + chunk_size <= max_chars
            ):
                current_merged.extend(chunk)
                current_size += chunk_size
            else:
                merged.append(current_merged)
                current_merged = chunk
                current_size = chunk_size

        if current_merged:
            merged.append(current_merged)

        return merged

    def _filter_content_poor_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Filter out chunks with minimal content.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            List of content-rich chunks only
        """
        content_rich_chunks = []

        for chunk in chunks:
            chunk_dom = chunk.get("chunk_dom", "")

            # Parse the chunk DOM to extract text
            soup = BeautifulSoup(chunk_dom, "html.parser")
            text = soup.get_text(strip=True)

            # Keep chunks with at least 200 characters of text content
            # This filters out chunks that are just navigation, headers, etc.
            if len(text) > 200:
                content_rich_chunks.append(chunk)

        # If all chunks were filtered out, keep at least one
        # (the one with the most content)
        if not content_rich_chunks and chunks:
            chunks_with_length = [
                (
                    chunk,
                    len(
                        BeautifulSoup(
                            chunk.get("chunk_dom", ""), "html.parser"
                        ).get_text(strip=True)
                    ),
                )
                for chunk in chunks
            ]
            chunks_with_length.sort(key=lambda x: x[1], reverse=True)
            content_rich_chunks = [chunks_with_length[0][0]]

        return content_rich_chunks

    def _build_chunk_objects(
        self, chunks: List[List], parent_context: Dict
    ) -> List[Dict]:
        """Convert chunk elements to final chunk dictionaries."""
        total_chunks = len(chunks)
        return [
            {
                "chunk_index": i,
                "total_chunks": total_chunks,
                "chunk_dom": "\n".join(str(el) for el in elements),
                "parent_context": parent_context,
            }
            for i, elements in enumerate(chunks)
        ]
