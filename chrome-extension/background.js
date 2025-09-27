/**
 * Background script for Web Notes Chrome Extension
 * Handles context menu creation, click events, and error handling
 */

// Import shared utilities
importScripts("./shared-utils.js");

// Constants
const EXTENSION_ID = "add-web-note";
const MENU_TITLE = "🗒️ Add Web Note";

// Use shared utility functions from shared-utils.js
// logError, safeApiCall, getStats, setStats, getNotes, isTabValid are now imported

// Track ongoing injections to prevent race conditions
const ongoingInjections = new Set();

/**
 * Creates context menu with error handling
 */
async function createContextMenu() {
  try {
    await safeApiCall(() => {
      // Main add note menu item
      chrome.contextMenus.create({
        id: EXTENSION_ID,
        title: MENU_TITLE,
        contexts: ["page", "selection", "link", "image"],
      });

      // Sharing submenu (will be shown/hidden based on authentication)
      chrome.contextMenus.create({
        id: "share-submenu",
        title: "🔗 Share",
        contexts: ["page"],
        visible: false, // Hidden by default, shown when user is authenticated
      });

      chrome.contextMenus.create({
        id: "share-current-page",
        parentId: "share-submenu",
        title: "Share Current Page",
        contexts: ["page"],
      });

      chrome.contextMenus.create({
        id: "share-current-site",
        parentId: "share-submenu",
        title: "Share Current Site",
        contexts: ["page"],
      });
    }, "Creating context menu");

    console.log("[Web Notes Extension] Context menu created successfully");
  } catch (error) {
    logError("Failed to create context menu", error);
  }
}

/**
 * Update context menu visibility based on sharing capability
 * @param {boolean} canShare - Whether sharing is available
 */
async function updateSharingContextMenu(canShare) {
  try {
    await safeApiCall(() => {
      chrome.contextMenus.update("share-submenu", {
        visible: canShare,
      });
    }, "Updating sharing context menu");

    console.log(`[Web Notes Extension] Sharing context menu ${canShare ? "enabled" : "disabled"}`);
  } catch (error) {
    // Silently fail if context menu doesn't exist yet
    console.debug("Context menu update failed (expected during initialization):", error);
  }
}

/**
 * Initializes extension stats
 */
async function initializeStats() {
  try {
    // Check if stats exist in storage directly, not via getStats()
    const result = await new Promise(resolve => {
      chrome.storage.local.get([EXTENSION_CONSTANTS.STATS_KEY], result => {
        if (chrome.runtime.lastError) {
          logError("Failed to check stats existence", chrome.runtime.lastError);
          resolve(null);
        } else {
          resolve(result);
        }
      });
    });

    if (!result || !result[EXTENSION_CONSTANTS.STATS_KEY]) {
      await setStats(EXTENSION_CONSTANTS.DEFAULT_STATS);
      console.log("[Web Notes Extension] Stats initialized");
    }
  } catch (error) {
    logError("Failed to initialize stats", error);
  }
}

/**
 * Creates a note using coordinates from content script
 * @param {number} tabId - Tab ID to send message to
 * @param {number} noteNumber - The note number for this URL
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function createNoteWithCoordinates(tabId, noteNumber) {
  try {
    // Check for ongoing operation in this tab
    if (ongoingInjections.has(tabId)) {
      logError("Note creation already in progress", `Tab ID: ${tabId}`);
      return false;
    }

    // Mark operation as ongoing
    ongoingInjections.add(tabId);

    // Get click coordinates from content script
    const response = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error("Message timeout"));
      }, EXTENSION_CONSTANTS.SCRIPT_INJECTION_TIMEOUT);

      chrome.tabs.sendMessage(tabId, { action: "getLastClickCoords" }, result => {
        clearTimeout(timeout);
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(result);
        }
      });
    });

    if (!response || !response.success) {
      logError("Failed to get click coordinates", "No valid response");
      return false;
    }

    // Send message to create note with coordinates
    const createResponse = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error("Note creation timeout"));
      }, EXTENSION_CONSTANTS.SCRIPT_INJECTION_TIMEOUT);

      chrome.tabs.sendMessage(
        tabId,
        {
          action: "createNote",
          noteNumber: noteNumber,
          coords: response.coords,
        },
        result => {
          clearTimeout(timeout);
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(result);
          }
        }
      );
    });

    return createResponse && createResponse.success;
  } catch (error) {
    logError(`Failed to create note in tab ${tabId}`, error);
    return false;
  } finally {
    // Always clean up the operation tracker
    ongoingInjections.delete(tabId);
  }
}

// Event Listeners

chrome.runtime.onInstalled.addListener(async () => {
  console.log("[Web Notes Extension] Extension installed/updated");

  try {
    await createContextMenu();
    await initializeStats();
  } catch (error) {
    logError("Error during extension initialization", error);
  }
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  try {
    // Validate tab
    if (!isTabValid(tab)) {
      logError("Invalid tab for context menu action", `Tab ID: ${tab?.id}, URL: ${tab?.url}`);
      return;
    }

    switch (info.menuItemId) {
      case EXTENSION_ID:
        // Handle add note action
        await handleAddNote(info, tab);
        break;

      case "share-current-page":
        // Handle share page action
        await handleSharePage(info, tab);
        break;

      case "share-current-site":
        // Handle share site action
        await handleShareSite(info, tab);
        break;

      default:
        console.log(`[Web Notes Extension] Unknown context menu item: ${info.menuItemId}`);
    }
  } catch (error) {
    logError("Error handling context menu click", error);
  }
});

/**
 * Handle add note context menu action
 * @param {Object} info - Context menu info
 * @param {Object} tab - Tab object
 */
