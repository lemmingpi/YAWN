/**
 * Shared utilities for Web Notes Chrome Extension
 * Common functions used across background, popup, and content scripts
 */

/* eslint-env webextensions */

// Constants
const EXTENSION_CONSTANTS = {
  STATS_KEY: "extensionStats",
  SCRIPT_INJECTION_TIMEOUT: 5000,
  DEFAULT_STATS: {
    installDate: Date.now(),
    bannerShows: 0,
    popupOpens: 0,
    contextMenuClicks: 0,
    notesCreated: 0,
    lastSeen: Date.now(),
  },
};

/**
 * Centralized error logging with context
 * @param {string} context - Where the error occurred
 * @param {Error|any} error - The error object or message
 * @param {string} prefix - Optional prefix for log messages
 */
function logError(context, error, prefix = "[YAWN]") {
  console.error(`${prefix} ${context}:`, error);
}

/**
 * Gets extension stats from storage with error handling
 * @returns {Promise<Object>} Promise resolving to stats object
 */
async function getStats() {
  try {
    return new Promise(resolve => {
      chrome.storage.local.get([EXTENSION_CONSTANTS.STATS_KEY], result => {
        if (chrome.runtime.lastError) {
          logError("Failed to get stats", chrome.runtime.lastError);
          resolve(EXTENSION_CONSTANTS.DEFAULT_STATS);
        } else {
          resolve(result[EXTENSION_CONSTANTS.STATS_KEY] || EXTENSION_CONSTANTS.DEFAULT_STATS);
        }
      });
    });
  } catch (error) {
    logError("Error in getStats", error);
    return EXTENSION_CONSTANTS.DEFAULT_STATS;
  }
}

/**
 * Sets extension stats in storage with error handling
 * @param {Object} stats - Stats object to save
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function setStats(stats) {
  try {
    return new Promise(resolve => {
      chrome.storage.local.set({ [EXTENSION_CONSTANTS.STATS_KEY]: stats }, () => {
        if (chrome.runtime.lastError) {
          logError("Failed to set stats", chrome.runtime.lastError);
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });
  } catch (error) {
    logError("Error in setStats", error);
    return false;
  }
}

/**
 * Check if server sync is enabled
 * @returns {Promise<boolean>} True if server sync is enabled
 */
async function isServerSyncEnabled() {
  try {
    const config = await getWNConfig();
    return !!config.syncServerUrl;
  } catch (error) {
    logError("Failed to check server sync status", error);
    return false;
  }
}

/**
 * Check if user is authenticated for server operations
 * @returns {Promise<boolean>} True if authenticated requests should be made
 */
async function isServerAuthenticated() {
  try {
    // Check if we're in service worker (background) context
    const isServiceWorker = typeof importScripts === "function";

    if (isServiceWorker) {
      // Background service worker - check directly but ensure initialization
      if (typeof AuthManager === "undefined") {
        return false;
      }
      // Wait for initialization before checking
      await AuthManager.waitForInitialization();
      return AuthManager.isAuthenticated();
    } else {
      // Content script or popup - ask background script via message passing
      const response = await chrome.runtime.sendMessage({ action: "AUTHMANAGER_isAuthenticated" });
      return response.success && response.data === true;
    }
  } catch (error) {
    logError("Failed to check auth status", error);
    return false;
  }
}

/**
 * Gets notes from appropriate storage based on configuration
 * @returns {Promise<Object>} Promise resolving to notes object organized by URL
 */
async function getBytesUsed() {
  try {
    const config = await getWNConfig();
    const storage = config.useChromeSync ? chrome.storage.sync : chrome.storage.local;
    return new Promise(resolve => {
      storage.getBytesInUse(null, bytes => {
        if (chrome.runtime.lastError) {
          logError("Failed to get bytes used", chrome.runtime.lastError);
          resolve(-1);
        } else {
          resolve(bytes);
        }
      });
    });
  } catch (error) {
    logError("Error in getBytesUsed", error);
    return -1;
  }
}

/**
 * Gets notes from appropriate storage based on configuration
 * If authenticated with server: fetches from server
 * Otherwise: fetches from local storage
 * @returns {Promise<Object>} Promise resolving to notes object organized by URL
 */
