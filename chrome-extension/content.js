// Web Notes - Content script
// Loads and displays existing notes for the current page

/* global EXTENSION_CONSTANTS */

console.log("Web Notes - Content script loaded!");

// Store the last right-click coordinates for note positioning
let lastRightClickCoords = null;

// Listen for right-click events to capture coordinates
document.addEventListener("contextmenu", function (event) {
  lastRightClickCoords = {
    x: event.pageX,
    y: event.pageY,
    clientX: event.clientX,
    clientY: event.clientY,
    target: event.target,
    timestamp: Date.now(),
  };
});

// Listen for messages from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "getLastClickCoords") {
    // Return the last right-click coordinates
    sendResponse({
      coords: lastRightClickCoords,
      success: true,
    });
  } else if (message.action === "createNote") {
    // Create note with provided data
    createNoteAtCoords(message.noteNumber, message.coords);
    sendResponse({ success: true });
  }
});

/**
 * Load and display existing notes for the current URL
 */
function loadExistingNotes() {
  try {
    chrome.storage.local.get([EXTENSION_CONSTANTS.NOTES_KEY], function (result) {
      if (chrome.runtime.lastError) {
        console.error("[Web Notes] Failed to load notes:", chrome.runtime.lastError);
        return;
      }

      const notes = result[EXTENSION_CONSTANTS.NOTES_KEY] || {};
      const urlNotes = notes[window.location.href] || [];

      console.log(`[Web Notes] Found ${urlNotes.length} notes for current URL`);

      urlNotes.forEach(noteData => {
        if (noteData.isVisible) {
          displayNote(noteData);
        }
      });
    });
  } catch (error) {
    console.error("[Web Notes] Error loading existing notes:", error);
  }
}

// Cache for DOM queries to improve performance
const elementCache = new Map();

/**
 * Display a note on the page with optimized DOM queries
 * @param {Object} noteData - The note data object
 */
function displayNote(noteData) {
  try {
    // Check if note already exists on page
    if (document.getElementById(noteData.id)) {
      return;
    }

    let targetElement = null;
    const cacheKey = `${noteData.elementSelector}-${noteData.elementXPath}`;

    // Check cache first
    if (elementCache.has(cacheKey)) {
      const cachedElement = elementCache.get(cacheKey);
      // Verify the cached element is still in the DOM
      if (cachedElement && document.contains(cachedElement)) {
        targetElement = cachedElement;
      } else {
        // Remove stale cache entry
        elementCache.delete(cacheKey);
      }
    }

    // Intelligent selector fallback: try the best option first
    if (!targetElement) {
      const selectorResults = tryBothSelectors(noteData, cacheKey);
      targetElement = selectorResults.element;

      if (targetElement && selectorResults.usedSelector) {
        console.log(`[Web Notes] Found element using ${selectorResults.usedSelector}`);
        elementCache.set(cacheKey, targetElement);
      }
    }

    // Create note element
    const note = document.createElement("div");
    note.id = noteData.id;
    note.className = "web-note";
    note.style.cssText = `
      position: absolute;
      background: ${targetElement ? "lightblue" : "pink"};
      color: black;
      padding: 8px 12px;
      border-radius: 4px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 12px;
      font-weight: 500;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      z-index: 10000;
      cursor: move;
      border: 1px solid rgba(0, 0, 0, 0.1);
      min-width: 80px;
      max-width: 200px;
      word-wrap: break-word;
    `;

    // Set note text
    note.textContent = noteData.text;

    // Position the note
    if (targetElement) {
      // Position relative to found DOM element
      const rect = targetElement.getBoundingClientRect();
      note.style.left = `${rect.left + window.scrollX}px`;
      note.style.top = `${rect.top + window.scrollY - 30}px`;
      console.log(
        `[Web Notes] Displaying note anchored to DOM element: ${
          noteData.elementSelector || noteData.elementXPath
        }`,
      );
    } else {
      // Use fallback position with pink background
      note.style.left = `${noteData.fallbackPosition.x}px`;
      note.style.top = `${noteData.fallbackPosition.y}px`;
      note.style.background = "pink";
      console.log(
        "[Web Notes] Displaying note at fallback position (DOM element not found)",
      );
    }

    // Add to page
    document.body.appendChild(note);
  } catch (error) {
    console.error("[Web Notes] Error displaying note:", error);
  }
}

// Load notes when page is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", loadExistingNotes);
} else {
  // DOM already loaded
  loadExistingNotes();
}

// Handle URL changes for SPAs with proper cleanup
let currentUrl = window.location.href;
let urlCheckInterval = null;

