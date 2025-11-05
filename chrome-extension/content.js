// Web Notes - Content script

/* global EXTENSION_CONSTANTS, NoteDataUtils, updateNote, deleteNote, normalizeUrlForNoteStorage */
/* global getNotesForUrl, findMatchingUrlsInStorage */
/* global createColorDropdown, handleColorSelection */
/* global TIMING, EditingState, noteHighlights, MAX_HIGHLIGHTS, MAX_SELECTION_LENGTH, lastRightClickCoords, elementCache */
/* global handleNoteSharing, handlePageSharing, handleSiteSharing, getNoteDataFromElement, addSharingContextMenuOptions */
/* global handleNoteContextSharing, updateSharingStatusIndicators, updateNoteSharingIndicator */
/* global extractPageDOM, estimateTokenCount, findSemanticBoundaries, extractParentContext */
/* global handleGenerateDOMTestNotes, handleShowAIContextDialog */

console.log("Web Notes - Content script loaded!");

/**
 * Check authentication on page load (token validation/refresh happens during AuthManager initialization)
 * @returns {Promise<boolean>} True if authenticated
 */
async function checkAuthenticationOnLoad() {
  try {
    // Check if server sync is configured
    const config = await getWNConfig();
    if (!config.syncServerUrl) {
      return false;
    }

    // Check authentication status (AuthManager initialization handles token validation/refresh)
    const isAuth = await isServerAuthenticated();
    if (isAuth) {
      console.log("[YAWN] Authenticated with server on page load");
    }
    return isAuth;
  } catch (error) {
    console.error("[YAWN] Error checking authentication on load:", error);
    return false;
  }
}

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
      console.log("[YARN] Invalid range containers");
      return null;
    }

    // Validate selection size
    const selectedText = selection.toString().trim();
    if (selectedText.length > MAX_SELECTION_LENGTH) {
      console.log(`[YARN] Selected text exceeds maximum length (${MAX_SELECTION_LENGTH} chars)`);
      return null;
    }

    if (selectedText.length === 0) {
      return null;
    }

    const startContainer = range.startContainer;
    const endContainer = range.endContainer;

    // Only support selections within element nodes or their text children
    const startElement = startContainer.nodeType === Node.TEXT_NODE ? startContainer.parentElement : startContainer;
    const endElement = endContainer.nodeType === Node.TEXT_NODE ? endContainer.parentElement : endContainer;

    if (!startElement || !endElement) {
      return null;
    }

    // Validate that range doesn't span critical elements
    const commonAncestor = range.commonAncestorContainer;
    const commonElement = commonAncestor.nodeType === Node.TEXT_NODE ? commonAncestor.parentElement : commonAncestor;

    if (commonElement && commonElement.closest) {
      const criticalElement = commonElement.closest("script, style, iframe, object, embed");
      if (criticalElement) {
        console.warn("[YAWN] Cannot highlight within critical elements (script/style/iframe)");
        return null;
      }
    }

    // Generate selectors for the start and end elements
    let startSelector, endSelector;

    try {
      startSelector = generateOptimalSelector(startElement);
      endSelector = generateOptimalSelector(endElement);
    } catch (error) {
      console.log("[YAWN] Error generating selectors:", error);
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
      commonAncestorSelector: generateOptimalSelector(
        range.commonAncestorContainer.nodeType === Node.TEXT_NODE
          ? range.commonAncestorContainer.parentElement
          : range.commonAncestorContainer,
      ).cssSelector,
    };
  } catch (error) {
    console.warn("[YAWN] Error capturing selection data:", error);
    return null;
  }
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Add ping response for injection detection
  if (message.action === "ping") {
    sendResponse({ success: true });
    return true;
  }

  if (message.action === "getLastClickCoords") {
    // Return the last right-click coordinates
    sendResponse({
      coords: lastRightClickCoords,
      success: true,
    });
  } else if (message.action === "createNote") {
    // Create note with provided data
    createNoteAtCoords(message.noteNumber, message.coords, message.selectionText);
    sendResponse({ success: true });
  }
});