async function handleAddNote(info, tab) {
  try {
    // Get next note number using enhanced URL matching
    const notes = await getNotes();
    const urlNotes = getNotesForUrl(tab.url, notes);
    const noteNumber = urlNotes.length + 1;

    // Get click coordinates from content script and create note
    const success = await createNoteWithCoordinates(tab.id, noteNumber);

    if (success) {
      // Update stats only on successful injection
      const stats = await getStats();
      await setStats({
        ...stats,
        contextMenuClicks: stats.contextMenuClicks + 1,
        notesCreated: stats.notesCreated + 1,
        lastSeen: Date.now(),
      });
    }
  } catch (error) {
    logError("Error handling add note action", error);
  }
}

/**
 * Handle share page context menu action
 * @param {Object} info - Context menu info
 * @param {Object} tab - Tab object
 */
async function handleSharePage(info, tab) {
  try {
    console.log("[Web Notes Extension] Share page requested via context menu");

    // Send message to content script to open sharing dialog
    chrome.tabs
      .sendMessage(tab.id, {
        type: "shareCurrentPage",
      })
      .catch(error => {
        console.error("[Web Notes Extension] Failed to send share page message:", error);
      });
  } catch (error) {
    logError("Error handling share page action", error);
  }
}

/**
 * Handle share site context menu action
 * @param {Object} info - Context menu info
 * @param {Object} tab - Tab object
 */
async function handleShareSite(info, tab) {
  try {
    console.log("[Web Notes Extension] Share site requested via context menu");

    // Send message to content script to open sharing dialog
    chrome.tabs
      .sendMessage(tab.id, {
        type: "shareCurrentSite",
      })
      .catch(error => {
        console.error("[Web Notes Extension] Failed to send share site message:", error);
      });
  } catch (error) {
    logError("Error handling share site action", error);
  }
}

// ===== SHARING MESSAGE HANDLING =====

/**
 * Handle messages from content scripts and popup
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) {
    return;
  }

  try {
    switch (message.type) {
      case "updateContextMenu":
        handleContextMenuUpdate(message.data);
        sendResponse({ success: true });
        break;

      case "getSharingCapability":
        // This will be handled by content script, just acknowledge
        sendResponse({ success: true });
        break;

      default:
        // Unknown message type, let other handlers process it
        return;
    }
  } catch (error) {
    logError("Error handling background message", error);
    sendResponse({ success: false, error: error.message });
  }

  return true; // Keep message channel open for async response
});

/**
 * Handle context menu update request
 * @param {Object} data - Update data
 */
async function handleContextMenuUpdate(data) {
  try {
    if (data && typeof data.hasSharingCapability === "boolean") {
      await updateSharingContextMenu(data.hasSharingCapability);
      console.log("[Web Notes Extension] Context menu updated based on sharing capability");
    }
  } catch (error) {
    logError("Error updating context menu", error);
  }
}

// Handle extension errors
chrome.runtime.onStartup.addListener(() => {
  console.log("[Web Notes Extension] Extension startup");
});
