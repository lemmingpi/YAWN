// Web Notes - Content script
// Loads and displays existing notes for the current page with markdown editing support

/* global EXTENSION_CONSTANTS, NoteDataUtils, updateNote, deleteNote, normalizeUrlForNoteStorage */
/* global getNotesForUrl, findMatchingUrlsInStorage */
/* global createColorDropdown, handleColorSelection */

// Timing constants for better maintainability
const TIMING = {
  DOM_UPDATE_DELAY: 100, // Time to allow DOM updates to complete
  FADE_ANIMATION_DELAY: 250, // Time for fade-in animation to complete
  RESIZE_DEBOUNCE: 300, // Debounce delay for resize events
  SCROLL_DEBOUNCE: 200, // Debounce delay for scroll events (if needed)
  URL_MONITOR_INTERVAL: 2000, // Interval for URL change monitoring (2 seconds)
  AUTOSAVE_DELAY: 1000, // Auto-save delay during editing (1 second)
  DOUBLE_CLICK_DELAY: 300, // Max time between clicks for double-click (300ms)
};

// Editing state management
const EditingState = {
  currentlyEditingNote: null,
  lastClickTime: 0,
  lastClickedNote: null,
  autosaveTimeouts: new Map(), // Map of noteId -> timeout
};

console.log("Web Notes - Content script loaded!");

// Map to store highlighting elements by note ID
const noteHighlights = new Map();
const MAX_HIGHLIGHTS = 1000;
const MAX_SELECTION_LENGTH = 50000;

// Store the last right-click coordinates for note positioning
let lastRightClickCoords = null;

// Listen for right-click events to capture coordinates and selected text
document.addEventListener("contextmenu", function (event) {
  const selection = window.getSelection();
  const selectedText = selection.toString().trim();

  lastRightClickCoords = {
    x: event.pageX,
    y: event.pageY,
    clientX: event.clientX,
    clientY: event.clientY,
    target: event.target,
    timestamp: Date.now(),
    selectedText: selectedText,
    selectionData: selectedText ? captureSelectionData(selection) : null,
  };
});

/**
 * Validate and sanitize color values to prevent CSS injection
 * @param {string} color - Color value to validate
 * @returns {string} Safe color value or fallback
 */
function sanitizeColor(color) {
  if (!color || typeof color !== 'string') {
    return '#fff3cd'; // Default light yellow
  }

  // Allow hex colors (3 or 6 digits)
  const hexPattern = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;
  if (hexPattern.test(color)) {
    return color;
  }

  // Allow rgb() values with basic validation
  const rgbPattern = /^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/;
  const rgbMatch = color.match(rgbPattern);
  if (rgbMatch) {
    const [, r, g, b] = rgbMatch;
    // Validate RGB values are within 0-255 range
    if (parseInt(r) <= 255 && parseInt(g) <= 255 && parseInt(b) <= 255) {
      return color;
    }
  }

  // Allow rgba() values with basic validation
  const rgbaPattern = /^rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*([01]?\.?\d*)\s*\)$/;
  const rgbaMatch = color.match(rgbaPattern);
  if (rgbaMatch) {
    const [, r, g, b, a] = rgbaMatch;
    // Validate RGB values are within 0-255 range and alpha is 0-1
    if (parseInt(r) <= 255 && parseInt(g) <= 255 && parseInt(b) <= 255 && parseFloat(a) <= 1) {
      return color;
    }
  }

  // Allow named colors (basic set for security)
  const namedColors = [
    'transparent', 'white', 'black', 'red', 'green', 'blue', 'yellow', 'orange',
    'purple', 'pink', 'gray', 'grey', 'brown', 'cyan', 'magenta', 'lime'
  ];
  if (namedColors.includes(color.toLowerCase())) {
    return color.toLowerCase();
  }

  console.warn(`[Web Notes] Invalid color value: ${color}, using fallback`);
  return '#fff3cd'; // Fallback to default
}

/**
 * Validate XPath expressions to prevent injection attacks
 * @param {string} xpath - XPath expression to validate
 * @returns {boolean} True if XPath is safe to use
 */
function validateXPath(xpath) {
  if (!xpath || typeof xpath !== 'string') {
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
    /on\w+\s*=/i
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

    console.log(`[Web Notes] Cleaned up ${excessCount} excess highlights`);
  }
}

/**
 * Capture detailed selection data for text highlighting
 * @param {Selection} selection - The current text selection
 * @returns {Object|null} Selection data for highlighting, or null if invalid
 */
function captureSelectionData(selection) {
  try {
    if (!selection || selection.rangeCount === 0) {
      return null;
    }

    const range = selection.getRangeAt(0);

    // Validate range integrity
    if (!range.startContainer || !range.endContainer) {
      console.warn("[Web Notes] Invalid range containers");
      return null;
    }

    // Validate selection size
    const selectedText = selection.toString().trim();
    if (selectedText.length > MAX_SELECTION_LENGTH) {
      console.warn(`[Web Notes] Selected text exceeds maximum length (${MAX_SELECTION_LENGTH} chars)`);
      return null;
    }

    if (selectedText.length === 0) {
      return null;
    }

    const startContainer = range.startContainer;
    const endContainer = range.endContainer;

    // Only support selections within element nodes or their text children
    const startElement = startContainer.nodeType === Node.TEXT_NODE
      ? startContainer.parentElement
      : startContainer;
    const endElement = endContainer.nodeType === Node.TEXT_NODE
      ? endContainer.parentElement
      : endContainer;

    if (!startElement || !endElement) {
      return null;
    }

    // Validate that range doesn't span critical elements
    const commonAncestor = range.commonAncestorContainer;
    const commonElement = commonAncestor.nodeType === Node.TEXT_NODE
      ? commonAncestor.parentElement
      : commonAncestor;

    if (commonElement && commonElement.closest) {
      const criticalElement = commonElement.closest('script, style, iframe, object, embed');
      if (criticalElement) {
        console.warn("[Web Notes] Cannot highlight within critical elements (script/style/iframe)");
        return null;
      }
    }

    // Generate selectors for the start and end elements
    let startSelector, endSelector;

    try {
      startSelector = generateOptimalSelector(startElement);
      endSelector = generateOptimalSelector(endElement);
    } catch (error) {
      console.error("[Web Notes] Error generating selectors:", error);
      return null;
    }

    return {
      selectedText: selection.toString().trim(),
      startSelector: startSelector.cssSelector || startSelector.xpath,
      endSelector: endSelector.cssSelector || endSelector.xpath,
      startOffset: range.startOffset,
      endOffset: range.endOffset,
      startContainerType: startContainer.nodeType,
      endContainerType: endContainer.nodeType,
      // Store the range boundaries as text for verification
      commonAncestorSelector: generateOptimalSelector(range.commonAncestorContainer.nodeType === Node.TEXT_NODE
        ? range.commonAncestorContainer.parentElement
        : range.commonAncestorContainer).cssSelector,
    };
  } catch (error) {
    console.error("[Web Notes] Error capturing selection data:", error);
    return null;
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
    const safeBackgroundColor = sanitizeColor(backgroundColor);

    // Remove any existing highlight for this note
    removeTextHighlight(noteData.id);

    // Clean up highlights to prevent memory leaks
    cleanupHighlights();

    const selectionData = noteData.selectionData;

    // Find the elements using the stored selectors
    const startElement = findElementBySelector(selectionData.startSelector);
    const endElement = findElementBySelector(selectionData.endSelector);

    if (!startElement || !endElement) {
      console.warn(`[Web Notes] Could not find elements for highlighting note ${noteData.id}`);
      return;
    }

    // Reconstruct the range
    const range = document.createRange();

    try {
      // Find the text nodes within the elements
      const startTextNode = findTextNodeInElement(startElement, selectionData.startOffset, selectionData.startContainerType);
      const endTextNode = findTextNodeInElement(endElement, selectionData.endOffset, selectionData.endContainerType);

      if (!startTextNode || !endTextNode) {
        console.warn(`[Web Notes] Could not find text nodes for highlighting note ${noteData.id}`);
        return;
      }

      range.setStart(startTextNode, Math.min(selectionData.startOffset, startTextNode.textContent.length));
      range.setEnd(endTextNode, Math.min(selectionData.endOffset, endTextNode.textContent.length));

      // Validate range size before highlighting
      const rangeText = range.toString();
      if (rangeText.length > MAX_SELECTION_LENGTH) {
        console.warn(`[Web Notes] Range text too large for highlighting: ${rangeText.length} chars`);
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
        console.log(`[Web Notes] Created highlight for note ${noteData.id}`);
      } catch (error) {
        // If surroundContents fails (e.g., range crosses element boundaries),
        // try extracting and inserting instead
        const contents = range.extractContents();
        highlightSpan.appendChild(contents);
        range.insertNode(highlightSpan);
        noteHighlights.set(noteData.id, highlightSpan);
        console.log(`[Web Notes] Created highlight for note ${noteData.id} using extraction method`);
      }
    } catch (rangeError) {
      console.error(`[Web Notes] Error creating range for highlight: ${rangeError}`);
    }
  } catch (error) {
    console.error(`[Web Notes] Error creating highlight for note ${noteData.id}:`, error);
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
      console.log(`[Web Notes] Removed highlight for note ${noteId}`);
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
    console.error(`[Web Notes] Error removing highlight for note ${noteId}:`, error);
  }
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
    if (!selector.startsWith('/')) {
      try {
        const element = document.querySelector(selector);
        if (element) return element;
      } catch (cssError) {
        console.warn(`[Web Notes] Invalid CSS selector: ${selector}`);
      }
    }

    // Validate XPath before using
    if (!validateXPath(selector)) {
      console.warn(`[Web Notes] Invalid or potentially dangerous XPath: ${selector}`);
      return null;
    }

    // Try XPath with additional safety
    try {
      const xpathResult = document.evaluate(
        selector,
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null
      );
      return xpathResult.singleNodeValue;
    } catch (xpathError) {
      console.error(`[Web Notes] XPath evaluation failed: ${selector}`, xpathError);
      return null;
    }
  } catch (error) {
    console.error(`[Web Notes] Error finding element with selector ${selector}:`, error);
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
      const walker = document.createTreeWalker(
        element,
        NodeFilter.SHOW_TEXT,
        null,
        false
      );

      let currentOffset = 0;
      let textNode;
      while (textNode = walker.nextNode()) {
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
      const walker = document.createTreeWalker(
        element,
        NodeFilter.SHOW_TEXT,
        null,
        false
      );
      return walker.nextNode();
    }

    return null;
  } catch (error) {
    console.error("[Web Notes] Error finding text node:", error);
    return null;
  }
}

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
 * Load and display existing notes for the current URL with enhanced URL matching
 */