/**
 * Load and display existing notes for the current URL with enhanced URL matching
 */
async function loadExistingNotes() {
  try {
    // Check authentication on page load (validates/refreshes token if needed)
    await checkAuthenticationOnLoad();
    const normalizedUrl = normalizeUrlForNoteStorage(window.location.href);

    getNotes(normalizedUrl).then(async function (result) {
      if (chrome.runtime.lastError) {
        console.log("[YAWN] Failed to load notes:", chrome.runtime.lastError);
        return;
      }

      const notes = result || {};

      // Use enhanced URL matching to find all notes that match the current URL
      const urlNotes = getNotesForUrl(normalizedUrl, notes);

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
        notes[normalizedUrl] = migratedNotes;

        // Clean up old URL variations to avoid duplicates after migration
        const matchingUrls = findMatchingUrlsInStorage(normalizedUrl, notes);
        for (const oldUrl of matchingUrls) {
          if (oldUrl !== normalizedUrl && notes[oldUrl]) {
            delete notes[oldUrl];
          }
        }

        setNotes(notes, normalizedUrl).then(function (result) {
          if (chrome.runtime.lastError) {
            console.log("[YAWN] Failed to save migrated notes:", chrome.runtime.lastError);
          }
        });
      }
    });
  } catch (error) {
    console.error("[YAWN] Error loading existing notes:", error);
  }
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
      console.log(`[YAWN] Auto-saved note ${noteData.id}`);
    } else {
      console.log(`[YAWN] Auto-save failed for note ${noteData.id}`);
    }
  });
}

/**
 * Display a note on the page with optimized DOM queries
 * @param {Object} noteData - The note data object
 */
