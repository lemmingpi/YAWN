/**
 * Background script for Web Notes Chrome Extension
 * Handles context menu creation, click events, and error handling
 */

// Import shared utilities
importScripts("./shared-utils.js");
importScripts("./auth-manager.js");
importScripts("./server-api.js");

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

      // Register page menu item (hidden by default, shown when user is authenticated)
      chrome.contextMenus.create({
        id: "register-page",
        title: "📋 Register Page (without notes)",
        contexts: ["page"],
        visible: false, // Hidden by default, shown when user is authenticated
      });

      // DOM test auto-notes menu item (hidden by default, shown when user is authenticated)
      chrome.contextMenus.create({
        id: "generate-dom-test-notes",
        title: "🤖 Generate Auto Notes with DOM",
        contexts: ["page"],
        visible: false, // Hidden by default, shown when user is authenticated
      });
    }, "Creating context menu");

    console.log("[Web Notes Extension] Context menu created successfully");
  } catch (error) {
    logError("Failed to create context menu", error);
  }
}

/**
 * Update context menu visibility based on authentication
 * @param {boolean} isAuthenticated - Whether user is authenticated
 */
async function updateAuthenticatedContextMenus(isAuthenticated) {
  try {
    await safeApiCall(() => {
      // Update sharing submenu visibility
      chrome.contextMenus.update("share-submenu", {
        visible: isAuthenticated,
      });

      // Update register page menu visibility
      chrome.contextMenus.update("register-page", {
        visible: isAuthenticated,
      });

      // Update DOM test auto-notes menu visibility
      chrome.contextMenus.update("generate-dom-test-notes", {
        visible: isAuthenticated,
      });
    }, "Updating authenticated context menus");

    console.log(`[Web Notes Extension] Authenticated context menus ${isAuthenticated ? "enabled" : "disabled"}`);
  } catch (error) {
    // Silently fail if context menu doesn't exist yet
    console.debug("Context menu update failed (expected during initialization):", error);
  }
}

/**
 * Legacy function name for backward compatibility
 * @param {boolean} canShare - Whether sharing is available
 */
