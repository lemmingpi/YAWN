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
      chrome.contextMenus.create({
        id: EXTENSION_ID,
        title: MENU_TITLE,
        contexts: ["page", "selection", "link", "image"],
      });
    }, "Creating context menu");

    console.log("[Web Notes Extension] Context menu created successfully");
  } catch (error) {
    logError("Failed to create context menu", error);
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
        },
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
  if (info.menuItemId !== EXTENSION_ID) {
    return;
  }

  try {
    // Validate tab
    if (!isTabValid(tab)) {
      logError(
        "Invalid tab for script injection",
        `Tab ID: ${tab?.id}, URL: ${tab?.url}`,
      );
      return;
    }

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
    logError("Error handling context menu click", error);
  }
});

// Handle extension errors
chrome.runtime.onStartup.addListener(() => {
  console.log("[Web Notes Extension] Extension startup");
});