async function getNotes(urlOverride = null) {
  try {
    // Check if user is authenticated with server
    const isServerEnabled = await isServerSyncEnabled();
    const isAuthenticated = await isServerAuthenticated();

    console.log(`[YAWN] Server sync enabled: ${isServerEnabled}, authenticated: ${isAuthenticated}`);
    const currentUrl = urlOverride || (typeof window !== "undefined" ? window.location?.href : null);
    const normalizedUrl = normalizeUrlForNoteStorage(currentUrl);

    // If authenticated with server, fetch from server only
    if (isServerEnabled && isAuthenticated) {
      try {
        if (currentUrl) {
          const response = await chrome.runtime.sendMessage({ action: "API_fetchNotesForPage", url: currentUrl });
          const serverNotes = response.success ? response.data : [];

          // Convert server notes to extension format
          const convertedNotes = serverNotes.map(serverNote => convertNoteFromServerFormat(serverNote));

          // Set URL for each note
          convertedNotes.forEach(note => {
            note.url = currentUrl;
          });

          const result = {};
          result[normalizedUrl] = convertedNotes;

          console.log(`[YAWN] Loaded ${convertedNotes.length} notes from server`);
          return result;
        }
        return {};
      } catch (serverError) {
        console.error("[YAWN] Server fetch failed:", serverError);
        return {};
      }
    }

    // Otherwise, fetch from local storage
    const config = await getWNConfig();
    const storage = config.useChromeSync ? chrome.storage.sync : chrome.storage.local;

    const localNotesMap = await new Promise(resolve => {
      storage.get([STORAGE_KEYS.NOTES_KEY], result => {
        if (chrome.runtime.lastError) {
          console.error("[YAWN] Failed to get local notes", chrome.runtime.lastError);
          resolve({});
        } else {
          resolve(result[STORAGE_KEYS.NOTES_KEY] || {});
        }
      });
    });
    const localNotes = localNotesMap[normalizedUrl] || [];
    console.log(`[YAWN] Loaded ${localNotes.length} notes from local storage`);
    return localNotesMap;
  } catch (error) {
    logError("Error in getNotes", error);
    return {};
  }
}

/**
 * Save notes to appropriate storage based on configuration
 * If authenticated with server: saves to server
 * Otherwise: saves to local storage
 * @param {Object} notes - Notes object organized by URL
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function setNotes(notes) {
  try {
    // Check if user is authenticated with server
    const isServerEnabled = await isServerSyncEnabled();
    const isAuthenticated = await isServerAuthenticated();

    // If authenticated with server, save to server only
    if (isServerEnabled && isAuthenticated) {
      try {
        // Sync notes for current page to server
        const currentUrl = window.location?.href;
        if (currentUrl) {
          const normalizedUrl = normalizeUrlForNoteStorage(currentUrl);
          const pageNotes = notes[normalizedUrl] || [];

          if (pageNotes.length > 0) {
            await chrome.runtime.sendMessage({ action: "API_bulkSyncNotes", url: currentUrl, notes: pageNotes });
            console.log(`[YAWN] Synced ${pageNotes.length} notes to server`);
            return true;
          }
        }
        return true;
      } catch (serverError) {
        console.error("[YAWN] Server sync failed:", serverError);
        return false;
      }
    }

    // Otherwise, save to local storage
    const config = await getWNConfig();
    const storage = config.useChromeSync ? chrome.storage.sync : chrome.storage.local;

    const localSuccess = await new Promise(resolve => {
      storage.set({ [STORAGE_KEYS.NOTES_KEY]: notes }, () => {
        if (chrome.runtime.lastError) {
          console.error("[YAWN] Failed to set notes locally:", chrome.runtime.lastError);
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });

    console.log("[YAWN] Saved notes to local storage");
    return localSuccess;
  } catch (error) {
    logError("Error in setNotes", error);
    return false;
  }
}

/**
 * Update a single note in storage
 * If authenticated with server: updates on server
 * Otherwise: updates in local storage
 * @param {string} url - The URL where the note exists
 * @param {string} noteId - The note ID to update
 * @param {Object} noteData - The updated note data
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function updateNote(url, noteId, noteData) {
  try {
    const isServerEnabled = await isServerSyncEnabled();
    const isAuthenticated = await isServerAuthenticated();

    // If authenticated with server, update on server
    if (isServerEnabled && isAuthenticated) {
      try {
        const updatedData = {
          ...noteData,
          lastEdited: Date.now(),
        };

        await chrome.runtime.sendMessage({
          action: "API_updateNote",
          serverId: noteId, // For server notes, noteId IS the serverId
          noteData: updatedData,
        });
        console.log(`[YAWN] Updated note ${noteId} on server`);
        return true;
      } catch (serverError) {
        console.error("[YAWN] Server update failed:", serverError);
        return false;
      }
    }

    // Otherwise, update in local storage
    const notes = await getNotes();
    const matchingUrls = findMatchingUrlsInStorage(url, notes);

    // Try to find the note in any of the matching URL variations
    for (const matchingUrl of matchingUrls) {
      const urlNotes = notes[matchingUrl] || [];
      const noteIndex = urlNotes.findIndex(note => note.id === noteId);

      if (noteIndex !== -1) {
        const updatedNote = {
          ...urlNotes[noteIndex],
          ...noteData,
          lastEdited: Date.now(),
        };

        urlNotes[noteIndex] = updatedNote;
        notes[matchingUrl] = urlNotes;

        const success = await setNotes(notes);
        console.log("[YAWN] Updated note in local storage");
        return success;
      }
    }

    // Note not found
    logError("Note not found for update", { url, noteId });
    return false;
  } catch (error) {
    logError("Error updating note", error);
    return false;
  }
}

/**
 * Find all URLs in storage that match the given URL (ignoring anchors)
 * This handles migration from exact URL matching to normalized URL matching
 * @param {string} targetUrl - The URL to find matches for
 * @param {Object} notes - The notes storage object
 * @returns {Array<string>} Array of matching URL keys found in storage
 */