async function displayNote(noteData) {
  try {
    // Check if note already exists on page
    if (document.getElementById(noteData.id)) {
      return;
    }

    // Check authentication status for server features
    const isAuthenticated = await isServerAuthenticated();

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
      max-width: 520px;
      word-wrap: break-word;
      opacity: 0;
      transform: scale(0.8);
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
    `;

    // Get display content (note should already be migrated)
    const displayContent = NoteDataUtils.getDisplayContent(noteData);

    // Create a wrapper for note content and buttons
    const noteWrapper = document.createElement("div");
    noteWrapper.style.cssText = `
      position: relative;
      width: 100%;
      height: 100%;
    `;

    // Create content div
    const contentDiv = document.createElement("div");
    contentDiv.className = "note-content";
    // Set note content (HTML for markdown, escaped HTML for plain text)
    if (displayContent.isMarkdown) {
      contentDiv.innerHTML = displayContent.html;
    } else {
      contentDiv.innerHTML = displayContent.html; // Already escaped by getDisplayContent
    }

    // Create "Open Details" button (external link icon)
    const detailsButton = document.createElement("button");
    detailsButton.className = "note-details-button";
    detailsButton.innerHTML = `<svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
      <path d="M9 3v1H13.5L6 11.5L7.5 13L15 5.5V10h1V3H9z"/>
      <path d="M4 4v10h10v-4h1v4.5c0 .3-.2.5-.5.5h-11c-.3 0-.5-.2-.5-.5v-11c0-.3.2-.5.5-.5H8v1H4z"/>
    </svg>`;
    detailsButton.title = "Open note details in new tab";
    detailsButton.style.cssText = `
      position: absolute;
      top: 2px;
      right: 2px;
      width: 20px;
      height: 20px;
      background: rgba(33, 150, 243, 0.9);
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      z-index: 10001;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: all 0.2s ease;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    `;

    // Add hover effect to show button (only if authenticated and note has server ID)
    noteWrapper.addEventListener("mouseenter", () => {
      if (!note.classList.contains("editing") && isAuthenticated && noteData.serverId) {
        detailsButton.style.opacity = "1";
      }
    });

    noteWrapper.addEventListener("mouseleave", () => {
      detailsButton.style.opacity = "0";
    });

    // Add hover effect to button itself
    detailsButton.addEventListener("mouseenter", () => {
      detailsButton.style.background = "rgba(25, 118, 210, 1)";
      detailsButton.style.transform = "scale(1.1)";
    });

    detailsButton.addEventListener("mouseleave", () => {
      detailsButton.style.background = "rgba(33, 150, 243, 0.9)";
      detailsButton.style.transform = "scale(1)";
    });

    // Add click handler for details button
    detailsButton.addEventListener("click", async event => {
      event.preventDefault();
      event.stopPropagation();

      // Check if note has a server ID
      if (noteData.serverId) {
        // Get the base server URL
        const config = await getWNConfig();
        if (config.syncServerUrl) {
          const baseUrl = config.syncServerUrl.replace(/\/api$/, "");
          const detailsUrl = `${baseUrl}/app/notes/${noteData.serverId}`;
          window.open(detailsUrl, "_blank");
        }
      } else {
        console.log("[YAWN] Note has no server ID - not synced to server");
        // Optionally, we could show a message to the user here
      }
    });

    // Assemble the wrapper
    noteWrapper.appendChild(contentDiv);
    noteWrapper.appendChild(detailsButton);
    note.appendChild(noteWrapper);

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
  } catch (error) {
    console.error("[YAWN] Error displaying note:", error);
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
      console.log("[YAWN] URL changed, reloading notes");

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
 * @param {String} [selectText=null]
 * @param {string} [backgroundColor="light-yellow"] - Optional background color for the note
 */
async function createNoteAtCoords(noteNumber, coords, selectText = null, backgroundColor = "light-yellow") {
  try {
    // Generate unique note ID
    const noteId = `web-note-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;

    // Use selected text if available, otherwise default note text

    let targetElement = null;
    let elementSelector = null;
    let elementXPath = null;
    let fallbackPosition = null;
    let selectionData = coords && coords.selectionData ? coords.selectionData : null;

    if (coords) {
      // Store absolute coordinates as fallback
      fallbackPosition = { x: coords.x, y: coords.y };
    }

    if (coords && coords.target) {
      targetElement = coords.target;

      if (targetElement.nodeType !== Node.ELEMENT_NODE) {
        targetElement = document.elementFromPoint(coords.clientX, coords.clientY);
      }
      if (!targetElement) {
        fallbackPosition = { x: coords.x, y: coords.y };
      } else {
        // Generate optimal selector using hybrid approach
        const selectorResult = generateOptimalSelector(targetElement);
        elementSelector = selectorResult.cssSelector;
        elementXPath = selectorResult.xpath;
      }
    } else {
      const selection = window?.getSelection();
      const selData = captureSelectionData(selection);
      if (selData) {
        elementSelector = selData.startSelector;
        elementXPath = selData.startSelector;
        selectionData = selData;
      }
    }

    let noteText;
    if (selectText) {
      noteText = selectText;
    } else if (selectionData && selectionData.selectedText) {
      noteText = selectionData.selectedText;
    } else if (coords && coords.selectedText) {
      noteText = coords.selectedText;
    } else {
      noteText = `MY NOTE #${noteNumber}`;
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
      selectionData: selectionData,
    };

    const noteData = NoteDataUtils.createNoteData(baseData, noteText);
    displayNote(noteData);

    // Save note (will sync to server if authenticated)
    const success = await addNote(window.location.href, noteData);
    if (success) {
      console.log("[YAWN] Note saved successfully");

      // Update the displayed note with server ID if it was set
      const notes = await getNotes();
      const normalizedUrl = normalizeUrlForNoteStorage(window.location.href);
      const urlNotes = notes[normalizedUrl] || [];
      const savedNote = urlNotes.find(n => n.id === noteData.id);
      if (savedNote && savedNote.serverId) {
        // Update the noteData reference with the server ID
        noteData.serverId = savedNote.serverId;
        console.log("[YAWN] Note synced to server with ID:", savedNote.serverId);
      }
    } else {
      console.error("[YAWN] Failed to save note");
    }
  } catch (error) {
    console.error("[YAWN] Error creating note:", error);
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
      }
    }, 300);

    // Delete from storage
    const success = await deleteNote(window.location.href, noteData.id);

    if (success) {
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
      console.error(`[YAWN] Failed to delete note ${noteData.id} from storage`);
      // Show error message to user (note is already removed from DOM, but this indicates a storage issue)
      showTemporaryMessage("Failed to delete note from storage. The note may reappear on page reload.", "error");
    }
  } catch (error) {
    console.error("[YAWN] Error during note deletion:", error);
    showTemporaryMessage("Error occurred while deleting note", "error");
  }
}

