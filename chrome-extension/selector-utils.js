/**
 * Selector Utilities for Web Notes Chrome Extension
 * Functions for generating, validating, and using CSS and XPath selectors
 */

/**
 * Validate XPath expressions to prevent injection attacks
 * @param {string} xpath - XPath expression to validate
 * @returns {boolean} True if XPath is safe to use
 */
function validateXPath(xpath) {
  if (!xpath || typeof xpath !== "string") {
    return false;
  }

  // Basic XPath validation - only allow safe patterns
  // This is a conservative approach that blocks potentially dangerous XPath
  const safeXPathPattern = /^\/\/?\*?[\w\[\]@='"\s\d\-_\.\/\(\)]*$/;

  // Check for dangerous XPath functions or patterns
  const dangerousPatterns = [
    /document\s*\(/,
    /eval\s*\(/,
    /script\s*\(/,
    /javascript:/i,
    /data:/i,
    /<script/i,
    /on\w+\s*=/i,
  ];

  if (!safeXPathPattern.test(xpath)) {
    return false;
  }

  for (const pattern of dangerousPatterns) {
    if (pattern.test(xpath)) {
      return false;
    }
  }

  return true;
}

/**
 * Find an element using CSS selector or XPath
 * @param {string} selector - CSS selector or XPath
 * @returns {Element|null} Found element or null
 */
function findElementBySelector(selector) {
  try {
    if (!selector) return null;

    // Try CSS selector first
    if (!selector.startsWith("/")) {
      try {
        const element = document.querySelector(selector);
        if (element) return element;
      } catch (cssError) {
        console.log(`[YAWN] Invalid CSS selector: ${selector}`);
      }
    }

    // Validate XPath before using
    if (!validateXPath(selector)) {
      return null;
    }

    // Try XPath with additional safety
    try {
      const xpathResult = document.evaluate(selector, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
      return xpathResult.singleNodeValue;
    } catch (xpathError) {
      console.log(`[YAWN] XPath evaluation failed: ${selector}`, xpathError);
      return null;
    }
  } catch (error) {
    console.log(`[YAWN] Error finding element with selector ${selector}:`, error);
    return null;
  }
}

/**
 * Find a text node within an element at a specific offset
 * @param {Element} element - The parent element
 * @param {number} offset - Text offset
 * @param {number} containerType - Original container node type
 * @returns {Text|null} Found text node or null
 */
function findTextNodeInElement(element, offset, containerType) {
  try {
    if (containerType === Node.TEXT_NODE) {
      // Original container was a text node, find the text node within the element
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);

      let currentOffset = 0;
      let textNode;
      while ((textNode = walker.nextNode())) {
        const nodeLength = textNode.textContent.length;
        if (currentOffset + nodeLength >= offset) {
          return textNode;
        }
        currentOffset += nodeLength;
      }
    } else {
      // Original container was an element node
      if (element.childNodes[offset] && element.childNodes[offset].nodeType === Node.TEXT_NODE) {
        return element.childNodes[offset];
      }
      // Find first text node
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
      return walker.nextNode();
    }

    return null;
  } catch (error) {
    console.log("[YAWN] Error finding text node:", error);
    return null;
  }
}

/**
 * Intelligently try both CSS and XPath selectors with fallback logic
 * @param {Object} noteData - Note data containing selectors
 * @param {string} _cacheKey - Cache key for performance (unused currently)
 * @returns {Object} Result with element and used selector type
 */
function tryBothSelectors(noteData, _cacheKey) {
  const result = {
    element: null,
    usedSelector: null,
  };

  // Strategy 1: Try CSS first (usually faster)
  if (noteData.elementSelector) {
    try {
      const cssElement = document.querySelector(noteData.elementSelector);
      if (cssElement) {
        // Verify this is actually unique (extra safety check)
        const allMatches = document.querySelectorAll(noteData.elementSelector);
        if (allMatches.length === 1) {
          result.element = cssElement;
          result.usedSelector = "CSS selector";
          return result;
        }
      }
    } catch (error) {
      console.warn("[YAWN] CSS selector failed:", noteData.elementSelector, error);
    }
  }

  // Strategy 2: Try XPath as fallback
  if (noteData.elementXPath) {
    try {
      const xpathResult = document.evaluate(
        noteData.elementXPath,
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null,
      );
      const xpathElement = xpathResult.singleNodeValue;
      if (xpathElement) {
        result.element = xpathElement;
        result.usedSelector = "XPath";
        return result;
      }
    } catch (error) {
      console.warn("[YAWN] XPath failed:", noteData.elementXPath, error);
    }
  }

  // Strategy 3: Cross-validation if we had partial success
  if (noteData.elementSelector && noteData.elementXPath) {
    try {
      const cssMatches = document.querySelectorAll(noteData.elementSelector);
      const xpathResult = document.evaluate(
        noteData.elementXPath,
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null,
      );
      const xpathElement = xpathResult.singleNodeValue;

      // If XPath found something and it's in the CSS results, it's probably right
      if (xpathElement && Array.from(cssMatches).includes(xpathElement)) {
        result.element = xpathElement;
        result.usedSelector = "cross-validated";
        return result;
      }
    } catch (error) {
      console.warn("[YAWN] Cross-validation failed:", error);
    }
  }

  console.log("[YAWN] All selector strategies failed");
  return result;
}

/**
 * Generate optimal selector using hybrid CSS/XPath approach
 * Prioritizes the most reliable and performant selector
 * @param {Element} element - The DOM element
 * @returns {Object} Object with cssSelector and xpath properties
 */
function generateOptimalSelector(element) {
  const result = {
    cssSelector: null,
    xpath: null,
    strategy: null,
  };

  try {
    // Always generate XPath as fallback
    result.xpath = generateXPath(element);

    // Try to generate unique CSS selector first (faster for browsers)
    const cssSelector = generateCSSSelector(element);

    if (cssSelector) {
      // CSS selector generation succeeded and is validated as unique
      result.cssSelector = cssSelector;
      result.strategy = "css-primary";
    } else {
      // CSS couldn't generate unique selector, XPath is primary
      result.strategy = "xpath-primary";
      console.log("[YAWN] CSS not unique, using XPath as primary:", result.xpath);
    }

    // Additional validation: Test both selectors work
    if (result.cssSelector) {
      try {
        const cssMatches = document.querySelectorAll(result.cssSelector);
        if (cssMatches.length !== 1 || cssMatches[0] !== element) {
          result.cssSelector = null;
          result.strategy = "xpath-only";
        }
      } catch (cssError) {
        result.cssSelector = null;
        result.strategy = "xpath-only";
      }
    }

    // Always validate XPath as backup
    if (result.xpath) {
      try {
        const xpathMatches = document.evaluate(result.xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        if (!xpathMatches.singleNodeValue || xpathMatches.singleNodeValue !== element) {
          console.error("[YAWN] XPath validation failed - this shouldn't happen!");
          result.xpath = null;
        }
      } catch (xpathError) {
        console.error("[YAWN] XPath invalid:", xpathError);
        result.xpath = null;
      }
    }

    return result;
  } catch (error) {
    console.error("[YAWN] Error in generateOptimalSelector:", error);
    return {
      cssSelector: null,
      xpath: result.xpath, // Try to keep XPath if it was generated
      strategy: "error-fallback",
    };
  }
}

/**
 * Generate hierarchical CSS selector for an element with security validation
 * Builds a path from element up to document root or first element with ID
 * @param {Element} element - The DOM element
 * @returns {string} CSS selector
 */
function generateCSSSelector(element) {
  try {
    // Validate element input
    if (!element || typeof element.tagName !== "string") {
      console.warn("[YAWN] Invalid element for CSS selector generation");
      return null;
    }

    const components = [];
    let current = element;

    while (current && current.nodeType === Node.ELEMENT_NODE) {
      let selector = null;

      // Check if current element has a unique ID
      if (current.id && typeof current.id === "string") {
        const sanitizedId = current.id.replace(/[^a-zA-Z0-9_-]/g, "");
        if (sanitizedId.length > 0 && sanitizedId === current.id) {
          // Found ID - use it and stop traversing
          components.unshift(`#${sanitizedId}`);
          break;
        }
      }

      // Generate selector for current element
      const tagName = current.tagName.toLowerCase();
      if (!/^[a-zA-Z][a-zA-Z0-9]*$/.test(tagName)) {
        console.warn("[YAWN] Invalid tag name:", tagName);
        return null;
      }

      // Try to use classes for better readability (but add position for uniqueness)
      if (current.className && typeof current.className === "string") {
        const classes = current.className
          .split(" ")
          .filter(c => c.trim())
          .map(c => c.replace(/[^a-zA-Z0-9_-]/g, ""))
          .filter(c => c.length > 0);

        if (classes.length > 0) {
          const classSelector = classes.join(".");

          // Check if this class combination is unique among siblings
          const parent = current.parentElement;
          if (parent) {
            const siblings = Array.from(parent.children).filter(child => child.tagName === current.tagName);
            const sameClassSiblings = siblings.filter(sibling => sibling.className === current.className);

            if (sameClassSiblings.length === 1) {
              // Unique among siblings - just use class
              selector = `${tagName}.${classSelector}`;
            } else {
              // Not unique - add nth-child for specificity
              const index = sameClassSiblings.indexOf(current) + 1;
              selector = `${tagName}.${classSelector}:nth-of-type(${index})`;
            }
          } else {
            selector = `${tagName}.${classSelector}`;
          }
        }
      }

      // Fallback to tag name with nth-child if no classes or classes weren't unique
      if (!selector) {
        const parent = current.parentElement;
        if (parent) {
          const siblings = Array.from(parent.children).filter(child => child.tagName === current.tagName);
          const index = siblings.indexOf(current) + 1;
          selector = `${tagName}:nth-child(${index})`;
        } else {
          selector = tagName;
        }
      }

      components.unshift(selector);

      // Move up to parent
      current = current.parentElement;

      // Stop at document root
      if (!current || current.nodeType === Node.DOCUMENT_NODE) {
        break;
      }
    }

    const finalSelector = components.join(" > ");

    // Validate the generated selector works and is unique
    try {
      const matches = document.querySelectorAll(finalSelector);
      if (matches.length === 1 && matches[0] === element) {
        return finalSelector;
      } else {
        return null;
      }
    } catch (selectorError) {
      console.warn("[YAWN] Invalid CSS selector generated:", finalSelector);
      return null;
    }
  } catch (error) {
    console.error("[YAWN] Error generating CSS selector:", error);
    return null;
  }
}

/**
 * Generate XPath for an element
 * @param {Element} element - The DOM element
 * @returns {string} XPath
 */
function generateXPath(element) {
  try {
    if (element.id) {
      return `//*[@id="${element.id}"]`;
    }

    const components = [];
    let child = element;

    while (child.parentNode) {
      if (child.id) {
        components.unshift(`/*[@id="${child.id}"]`);
        break;
      }
      if (child.parentNode.nodeType === Node.DOCUMENT_NODE) {
        components.unshift(child.tagName.toLowerCase());
        break;
      }

      let siblingIndex = 1;
      for (let sibling = child.previousSibling; sibling; sibling = sibling.previousSibling) {
        if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === child.tagName) {
          siblingIndex++;
        }
      }
      components.unshift(`${child.tagName.toLowerCase()}[${siblingIndex}]`);
      child = child.parentNode;
    }
    let retval = `/${components.join("/")}`;
    return retval;
  } catch (error) {
    console.error("[YAWN] Error generating XPath:", error);
    return null;
  }
}

/* global noteHighlights, MAX_HIGHLIGHTS, MAX_SELECTION_LENGTH, NoteColorUtils */

/**
 * Clean up highlights map to prevent memory leaks
 */
function cleanupHighlights() {
  if (noteHighlights.size > MAX_HIGHLIGHTS) {
    const entries = Array.from(noteHighlights.entries());
    const excessCount = noteHighlights.size - MAX_HIGHLIGHTS;

    // Remove oldest entries (first entries in the map)
    entries.slice(0, excessCount).forEach(([noteId]) => {
      removeTextHighlight(noteId);
    });

    // Cleaned up excess highlights
  }
}

/**
 * Create highlighting for selected text when a note is displayed
 * @param {Object} noteData - Note data containing selection information
 * @param {string} backgroundColor - Background color for the highlight
 */
function createTextHighlight(noteData, backgroundColor) {
  try {
    if (!noteData.selectionData || !noteData.selectionData.selectedText) {
      return; // No selection data to highlight
    }

    // Validate and sanitize background color
    const safeBackgroundColor = NoteColorUtils.sanitizeColor(backgroundColor);

    // Remove any existing highlight for this note
    removeTextHighlight(noteData.id);

    // Clean up highlights to prevent memory leaks
    cleanupHighlights();

    const selectionData = noteData.selectionData;

    // Find the elements using the stored selectors
    const startElement = findElementBySelector(selectionData.startSelector);
    const endElement = findElementBySelector(selectionData.endSelector);

    if (!startElement || !endElement) {
      console.log(`[YAWN] Could not find elements for highlighting note ${noteData.id}`);
      return;
    }

    // Reconstruct the range
    const range = document.createRange();

    try {
      // Find the text nodes within the elements
      const startTextNode = findTextNodeInElement(startElement, selectionData.startOffset, selectionData.startContainerType);
      const endTextNode = findTextNodeInElement(endElement, selectionData.endOffset, selectionData.endContainerType);

      if (!startTextNode || !endTextNode) {
        console.log(`[YAWN] Could not find text nodes for highlighting note ${noteData.id}`);
        return;
      }

      range.setStart(startTextNode, Math.min(selectionData.startOffset, startTextNode.textContent.length));
      range.setEnd(endTextNode, Math.min(selectionData.endOffset, endTextNode.textContent.length));

      // Validate range size before highlighting
      const rangeText = range.toString();
      if (rangeText.length > MAX_SELECTION_LENGTH) {
        console.log(`[YAWN] Range text too large for highlighting: ${rangeText.length} chars`);
        return;
      }

      // Create highlight span with sanitized color
      const highlightSpan = document.createElement("span");
      highlightSpan.className = `web-note-highlight web-note-highlight-${noteData.id}`;
      highlightSpan.style.cssText = `
        background-color: ${safeBackgroundColor} !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        transition: opacity 0.2s ease !important;
      `;
      highlightSpan.setAttribute("data-note-id", noteData.id);

      // Wrap the selected content
      try {
        range.surroundContents(highlightSpan);
        noteHighlights.set(noteData.id, highlightSpan);
      } catch (error) {
        // If surroundContents fails (e.g., range crosses element boundaries),
        // try extracting and inserting instead
        const contents = range.extractContents();
        highlightSpan.appendChild(contents);
        range.insertNode(highlightSpan);
        noteHighlights.set(noteData.id, highlightSpan);
      }
    } catch (rangeError) {
      console.error(`[YAWN] Error creating range for highlight: ${rangeError}`);
    }
  } catch (error) {
    console.error(`[YAWN] Error creating highlight for note ${noteData.id}:`, error);
  }
}

/**
 * Remove text highlighting for a note
 * @param {string} noteId - The note ID
 */
function removeTextHighlight(noteId) {
  try {
    const highlight = noteHighlights.get(noteId);
    if (highlight && highlight.parentNode) {
      // Replace the highlight span with its text content
      const textContent = highlight.textContent;
      const textNode = document.createTextNode(textContent);
      highlight.parentNode.replaceChild(textNode, highlight);
      noteHighlights.delete(noteId);
    }

    // Also remove any orphaned highlight elements
    const orphanedHighlights = document.querySelectorAll(`.web-note-highlight-${noteId}`);
    orphanedHighlights.forEach(element => {
      if (element.parentNode) {
        const textContent = element.textContent;
        const textNode = document.createTextNode(textContent);
        element.parentNode.replaceChild(textNode, element);
      }
    });
  } catch (error) {
    console.error(`[YAWN] Error removing highlight for note ${noteId}:`, error);
  }
}