async function loadExistingNotes() {
  try {
    getNotes().then( async function (result) {
      if (chrome.runtime.lastError) {
        console.error("[Web Notes] Failed to load notes:", chrome.runtime.lastError);
        return;
      }

      const notes = result || {};

      // Use enhanced URL matching to find all notes that match the current URL
      const urlNotes = getNotesForUrl(window.location.href, notes);

      console.log(
        `[Web Notes] Found ${urlNotes.length} notes for current URL (including anchor variations)`,
      );

      // Migrate and display notes, saving if migration occurred
      let needsBulkSave = false;
      const migratedNotes = [];

      for (const noteData of urlNotes) {
        if (noteData.isVisible) {
          const migratedNote = await NoteDataUtils.migrateLegacyNote(noteData, false);
          if (migratedNote !== noteData) {
            needsBulkSave = true;
          }
          migratedNotes.push(migratedNote);
          displayNote(migratedNote);
        } else {
          migratedNotes.push(noteData);
        }
      }

      // Save all migrated notes in bulk if any were migrated
      // Note: This will move all notes from URL variations (with different anchors)
      // under a single normalized URL and clean up the old entries to avoid duplicates.
      if (needsBulkSave) {
        const normalizedUrl = normalizeUrlForNoteStorage(window.location.href);
        notes[normalizedUrl] = migratedNotes;

        // Clean up old URL variations to avoid duplicates after migration
        const matchingUrls = findMatchingUrlsInStorage(window.location.href, notes);
        for (const oldUrl of matchingUrls) {
          if (oldUrl !== normalizedUrl && notes[oldUrl]) {
            console.log(`[Web Notes] Cleaning up old URL variation: ${oldUrl}`);
            delete notes[oldUrl];
          }
        }

        setNotes(notes).then(
          function (result) {
            if (chrome.runtime.lastError) {
              console.error(
                "[Web Notes] Failed to save migrated notes:",
                chrome.runtime.lastError,
              );
            } else {
              console.log(
                "[Web Notes] Successfully saved migrated notes and cleaned up URL variations",
              );
            }
          },
        );
      }
    });
  } catch (error) {
    console.error("[Web Notes] Error loading existing notes:", error);
  }
}

// Cache for DOM queries to improve performance
const elementCache = new Map();

/**
 * Debounce utility to limit function execution frequency
 * @param {Function} func - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, delay) {
  let timeoutId;
  return function (...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
}

/**
 * Ensure a note is accessible by repositioning if it's outside page boundaries
 * Only repositions notes that are truly inaccessible (beyond scrollable area)
 * @param {Element} noteElement - The note DOM element
 * @param {Object} noteData - The note data object
 * @returns {boolean} True if note was repositioned
 */
function ensureNoteVisibility(noteElement, noteData) {
  const noteRect = noteElement.getBoundingClientRect();
  const noteX = noteRect.left + window.scrollX;
  const noteY = noteRect.top + window.scrollY;

  // Get page dimensions (scrollable area)
  const pageWidth = document.documentElement.scrollWidth;
  const pageHeight = document.documentElement.scrollHeight;
  const minVisible = 50; // Minimum pixels that must be visible on page

  let newX = noteX;
  let newY = noteY;
  let wasRepositioned = false;

  // Only reposition if note is outside the scrollable page boundaries
  // (not just outside the current viewport)

  if (noteX + noteRect.width < 0) {
    // Note is completely off the left edge of the page
    newX = minVisible;
    wasRepositioned = true;
  } else if (noteX > pageWidth) {
    // Note is completely off the right edge of the page
    newX = pageWidth - noteRect.width - minVisible;
    wasRepositioned = true;
  }

  if (noteY + noteRect.height < 0) {
    // Note is completely off the top edge of the page
    newY = minVisible;
    wasRepositioned = true;
  } else if (noteY > pageHeight) {
    // Note is completely off the bottom edge of the page
    newY = pageHeight - noteRect.height - minVisible;
    wasRepositioned = true;
  }

  if (wasRepositioned) {
    // Update note position
    noteElement.style.left = `${newX}px`;
    noteElement.style.top = `${newY}px`;

    // Update stored offset based on note type
    if (noteData.elementSelector || noteData.elementXPath) {
      // For anchored notes, calculate new offset from target element
      const selectorResults = tryBothSelectors(
        noteData,
        `${noteData.elementSelector || ""}-${noteData.elementXPath || ""}`,
      );
      const targetElement = selectorResults.element;

      if (targetElement) {
        const rect = targetElement.getBoundingClientRect();
        const elementX = rect.left + window.scrollX;
        const elementY = rect.top + window.scrollY - 30;

        const newOffsetX = newX - elementX;
        const newOffsetY = newY - elementY;

        updateNoteOffset(noteData.id, newOffsetX, newOffsetY);
        noteData.offsetX = newOffsetX;
        noteData.offsetY = newOffsetY;
      }
    } else {
      // For fallback notes, update fallback position
      noteData.fallbackPosition.x = newX;
      noteData.fallbackPosition.y = newY;
    }

    console.log(
      `[Web Notes] Repositioned note ${noteData.id} from outside page bounds to (${newX}, ${newY})`,
    );
  }

  return wasRepositioned;
}

