"""Service for validating and repairing CSS selectors from LLM-generated notes."""

import logging
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from lxml import html
from lxml.cssselect import CSSSelector

logger = logging.getLogger(__name__)


class SelectorValidator:
    """
    Validates and repairs CSS selectors for DOM elements.

    This service helps fix selectors that may not work due to:
    - Overuse of nth-child pseudo-selectors
    - Non-unique selectors matching multiple elements
    - Wrong enclosing nodes or over-specification
    """

    def __init__(self, fuzzy_threshold: float = 0.80):
        """
        Initialize the selector validator.

        Args:
            fuzzy_threshold: Minimum similarity score (0-1) for fuzzy text matching
        """
        self.fuzzy_threshold = fuzzy_threshold

    def validate_selector(
        self,
        page_dom: str,
        css_selector: str,
        expected_text: Optional[str] = None,
    ) -> Tuple[bool, int, Optional[Any]]:
        """
        Validate if CSS selector works and is unique.

        Args:
            page_dom: HTML content as string
            css_selector: CSS selector to validate
            expected_text: Optional text that should be contained in matched element

        Returns:
            Tuple of (is_valid, match_count, first_element)
            - is_valid: True if exactly one element matches AND contains expected_text (if provided)
            - match_count: Number of elements matched
            - first_element: The matched element if any, else None
        """
        try:
            dom = html.fromstring(page_dom)
            selector = CSSSelector(css_selector)
            matches = selector(dom)

            match_count = len(matches)
            first_element = matches[0] if matches else None

            # Check uniqueness
            is_valid = match_count == 1

            # Additionally check text containment if expected_text provided
            if is_valid and expected_text and first_element is not None:
                element_text = self._get_element_text(first_element)
                if expected_text not in element_text:
                    is_valid = False
                    logger.debug(
                        f"CSS selector '{css_selector}' matched element but does not "
                        f"contain expected text: '{expected_text[:50]}...'"
                    )

            if not is_valid and match_count > 0 and not expected_text:
                logger.debug(
                    f"CSS selector '{css_selector}' matched {match_count} elements "
                    "(expected 1)"
                )

            return (is_valid, match_count, first_element)

        except Exception as e:
            logger.warning(f"CSS selector validation failed for '{css_selector}': {e}")
            return (False, 0, None)

    def find_text_in_dom(
        self, page_dom: str, highlighted_text: str, use_fuzzy: bool = True
    ) -> list[Tuple[Any, float]]:
        """
        Locate elements containing the highlighted text in the DOM.

        Strategy:
        1. Try exact text match first (fast)
        2. If no exact match and use_fuzzy=True, try fuzzy matching
        3. Prioritize most specific (leaf-most) elements

        Args:
            page_dom: HTML content as string
            highlighted_text: Text to search for
            use_fuzzy: Whether to use fuzzy matching as fallback

        Returns:
            List of (element, similarity_score) tuples, sorted by specificity and score
        """
        if not highlighted_text:
            return []

        try:
            dom = html.fromstring(page_dom)
            candidates = []

            # Strategy 1: Exact match (fast path)
            for element in dom.iter():
                element_text = self._get_element_text(element)
                if not element_text:
                    continue

                if highlighted_text in element_text:
                    candidates.append((element, 1.0))  # Perfect match

            # If we found exact matches, prioritize leaf elements
            if candidates:
                logger.debug(
                    f"Found {len(candidates)} exact matches for text: "
                    f"'{highlighted_text[:50]}...'"
                )
                # Sort by specificity: prefer elements with fewer descendants
                candidates = self._sort_by_specificity(candidates)
                return candidates

            # Strategy 2: Fuzzy matching (fallback)
            if use_fuzzy:
                for element in dom.iter():
                    element_text = self._get_element_text(element)
                    if not element_text:
                        continue

                    similarity = SequenceMatcher(
                        None, highlighted_text.lower(), element_text.lower()
                    ).ratio()

                    if similarity >= self.fuzzy_threshold:
                        candidates.append((element, similarity))

                if candidates:
                    logger.debug(
                        f"Found {len(candidates)} fuzzy matches for text: "
                        f"'{highlighted_text[:50]}...' (threshold={self.fuzzy_threshold})"
                    )
                    # Sort by specificity first, then similarity
                    candidates = self._sort_by_specificity(candidates)
                else:
                    logger.debug(
                        f"No fuzzy matches found for text: '{highlighted_text[:50]}...'"
                    )

                return candidates

            return []

        except Exception as e:
            logger.error(f"Error finding text in DOM: {e}")
            return []

    def _sort_by_specificity(
        self, candidates: List[Tuple[Any, float]]
    ) -> List[Tuple[Any, float]]:
        """
        Sort candidates by specificity (prefer leaf elements over parents).

        Args:
            candidates: List of (element, score) tuples

        Returns:
            Sorted list with most specific elements first
        """

        def specificity_key(item: Tuple[Any, float]) -> Tuple[float, int]:
            element, score = item
            # Count descendants (fewer is more specific)
            descendant_count = len(list(element.iter())) - 1  # -1 to exclude self
            # Prefer elements with fewer descendants, higher score
            return (-score, descendant_count)

        return sorted(candidates, key=specificity_key)

    def _get_element_text(self, element: Any) -> str:
        """
        Get all text content from an element, including descendants.

        Args:
            element: lxml element

        Returns:
            Combined text content, stripped
        """
        try:
            # Use text_content() which gets all text from element and descendants
            return element.text_content().strip() if element.text_content() else ""
        except Exception:
            return ""

    def _get_element_direct_text(self, element: Any) -> str:
        """
        Get only the direct text content of an element (not from descendants).

        Args:
            element: lxml element

        Returns:
            Direct text content, stripped
        """
        try:
            text_parts = []
            if element.text:
                text_parts.append(element.text.strip())
            if element.tail:
                text_parts.append(element.tail.strip())
            return " ".join(filter(None, text_parts))
        except Exception:
            return ""

    def generate_robust_selector(
        self, element: Any
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate robust CSS selector and XPath for an element.

        Strategy:
        1. If element has unique ID, use #id
        2. If element has unique classes, use tag.class1.class2
        3. Build hierarchical path with structural pseudo-selectors
        4. Always generate XPath as fallback

        Args:
            element: lxml element

        Returns:
            Tuple of (css_selector, xpath)
        """
        try:
            css_selector = self._generate_css_selector(element)
            xpath = self._generate_xpath(element)
            return (css_selector, xpath)
        except Exception as e:
            logger.error(f"Error generating selector: {e}")
            return (None, None)

    def _generate_css_selector(self, element: Any) -> Optional[str]:
        """
        Generate CSS selector for an element.

        Prioritizes:
        1. Unique IDs
        2. Unique class combinations
        3. Hierarchical path with nth-of-type (not nth-child)
        4. Skips generic wrapper divs without IDs
        5. Stops at semantic anchor elements (article, main, section, body)
        """
        # Semantic elements that make good anchor points
        SEMANTIC_ANCHORS = {
            "body",
            "main",
            "article",
            "section",
            "nav",
            "aside",
            "header",
            "footer",
        }

        try:
            # Check for unique ID
            element_id = element.get("id")
            if element_id:
                # Verify it's unique
                root = element.getroottree().getroot()
                matches = root.xpath(f'//*[@id="{element_id}"]')
                if len(matches) == 1:
                    return f"#{element_id}"

            # Build path from element to root
            path_parts: List[str] = []
            current = element

            while current is not None and current.tag != "html":
                tag = current.tag

                # Get classes
                classes = current.get("class", "").split()
                class_str = "." + ".".join(classes) if classes else ""

                # Check if this is a generic wrapper div to skip
                is_generic_div = tag == "div" and not element_id and not classes

                # Skip generic divs unless it's the starting element
                if is_generic_div and path_parts:
                    current = current.getparent()
                    continue

                # Get position among siblings of same type
                parent = current.getparent()
                if parent is not None:
                    siblings_of_type = [e for e in parent if e.tag == current.tag]
                    if len(siblings_of_type) > 1:
                        position = siblings_of_type.index(current) + 1
                        path_parts.insert(
                            0, f"{tag}{class_str}:nth-of-type({position})"
                        )
                    else:
                        path_parts.insert(0, f"{tag}{class_str}")
                else:
                    path_parts.insert(0, f"{tag}{class_str}")

                # Stop at semantic anchor points or after sufficient specificity
                if tag in SEMANTIC_ANCHORS:
                    break
                if element_id or (classes and len(path_parts) >= 3):
                    break

                current = parent

            if not path_parts:
                return None

            # Join with child combinator
            selector = " > ".join(path_parts)
            return selector

        except Exception as e:
            logger.error(f"Error generating CSS selector: {e}")
            return None

    def _generate_xpath(self, element: Any) -> Optional[str]:
        """
        Generate XPath for an element.

        Uses element tree structure to create absolute XPath.
        """
        try:
            # Build XPath manually since getpath() doesn't exist on HtmlElement
            path_parts: List[str] = []
            current = element

            while current is not None:
                parent = current.getparent()
                if parent is None:
                    # Root element
                    path_parts.insert(0, f"/{current.tag}")
                    break

                # Count position among siblings
                siblings = [e for e in parent if e.tag == current.tag]
                if len(siblings) > 1:
                    position = siblings.index(current) + 1
                    path_parts.insert(0, f"/{current.tag}[{position}]")
                else:
                    path_parts.insert(0, f"/{current.tag}")

                current = parent

            return "".join(path_parts) if path_parts else None

        except Exception as e:
            logger.error(f"Error generating XPath: {e}")
            return None

    def repair_selector(
        self,
        page_dom: str,
        highlighted_text: str,
        old_css_selector: Optional[str] = None,
        old_xpath: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Attempt to repair a failed selector by finding the text and generating new selectors.

        Args:
            page_dom: HTML content as string
            highlighted_text: The text that should be highlighted
            old_css_selector: Original CSS selector from LLM (may be invalid)
            old_xpath: Original XPath from LLM (may be invalid)

        Returns:
            Dictionary with:
                - success: bool - whether repair succeeded
                - css_selector: str | None - new CSS selector (if found)
                - xpath: str | None - new XPath (if found)
                - match_count: int - how many elements matched the text
                - text_similarity: float - similarity score if fuzzy match used
                - message: str - human-readable status message
        """
        result = {
            "success": False,
            "css_selector": old_css_selector,  # Keep original by default
            "xpath": old_xpath,
            "match_count": 0,
            "text_similarity": 0.0,
            "message": "",
        }

        # Try to find the text in the DOM
        matches = self.find_text_in_dom(page_dom, highlighted_text, use_fuzzy=True)

        if not matches:
            result["message"] = "Text not found in DOM (exact or fuzzy)"
            logger.warning(
                f"Cannot repair selector: text not found - '{highlighted_text[:50]}...'"
            )
            return result

        result["match_count"] = len(matches)

        # Use the best match (highest similarity)
        best_element, similarity = matches[0]
        result["text_similarity"] = similarity

        if len(matches) > 1:
            logger.debug(
                f"Multiple text matches ({len(matches)}), using best match "
                f"(similarity={similarity:.2f})"
            )

        # Generate new selectors for the found element
        new_css, new_xpath = self.generate_robust_selector(best_element)

        if not new_css and not new_xpath:
            result["message"] = "Text found but failed to generate selectors"
            logger.warning(
                f"Found text but failed to generate selectors for '{highlighted_text[:50]}...'"
            )
            return result

        # Validate the generated CSS selector
        validated_css = None
        if new_css:
            is_valid, count, matched_element = self.validate_selector(
                page_dom, new_css, highlighted_text
            )
            if is_valid:
                validated_css = new_css
                logger.debug(
                    f"Generated CSS selector validated successfully: {new_css}"
                )
            else:
                logger.warning(
                    f"Generated CSS selector failed validation: {new_css} "
                    f"(matches={count}, text_match={matched_element is not None})"
                )

        # TODO: Add XPath validation when needed (currently extension uses CSS primarily)
        validated_xpath = new_xpath  # Accept XPath for now as fallback

        # Success only if at least one selector is validated
        if validated_css or validated_xpath:
            result["success"] = True
            result["css_selector"] = validated_css
            result["xpath"] = validated_xpath
            result["message"] = (
                f"Repaired selector (similarity={similarity:.2f}, "
                f"matches={len(matches)})"
            )
            logger.info(
                f"Successfully repaired selector for text '{highlighted_text[:30]}...' - "
                f"validated CSS: {validated_css}, XPath: {validated_xpath}"
            )
        else:
            result["message"] = (
                "Text found and selectors generated but failed validation"
            )
            logger.warning(
                f"Generated selectors failed validation for '{highlighted_text[:50]}...'"
            )

        return result
