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
          resolve(
            result[EXTENSION_CONSTANTS.STATS_KEY] || EXTENSION_CONSTANTS.DEFAULT_STATS,
          );
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
 * Gets notes from storage with error handling
 * @returns {Promise<Object>} Promise resolving to notes object organized by URL
 */
async function getNotes() {
  try {
    return new Promise(resolve => {
      chrome.storage.local.get([EXTENSION_CONSTANTS.NOTES_KEY], result => {
        if (chrome.runtime.lastError) {
          logError("Failed to get notes", chrome.runtime.lastError);
          resolve({});
        } else {
          resolve(result[EXTENSION_CONSTANTS.NOTES_KEY] || {});
        }
      });
    });
  } catch (error) {
    logError("Error in getNotes", error);
    return {};
  }
}

/**
 * Save notes to storage with error handling
 * @param {Object} notes - Notes object organized by URL
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function setNotes(notes) {
  try {
    return new Promise(resolve => {
      chrome.storage.local.set({ [EXTENSION_CONSTANTS.NOTES_KEY]: notes }, () => {
        if (chrome.runtime.lastError) {
          logError("Failed to set notes", chrome.runtime.lastError);
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });
  } catch (error) {
    logError("Error in setNotes", error);
    return false;
  }
}

/**
 * Update a single note in storage with enhanced URL matching
 * @param {string} url - The URL where the note exists
 * @param {string} noteId - The note ID to update
 * @param {Object} noteData - The updated note data
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function updateNote(url, noteId, noteData) {
  try {
    const notes = await getNotes();
    const matchingUrls = findMatchingUrlsInStorage(url, notes);

    // Try to find the note in any of the matching URL variations
    for (const matchingUrl of matchingUrls) {
      const urlNotes = notes[matchingUrl] || [];
      const noteIndex = urlNotes.findIndex(note => note.id === noteId);

      if (noteIndex !== -1) {
        urlNotes[noteIndex] = { ...urlNotes[noteIndex], ...noteData, lastEdited: Date.now() };
        notes[matchingUrl] = urlNotes;
        return await setNotes(notes);
      }
    }

    // If not found in existing URLs, try adding to normalized URL
    const normalizedUrl = normalizeUrlForNoteStorage(url);
    if (!matchingUrls.includes(normalizedUrl)) {
      logError("Note not found for update", { url, noteId, searchedUrls: matchingUrls });
      return false;
    }

    logError("Note not found for update", { url, noteId });
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
    if (!url || typeof url !== 'string') {
      logError("Invalid URL for normalization", url);
      return url || '';
    }

    const urlObj = new URL(url);
    // Remove the hash/fragment (everything after #)
    urlObj.hash = '';

    // Keep query parameters as they're important for dynamic page content
    return urlObj.toString();
  } catch (error) {
    // If URL parsing fails, try simple string manipulation as fallback
    logError("URL parsing failed, using string fallback", error);

    const hashIndex = url.indexOf('#');
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
 * @param {string} url - The URL where to add the note
 * @param {Object} noteData - The note data to add
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function addNote(url, noteData) {
  try {
    const notes = await getNotes();
    const normalizedUrl = normalizeUrlForNoteStorage(url);
    const urlNotes = notes[normalizedUrl] || [];
    urlNotes.push(noteData);
    notes[normalizedUrl] = urlNotes;
    return await setNotes(notes);
  } catch (error) {
    logError("Error adding note", error);
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
  const restrictedProtocols = [
    "chrome:",
    "chrome-extension:",
    "edge:",
    "moz-extension:",
  ];
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
    EXTENSION_CONSTANTS,
    logError,
    getStats,
    setStats,
    getNotes,
    setNotes,
    updateNote,
    addNote,
    normalizeUrlForNoteStorage,
    findMatchingUrlsInStorage,
    getNotesForUrl,
    isTabValid,
    safeApiCall,
  };
}