/**
 * Reposition all existing notes after window resize
 */
function repositionAllNotes() {
  const notes = document.querySelectorAll(".web-note");
  console.log(`[Web Notes] Repositioning ${notes.length} notes after window resize`);

  if (notes.length === 0) {
    return;
  }

  // Batch storage operation - fetch all notes once
  getNotes().then(function (result) {
    if (chrome.runtime.lastError) {
      console.error(
        "[Web Notes] Failed to get notes for repositioning:",
        chrome.runtime.lastError,
      );
      return;
    }

    const allNotes = result || {};
    const urlNotes = getNotesForUrl(window.location.href, allNotes);

    notes.forEach(noteElement => {
      const noteId = noteElement.id;

      // Find the note data
      const noteData = urlNotes.find(note => note.id === noteId);
      if (!noteData) {
        console.warn(`[Web Notes] Note data not found for repositioning: ${noteId}`);
        return;
      }

      // Find target element if note is anchored
      let targetElement = null;
      if (noteData.elementSelector || noteData.elementXPath) {
        const selectorResults = tryBothSelectors(
          noteData,
          `${noteData.elementSelector || ""}-${noteData.elementXPath || ""}`,
        );
        targetElement = selectorResults.element;
      }

      // Recalculate position
      const newPosition = calculateNotePosition(noteData, targetElement);

      // Update note position with smooth transition
      noteElement.style.left = `${newPosition.x}px`;
      noteElement.style.top = `${newPosition.y}px`;

      console.log(
        `[Web Notes] Repositioned note ${noteId} to (${newPosition.x}, ${newPosition.y})`,
      );
    });

    // Ensure all notes have minimum visibility after repositioning
    setTimeout(() => {
      ensureAllNotesVisibleBatched(allNotes, urlNotes);
    }, TIMING.DOM_UPDATE_DELAY);
  });
}

/**
 * Handle window resize events
 */
function handleWindowResize() {
  console.log("[Web Notes] Window resized, repositioning notes");
  repositionAllNotes();
}

/**
 * Batched version of ensureAllNotesVisible that uses pre-fetched data
 * @param {Object} allNotes - All notes from storage
 * @param {Array} urlNotes - Notes for current URL
 */
function ensureAllNotesVisibleBatched(allNotes, urlNotes) {
  const notes = document.querySelectorAll(".web-note");
  let notesRepositioned = 0;

  notes.forEach((noteElement, index) => {
    console.log(
      `[Web Notes] Checking note ${index + 1}/${notes.length}: ${noteElement.id}`,
    );

    const noteData = urlNotes.find(note => note.id === noteElement.id);

    if (noteData) {
      const wasRepositioned = ensureNoteVisibility(noteElement, noteData);
      if (wasRepositioned) {
        notesRepositioned++;
        console.log(`[Web Notes] Repositioned note ${noteElement.id} for visibility`);
      }
    } else {
      console.warn(`[Web Notes] Note data not found for ${noteElement.id}`);
    }
  });

  // eslint-disable-next-line max-len
  console.log(
    `[Web Notes] Completed visibility check - processed ${notes.length} notes, repositioned ${notesRepositioned}`,
  );
}

/**
 * Calculate note position based on target element or fallback coordinates with offset
 * Notes can be positioned anywhere including off-screen - no restrictions applied
 * @param {Object} noteData - The note data object
 * @param {Element|null} targetElement - The target DOM element (if found)
 * @returns {Object} Position object with x, y coordinates and anchoring status
 */
function calculateNotePosition(noteData, targetElement) {
  const offsetX = noteData.offsetX || 0;
  const offsetY = noteData.offsetY || 0;

  if (targetElement) {
    // Position relative to found DOM element with offset
    const rect = targetElement.getBoundingClientRect();
    return {
      x: rect.left + window.scrollX + offsetX,
      y: rect.top + window.scrollY - 30 + offsetY,
      isAnchored: true,
    };
  } else {
    // Use fallback position with offset
    return {
      x: noteData.fallbackPosition.x + offsetX,
      y: noteData.fallbackPosition.y + offsetY,
      isAnchored: false,
    };
  }
}

/**
 * Update note offset in storage with enhanced URL matching
 * @param {string} noteId - The note ID
 * @param {number} newOffsetX - New X offset
 * @param {number} newOffsetY - New Y offset
 */
function updateNoteOffset(noteId, newOffsetX, newOffsetY) {
  try {
    getNotes().then( function (result) {
      if (chrome.runtime.lastError) {
        console.error(
          "[Web Notes] Failed to get notes for offset update:",
          chrome.runtime.lastError,
        );
        return;
      }

      const notes = result || {};
      const matchingUrls = findMatchingUrlsInStorage(window.location.href, notes);
      let noteFound = false;

      // Find and update the specific note in any of the matching URLs
      for (const matchingUrl of matchingUrls) {
        const urlNotes = notes[matchingUrl] || [];
        const noteIndex = urlNotes.findIndex(note => note.id === noteId);

        if (noteIndex !== -1) {
          urlNotes[noteIndex].offsetX = newOffsetX;
          urlNotes[noteIndex].offsetY = newOffsetY;

          // Save back to storage
          notes[matchingUrl] = urlNotes;
          setNotes(notes).then(
            function () {
              if (chrome.runtime.lastError) {
                console.error(
                  "[Web Notes] Failed to save note offset:",
                  chrome.runtime.lastError,
                );
              } else {
                console.log(
                  `[Web Notes] Updated note ${noteId} offset to (${newOffsetX}, ${newOffsetY})`,
                );
              }
            },
          );
          noteFound = true;
          break;
        }
      }

      if (!noteFound) {
        console.warn(`[Web Notes] Note ${noteId} not found for offset update`);
      }
    });
  } catch (error) {
    console.error("[Web Notes] Error updating note offset:", error);
  }
}

/**
 * Update note cursor based on current state (edit mode vs drag mode)
 * @param {Element} noteElement - The note DOM element
 */
function updateNoteCursor(noteElement) {
  if (noteElement.classList.contains("editing")) {
    noteElement.style.cursor = "text";
  } else if (noteElement.classList.contains("dragging")) {
    noteElement.style.cursor = "grabbing";
  } else {
    noteElement.style.cursor = "move";
  }
}

/**
 * Add interactive hover and focus effects to a note element
 * @param {Element} noteElement - The note DOM element
 * @param {boolean} isAnchored - Whether the note is anchored to a DOM element
 */
function addInteractiveEffects(noteElement, isAnchored) {
  // Hover effects
  noteElement.addEventListener("mouseenter", () => {
    if (
      !noteElement.classList.contains("dragging") &&
      !noteElement.classList.contains("editing")
    ) {
      noteElement.style.transform = "scale(1.02) translateZ(0)";
      noteElement.style.boxShadow =
        "0 5px 20px rgba(0, 0, 0, 0.15), 0 2px 6px rgba(0, 0, 0, 0.1)";
      noteElement.style.borderColor = isAnchored
        ? "rgba(33, 150, 243, 0.4)"
        : "rgba(233, 30, 99, 0.4)";
    }
  });

  noteElement.addEventListener("mouseleave", () => {
    if (
      !noteElement.classList.contains("dragging") &&
      !noteElement.classList.contains("editing")
    ) {
      noteElement.style.transform = "scale(1) translateZ(0)";
      noteElement.style.boxShadow =
        "0 3px 12px rgba(0, 0, 0, 0.12), 0 1px 3px rgba(0, 0, 0, 0.08)";
      noteElement.style.borderColor = isAnchored
        ? "rgba(33, 150, 243, 0.2)"
        : "rgba(233, 30, 99, 0.2)";
    }
  });

  // Focus effects for accessibility
  noteElement.setAttribute("tabindex", "0");
  noteElement.setAttribute("role", "button");
  noteElement.setAttribute("aria-label", `Draggable note: ${noteElement.textContent}`);

  noteElement.addEventListener("focus", () => {
    noteElement.style.outline = `2px solid ${isAnchored ? "#2196F3" : "#E91E63"}`;
    noteElement.style.outlineOffset = "2px";
  });

  noteElement.addEventListener("blur", () => {
    noteElement.style.outline = "none";
    noteElement.style.outlineOffset = "0";
  });
}

