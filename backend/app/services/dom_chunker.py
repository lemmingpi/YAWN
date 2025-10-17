"""
DOM chunking service ported from JavaScript.
Splits large HTML into semantic chunks for LLM processing.
"""

import re
from typing import Dict, List, Optional

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

    def __init__(self, max_chars: int = 40000, min_chars: int = 10000):
        """
        Initialize chunker with size constraints.

        Args:
            max_chars: Maximum characters per chunk (~10k tokens)
            min_chars: Minimum characters to avoid tiny chunks
        """
        self.max_chars = max_chars
        self.min_chars = min_chars

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

        # Small enough for single chunk?
        if len(html_content) <= max_chars_to_use:
            return [
                {
                    "chunk_index": 0,
                    "total_chunks": 1,
                    "chunk_dom": html_content,
                    "parent_context": self._extract_parent_context(html_content),
                }
            ]

        # Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")
        body = soup.body if soup.body else soup

        # Extract parent context once
        parent_context = self._extract_parent_context(html_content)

        # Find semantic boundaries
        boundaries = self._find_semantic_boundaries(body)

        # Group into chunks
        raw_chunks = self._group_boundaries_into_chunks(boundaries, max_chars_to_use)

        # Merge small chunks
        merged_chunks = self._merge_small_chunks(raw_chunks, max_chars_to_use)

        # Build final chunk objects
        return self._build_chunk_objects(merged_chunks, parent_context)

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

    def _find_semantic_boundaries(self, element) -> List:
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

        # Fallback to paragraphs and divs
        return element.find_all(["p", "div"])

    def _group_boundaries_into_chunks(
        self, boundaries: List, max_chars: int
    ) -> List[List]:
        """Group boundary elements into size-appropriate chunks."""
        chunks = []
        current_chunk = []
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
        merged = []
        current_merged = []
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