function findMatchingUrlsInStorage(targetUrl, notes) {
  try {
    const normalizedTarget = normalizeUrlForNoteStorage(targetUrl);
    const matchingUrls = [];

    for (const url of Object.keys(notes)) {
      const normalizedStored = normalizeUrlForNoteStorage(url);
      if (normalizedStored === normalizedTarget) {
        matchingUrls.push(url);
      }
    }

    return matchingUrls;
  } catch (error) {
    logError("Error finding matching URLs", error);
    return [];
  }
}

/**
 * Get all notes for a URL, including notes stored under different anchor variations
 * @param {string} url - The URL to get notes for
 * @param {Object} allNotes - The complete notes storage object
 * @returns {Array} Combined array of all matching notes
 */
function getNotesForUrl(url, allNotes) {
  try {
    const matchingUrls = findMatchingUrlsInStorage(url, allNotes);
    const combinedNotes = [];

    for (const matchingUrl of matchingUrls) {
      const urlNotes = allNotes[matchingUrl] || [];
      combinedNotes.push(...urlNotes);
    }

    // Remove duplicates based on note ID (shouldn't happen, but safety check)
    const uniqueNotes = [];
    const seenIds = new Set();

    for (const note of combinedNotes) {
      if (!seenIds.has(note.id)) {
        seenIds.add(note.id);
        uniqueNotes.push(note);
      }
    }

    return uniqueNotes;
  } catch (error) {
    logError("Error getting notes for URL", error);
    return [];
  }
}