/**
 * Make a note element draggable
 * @param {Element} noteElement - The note DOM element
 * @param {Object} noteData - The note data object
 * @param {Element|null} targetElement - The target element the note is anchored to
 */
function makeDraggable(noteElement, noteData, targetElement) {
  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let startOffsetX = noteData.offsetX || 0;
  let startOffsetY = noteData.offsetY || 0;

  function handleDragStart(e) {
    // CRITICAL: Prevent drag operations when note is in edit mode
    if (noteElement.classList.contains("editing")) {
      return; // Allow normal text selection and cursor behavior in edit mode
    }

    // Prevent default drag behavior and text selection
    e.preventDefault();
    e.stopPropagation();

    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    startOffsetX = noteData.offsetX || 0;
    startOffsetY = noteData.offsetY || 0;

    // Enhanced drag visual feedback
    noteElement.classList.add("dragging");
    updateNoteCursor(noteElement);
    noteElement.style.transform = "scale(1.05) rotateZ(2deg) translateZ(0)";
    noteElement.style.boxShadow =
      "0 8px 32px rgba(0, 0, 0, 0.24), 0 4px 8px rgba(0, 0, 0, 0.12)";
    noteElement.style.zIndex = "10001";
    noteElement.style.opacity = "0.9";
    noteElement.style.transition = "none"; // Disable transitions during drag

    // Add event listeners to document for smooth dragging
    // Note: { passive: false } is required on mousemove to allow preventDefault()
    // This prevents text selection and other default behaviors during drag
    // Performance impact: Disables scroll optimizations during drag operations
    document.addEventListener("mousemove", handleDragMove, { passive: false });
    document.addEventListener("mouseup", handleDragEnd, { once: true });

    console.log(`[Web Notes] Started dragging note ${noteData.id}`);
  }

  function handleDragMove(e) {
    if (!isDragging) return;

    e.preventDefault();
    e.stopPropagation();

    // Calculate new offset based on drag delta
    const deltaX = e.clientX - dragStartX;
    const deltaY = e.clientY - dragStartY;
    const newOffsetX = startOffsetX + deltaX;
    const newOffsetY = startOffsetY + deltaY;

    // Calculate and apply new position immediately (no restrictions)
    const newPosition = calculateNotePosition(
      { ...noteData, offsetX: newOffsetX, offsetY: newOffsetY },
      targetElement,
    );

    // Update visual position immediately
    noteElement.style.left = `${newPosition.x}px`;
    noteElement.style.top = `${newPosition.y}px`;

    // Update the working offset values for this session
    noteData.offsetX = newOffsetX;
    noteData.offsetY = newOffsetY;
  }

  function handleDragEnd(e) {
    if (!isDragging) return;

    e.preventDefault();
    e.stopPropagation();

    isDragging = false;

    // Restore normal styling with smooth transition
    noteElement.classList.remove("dragging");
    updateNoteCursor(noteElement);
    noteElement.style.transform = "scale(1) rotateZ(0deg) translateZ(0)";
    noteElement.style.boxShadow =
      "0 3px 12px rgba(0, 0, 0, 0.12), 0 1px 3px rgba(0, 0, 0, 0.08)";
    noteElement.style.zIndex = "10000";
    noteElement.style.opacity = "1";
    noteElement.style.transition = "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)"; // Re-enable transitions

    // Remove drag event listeners
    document.removeEventListener("mousemove", handleDragMove);

    // Save the final offset to storage
    updateNoteOffset(noteData.id, noteData.offsetX || 0, noteData.offsetY || 0);

    // Ensure note maintains minimum visibility after drag
    setTimeout(() => {
      ensureNoteVisibility(noteElement, noteData);
    }, TIMING.DOM_UPDATE_DELAY);

    // eslint-disable-next-line max-len
    console.log(
      `[Web Notes] Finished dragging note ${noteData.id} to offset ` +
      `(${noteData.offsetX || 0}, ${noteData.offsetY || 0})`,
    );
  }

  // Add mousedown event listener to start dragging
  noteElement.addEventListener("mousedown", handleDragStart);

  // Prevent text selection during potential drag (but allow it in edit mode)
  noteElement.addEventListener("selectstart", e => {
    if (!noteElement.classList.contains("editing")) {
      e.preventDefault();
    }
  });
}

/**
 * Add double-click editing capability to a note
 * @param {Element} noteElement - The note DOM element
 * @param {Object} noteData - The note data object
 */
function addEditingCapability(noteElement, noteData) {
  let clickTimeout = null;

  // Handle click events for double-click detection
  function handleNoteClick(event) {
    // Don't interfere with dragging
    if (noteElement.classList.contains("dragging")) {
      return;
    }

    event.stopPropagation();

    const now = Date.now();
    const timeDiff = now - EditingState.lastClickTime;

    if (
      EditingState.lastClickedNote === noteElement &&
      timeDiff < TIMING.DOUBLE_CLICK_DELAY
    ) {
      // Double-click detected - always use current data from element
      clearTimeout(clickTimeout);
      const currentNoteData = noteElement.noteData || noteData;
      enterEditMode(noteElement, currentNoteData);
    } else {
      // Single click - wait to see if there's a second click
      EditingState.lastClickTime = now;
      EditingState.lastClickedNote = noteElement;

      clickTimeout = setTimeout(() => {
        // Single click confirmed - do nothing for now
        EditingState.lastClickedNote = null;
      }, TIMING.DOUBLE_CLICK_DELAY);
    }
  }

  // Add click listener
  noteElement.addEventListener("click", handleNoteClick);

  // Prevent text selection during potential double-click
  noteElement.addEventListener("selectstart", e => {
    if (!noteElement.classList.contains("editing")) {
      e.preventDefault();
    }
  });
}

/**
 * Enter edit mode for a note
 * @param {Element} noteElement - The note DOM element
 * @param {Object} noteData - The note data object (may be stale, will use fresh data from element)
 */
