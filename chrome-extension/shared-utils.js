/**
 * Shared utilities for Web Notes Chrome Extension
 * Common functions used across background, popup, and content scripts
 */

/* eslint-env webextensions */

// Constants
const EXTENSION_CONSTANTS = {
  STATS_KEY: "extensionStats",
  NOTES_KEY: "webNotes",
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
function logError(context, error, prefix = "[Web Notes]") {
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
 * Gets configuration from chrome.storage.sync
 * @returns {Promise<Object>} Promise resolving to config object
 */
async function getWNConfig() {
  try {
    return new Promise(resolve => {
      chrome.storage.sync.get(["syncServerUrl", "useChromeSync"], result => {
        if (chrome.runtime.lastError) {
          logError("Failed to get config", chrome.runtime.lastError);
          resolve({ syncServerUrl: "", useChromeSync: false });
        } else {
          resolve({
            syncServerUrl: result.syncServerUrl || "",
            useChromeSync: result.useChromeSync || false,
          });
        }
      });
    });
  } catch (error) {
    logError("Error in getConfig", error);
    return { syncServerUrl: "", useChromeSync: false };
  }
}

/**
 * Saves configuration to chrome.storage.sync
 * @param {Object} config - Configuration object
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function setWNConfig(config) {
  try {
    return new Promise(resolve => {
      chrome.storage.sync.set(config, () => {
        if (chrome.runtime.lastError) {
          logError("Failed to set config", chrome.runtime.lastError);
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });
  } catch (error) {
    logError("Error in setConfig", error);
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
 * If server sync is enabled, fetches from server and merges with local cache
 * @returns {Promise<Object>} Promise resolving to notes object organized by URL
 */
async function getNotes() {
  try {
    const config = await getWNConfig();
    const storage = config.useChromeSync ? chrome.storage.sync : chrome.storage.local;

    // Get local notes first
    const localNotes = await new Promise(resolve => {
      storage.get([EXTENSION_CONSTANTS.NOTES_KEY], result => {
        if (chrome.runtime.lastError) {
          logError("Failed to get local notes", chrome.runtime.lastError);
          resolve({});
        } else {
          resolve(result[EXTENSION_CONSTANTS.NOTES_KEY] || {});
        }
      });
    });

    // If server sync is enabled, check authentication and fetch from server
    if (config.syncServerUrl && typeof ServerAPI !== "undefined") {
      // Check if server sync is enabled and authentication is available
      const isServerEnabled = await ServerAPI.isEnabled();
      const isAuthenticated = await ServerAPI.isAuthenticatedMode();

      console.log(`[Web Notes] Server sync enabled: ${isServerEnabled}, authenticated: ${isAuthenticated}`);

      if (isServerEnabled && isAuthenticated) {
        const serverNotes = await (typeof ErrorHandler !== "undefined"
          ? ErrorHandler.withErrorHandling(
              "fetch_notes",
              async () => {
                const currentUrl = window.location?.href;
                if (currentUrl) {
                  const serverNotes = await ServerAPI.fetchNotesForPage(currentUrl);
                  const normalizedUrl = normalizeUrlForNoteStorage(currentUrl);

                  // Convert server notes to extension format
                  const convertedNotes = serverNotes.map(serverNote => ServerAPI.convertFromServerFormat(serverNote));

                  // Set URL for each note
                  convertedNotes.forEach(note => {
                    note.url = currentUrl;
                  });

                  // Merge server notes with local notes
                  const mergedNotes = { ...localNotes };
                  mergedNotes[normalizedUrl] = convertedNotes;

                  console.log(`[Web Notes] Merged ${convertedNotes.length} server notes with local notes`);
                  return mergedNotes;
                }
                return localNotes;
              },
              { showUserFeedback: false }
            ) // Don't show feedback for background fetches
          : (async () => {
              try {
                const currentUrl = window.location?.href;
                if (currentUrl) {
                  const serverNotes = await ServerAPI.fetchNotesForPage(currentUrl);
                  const normalizedUrl = normalizeUrlForNoteStorage(currentUrl);

                  const convertedNotes = serverNotes.map(serverNote => ServerAPI.convertFromServerFormat(serverNote));

                  convertedNotes.forEach(note => {
                    note.url = currentUrl;
                  });

                  const mergedNotes = { ...localNotes };
                  mergedNotes[normalizedUrl] = convertedNotes;

                  console.log(`[Web Notes] Merged ${convertedNotes.length} server notes with local notes`);
                  return mergedNotes;
                }
              } catch (serverError) {
                console.warn("[Web Notes] Server fetch failed, using local notes:", serverError);
              }
              return localNotes;
            })());

        if (serverNotes) {
          return serverNotes;
        }
      } else if (isServerEnabled && !isAuthenticated) {
        console.log("[Web Notes] Server configured but user not authenticated, using local notes only");
      }
    }

    return localNotes;
  } catch (error) {
    logError("Error in getNotes", error);
    return {};
  }
}

/**
 * Save notes to appropriate storage based on configuration
 * If server sync is enabled, also syncs to server
 * @param {Object} notes - Notes object organized by URL
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function setNotes(notes) {
  try {
    const config = await getWNConfig();
    const storage = config.useChromeSync ? chrome.storage.sync : chrome.storage.local;

    // Save to local storage first
    const localSuccess = await new Promise(resolve => {
      storage.set({ [EXTENSION_CONSTANTS.NOTES_KEY]: notes }, () => {
        if (chrome.runtime.lastError) {
          logError("Failed to set notes locally", chrome.runtime.lastError);
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });

    // If server sync is enabled and user is authenticated, also save to server
    if (config.syncServerUrl && typeof ServerAPI !== "undefined" && localSuccess) {
      try {
        // Check authentication before attempting server sync
        const isAuthenticated = await ServerAPI.isAuthenticatedMode();
        if (!isAuthenticated) {
          console.log("[Web Notes] User not authenticated, skipping server sync");
          return localSuccess;
        }

        // Only sync notes for current page to avoid bulk operations
        const currentUrl = window.location?.href;
        if (currentUrl) {
          const normalizedUrl = normalizeUrlForNoteStorage(currentUrl);
          const pageNotes = notes[normalizedUrl] || [];

          if (pageNotes.length > 0) {
            await ServerAPI.bulkSyncNotes(currentUrl, pageNotes);
            console.log(`[Web Notes] Synced ${pageNotes.length} notes to server`);
          }
        }
      } catch (serverError) {
        // Handle authentication errors gracefully
        if (
          serverError.message === "AUTHENTICATION_REQUIRED" ||
          (serverError.message && (serverError.message.includes("HTTP 401") || serverError.message.includes("HTTP 403")))
        ) {
          console.log("[Web Notes] Authentication failed during sync, notes saved locally only:", serverError.message);
        } else {
          console.warn("[Web Notes] Server sync failed, notes saved locally:", serverError);
        }
        // Local save succeeded, so still return true
      }
    }

    return localSuccess;
  } catch (error) {
    logError("Error in setNotes", error);
    return false;
  }
}

/**
 * Update a single note in storage, searching across URL variations that match
 * when normalized (ignoring anchor fragments)
 * If server sync is enabled, also updates on server
 * @param {string} url - The URL where the note exists
 * @param {string} noteId - The note ID to update
 * @param {Object} noteData - The updated note data
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function updateNote(url, noteId, noteData) {
  try {
    const config = await getWNConfig();
    const notes = await getNotes();
    const matchingUrls = findMatchingUrlsInStorage(url, notes);

    // Try to find the note in any of the matching URL variations
    for (const matchingUrl of matchingUrls) {
      const urlNotes = notes[matchingUrl] || [];
      const noteIndex = urlNotes.findIndex(note => note.id === noteId);

      if (noteIndex !== -1) {
        const existingNote = urlNotes[noteIndex];
        const updatedNote = {
          ...existingNote,
          ...noteData,
          lastEdited: Date.now(),
        };

        urlNotes[noteIndex] = updatedNote;
        notes[matchingUrl] = urlNotes;

        // Save locally first
        const localSuccess = await setNotes(notes);

        // If server sync is enabled and note has server ID, update on server
        if (config.syncServerUrl && typeof ServerAPI !== "undefined" && localSuccess) {
          try {
            // Check authentication before attempting server sync
            const isAuthenticated = await ServerAPI.isAuthenticatedMode();
            if (!isAuthenticated) {
              console.log("[Web Notes] User not authenticated, skipping server update");
            } else {
              if (existingNote.serverId) {
                await ServerAPI.updateNote(existingNote.serverId, updatedNote);
                console.log(`[Web Notes] Updated note ${existingNote.serverId} on server`);
              } else {
                // Note doesn't have server ID, create it on server
                const serverNote = await ServerAPI.createNote(url, updatedNote);
                // Update local note with server ID
                updatedNote.serverId = serverNote.id;
                await setNotes(notes);
                console.log(`[Web Notes] Created note ${serverNote.id} on server during update`);
              }
            }
          } catch (serverError) {
            // Handle authentication errors gracefully
            if (serverError.message === "AUTHENTICATION_REQUIRED") {
              console.log("[Web Notes] Authentication required for server update, note updated locally only");
            } else {
              console.warn("[Web Notes] Server update failed, note updated locally:", serverError);
            }
          }
        }

        return localSuccess;
      }
    }

    // Note not found in any matching URL variations
    logError("Note not found for update", { url, noteId, searchedUrls: matchingUrls });
    return false;
  } catch (error) {
    logError("Error updating note", error);
    return false;
  }
}

/**
 * Normalize URL for note storage by removing anchor fragments while preserving query parameters
 * This allows notes to be visible across anchor navigation within the same page
 * @param {string} url - The URL to normalize
 * @returns {string} Normalized URL without anchor fragment
 */
function normalizeUrlForNoteStorage(url) {
  try {
    if (!url || typeof url !== "string") {
      logError("Invalid URL for normalization", url);
      return url || "";
    }

    const urlObj = new URL(url);
    // Remove the hash/fragment (everything after #)
    urlObj.hash = "";

    // Keep query parameters as they're important for dynamic page content
    return urlObj.toString();
  } catch (error) {
    // If URL parsing fails, try simple string manipulation as fallback
    logError("URL parsing failed, using string fallback", error);

    const hashIndex = url.indexOf("#");
    if (hashIndex !== -1) {
      return url.substring(0, hashIndex);
    }
    return url;
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

    for (const storedUrl of Object.keys(notes)) {
      const normalizedStored = normalizeUrlForNoteStorage(storedUrl);
      if (normalizedStored === normalizedTarget) {
        matchingUrls.push(storedUrl);
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
 * If server sync is enabled, also creates on server
 * @param {string} url - The URL where to add the note
 * @param {Object} noteData - The note data to add
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function addNote(url, noteData) {
  try {
    const config = await getWNConfig();
    const notes = await getNotes();
    const normalizedUrl = normalizeUrlForNoteStorage(url);
    const urlNotes = notes[normalizedUrl] || [];

    // Add to local storage first
    urlNotes.push(noteData);
    notes[normalizedUrl] = urlNotes;
    const localSuccess = await setNotes(notes);

    // If server sync is enabled, also create on server
    if (config.syncServerUrl && typeof ServerAPI !== "undefined" && localSuccess) {
      try {
        // Check authentication before attempting server sync
        const isAuthenticated = await ServerAPI.isAuthenticatedMode();
        if (!isAuthenticated) {
          console.log("[Web Notes] User not authenticated, skipping server create");
        } else {
          const serverNote = await ServerAPI.createNote(url, noteData);
          // Update local note with server ID
          noteData.serverId = serverNote.id;
          await setNotes(notes);
          console.log(`[Web Notes] Created note ${serverNote.id} on server`);
        }
      } catch (serverError) {
        // Handle authentication errors gracefully
        if (serverError.message === "AUTHENTICATION_REQUIRED") {
          console.log("[Web Notes] Authentication required for server create, note saved locally only");
        } else {
          console.warn("[Web Notes] Server create failed, note saved locally:", serverError);
        }
      }
    }

    return localSuccess;
  } catch (error) {
    logError("Error adding note", error);
    return false;
  }
}

/**
 * Delete a note from storage, searching across URL variations that match when normalized
 * If server sync is enabled, also deletes from server
 * @param {string} url - The URL where the note exists
 * @param {string} noteId - The note ID to delete
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function deleteNote(url, noteId) {
  try {
    const config = await getWNConfig();
    const notes = await getNotes();
    const matchingUrls = findMatchingUrlsInStorage(url, notes);
    let noteFound = false;
    let deletedNote = null;

    // Try to find and delete the note from any of the matching URL variations
    for (const matchingUrl of matchingUrls) {
      const urlNotes = notes[matchingUrl] || [];
      const noteIndex = urlNotes.findIndex(note => note.id === noteId);

      if (noteIndex !== -1) {
        deletedNote = urlNotes[noteIndex];

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
        console.log(`[Web Notes] Deleted note ${noteId} from URL: ${matchingUrl}`);
        break;
      }
    }

    if (!noteFound) {
      logError("Note not found for deletion", {
        url,
        noteId,
        searchedUrls: matchingUrls,
      });
      return false;
    }

    // Save locally first
    const localSuccess = await setNotes(notes);

    // If server sync is enabled and note has server ID, delete from server
    if (config.syncServerUrl && typeof ServerAPI !== "undefined" && deletedNote?.serverId && localSuccess) {
      try {
        // Check authentication before attempting server sync
        const isAuthenticated = await ServerAPI.isAuthenticatedMode();
        if (!isAuthenticated) {
          console.log("[Web Notes] User not authenticated, skipping server delete");
        } else {
          await ServerAPI.deleteNote(deletedNote.serverId);
          console.log(`[Web Notes] Deleted note ${deletedNote.serverId} from server`);
        }
      } catch (serverError) {
        // Handle authentication errors gracefully
        if (serverError.message === "AUTHENTICATION_REQUIRED") {
          console.log("[Web Notes] Authentication required for server delete, note deleted locally only");
        } else {
          console.warn("[Web Notes] Server delete failed, note deleted locally:", serverError);
        }
      }
    }

    return localSuccess;
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
    normalizeUrlForNoteStorage,
    findMatchingUrlsInStorage,
    getNotesForUrl,
    isTabValid,
    safeApiCall,
  };
}
