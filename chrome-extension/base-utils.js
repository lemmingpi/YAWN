/**
 * Base Utilities Module
 * Contains core utility functions used across the extension
 * No dependencies on other extension modules to avoid circular dependencies
 */

/* eslint-env webextensions */

/**
 * Storage key constants
 */
const STORAGE_KEYS = {
  NOTES_KEY: "webNotes",
  STATS_KEY: "extensionStats",
  SYNC_SERVER_URL: "syncServerUrl",
  USE_CHROME_SYNC: "useChromeSync",
  JWT_TOKEN: "webNotesJWT",
  USER_INFO: "webNotesUser",
  AUTH_STATE: "webNotesAuthState",
  LAST_AUTH_CHECK: "webNotesLastAuthCheck",
};

/**
 * Gets configuration from chrome.storage.sync
 * @returns {Promise<Object>} Promise resolving to config object with syncServerUrl and useChromeSync
 */
async function getWNConfig() {
  try {
    return new Promise(resolve => {
      chrome.storage.sync.get([STORAGE_KEYS.SYNC_SERVER_URL, STORAGE_KEYS.USE_CHROME_SYNC], result => {
        if (chrome.runtime.lastError) {
          console.error("[YAWN] Failed to get config from storage:", chrome.runtime.lastError);
          resolve({ syncServerUrl: "", useChromeSync: false });
        } else {
          resolve({
            syncServerUrl: result[STORAGE_KEYS.SYNC_SERVER_URL] || "",
            useChromeSync: result[STORAGE_KEYS.USE_CHROME_SYNC] || false,
          });
        }
      });
    });
  } catch (error) {
    console.error("[YAWN] Error in getWNConfig:", error);
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
          console.error("[YAWN] Failed to set config:", chrome.runtime.lastError);
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });
  } catch (error) {
    console.error("[YAWN] Error in setWNConfig:", error);
    return false;
  }
}

/**
 * Normalize URL for consistent note storage
 * Removes hash/fragment but keeps query parameters
 * @param {string} url - The URL to normalize
 * @returns {string} Normalized URL
 */
function normalizeUrlForNoteStorage(url) {
  let urlStr = url;
  try {
    if (!url || typeof url !== "string") {
      console.error("[YAWN] Invalid URL for normalization:", url);
      return url || "";
    }

    const urlObj = new URL(url);
    // Remove the hash/fragment (everything after #)
    urlObj.hash = "";

    // Keep query parameters as they're important for dynamic page content
    urlStr = urlObj.toString();
  } catch (error) {
    // If URL parsing fails, try simple string manipulation as fallback
    console.error("[YAWN] URL parsing failed, using string fallback:", error);

    const hashIndex = url.indexOf("#");
    if (hashIndex !== -1) {
      urlStr = url.substring(0, hashIndex);
    } else {
      urlStr = url;
    }
  }
  if (urlStr.endsWith("/")) {
    urlStr = urlStr.substring(0, urlStr.length - 1);
  }
  return urlStr;
}

/**
 * Convert server note format to extension format
 * @param {Object} serverNote - Note in server format
 * @returns {Object} Note in extension format
 */
function convertNoteFromServerFormat(serverNote) {
  const anchorData = serverNote.anchor_data || {};

  return {
    id: serverNote.id, // Use database ID directly
    serverId: serverNote.id, // Keep for backwards compatibility
    content: serverNote.content || "",
    url: "", // Will be set by calling code
    elementSelector: anchorData.elementSelector || null,
    elementXPath: anchorData.elementXPath || null,
    fallbackPosition: {
      x: serverNote.position_x || 0,
      y: serverNote.position_y || 0,
    },
    offsetX: anchorData.offsetX || 0,
    offsetY: anchorData.offsetY || 0,
    timestamp: new Date(serverNote.created_at).getTime(),
    lastEdited: new Date(serverNote.updated_at).getTime(),
    isVisible: serverNote.is_active !== false,
    backgroundColor: anchorData.backgroundColor || "light-yellow",
    selectionData: anchorData.selectionData || null,
    isMarkdown: anchorData.isMarkdown || false,
    contentHash: anchorData.contentHash || null,
    // Mark as synced with server
    isSynced: true,
  };
}

/**
 * Centralized error logging with context
 * @param {string} context - Where the error occurred
 * @param {Error|any} error - The error object or message
 * @param {string} prefix - Optional prefix for log messages
 */
function logError(context, error, prefix = "[YAWN]") {
  console.error(`${prefix} ${context}:`, error);
}

// Export for use in other scripts
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    STORAGE_KEYS,
    getWNConfig,
    setWNConfig,
    normalizeUrlForNoteStorage,
    convertNoteFromServerFormat,
    logError,
  };
}