function enterEditMode(noteElement, noteData) {
  // Exit any currently editing note
  if (
    EditingState.currentlyEditingNote &&
    EditingState.currentlyEditingNote !== noteElement
  ) {
    exitEditMode(EditingState.currentlyEditingNote, false);
  }

  EditingState.currentlyEditingNote = noteElement;
  noteElement.classList.add("editing");

  // CRITICAL FIX: Always use the most recent data from the DOM element
  // The noteData parameter may be stale from the original closure
  const currentNoteData = noteElement.noteData || noteData;
  const content = currentNoteData.content || "";

  // Create textarea for editing
  const textarea = document.createElement("textarea");
  textarea.className = "note-editor";
  textarea.value = content;

  // Style the textarea to match the note
  const noteStyles = window.getComputedStyle(noteElement);
  textarea.style.cssText = `
    width: 100%;
    height: 100%;
    border: none;
    background: transparent;
    font-family: ${noteStyles.fontFamily};
    font-size: ${noteStyles.fontSize};
    font-weight: ${noteStyles.fontWeight};
    line-height: ${noteStyles.lineHeight};
    letter-spacing: ${noteStyles.letterSpacing};
    color: ${noteStyles.color};
    padding: 0;
    margin: 0;
    resize: none;
    outline: none;
    overflow: hidden;
  `;

  // Store original content for cancellation
  textarea.originalContent = content;

  // Create container for toolbar, textarea and delete button
  const editContainer = document.createElement("div");
  editContainer.style.cssText = `
    position: relative;
    width: 100%;
    height: 100%;
  `;

  // Create markdown toolbar
  const toolbar = createMarkdownToolbar(textarea);
  toolbar.className += " edit-toolbar";

  // Create delete button
  const deleteButton = document.createElement("button");
  deleteButton.className = "note-delete-button";
  deleteButton.innerHTML = "&times;";
  deleteButton.style.cssText = `
    position: absolute;
    top: -8px;
    right: -8px;
    width: 20px;
    height: 20px;
    background: #f44336;
    color: white;
    border: none;
    border-radius: 50%;
    font-size: 14px;
    font-weight: bold;
    cursor: pointer;
    z-index: 10002;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    transition: all 0.2s ease;
    line-height: 1;
    padding: 0;
  `;

  // Add hover effects to delete button
  deleteButton.addEventListener("mouseenter", () => {
    deleteButton.style.background = "#d32f2f";
    deleteButton.style.transform = "scale(1.1)";
    deleteButton.style.boxShadow = "0 3px 6px rgba(0, 0, 0, 0.3)";
  });

  deleteButton.addEventListener("mouseleave", () => {
    deleteButton.style.background = "#f44336";
    deleteButton.style.transform = "scale(1)";
    deleteButton.style.boxShadow = "0 2px 4px rgba(0, 0, 0, 0.2)";
  });

  // Add delete button click handler
  deleteButton.addEventListener("click", event => {
    event.preventDefault();
    event.stopPropagation();
    handleNoteDelete(noteElement, currentNoteData);
  });

  // Clear note content and add edit container
  noteElement.innerHTML = "";
  editContainer.appendChild(toolbar);
  editContainer.appendChild(textarea);
  editContainer.appendChild(deleteButton);
  noteElement.appendChild(editContainer);

  // Focus and select content
  textarea.focus();
  textarea.select();

  // Update cursor for edit mode
  updateNoteCursor(noteElement);

  // Add visual indicator for edit mode
  noteElement.style.borderColor = "#2196F3";
  noteElement.style.borderWidth = "2px";
  noteElement.style.borderStyle = "solid";

  // Auto-resize textarea
  function autoResize() {
    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
  }

  textarea.addEventListener("input", autoResize);
  autoResize(); // Initial resize

  // Add keyboard shortcuts
  textarea.addEventListener("keydown", event => {
    handleEditKeydown(event, noteElement, currentNoteData, textarea);
  });

  // Auto-save functionality
  let saveTimeout;
  textarea.addEventListener("input", () => {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
      autoSaveNote(noteElement, currentNoteData, textarea.value);
    }, TIMING.AUTOSAVE_DELAY);
    EditingState.autosaveTimeouts.set(currentNoteData.id, saveTimeout);
  });

  // Click outside to save and exit
  function handleClickOutside(event) {
    if (!noteElement.contains(event.target)) {
      exitEditMode(noteElement, true);
      document.removeEventListener("click", handleClickOutside);
    }
  }

  // Add click outside listener after a brief delay to avoid immediate trigger
  setTimeout(() => {
    document.addEventListener("click", handleClickOutside);
  }, 100);

  console.log(`[Web Notes] Entered edit mode for note ${currentNoteData.id}`);
}

/**
 * Exit edit mode for a note
 * @param {Element} noteElement - The note DOM element
 * @param {boolean} save - Whether to save changes
 */
function exitEditMode(noteElement, save = true) {
  if (!noteElement.classList.contains("editing")) {
    return; // Not in edit mode
  }

  const textarea = noteElement.querySelector(".note-editor");
  if (!textarea) {
    return; // No textarea found
  }

  // Always use current data from element (may have been updated since edit mode started)
  const noteData = noteElement.noteData;
  if (!noteData) {
    console.error("[Web Notes] No note data found on element during exit edit mode");
    return;
  }
  const newContent = save ? textarea.value : textarea.originalContent;

  // Clear any pending auto-save
  if (EditingState.autosaveTimeouts.has(noteData.id)) {
    clearTimeout(EditingState.autosaveTimeouts.get(noteData.id));
    EditingState.autosaveTimeouts.delete(noteData.id);
  }

  // Update note data and display
  if (save && newContent !== textarea.originalContent) {
    const updatedData = NoteDataUtils.createNoteData(noteData, newContent);
    // CRITICAL: Update the DOM element's data to ensure consistency
    noteElement.noteData = updatedData;

    // Save to storage
    updateNote(window.location.href, noteData.id, updatedData).then(success => {
      if (success) {
        console.log(`[Web Notes] Note ${noteData.id} saved successfully`);
      } else {
        console.error(`[Web Notes] Failed to save note ${noteData.id}`);
      }
    });
  }

  // Restore note display using the most current data
  const displayContent = NoteDataUtils.getDisplayContent(noteElement.noteData);
  noteElement.innerHTML = displayContent.html;

  // Restore styling
  noteElement.classList.remove("editing");
  updateNoteCursor(noteElement);
  noteElement.style.borderColor = "";
  noteElement.style.borderWidth = "";
  noteElement.style.borderStyle = "";

  // Clear editing state
  EditingState.currentlyEditingNote = null;

  console.log(`[Web Notes] Exited edit mode for note ${noteData.id}, saved: ${save}`);
}

/**
 * Handle keyboard shortcuts during editing
 * @param {KeyboardEvent} event - The keyboard event
 * @param {Element} noteElement - The note DOM element
 * @param {Object} noteData - The note data object
 * @param {Element} textarea - The textarea element
 */
function handleEditKeydown(event, noteElement, noteData, textarea) {
  // Escape key - cancel and revert
  if (event.key === "Escape") {
    event.preventDefault();
    exitEditMode(noteElement, false);
    return;
  }

  // Ctrl+Enter or Cmd+Enter - save and exit
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    exitEditMode(noteElement, true);
    return;
  }

  // Tab for indentation (basic markdown support)
  if (event.key === "Tab") {
    event.preventDefault();
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;

    if (event.shiftKey) {
      // Shift+Tab - remove indentation
      const lineStart = value.lastIndexOf("\n", start - 1) + 1;
      const lineContent = value.substring(lineStart, start);
      if (lineContent.match(/^\s{1,2}/)) {
        textarea.value =
          value.substring(0, lineStart) +
          lineContent.replace(/^\s{1,2}/, "") +
          value.substring(start);
        // eslint-disable-next-line max-len
        textarea.setSelectionRange(
          start - Math.min(2, lineContent.match(/^\s*/)[0].length),
          end - Math.min(2, lineContent.match(/^\s*/)[0].length),
        );
      }
    } else {
      // Tab - add indentation
      textarea.value = value.substring(0, start) + "  " + value.substring(end);
      textarea.setSelectionRange(start + 2, end + 2);
    }

    // Trigger auto-resize
    textarea.dispatchEvent(new Event("input"));
  }

  // Ctrl+B for bold (basic markdown shortcut)
  if ((event.ctrlKey || event.metaKey) && event.key === "b") {
    event.preventDefault();
    insertMarkdownSyntax(textarea, "**", "**");
  }

  // Ctrl+I for italic (basic markdown shortcut)
  if ((event.ctrlKey || event.metaKey) && event.key === "i") {
    event.preventDefault();
    insertMarkdownSyntax(textarea, "*", "*");
  }
}

/**
 * Create a markdown toolbar for the editing interface
 * @param {Element} textarea - The textarea element to control
 * @returns {Element} The toolbar element
 */
