/**
 * Sharing Functionality
 * Handles sharing of individual notes, pages, and sites
 */

/* global showTemporaryMessage, isServerAuthenticated, SharingInterface, getNoteDataFromElement */

/**
 * Share an individual note
 * @param {HTMLElement} textarea - The textarea element from note editing
 */
async function handleNoteSharing(textarea) {
  try {
    // Find the note element and data
    const noteElement = textarea.closest(".web-note");
    if (!noteElement) {
      showTemporaryMessage("Error: Cannot identify note for sharing", "error");
      return;
    }

    const noteData = getNoteDataFromElement(noteElement);
    if (!noteData) {
      showTemporaryMessage("Error: Cannot access note data for sharing", "error");
      return;
    }

    // Prepare page data
    const pageData = {
      url: window.location.href,
      title: document.title || window.location.href,
      domain: window.location.hostname,
    };

    // Open sharing dialog
    if (typeof SharingInterface !== "undefined") {
      await SharingInterface.createSharingDialog(noteData, pageData);
    } else {
      showTemporaryMessage("Sharing feature not available", "error");
    }
  } catch (error) {
    console.error("[YAWN] Error opening note sharing dialog:", error);
    showTemporaryMessage("Failed to open sharing dialog", "error");
  }
}

/**
 * Handle page sharing
 */
async function handlePageSharing() {
  try {
    const pageUrl = window.location.href;
    const pageTitle = document.title || pageUrl;

    if (typeof SharingInterface !== "undefined") {
      await SharingInterface.showPageSharingDialog(pageUrl, pageTitle);
    } else {
      showTemporaryMessage("Sharing feature not available", "error");
    }
  } catch (error) {
    console.error("[YAWN] Error opening page sharing dialog:", error);
    showTemporaryMessage("Failed to open page sharing dialog", "error");
  }
}

/**
 * Handle site sharing
 */
async function handleSiteSharing() {
  try {
    const domain = window.location.hostname;

    if (typeof SharingInterface !== "undefined") {
      await SharingInterface.showSiteSharingDialog(domain);
    } else {
      showTemporaryMessage("Sharing feature not available", "error");
    }
  } catch (error) {
    console.error("[YAWN] Error opening site sharing dialog:", error);
    showTemporaryMessage("Failed to open site sharing dialog", "error");
  }
}

/**
 * Get note data from a note element
 * @param {HTMLElement} noteElement - The note element
 * @returns {Object|null} Note data or null if not found
 */
function getNoteDataFromElement(noteElement) {
  try {
    const noteIdAttr = noteElement.getAttribute("data-note-id");
    if (!noteIdAttr) {
      return null;
    }

    // Get current content from the note
    const contentElement = noteElement.querySelector(".note-content, textarea");
    const content = contentElement ? contentElement.value || contentElement.textContent || contentElement.innerHTML : "";

    // Extract other note properties if available
    const backgroundColor = noteElement.style.backgroundColor || "light-yellow";
    const isMarkdown = noteElement.classList.contains("markdown-note") || false;

    return {
      id: noteIdAttr,
      content: content,
      backgroundColor: backgroundColor,
      isMarkdown: isMarkdown,
      timestamp: Date.now(), // Current timestamp as fallback
      url: window.location.href,
    };
  } catch (error) {
    console.error("[YAWN] Error extracting note data from element:", error);
    return null;
  }
}

/**
 * Add context menu options for sharing
 * This function will be called when context menu is requested
 */
async function addSharingContextMenuOptions() {
  // This will be handled by the background script
  // We'll send messages to request context menu updates

  try {
    // Check if sharing is available and user is authenticated
    const isAuth = await isServerAuthenticated();
    const canShare = typeof SharingInterface !== "undefined" && isAuth;

    if (canShare) {
      // Send message to background script to update context menu
      chrome.runtime
        .sendMessage({
          type: "updateContextMenu",
          data: {
            hasSharingCapability: true,
            pageUrl: window.location.href,
            pageTitle: document.title,
            domain: window.location.hostname,
          },
        })
        .catch(error => {
          console.log("[YAWN] Context menu update message failed (expected if background script not ready):", error);
        });
    }
  } catch (error) {
    console.error("[YAWN] Error setting up sharing context menu:", error);
  }
}

/**
 * Handle sharing for a note at specific coordinates (from context menu)
 * @param {number} x - X coordinate
 * @param {number} y - Y coordinate
 */
async function handleNoteContextSharing(x, y) {
  try {
    // Find note element at the specified coordinates
    const element = document.elementFromPoint(x, y);
    if (!element) {
      showTemporaryMessage("No note found at this location", "info");
      return;
    }

    const noteElement = element.closest(".web-note");
    if (!noteElement) {
      showTemporaryMessage("No note found at this location", "info");
      return;
    }

    const noteData = getNoteDataFromElement(noteElement);
    if (!noteData) {
      showTemporaryMessage("Unable to access note data", "error");
      return;
    }

    const pageData = {
      url: window.location.href,
      title: document.title || window.location.href,
      domain: window.location.hostname,
    };

    if (typeof SharingInterface !== "undefined") {
      await SharingInterface.createSharingDialog(noteData, pageData);
    } else {
      showTemporaryMessage("Sharing feature not available", "error");
    }
  } catch (error) {
    console.error("[YAWN] Error handling note context sharing:", error);
    showTemporaryMessage("Failed to share note", "error");
  }
}

/**
 * Check and update sharing status indicators
 * This will be called periodically to show sharing status on notes
 */
async function updateSharingStatusIndicators() {
  try {
    // Only proceed if sharing interface is available and user is authenticated
    const isAuth = await isServerAuthenticated();
    if (typeof SharingInterface === "undefined" || !isAuth) {
      return;
    }

    const noteElements = document.querySelectorAll(".web-note");

    for (const noteElement of noteElements) {
      const noteData = getNoteDataFromElement(noteElement);
      if (!noteData) continue;

      try {
        // Check if note is shared
        const sharingStatus = await SharingInterface.getSharingStatus("note", noteData.id);

        // Add/remove sharing indicator
        updateNoteSharingIndicator(noteElement, sharingStatus.isShared);
      } catch (error) {
        // Silently continue if sharing status check fails
        console.debug("[YAWN] Failed to check sharing status for note:", noteData.id, error);
      }
    }
  } catch (error) {
    console.error("[YAWN] Error updating sharing status indicators:", error);
  }
}

/**
 * Update sharing indicator on a note element
 * @param {HTMLElement} noteElement - The note element
 * @param {boolean} isShared - Whether the note is shared
 */
function updateNoteSharingIndicator(noteElement, isShared) {
  try {
    // Remove existing indicator
    const existingIndicator = noteElement.querySelector(".sharing-indicator");
    if (existingIndicator) {
      existingIndicator.remove();
    }

    // Add indicator if shared
    if (isShared) {
      const indicator = document.createElement("div");
      indicator.className = "sharing-indicator";
      indicator.title = "This note is shared";
      indicator.innerHTML = "👥";
      indicator.style.cssText = `
        position: absolute;
        top: 2px;
        right: 2px;
        font-size: 12px;
        background: rgba(255, 255, 255, 0.9);
        border-radius: 50%;
        width: 18px;
        height: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1001;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
      `;

      noteElement.appendChild(indicator);
    }
  } catch (error) {
    console.error("[YAWN] Error updating sharing indicator:", error);
  }
}