async function updateSharingContextMenu(canShare) {
  await updateAuthenticatedContextMenus(canShare);
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

      case "register-page":
        // Handle register page action
        await handleRegisterPage(tab);
        break;

      case "share-current-page":
        // Handle share page action
        await handleSharePage(info, tab);
        break;

      case "share-current-site":
        // Handle share site action
        await handleShareSite(info, tab);
        break;

      case "generate-dom-test-notes":
        // Handle DOM test auto-notes generation
        await handleGenerateDOMTestNotes(tab);
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
    const notes = await getNotes(tab.url);
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

/**
 * Handle register page context menu action
 * @param {Object} tab - Tab object
 */
async function handleRegisterPage(tab) {
  try {
    console.log("[Web Notes Extension] Register page requested via context menu");

    // Register the page without creating a note - call ServerAPI directly
    const pageData = await ServerAPI.registerPage(tab.url, tab.title);

    console.log("[Web Notes Extension] Page registered successfully:", pageData);

    // Open the server page in a new tab
    const baseUrl = await ServerAPI.getBaseUrl();
    const serverPageUrl = `${baseUrl}/app/pages/${pageData.id}`;
    chrome.tabs.create({ url: serverPageUrl });
  } catch (error) {
    console.error("[Web Notes Extension] Failed to register page:", error);

    // Send error message to content script to show alert
    chrome.tabs
      .sendMessage(tab.id, {
        type: "showRegistrationError",
        error: error.message || "Unknown error",
      })
      .catch(err => {
        console.warn("[Web Notes Extension] Could not send error message to tab:", err);
      });

    logError("Error handling register page action", error);
  }
}

/**
 * Handle DOM test auto-notes generation
 * @param {Object} tab - Tab object
 */
async function handleGenerateDOMTestNotes(tab) {
  try {
    console.log("[Web Notes Extension] Generate DOM test notes requested via context menu");

    // Send message to content script to extract DOM and generate notes
    chrome.tabs
      .sendMessage(tab.id, {
        type: "generateDOMTestNotes",
      })
      .then(response => {
        if (response && response.success) {
          console.log("[Web Notes Extension] DOM test notes generation initiated");
        }
      })
      .catch(err => {
        console.warn("[Web Notes Extension] Could not send message to tab:", err);
        // Try to inject content script first if it's not loaded
        injectContentScriptAndRetry(tab.id, {
          type: "generateDOMTestNotes",
        });
      });
  } catch (error) {
    logError("Error handling DOM test notes generation", error);
  }
}

// ===== SHARING MESSAGE HANDLING =====

/**
 * Handle messages from content scripts and popup
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message) {
    return;
  }

  // Handle API requests from content scripts (async)
  if (message.action && message.action.startsWith("API_")) {
    (async () => {
      try {
        let result;
        switch (message.action) {
          case "API_fetchNotesForPage":
            result = await ServerAPI.fetchNotesForPage(message.url);
            break;
          case "API_createNote":
            result = await ServerAPI.createNote(message.url, message.noteData);
            break;
          case "API_updateNote":
            result = await ServerAPI.updateNote(message.serverId, message.noteData);
            break;
          case "API_deleteNote":
            result = await ServerAPI.deleteNote(message.serverId);
            break;
          case "API_bulkSyncNotes":
            result = await ServerAPI.bulkSyncNotes(message.url, message.notes);
            break;
          case "API_sharePageWithUser":
            result = await ServerAPI.sharePageWithUser(message.pageId, message.userEmail, message.permissionLevel);
            break;
          case "API_shareSiteWithUser":
            result = await ServerAPI.shareSiteWithUser(message.siteId, message.userEmail, message.permissionLevel);
            break;
          case "API_getPageShares":
            result = await ServerAPI.getPageShares(message.pageId);
            break;
          case "API_getSiteShares":
            result = await ServerAPI.getSiteShares(message.siteId);
            break;
          case "API_updatePageSharePermission":
            result = await ServerAPI.updatePageSharePermission(
              message.pageId,
              message.userId,
              message.newPermission,
              message.isActive
            );
            break;
          case "API_updateSiteSharePermission":
            result = await ServerAPI.updateSiteSharePermission(
              message.siteId,
              message.userId,
              message.newPermission,
              message.isActive
            );
            break;
          case "API_removePageShare":
            result = await ServerAPI.removePageShare(message.pageId, message.userId);
            break;
          case "API_removeSiteShare":
            result = await ServerAPI.removeSiteShare(message.siteId, message.userId);
            break;
          case "API_getConfig":
            result = await ServerAPI.getConfig();
            break;
          default:
            throw new Error(`Unknown API action: ${message.action}`);
        }
        sendResponse({ success: true, data: result });
      } catch (error) {
        logError(`API call failed: ${message.action}`, error);
        sendResponse({ success: false, error: error.message });
      }
    })();
    return true; // Keep message channel open for async response
  }

  // Handle AUTH fetch requests from content scripts (async)
  if (message.action && message.action.startsWith("AUTH_")) {
    (async () => {
      try {
        let result;
        switch (message.action) {
          case "AUTH_register":
            result = await fetch(message.url, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
              },
              body: JSON.stringify(message.body),
            });
            break;
          case "AUTH_login":
            result = await fetch(message.url, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
              },
              body: JSON.stringify(message.body),
            });
            break;
          case "AUTH_validateToken":
            result = await fetch(message.url, {
              method: "GET",
              headers: {
                Authorization: `Bearer ${message.token}`,
                Accept: "application/json",
              },
            });
            break;
          default:
            throw new Error(`Unknown AUTH action: ${message.action}`);
        }

        // Process fetch response
        const ok = result.ok;
        const status = result.status;
        let data;
        const contentType = result.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          data = await result.json();
        } else {
          data = await result.text();
        }

        sendResponse({ success: ok, status: status, data: data });
      } catch (error) {
        logError(`AUTH call failed: ${message.action}`, error);
        sendResponse({ success: false, error: error.message });
      }
    })();
    return true; // Keep message channel open for async response
  }

  // Handle chrome.identity requests from content scripts (async)
  if (message.action && message.action.startsWith("IDENTITY_")) {
    (async () => {
      try {
        let result;
        switch (message.action) {
          case "IDENTITY_getAuthToken":
            result = await new Promise(resolve => {
              chrome.identity.getAuthToken(
                {
                  interactive: message.interactive,
                  scopes: message.scopes,
                },
                token => {
                  if (chrome.runtime.lastError) {
                    resolve({ error: chrome.runtime.lastError.message || String(chrome.runtime.lastError) });
                  } else {
                    resolve({ token });
                  }
                }
              );
            });
            sendResponse({ success: !result.error, data: result.token, error: result.error });
            break;
          case "IDENTITY_removeCachedAuthToken":
            result = await new Promise(resolve => {
              chrome.identity.removeCachedAuthToken({ token: message.token }, () => {
                if (chrome.runtime.lastError) {
                  resolve({ error: chrome.runtime.lastError.message || String(chrome.runtime.lastError) });
                } else {
                  resolve({ success: true });
                }
              });
            });
            sendResponse({ success: !result.error, error: result.error });
            break;
          default:
            throw new Error(`Unknown IDENTITY action: ${message.action}`);
        }
      } catch (error) {
        logError(`Identity call failed: ${message.action}`, error);
        sendResponse({ success: false, error: error.message });
      }
    })();
    return true; // Keep message channel open for async response
  }

  // Handle AuthManager requests from content scripts (async)
  if (message.action && message.action.startsWith("AUTHMANAGER_")) {
    (async () => {
      try {
        let result;

        // Ensure AuthManager is available
        if (typeof AuthManager === "undefined") {
          sendResponse({ success: false, error: "AuthManager not available" });
          return;
        }

        // Wait for initialization before processing requests
        const initialized = await AuthManager.waitForInitialization();
        if (!initialized) {
          sendResponse({ success: false, error: "AuthManager initialization timeout" });
          return;
        }

        switch (message.action) {
          case "AUTHMANAGER_isAuthenticated":
            result = AuthManager.isAuthenticated();
            sendResponse({ success: true, data: result });
            break;
          case "AUTHMANAGER_getCurrentToken":
            if (AuthManager.isAuthenticated()) {
              result = AuthManager.getCurrentToken();
              sendResponse({ success: true, data: result });
            } else {
              sendResponse({ success: false, data: null });
            }
            break;
          case "AUTHMANAGER_getCurrentUser":
            if (AuthManager.isAuthenticated()) {
              result = AuthManager.getCurrentUser();
              sendResponse({ success: true, data: result });
            } else {
              sendResponse({ success: false, data: null });
            }
            break;
          case "AUTHMANAGER_refreshTokenIfNeeded":
            result = await AuthManager.refreshTokenIfNeeded();
            sendResponse({ success: true, data: result });
            break;
          case "AUTHMANAGER_attemptAutoAuth":
            result = await AuthManager.attemptAutoAuth();
            sendResponse({ success: true, data: result });
            break;
          case "AUTHMANAGER_signIn":
            result = await AuthManager.signIn(message.interactive || false);
            sendResponse({ success: true, data: result });
            break;
          case "AUTHMANAGER_signOut":
            await AuthManager.signOut();
            sendResponse({ success: true });
            break;
          default:
            throw new Error(`Unknown AUTHMANAGER action: ${message.action}`);
        }
      } catch (error) {
        logError(`AuthManager call failed: ${message.action}`, error);
        sendResponse({ success: false, error: error.message });
      }
    })();
    return true; // Keep message channel open for async response
  }

  // Handle regular message types
  if (!message.type) {
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