function createMarkdownToolbar(textarea) {
  const toolbar = document.createElement("div");
  toolbar.className = "markdown-toolbar";
  toolbar.style.cssText = `
    display: flex;
    flex-wrap: nowrap;
    gap: 2px;
    padding: 4px;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-radius: 4px;
    border: 0.5px solid rgba(0, 0, 0, 0.08);
    margin-bottom: 4px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    width: max-content;
  `;

  // Define toolbar buttons with their configurations
  const toolbarButtons = [
    {
      title: "Bold",
      icon: "B",
      style: "font-weight: bold;",
      action: () => insertMarkdownSyntax(textarea, "**", "**"),
    },
    {
      title: "Italic",
      icon: "I",
      style: "font-style: italic;",
      action: () => insertMarkdownSyntax(textarea, "*", "*"),
    },
    {
      title: "Header 1",
      icon: "H1",
      style: "font-size: 12px; font-weight: bold;",
      action: () => insertLinePrefix(textarea, "# "),
    },
    {
      title: "Header 2",
      icon: "H2",
      style: "font-size: 11px; font-weight: bold;",
      action: () => insertLinePrefix(textarea, "## "),
    },
    {
      title: "Header 3",
      icon: "H3",
      style: "font-size: 10px; font-weight: bold;",
      action: () => insertLinePrefix(textarea, "### "),
    },
    {
      title: "Link",
      icon: "🔗",
      style: "",
      action: () => insertMarkdownLink(textarea),
    },
    {
      title: "Unordered List",
      icon: "•",
      style: "font-weight: bold;",
      action: () => insertLinePrefix(textarea, "- "),
    },
    {
      title: "Ordered List",
      icon: "1.",
      style: "font-size: 11px; font-weight: bold;",
      action: () => insertOrderedListItem(textarea),
    },
    {
      title: "Inline Code",
      icon: "<>",
      style: "font-family: monospace; font-size: 11px;",
      action: () => insertMarkdownSyntax(textarea, "`", "`"),
    },
    {
      title: "Quote",
      icon: "\"",
      style: "font-weight: bold; font-size: 14px;",
      action: () => insertLinePrefix(textarea, "> "),
    },
    {
      title: "Strikethrough",
      icon: "S",
      style: "text-decoration: line-through;",
      action: () => insertMarkdownSyntax(textarea, "~~", "~~"),
    },
  ];

  // Create buttons
  toolbarButtons.forEach(buttonConfig => {
    const button = document.createElement("button");
    button.className = "toolbar-button";
    button.title = buttonConfig.title;
    button.innerHTML = buttonConfig.icon;

    button.style.cssText = `
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 14px;
      height: 14px;
      border: 0.5px solid rgba(0, 0, 0, 0.12);
      background: linear-gradient(135deg, #ffffff 0%, #f0f2f5 100%);
      color: #333;
      border-radius: 2px;
      cursor: pointer;
      font-size: 8px;
      padding: 0;
      transition: all 0.2s ease;
      user-select: none;
      ${buttonConfig.style}
    `;

    // Add hover and active effects
    button.addEventListener("mouseenter", () => {
      button.style.background = "linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)";
      button.style.borderColor = "#2196F3";
      button.style.transform = "translateY(-1px)";
      button.style.boxShadow = "0 2px 4px rgba(0, 0, 0, 0.15)";
    });

    button.addEventListener("mouseleave", () => {
      button.style.background = "linear-gradient(135deg, #ffffff 0%, #f0f2f5 100%)";
      button.style.borderColor = "rgba(0, 0, 0, 0.15)";
      button.style.transform = "translateY(0)";
      button.style.boxShadow = "none";
    });

    button.addEventListener("mousedown", () => {
      button.style.transform = "translateY(1px)";
    });

    button.addEventListener("mouseup", () => {
      button.style.transform = "translateY(-1px)";
    });

    // Add click handler
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      buttonConfig.action();

      // Maintain focus on textarea
      setTimeout(() => {
        textarea.focus();
      }, 0);
    });

    toolbar.appendChild(button);
  });

  // Add color dropdown if the function is available
  if (typeof createColorDropdown === "function") {
    try {
      const colorDropdown = createColorDropdown(textarea);
      toolbar.appendChild(colorDropdown);
    } catch (error) {
      console.error("[Web Notes] Error adding color dropdown to toolbar:", error);
    }
  }

  return toolbar;
}

/**
 * Insert markdown syntax around selected text
 * @param {Element} textarea - The textarea element
 * @param {string} before - Text to insert before selection
 * @param {string} after - Text to insert after selection
 */
function insertMarkdownSyntax(textarea, before, after) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const selectedText = textarea.value.substring(start, end);
  const replacement = before + selectedText + after;

  textarea.value =
    textarea.value.substring(0, start) + replacement + textarea.value.substring(end);

  // Position cursor
  if (selectedText) {
    textarea.setSelectionRange(start, start + replacement.length);
  } else {
    textarea.setSelectionRange(start + before.length, start + before.length);
  }

  // Trigger auto-resize and change events
  textarea.dispatchEvent(new Event("input"));
  textarea.focus();
}

/**
 * Insert prefix at the beginning of the current line
 * @param {Element} textarea - The textarea element
 * @param {string} prefix - The prefix to insert
 */
function insertLinePrefix(textarea, prefix) {
  const start = textarea.selectionStart;
  const value = textarea.value;

  // Find the beginning of the current line
  const lineStart = value.lastIndexOf("\n", start - 1) + 1;
  const lineEnd = value.indexOf("\n", start);
  const actualLineEnd = lineEnd === -1 ? value.length : lineEnd;
  const currentLine = value.substring(lineStart, actualLineEnd);

  // Check if the line already has this prefix
  if (currentLine.startsWith(prefix)) {
    // Remove the prefix
    const newLine = currentLine.substring(prefix.length);
    textarea.value =
      value.substring(0, lineStart) + newLine + value.substring(actualLineEnd);
    textarea.setSelectionRange(start - prefix.length, start - prefix.length);
  } else {
    // Add the prefix
    const newLine = prefix + currentLine;
    textarea.value =
      value.substring(0, lineStart) + newLine + value.substring(actualLineEnd);
    textarea.setSelectionRange(start + prefix.length, start + prefix.length);
  }

  // Trigger auto-resize and change events
  textarea.dispatchEvent(new Event("input"));
  textarea.focus();
}

/**
 * Insert an ordered list item with proper numbering
 * @param {Element} textarea - The textarea element
 */
function insertOrderedListItem(textarea) {
  const start = textarea.selectionStart;
  const value = textarea.value;

  // Find the beginning of the current line
  const lineStart = value.lastIndexOf("\n", start - 1) + 1;
  const lineEnd = value.indexOf("\n", start);
  const actualLineEnd = lineEnd === -1 ? value.length : lineEnd;
  const currentLine = value.substring(lineStart, actualLineEnd);

  // Check if there's already a numbered list item
  const listItemMatch = currentLine.match(/^(\d+)\.\s/);
  if (listItemMatch) {
    // Remove the numbering
    const newLine = currentLine.substring(listItemMatch[0].length);
    textarea.value =
      value.substring(0, lineStart) + newLine + value.substring(actualLineEnd);
    textarea.setSelectionRange(
      start - listItemMatch[0].length,
      start - listItemMatch[0].length,
    );
  } else {
    // Look for the previous line to determine the number
    let number = 1;
    const prevLineEnd = lineStart - 1;
    if (prevLineEnd > 0) {
      const prevLineStart = value.lastIndexOf("\n", prevLineEnd - 1) + 1;
      const prevLine = value.substring(prevLineStart, prevLineEnd);
      const prevMatch = prevLine.match(/^(\d+)\.\s/);
      if (prevMatch) {
        number = parseInt(prevMatch[1]) + 1;
      }
    }

    // Add the numbered prefix
    const prefix = `${number}. `;
    const newLine = prefix + currentLine;
    textarea.value =
      value.substring(0, lineStart) + newLine + value.substring(actualLineEnd);
    textarea.setSelectionRange(start + prefix.length, start + prefix.length);
  }

  // Trigger auto-resize and change events
  textarea.dispatchEvent(new Event("input"));
  textarea.focus();
}

/**
 * Insert a markdown link with placeholder text
 * @param {Element} textarea - The textarea element
 */
function insertMarkdownLink(textarea) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const selectedText = textarea.value.substring(start, end);

  let linkText, linkUrl, replacement;

  if (selectedText) {
    // If text is selected, use it as the link text
    linkText = selectedText;
    linkUrl = "url";
    replacement = `[${linkText}](${linkUrl})`;
  } else {
    // No selection, insert template
    linkText = "link text";
    linkUrl = "url";
    replacement = `[${linkText}](${linkUrl})`;
  }

  textarea.value =
    textarea.value.substring(0, start) + replacement + textarea.value.substring(end);

  // Select the URL part for easy editing
  const urlStart = start + linkText.length + 3; // [link text](
  const urlEnd = urlStart + linkUrl.length;
  textarea.setSelectionRange(urlStart, urlEnd);

  // Trigger auto-resize and change events
  textarea.dispatchEvent(new Event("input"));
  textarea.focus();
}