function startUrlMonitoring() {
  // Clear any existing interval to prevent duplicates
  if (urlCheckInterval) {
    clearInterval(urlCheckInterval);
  }

  urlCheckInterval = setInterval(() => {
    if (window.location.href !== currentUrl) {
      currentUrl = window.location.href;
      console.log("[Web Notes] URL changed, reloading notes");

      // Clear element cache for new page
      elementCache.clear();

      // Remove existing notes
      document.querySelectorAll(".web-note").forEach(note => note.remove());

      // Load notes for new URL with debouncing
      setTimeout(loadExistingNotes, 100);
    }
  }, 2000); // Reduced frequency to 2 seconds
}

// Start monitoring
startUrlMonitoring();

// Clean up on page unload to prevent memory leaks
window.addEventListener("beforeunload", () => {
  if (urlCheckInterval) {
    clearInterval(urlCheckInterval);
    urlCheckInterval = null;
  }
});

// Also use modern navigation API if available
if ("navigation" in window) {
  window.navigation.addEventListener("navigate", () => {
    console.log("[Web Notes] Navigation detected, reloading notes");
    setTimeout(() => {
      // Clear element cache for new page
      elementCache.clear();

      // Remove existing notes
      document.querySelectorAll(".web-note").forEach(note => note.remove());

      // Load notes for new URL
      loadExistingNotes();
    }, 100);
  });
}

/**
 * Create a note at specific coordinates
 * @param {number} noteNumber - The note number
 * @param {Object} coords - Click coordinates with target element
 */