/**
 * Add a new note to storage
 * If authenticated with server: creates on server
 * Otherwise: saves to local storage
 * @param {string} url - The URL where to add the note
 * @param {Object} noteData - The note data to add
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function addNote(url, noteData) {
  try {
    const isServerEnabled = await isServerSyncEnabled();
    const isAuthenticated = await isServerAuthenticated();

    // If authenticated with server, create on server
    if (isServerEnabled && isAuthenticated) {
      try {
        const createResponse = await chrome.runtime.sendMessage({
          action: "API_createNote",
          url: url,
          noteData: noteData,
        });
        const serverNote = createResponse.success ? createResponse.data : null;
        if (serverNote) {
          noteData.serverId = serverNote.id;
          console.log(`[YAWN] Created note ${serverNote.id} on server`);
          return true;
        }
        return false;
      } catch (serverError) {
        console.error("[YAWN] Server create failed:", serverError);
        return false;
      }
    }

    // Otherwise, save to local storage
    const notes = await getNotes();
    const normalizedUrl = normalizeUrlForNoteStorage(url);
    const urlNotes = notes[normalizedUrl] || [];

    urlNotes.push(noteData);
    notes[normalizedUrl] = urlNotes;
    const success = await setNotes(notes);

    console.log(`[YAWN] Added note to local storage`);
    return success;
  } catch (error) {
    logError("Error adding note", error);
    return false;
  }
}

/**
 * Delete a note from storage
 * If authenticated with server: deletes from server
 * Otherwise: deletes from local storage
 * @param {string} url - The URL where the note exists
 * @param {string} noteId - The note ID to delete
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function deleteNote(url, noteId) {
  try {
    const isServerEnabled = await isServerSyncEnabled();
    const isAuthenticated = await isServerAuthenticated();

    // If authenticated with server, delete from server
    if (isServerEnabled && isAuthenticated) {
      try {
        await chrome.runtime.sendMessage({
          action: "API_deleteNote",
          serverId: noteId, // For server notes, noteId IS the serverId
        });
        console.log(`[YAWN] Deleted note ${noteId} from server`);
        return true;
      } catch (serverError) {
        console.error("[YAWN] Server delete failed:", serverError);
        return false;
      }
    }

    // Otherwise, delete from local storage
    const notes = await getNotes();
    const matchingUrls = findMatchingUrlsInStorage(url, notes);
    let noteFound = false;

    // Try to find and delete the note from any of the matching URL variations
    for (const matchingUrl of matchingUrls) {
      const urlNotes = notes[matchingUrl] || [];
      const noteIndex = urlNotes.findIndex(note => note.id === noteId);

      if (noteIndex !== -1) {
        // Remove the note from the array
        urlNotes.splice(noteIndex, 1);

        // Update storage
        if (urlNotes.length === 0) {
          // Remove the URL key entirely if no notes remain
          delete notes[matchingUrl];
        } else {
          notes[matchingUrl] = urlNotes;
        }

        noteFound = true;
        break;
      }
    }

    if (!noteFound) {
      logError("Note not found for deletion", { url, noteId });
      return false;
    }

    const success = await setNotes(notes);
    console.log("[YAWN] Deleted note from local storage");
    return success;
  } catch (error) {
    logError("Error deleting note", error);
    return false;
  }
}

/**
 * Validates tab before script injection
 * @param {Object} tab - Chrome tab object
 * @returns {boolean} Whether tab is valid for injection
 */
function isTabValid(tab) {
  if (!tab || !tab.id || tab.id === chrome.tabs.TAB_ID_NONE) {
    return false;
  }

  // Check for restricted URLs
  const restrictedProtocols = ["chrome:", "chrome-extension:", "edge:", "moz-extension:"];
  const url = tab.url || "";

  return !restrictedProtocols.some(protocol => url.startsWith(protocol));
}

/**
 * Safely executes Chrome API calls with error handling
 * @param {Function} apiCall - The Chrome API function to call
 * @param {string} context - Description of the operation
 * @returns {Promise} Promise that resolves with the result or rejects with error
 */
function safeApiCall(apiCall, context) {
  return new Promise((resolve, reject) => {
    try {
      const result = apiCall();
      if (chrome.runtime.lastError) {
        const error = new Error(chrome.runtime.lastError.message);
        logError(context, error);
        reject(error);
      } else {
        resolve(result);
      }
    } catch (error) {
      logError(context, error);
      reject(error);
    }
  });
}

// Export for use in other scripts (Node.js compatibility)
/* global module */
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    getStats,
    setStats,
    getNotes,
    setNotes,
    getWNConfig,
    setWNConfig,
    getBytesUsed,
    updateNote,
    addNote,
    deleteNote,
    findMatchingUrlsInStorage,
    getNotesForUrl,
    isTabValid,
    safeApiCall,
    isServerSyncEnabled,
    isServerAuthenticated,
  };
}