/**
 * Auto-save note during editing
 * @param {Element} noteElement - The note DOM element
 * @param {Object} noteData - The note data object
 * @param {string} content - The current content
 */
function autoSaveNote(noteElement, noteData, content) {
  const updatedData = NoteDataUtils.createNoteData(noteData, content);
  // CRITICAL: Update the DOM element's data to ensure consistency for next edit
  noteElement.noteData = updatedData;

  updateNote(window.location.href, noteData.id, updatedData).then(success => {
    if (success) {
      console.log(`[Web Notes] Auto-saved note ${noteData.id}`);
    } else {
      console.error(`[Web Notes] Auto-save failed for note ${noteData.id}`);
    }
  });
}

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
    const cacheKey = `${noteData.elementSelector || ""}-${noteData.elementXPath || ""}`;

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

    // Enhanced styling with modern gradients and smooth transitions
    const isAnchored = targetElement !== null;
    note.style.cssText = `
      position: absolute;
      background: ${NoteColorUtils.getColorValue(noteData.backgroundColor || "light-yellow")};
      color: #2c3e50;
      padding: 10px 14px;
      border-radius: 8px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      font-size: 13px;
      font-weight: 500;
      line-height: 1.4;
      letter-spacing: 0.25px;
      box-shadow: 0 3px 12px rgba(0, 0, 0, 0.12), 0 1px 3px rgba(0, 0, 0, 0.08);
      z-index: 10000;
      cursor: move;
      border: 1px solid ${isAnchored ? "rgba(33, 150, 243, 0.2)" : "rgba(233, 30, 99, 0.2)"};
      min-width: 85px;
      max-width: 220px;
      word-wrap: break-word;
      opacity: 0;
      transform: scale(0.8);
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
    `;

    // Get display content (note should already be migrated)
    const displayContent = NoteDataUtils.getDisplayContent(noteData);

    // Set note content (HTML for markdown, escaped HTML for plain text)
    if (displayContent.isMarkdown) {
      note.innerHTML = displayContent.html;
    } else {
      note.innerHTML = displayContent.html; // Already escaped by getDisplayContent
    }

    // Store the full note data on the element for editing
    note.noteData = noteData;

    // Add to page temporarily to get accurate dimensions for positioning
    note.style.visibility = "hidden"; // Hide during positioning
    document.body.appendChild(note);

    // Calculate final position with offset support
    const finalPosition = calculateNotePosition(noteData, targetElement);

    // Apply position (no restrictions - notes can be positioned anywhere)
    note.style.left = `${finalPosition.x}px`;
    note.style.top = `${finalPosition.y}px`;
    note.style.visibility = "visible"; // Show the note

    // Add hover and focus effects
    addInteractiveEffects(note, isAnchored);

    // Make the note draggable
    makeDraggable(note, noteData, targetElement);

    // Add double-click editing functionality
    addEditingCapability(note, noteData);

    // Create text highlighting if selection data exists
    if (noteData.selectionData && noteData.selectionData.selectedText) {
      const highlightColor = NoteColorUtils.getColorValue(noteData.backgroundColor || "light-yellow");
      createTextHighlight(noteData, highlightColor);
    }

    // Animate in with a slight delay for smooth appearance
    requestAnimationFrame(() => {
      note.style.opacity = "1";
      note.style.transform = "scale(1)";

      // Ensure note has minimum visibility after animation
      setTimeout(() => {
        ensureNoteVisibility(note, noteData);
      }, TIMING.FADE_ANIMATION_DELAY);
    });

    // Enhanced logging
    const offsetX = noteData.offsetX || 0;
    const offsetY = noteData.offsetY || 0;
    console.log(
      `[Web Notes] Displaying draggable note ${finalPosition.isAnchored ? "anchored to DOM element" : "at fallback position"}: ` +
        `${noteData.elementSelector || noteData.elementXPath || "absolute coordinates"} ` +
        `with offset (${offsetX}, ${offsetY}) at position (${finalPosition.x}, ${finalPosition.y})`,
    );
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

      // Remove existing notes and highlights
      document.querySelectorAll(".web-note").forEach(note => note.remove());

      // Clear all highlights
      noteHighlights.forEach((highlight, noteId) => {
        removeTextHighlight(noteId);
      });
      noteHighlights.clear();

      // Load notes for new URL with debouncing
      setTimeout(loadExistingNotes, TIMING.DOM_UPDATE_DELAY);
    }
  }, TIMING.URL_MONITOR_INTERVAL);
}

// Start monitoring
startUrlMonitoring();

// Add window resize handling with debouncing
window.addEventListener("resize", debounce(handleWindowResize, TIMING.RESIZE_DEBOUNCE));

// Note: Scroll handling removed to prevent repositioning during normal scrolling
// Notes should only be repositioned when truly inaccessible (outside page bounds)

// Clean up on page unload to prevent memory leaks
window.addEventListener("beforeunload", () => {
  if (urlCheckInterval) {
    clearInterval(urlCheckInterval);
    urlCheckInterval = null;
  }

  // Clean up editing state
  if (EditingState.currentlyEditingNote) {
    exitEditMode(EditingState.currentlyEditingNote, true); // Save on page unload
  }

  // Clear all auto-save timeouts
  EditingState.autosaveTimeouts.forEach(timeout => clearTimeout(timeout));
  EditingState.autosaveTimeouts.clear();

  // Clean up any remaining note elements and highlights
  document.querySelectorAll(".web-note").forEach(note => note.remove());

  // Clear all highlights
  noteHighlights.forEach((highlight, noteId) => {
    removeTextHighlight(noteId);
  });
  noteHighlights.clear();
});

// Also use modern navigation API if available
if ("navigation" in window) {
  window.navigation.addEventListener("navigate", () => {
    console.log("[Web Notes] Navigation detected, reloading notes");
    setTimeout(() => {
      // Clear element cache for new page
      elementCache.clear();

      // Remove existing notes and highlights
      document.querySelectorAll(".web-note").forEach(note => note.remove());

      // Clear all highlights
      noteHighlights.forEach((highlight, noteId) => {
        removeTextHighlight(noteId);
      });
      noteHighlights.clear();

      // Load notes for new URL
      loadExistingNotes();
    }, 100);
  });
}

/**
 * Create a note at specific coordinates
 * @param {number} noteNumber - The note number
 * @param {Object} coords - Click coordinates with target element
 * @param {string} [backgroundColor="light-yellow"] - Optional background color for the note
 */