/**
 * Handle messages from background script for sharing actions
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) {
    return;
  }

  // Handle async cases
  if (message.type === "checkSharingCapability") {
    (async () => {
      try {
        const isAuth = await isServerAuthenticated();
        const canShare = typeof SharingInterface !== "undefined" && isAuth;
        sendResponse({ canShare });
      } catch (error) {
        console.error("[YAWN] Error checking sharing capability:", error);
        sendResponse({ canShare: false });
      }
    })();
    return true; // Keep message channel open for async response
  }

  try {
    switch (message.type) {
      case "showPageRegistered":
        alert(`✓ Page "${message.title}" has been registered.\n\nYou can now generate AI context or add notes.`);
        sendResponse({ success: true });
        break;

      case "showRegistrationError":
        alert(`✗ Failed to register page.\n\nError: ${message.error}\n\nPlease try again.`);
        sendResponse({ success: true });
        break;

      case "shareCurrentPage":
        handlePageSharing();
        sendResponse({ success: true });
        break;

      case "shareCurrentSite":
        handleSiteSharing();
        sendResponse({ success: true });
        break;

      case "shareNoteAtPosition":
        handleNoteContextSharing(message.data.x, message.data.y);
        sendResponse({ success: true });
        break;

      case "showAIContextDialog":
        handleShowAIContextDialog();
        sendResponse({ success: true });
        break;

      case "generateDOMTestNotes":
        handleGenerateDOMNotes();
        sendResponse({ success: true });
        break;

      default:
        // Let other message handlers process this
        return;
    }
  } catch (error) {
    console.error("[YAWN] Error handling sharing message:", error);
    sendResponse({ success: false, error: error.message });
  }

  return true; // Keep message channel open for async response
});

// Initialize sharing functionality when document is ready
document.addEventListener("DOMContentLoaded", async () => {
  try {
    // Set up context menu options
    await addSharingContextMenuOptions();

    // Update sharing indicators periodically if authenticated
    const isAuth = await isServerAuthenticated();
    if (isAuth) {
      // Initial update
      setTimeout(updateSharingStatusIndicators, 2000);

      // Periodic updates every 5 minutes
      setInterval(updateSharingStatusIndicators, 5 * 60 * 1000);
    }
  } catch (error) {
    console.error("[YAWN] Error initializing sharing functionality:", error);
  }
});

// Also initialize if document is already ready
if (document.readyState === "loading") {
  // Already handled above
} else {
  // Document already loaded, initialize immediately
  (async () => {
    try {
      await addSharingContextMenuOptions();

      const isAuth = await isServerAuthenticated();
      if (isAuth) {
        setTimeout(updateSharingStatusIndicators, 2000);
        setInterval(updateSharingStatusIndicators, 5 * 60 * 1000);
      }
    } catch (error) {
      console.error("[YAWN] Error initializing sharing functionality on loaded document:", error);
    }
  })();
}

// Listen for auth state changes from popup/background
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== "sync") return;

  // Check if any auth-related keys changed
  const authKeys = ["auth_access_token", "auth_refresh_token", "auth_id_token", "auth_token_expires_at", "auth_user_info"];
  const authChanged = authKeys.some(key => key in changes);

  if (authChanged) {
    console.log("[YAWN] Auth state changed, reinitializing sharing features");

    // Reinitialize sharing features
    (async () => {
      try {
        await addSharingContextMenuOptions();

        const isAuth = await isServerAuthenticated();
        if (isAuth) {
          // User just logged in, update indicators
          setTimeout(updateSharingStatusIndicators, 2000);
        }
      } catch (error) {
        console.error("[YAWN] Error reinitializing after auth change:", error);
      }
    })();
  }
});