function createNoteAtCoords(noteNumber, coords) {
  try {
    // Generate unique note ID
    const noteId = `web-note-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const noteText = `MY NOTE #${noteNumber}`;

    let targetElement = null;
    let elementSelector = null;
    let elementXPath = null;
    let fallbackPosition = null;

    if (coords && coords.target) {
      targetElement = coords.target;
      if (targetElement.nodeType !== Node.ELEMENT_NODE) {
        targetElement = document.elementFromPoint(coords.clientX, coords.clientY);
      }
      if (!targetElement) {
        console.warn("[Web Notes] Could not determine target element for note");
        fallbackPosition = { x: coords.x, y: coords.y };
      } else {
        // Generate optimal selector using hybrid approach
        const selectorResult = generateOptimalSelector(targetElement);
        elementSelector = selectorResult.cssSelector;
        elementXPath = selectorResult.xpath;
      }
    } else if (coords) {
      // Store absolute coordinates as fallback
      fallbackPosition = { x: coords.x, y: coords.y };
    } else {
      // Default fallback position
      fallbackPosition = { x: 100, y: 100 };
    }

    // // Create note element
    // const note = document.createElement("div");
    // note.id = noteId;
    // note.className = "web-note";
    // note.style.cssText = `
    //   position: absolute;
    //   background: ${targetElement ? "lightblue" : "pink"};
    //   color: black;
    //   padding: 8px 12px;
    //   border-radius: 4px;
    //   font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    //   font-size: 12px;
    //   font-weight: 500;
    //   box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    //   z-index: 10000;
    //   cursor: move;
    //   border: 1px solid rgba(0, 0, 0, 0.1);
    //   min-width: 80px;
    //   max-width: 200px;
    //   word-wrap: break-word;
    // `;

    // // Set note text
    // note.textContent = noteText;

    // Position the note
    let posLeft = 100;
    let posTop = 100;
    if (targetElement && elementSelector) {
      // Position relative to target element
      const rect = targetElement.getBoundingClientRect();
      posLeft = rect.left + window.scrollX;
      posTop = rect.top + window.scrollY - 30;
    } else if (fallbackPosition) {
      // Use fallback absolute position
      posLeft = fallbackPosition.x;
      posTop = fallbackPosition.y - 30;
    }



    // // Add to page
    // document.body.appendChild(note);

    // Store note data
    const noteData = {
      id: noteId,
      text: noteText,
      url: window.location.href,
      elementSelector: elementSelector,
      elementXPath: elementXPath,
      fallbackPosition: fallbackPosition || {
        x: posLeft,
        y: posTop,
      },
      timestamp: Date.now(),
      isVisible: true,
    };
    displayNote(noteData);

    // Store in chrome storage using shared constants
    chrome.storage.local.get([EXTENSION_CONSTANTS.NOTES_KEY], function (result) {
      const notes = result[EXTENSION_CONSTANTS.NOTES_KEY] || {};
      const urlNotes = notes[window.location.href] || [];
      urlNotes.push(noteData);
      notes[window.location.href] = urlNotes;

      chrome.storage.local.set({ [EXTENSION_CONSTANTS.NOTES_KEY]: notes }, function () {
        if (chrome.runtime.lastError) {
          console.error("[Web Notes] Failed to save note:", chrome.runtime.lastError);
        } else {
          console.log("[Web Notes] Note saved successfully");
        }
      });
    });

    console.log(
      `[Web Notes] Created note #${noteNumber} at ${targetElement ? "DOM element" : "coordinates"}`,
    );
  } catch (error) {
    console.error("[Web Notes] Error creating note:", error);
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
        } else {
          console.warn(
            `[Web Notes] CSS selector matches ${allMatches.length} elements, ` +
              "trying XPath",
          );
        }
      }
    } catch (error) {
      console.warn("[Web Notes] CSS selector failed:", noteData.elementSelector, error);
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
      console.warn("[Web Notes] XPath failed:", noteData.elementXPath, error);
    }
  }

  // Strategy 3: Cross-validation if we had partial success
  if (noteData.elementSelector && noteData.elementXPath) {
    console.log("[Web Notes] Attempting cross-validation of selectors");

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
      console.warn("[Web Notes] Cross-validation failed:", error);
    }
  }

  console.log("[Web Notes] All selector strategies failed");
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
      console.log("[Web Notes] Using CSS selector as primary:", cssSelector);
    } else {
      // CSS couldn't generate unique selector, XPath is primary
      result.strategy = "xpath-primary";
      console.log("[Web Notes] CSS not unique, using XPath as primary:", result.xpath);
    }

    // Additional validation: Test both selectors work
    if (result.cssSelector) {
      try {
        const cssMatches = document.querySelectorAll(result.cssSelector);
        if (cssMatches.length !== 1 || cssMatches[0] !== element) {
          console.warn("[Web Notes] CSS selector validation failed, discarding");
          result.cssSelector = null;
          result.strategy = "xpath-only";
        }
      } catch (cssError) {
        console.warn("[Web Notes] CSS selector invalid, discarding:", cssError);
        result.cssSelector = null;
        result.strategy = "xpath-only";
      }
    }

    // Always validate XPath as backup
    if (result.xpath) {
      try {
        const xpathMatches = document.evaluate(
          result.xpath,
          document,
          null,
          XPathResult.FIRST_ORDERED_NODE_TYPE,
          null,
        );
        if (!xpathMatches.singleNodeValue || xpathMatches.singleNodeValue !== element) {
          console.error("[Web Notes] XPath validation failed - this shouldn't happen!");
          result.xpath = null;
        }
      } catch (xpathError) {
        console.error("[Web Notes] XPath invalid:", xpathError);
        result.xpath = null;
      }
    }

    // Log final strategy
    console.log(`[Web Notes] Selector strategy: ${result.strategy}`, {
      css: result.cssSelector,
      xpath: result.xpath,
    });

    return result;
  } catch (error) {
    console.error("[Web Notes] Error in generateOptimalSelector:", error);
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
      console.warn("[Web Notes] Invalid element for CSS selector generation");
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
        console.warn("[Web Notes] Invalid tag name:", tagName);
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
            const siblings = Array.from(parent.children).filter(
              child => child.tagName === current.tagName,
            );
            const sameClassSiblings = siblings.filter(
              sibling => sibling.className === current.className,
            );

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
          const siblings = Array.from(parent.children).filter(
            child => child.tagName === current.tagName,
          );
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
        console.log("[Web Notes] Generated unique CSS selector:", finalSelector);
        return finalSelector;
      } else {
        console.warn(
          `[Web Notes] CSS selector not unique: ${finalSelector} ` +
            `(matches ${matches.length} elements)`,
        );
        return null;
      }
    } catch (selectorError) {
      console.warn("[Web Notes] Invalid CSS selector generated:", finalSelector);
      return null;
    }
  } catch (error) {
    console.error("[Web Notes] Error generating CSS selector:", error);
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
      for (
        let sibling = child.previousSibling;
        sibling;
        sibling = sibling.previousSibling
      ) {
        if (
          sibling.nodeType === Node.ELEMENT_NODE &&
          sibling.tagName === child.tagName
        ) {
          siblingIndex++;
        }
      }
      components.unshift(`${child.tagName.toLowerCase()}[${siblingIndex}]`);
      child = child.parentNode;
    }
    let retval = `/${components.join("/")}`;
    console.log("[Web Notes] Generated XPath:", retval);
    return retval;
  } catch (error) {
    console.error("[Web Notes] Error generating XPath:", error);
    return null;
  }
}