function createNoteAtCoords(noteNumber, coords, backgroundColor = "light-yellow") {
  try {
    // Generate unique note ID
    const noteId = `web-note-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;

    // Use selected text if available, otherwise default note text
    let noteText;
    if (coords && coords.selectedText) {
      noteText = coords.selectedText;
    } else {
      noteText = `MY NOTE #${noteNumber}`;
    }

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

    // Create enhanced note data with markdown support and selection data
    const baseData = {
      id: noteId,
      url: window.location.href,
      elementSelector: elementSelector,
      elementXPath: elementXPath,
      fallbackPosition: fallbackPosition || {
        x: posLeft,
        y: posTop,
      },
      offsetX: 0,
      offsetY: 0,
      timestamp: Date.now(),
      isVisible: true,
      backgroundColor: backgroundColor,
      // Include selection data if text was selected
      selectionData: coords && coords.selectionData ? coords.selectionData : null,
    };

    const noteData = NoteDataUtils.createNoteData(baseData, noteText);
    displayNote(noteData);

    // Store in chrome storage using normalized URL
    getNotes().then(function (result) {
      const notes = result || {};
      const normalizedUrl = normalizeUrlForNoteStorage(window.location.href);
      const urlNotes = notes[normalizedUrl] || [];
      urlNotes.push(noteData);
      notes[normalizedUrl] = urlNotes;

      setNotes(notes).then(function () {
        if (chrome.runtime.lastError) {
          console.error("[Web Notes] Failed to save note:", chrome.runtime.lastError);
        } else {
          console.log("[Web Notes] Note saved successfully to normalized URL");
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

/**
 * Handle note deletion with confirmation dialog
 * @param {Element} noteElement - The note DOM element
 * @param {Object} noteData - The note data object
 */
async function handleNoteDelete(noteElement, noteData) {
  try {
    // Create custom confirmation dialog to maintain consistency with extension styling
    const confirmed = await createCustomConfirmDialog(
      "Delete Note",
      "Are you sure you want to delete this note? This action cannot be undone.",
      "Delete",
      "Cancel",
    );

    if (!confirmed) {
      console.log(`[Web Notes] Note deletion cancelled by user: ${noteData.id}`);
      return;
    }

    // Exit edit mode without saving
    exitEditMode(noteElement, false);

    // Remove text highlighting first
    removeTextHighlight(noteData.id);

    // Remove note from DOM with animation
    noteElement.style.transition = "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)";
    noteElement.style.opacity = "0";
    noteElement.style.transform = "scale(0.8)";

    setTimeout(() => {
      if (noteElement.parentNode) {
        noteElement.remove();
        console.log(`[Web Notes] Note ${noteData.id} removed from DOM`);
      }
    }, 300);

    // Delete from storage
    const success = await deleteNote(window.location.href, noteData.id);

    if (success) {
      console.log(`[Web Notes] Successfully deleted note ${noteData.id}`);

      // Clear editing state if this was the currently editing note
      if (EditingState.currentlyEditingNote === noteElement) {
        EditingState.currentlyEditingNote = null;
      }

      // Clear any pending auto-save timeouts
      if (EditingState.autosaveTimeouts.has(noteData.id)) {
        clearTimeout(EditingState.autosaveTimeouts.get(noteData.id));
        EditingState.autosaveTimeouts.delete(noteData.id);
      }
    } else {
      console.error(`[Web Notes] Failed to delete note ${noteData.id} from storage`);
      // Show error message to user (note is already removed from DOM, but this indicates a storage issue)
      showTemporaryMessage(
        "Failed to delete note from storage. The note may reappear on page reload.",
        "error",
      );
    }
  } catch (error) {
    console.error("[Web Notes] Error during note deletion:", error);
    showTemporaryMessage("Error occurred while deleting note", "error");
  }
}

/**
 * Create a custom styled confirmation dialog
 * @param {string} title - Dialog title
 * @param {string} message - Dialog message
 * @param {string} confirmText - Confirm button text
 * @param {string} cancelText - Cancel button text
 * @returns {Promise<boolean>} Promise resolving to user choice
 */
function createCustomConfirmDialog(title, message, confirmText, cancelText) {
  return new Promise(resolve => {
    // Create overlay
    const overlay = document.createElement("div");
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      z-index: 10002;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: opacity 0.2s ease;
    `;

    // Create dialog
    const dialog = document.createElement("div");
    dialog.style.cssText = `
      background: white;
      border-radius: 12px;
      padding: 24px;
      min-width: 320px;
      max-width: 400px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      transform: scale(0.8);
      transition: transform 0.2s ease;
    `;

    // Create title
    const titleElement = document.createElement("h3");
    titleElement.textContent = title;
    titleElement.style.cssText = `
      margin: 0 0 12px 0;
      font-size: 18px;
      font-weight: 600;
      color: #333;
    `;

    // Create message
    const messageElement = document.createElement("p");
    messageElement.textContent = message;
    messageElement.style.cssText = `
      margin: 0 0 24px 0;
      font-size: 14px;
      line-height: 1.5;
      color: #666;
    `;

    // Create button container
    const buttonContainer = document.createElement("div");
    buttonContainer.style.cssText = `
      display: flex;
      gap: 12px;
      justify-content: flex-end;
    `;

    // Create cancel button
    const cancelButton = document.createElement("button");
    cancelButton.textContent = cancelText;
    cancelButton.style.cssText = `
      padding: 10px 20px;
      border: 1px solid #ddd;
      background: white;
      color: #666;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    `;

    // Create confirm button
    const confirmButton = document.createElement("button");
    confirmButton.textContent = confirmText;
    confirmButton.style.cssText = `
      padding: 10px 20px;
      border: none;
      background: #f44336;
      color: white;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    `;

    // Add hover effects
    cancelButton.addEventListener("mouseenter", () => {
      cancelButton.style.background = "#f5f5f5";
      cancelButton.style.borderColor = "#ccc";
    });

    cancelButton.addEventListener("mouseleave", () => {
      cancelButton.style.background = "white";
      cancelButton.style.borderColor = "#ddd";
    });

    confirmButton.addEventListener("mouseenter", () => {
      confirmButton.style.background = "#d32f2f";
    });

    confirmButton.addEventListener("mouseleave", () => {
      confirmButton.style.background = "#f44336";
    });

    // Handle responses
    function handleResponse(result) {
      overlay.style.opacity = "0";
      dialog.style.transform = "scale(0.8)";

      setTimeout(() => {
        if (overlay.parentNode) {
          overlay.remove();
        }
        resolve(result);
      }, 200);
    }

    cancelButton.addEventListener("click", e => {
      e.preventDefault();
      e.stopPropagation();
      handleResponse(false);
    });

    confirmButton.addEventListener("click", e => {
      e.preventDefault();
      e.stopPropagation();
      handleResponse(true);
    });

    // Handle overlay click (cancel)
    overlay.addEventListener("click", e => {
      if (e.target === overlay) {
        handleResponse(false);
      }
    });

    // Handle escape key
    function handleEscapeKey(e) {
      if (e.key === "Escape") {
        e.preventDefault();
        document.removeEventListener("keydown", handleEscapeKey);
        handleResponse(false);
      }
    }
    document.addEventListener("keydown", handleEscapeKey);

    // Assemble dialog
    buttonContainer.appendChild(cancelButton);
    buttonContainer.appendChild(confirmButton);
    dialog.appendChild(titleElement);
    dialog.appendChild(messageElement);
    dialog.appendChild(buttonContainer);
    overlay.appendChild(dialog);

    // Add to page and animate in
    document.body.appendChild(overlay);

    // Animate in
    requestAnimationFrame(() => {
      overlay.style.opacity = "1";
      dialog.style.transform = "scale(1)";
    });

    // Focus confirm button for accessibility
    setTimeout(() => {
      confirmButton.focus();
    }, 100);
  });
}

/**
 * Show a temporary message to the user
 * @param {string} message - Message to show
 * @param {string} type - Message type ('error', 'success', 'info')
 */
function showTemporaryMessage(message, type = "info") {
  try {
    const messageElement = document.createElement("div");
    messageElement.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: ${type === "error" ? "#f44336" : type === "success" ? "#4caf50" : "#2196f3"};
      color: white;
      padding: 12px 16px;
      border-radius: 6px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      font-weight: 500;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
      z-index: 10003;
      max-width: 300px;
      opacity: 0;
      transform: translateX(100%);
      transition: all 0.3s ease;
    `;

    messageElement.textContent = message;
    document.body.appendChild(messageElement);

    // Animate in
    requestAnimationFrame(() => {
      messageElement.style.opacity = "1";
      messageElement.style.transform = "translateX(0)";
    });

    // Remove after 4 seconds
    setTimeout(() => {
      messageElement.style.opacity = "0";
      messageElement.style.transform = "translateX(100%)";
      setTimeout(() => {
        if (messageElement.parentNode) {
          messageElement.remove();
        }
      }, 300);
    }, 4000);
  } catch (error) {
    console.error("[Web Notes] Error showing temporary message:", error);
    // Fallback to alert if custom message fails
    alert(message);
  }
}
