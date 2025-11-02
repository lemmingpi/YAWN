/**
 * Popup script for Web Notes Chrome Extension
 * Handles popup UI interactions with comprehensive error handling
 * Uses shared utilities from shared-utils.js
 */

/* global EXTENSION_CONSTANTS, logError, getStats, setStats, isTabValid, showHelloWorldBanner, hideHelloWorldBanner */

// Use shared constants and functions
// EXTENSION_CONSTANTS, logError, getStats, setStats, isTabValid are imported

/**
 * Updates stats display in the popup
 */
async function updateStatsDisplay() {
  try {
    const statsContentElement = document.getElementById("stats-content");

    const useChromeSyncCheckbox = document.getElementById("use-chrome-sync");
    const syncServerUrlInput = document.getElementById("sync-server-url");

    if (!statsContentElement) {
      logError("Stats display update failed", "stats-content element not found");
      return;
    }

    const stats = await getStats();
    const config = await getWNConfig();
    if (useChromeSyncCheckbox && config) {
      useChromeSyncCheckbox.checked = !!config.useChromeSync;
    }
    if (syncServerUrlInput && config) {
      syncServerUrlInput.value = config.syncServerUrl || "";
    }

    const installDate = new Date(stats.installDate).toLocaleDateString();
    const lastSeen = new Date(stats.lastSeen).toLocaleString();

    // Clear existing content first
    while (statsContentElement.firstChild) {
      statsContentElement.removeChild(statsContentElement.firstChild);
    }

    // Create stats display safely using DOM methods
    const statsDiv = document.createElement("div");
    statsDiv.style.cssText = "font-size: 11px; line-height: 1.4;";
    const bytesUsed = (await getBytesUsed()) / 1024; // Convert to KB

    // Check server sync status
    let serverStatus = "Disabled";
    let authStatus = "Local Only";

    if (config.syncServerUrl) {
      serverStatus = "Configured";

      // Check authentication status if AuthManager is available
      if (typeof AuthManager !== "undefined") {
        const isAuthenticated = AuthManager.isAuthenticated();
        authStatus = isAuthenticated ? "Authenticated" : "Not Authenticated";
      }
    }

    const statsData = [
      `• Installed: ${installDate}`,
      `• Last seen: ${lastSeen}`,
      `• Storage Used: ${bytesUsed.toFixed(1)} KB`,
      `• Server Sync: ${serverStatus}`,
      `• Auth Status: ${authStatus}`,
    ];

    statsData.forEach(statText => {
      const statLine = document.createElement("div");
      statLine.textContent = statText;
      statsDiv.appendChild(statLine);
    });

    statsContentElement.appendChild(statsDiv);

    // Note: Stats initialization is handled by background script
    // This function only displays existing stats
  } catch (error) {
    logError("Error updating stats display", error);

    // Fallback display
    const statsContentElement = document.getElementById("stats-content");
    if (statsContentElement) {
      statsContentElement.textContent = "Error loading stats";
    }
  }
}

/**
 * Updates user authentication status display
 */
async function updateUserStatus() {
  try {
    const signedInView = document.getElementById("signed-in-view");
    const signedOutView = document.getElementById("signed-out-view");
    const userNameElement = document.getElementById("user-name");
    const userEmailElement = document.getElementById("user-email");

    if (!signedInView || !signedOutView) {
      logError("User status update failed", "Required elements not found");
      return;
    }

    // Always use message passing to background script - never direct AuthManager access
    const authResponse = await chrome.runtime.sendMessage({
      action: "AUTHMANAGER_isAuthenticated",
    });

    if (!authResponse.success) {
      // Show signed out view if check failed
      signedInView.style.display = "none";
      signedOutView.style.display = "block";
      return;
    }

    const isAuthenticated = authResponse.data;

    if (isAuthenticated) {
      // Get user information from background
      const userResponse = await chrome.runtime.sendMessage({
        action: "AUTHMANAGER_getCurrentUser",
      });

      if (userResponse.success && userResponse.data) {
        const user = userResponse.data;

        // Show signed in view
        signedInView.style.display = "block";
        signedOutView.style.display = "none";

        // Update user information
        if (userNameElement) {
          userNameElement.textContent = user.name || "Unknown User";
        }
        if (userEmailElement) {
          userEmailElement.textContent = user.email || "";
        }
      } else {
        // Show signed out view if no user data
        signedInView.style.display = "none";
        signedOutView.style.display = "block";
      }
    } else {
      // Show signed out view
      signedInView.style.display = "none";
      signedOutView.style.display = "block";
    }
  } catch (error) {
    logError("Error updating user status", error);

    // Fallback to signed out view
    const signedInView = document.getElementById("signed-in-view");
    const signedOutView = document.getElementById("signed-out-view");
    if (signedInView && signedOutView) {
      signedInView.style.display = "none";
      signedOutView.style.display = "block";
    }
  }
}

/**
 * Handle sign in button click
 */
async function handleSignIn() {
  try {
    const signInBtn = document.getElementById("sign-in-btn");
    if (signInBtn) {
      signInBtn.textContent = "Signing in...";
      signInBtn.disabled = true;
    }

    // Use message passing to background script
    const response = await chrome.runtime.sendMessage({
      action: "AUTHMANAGER_signIn",
      interactive: true,
    });

    if (response.success && response.data) {
      console.log("[Popup] Sign-in successful:", response.data);
      await updateUserStatus();
      await updateStatsDisplay();
    } else {
      showUserError("Sign-in failed: " + (response.error || "Unknown error"));
    }
  } catch (error) {
    logError("Sign-in error", error);
    showUserError("Sign-in failed: " + error.message);
  } finally {
    const signInBtn = document.getElementById("sign-in-btn");
    if (signInBtn) {
      signInBtn.textContent = "Sign In with Google";
      signInBtn.disabled = false;
    }
  }
}

/**
 * Handle sign out button click
 */
async function handleSignOut() {
  try {
    const signOutBtn = document.getElementById("sign-out-btn");
    if (signOutBtn) {
      signOutBtn.textContent = "Signing out...";
      signOutBtn.disabled = true;
    }

    // Use message passing to background script
    const response = await chrome.runtime.sendMessage({
      action: "AUTHMANAGER_signOut",
    });

    if (response.success) {
      console.log("[Popup] Sign-out successful");
      await updateUserStatus();
      await updateStatsDisplay();
    } else {
      showUserError("Sign-out failed: " + (response.error || "Unknown error"));
    }
  } catch (error) {
    logError("Sign-out error", error);
    showUserError("Sign-out failed: " + error.message);
  } finally {
    const signOutBtn = document.getElementById("sign-out-btn");
    if (signOutBtn) {
      signOutBtn.textContent = "Sign Out";
      signOutBtn.disabled = false;
    }
  }
}

/**
 * Gets current active tab with error handling
 * @returns {Promise<Object|null>} Promise resolving to tab object or null
 */
async function getCurrentTab() {
  try {
    return new Promise(resolve => {
      chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
        if (chrome.runtime.lastError) {
          logError("Failed to query tabs", chrome.runtime.lastError);
          resolve(null);
        } else if (!tabs || tabs.length === 0) {
          logError("No active tab found", "tabs array is empty");
          resolve(null);
        } else {
          resolve(tabs[0]);
        }
      });
    });
  } catch (error) {
    logError("Error getting current tab", error);
    return null;
  }
}

/**
 * Executes script in tab with timeout and error handling
 * @param {number} tabId - Tab ID to inject into
 * @param {Function} func - Function to inject
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function executeScriptInTab(tabId, func) {
  try {
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error("Script injection timeout")), EXTENSION_CONSTANTS.SCRIPT_INJECTION_TIMEOUT);
    });

    const injectionPromise = new Promise((resolve, reject) => {
      chrome.scripting.executeScript(
        {
          target: { tabId: tabId },
          function: func,
        },
        result => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(result);
          }
        },
      );
    });

    await Promise.race([injectionPromise, timeoutPromise]);
    return true;
  } catch (error) {
    logError(`Failed to execute script in tab ${tabId}`, error);
    return false;
  }
}

/**
 * Shows error message to user
 * @param {string} message - Error message to display
 */
function showUserError(message) {
  try {
    const statusElement = document.querySelector(".status");
    if (statusElement) {
      // Store original content for restoration
      const originalChildren = Array.from(statusElement.childNodes);

      // Clear and create error message safely
      while (statusElement.firstChild) {
        statusElement.removeChild(statusElement.firstChild);
      }

      const errorStrong = document.createElement("strong");
      errorStrong.textContent = "Error:";

      const errorText = document.createTextNode(` ${message}`);

      statusElement.appendChild(errorStrong);
      statusElement.appendChild(errorText);
      statusElement.style.background = "rgba(255, 0, 0, 0.2)";

      // Revert after 3 seconds
      setTimeout(() => {
        while (statusElement.firstChild) {
          statusElement.removeChild(statusElement.firstChild);
        }
        originalChildren.forEach(child => {
          statusElement.appendChild(child.cloneNode(true));
        });
        statusElement.style.background = "";
      }, 3000);
    }
  } catch (error) {
    logError("Error showing user error message", error);
  }
}

// DOM Ready Handler
document.addEventListener("DOMContentLoaded", async function () {
  try {
    // Get DOM elements with validation

    const clearStatsBtn = document.getElementById("clear-stats");
    const useChromeSyncCheckbox = document.getElementById("use-chrome-sync");
    const syncServerUrlInput = document.getElementById("sync-server-url");
    const signInBtn = document.getElementById("sign-in-btn");
    const signOutBtn = document.getElementById("sign-out-btn");

    if (!clearStatsBtn) {
      logError("DOM initialization failed", "Required buttons not found");
      return;
    }

    // Clear Stats Button
    clearStatsBtn.addEventListener("click", async function () {
      try {
        const success = await new Promise(resolve => {
          chrome.storage.local.remove([EXTENSION_CONSTANTS.STATS_KEY], () => {
            if (chrome.runtime.lastError) {
              logError("Failed to clear stats", chrome.runtime.lastError);
              resolve(false);
            } else {
              resolve(true);
            }
          });
        });

        if (success) {
          await updateStatsDisplay();
        } else {
          showUserError("Failed to clear stats");
        }
      } catch (error) {
        logError("Error in clear stats click handler", error);
        showUserError("Failed to clear stats");
      }
    });

    useChromeSyncCheckbox.addEventListener("change", async function () {
      try {
        const newValue = useChromeSyncCheckbox.checked;
        let cfg = await getWNConfig();
        if (cfg.useChromeSync !== newValue) {
          let notes = await getNotes();
          cfg.useChromeSync = newValue;
          await setWNConfig(cfg);
          await setNotes(notes);
        }
      } catch (error) {
        logError("Error in settings click handler", error);
        showUserError("Failed to update settings");
      }
    });

    syncServerUrlInput.addEventListener("change", async function () {
      try {
        const newValue = syncServerUrlInput.value.trim();
        await new Promise((resolve, reject) => {
          let cfg = getWNConfig()
            .then(cfg => {
              cfg.syncServerUrl = newValue;
              setWNConfig(cfg);
              resolve();
            })
            .catch(reject);
        });
      } catch (error) {
        logError("Error in settings input handler", error);
        showUserError("Failed to update settings");
      }
    });

    // Sign In Button
    if (signInBtn) {
      signInBtn.addEventListener("click", handleSignIn);
    }

    // Sign Out Button
    if (signOutBtn) {
      signOutBtn.addEventListener("click", handleSignOut);
    }

    // Listen for auth state changes from storage
    chrome.storage.onChanged.addListener((changes, areaName) => {
      if (areaName !== "sync") return;

      // Check if any auth-related keys changed
      const authKeys = ["webNotesJWT", "webNotesUser", "webNotesAuthState"];
      const authChanged = authKeys.some(key => key in changes);

      if (authChanged) {
        console.log("[Popup] Auth state changed in storage, updating UI");
        updateUserStatus().catch(error => {
          console.error("[Popup] Failed to update user status:", error);
        });
        updateStatsDisplay().catch(error => {
          console.error("[Popup] Failed to update stats display:", error);
        });
        // Update sharing section when auth changes
        initializeSharingSection().catch(error => {
          console.error("[Popup] Failed to update sharing section:", error);
        });
      }
    });

    // Initialize popup displays
    await updateUserStatus();
    await updateStatsDisplay();

    // Initialize sharing functionality
    await initializeSharingSection();

    // Initialize sync functionality
    await initializeSyncSection();
  } catch (error) {
    logError("Error during popup initialization", error);
  }
});

// ===== SHARING FUNCTIONALITY =====

/**
 * Initialize sharing section in popup
 */
async function initializeSharingSection() {
  try {
    const sharingSectionElement = document.getElementById("sharing-section");
    const sharePageBtn = document.getElementById("share-page-btn");
    const shareSiteBtn = document.getElementById("share-site-btn");
    const manageSharesBtn = document.getElementById("manage-shares-btn");

    if (!sharingSectionElement) {
      console.log("[Popup] Sharing section not found in DOM");
      return;
    }

    // Check if sharing is available (user authenticated and server configured)
    const canShare = await checkSharingCapability();

    if (canShare) {
      // Show sharing section
      sharingSectionElement.style.display = "block";

      // Set up event listeners
      if (sharePageBtn) {
        sharePageBtn.addEventListener("click", handleSharePageClick);
      }
      if (shareSiteBtn) {
        shareSiteBtn.addEventListener("click", handleShareSiteClick);
      }
      if (manageSharesBtn) {
        manageSharesBtn.addEventListener("click", handleManageSharesClick);
      }

      // Update sharing status
      await updateSharingStatus();

      console.log("[Popup] Sharing section initialized");
    } else {
      // Hide sharing section if user not authenticated
      sharingSectionElement.style.display = "none";
      console.log("[Popup] Sharing section hidden - authentication required");
    }
  } catch (error) {
    logError("Error initializing sharing section", error);
  }
}

/**
 * Check if sharing capabilities are available
 * @returns {Promise<boolean>} True if sharing is available
 */
async function checkSharingCapability() {
  try {
    // Check if user is authenticated via background script
    const authResponse = await chrome.runtime.sendMessage({
      action: "AUTHMANAGER_isAuthenticated",
    });

    if (!authResponse.success || !authResponse.data) {
      return false;
    }

    // Check if server sync is configured
    const config = await getWNConfig();
    if (!config.syncServerUrl) {
      return false;
    }

    // Check if ServerAPI is available
    if (typeof ServerAPI === "undefined") {
      return false;
    }

    return true;
  } catch (error) {
    console.error("[Popup] Error checking sharing capability:", error);
    return false;
  }
}

/**
 * Update sharing status display
 */
async function updateSharingStatus() {
  try {
    // Get current tab information
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs || tabs.length === 0) {
      console.log("[Popup] No active tab found");
      return;
    }

    const currentTab = tabs[0];
    const pageUrl = currentTab.url;
    const domain = new URL(pageUrl).hostname;

    // Update page sharing status
    await updatePageSharingStatus(pageUrl);

    // Update site sharing status
    await updateSiteSharingStatus(domain);
  } catch (error) {
    console.error("[Popup] Error updating sharing status:", error);

    // Set default state on error
    setPageSharingStatus(false, "Unable to check status");
    setSiteSharingStatus(false, "Unable to check status");
  }
}

/**
 * Update page sharing status
 * @param {string} pageUrl - Page URL
 */
async function updatePageSharingStatus(pageUrl) {
  try {
    const status = await ServerAPI.getSharingStatus("page", pageUrl);
    const isShared = status.isShared || false;
    const shareCount = status.shareCount || 0;

    let statusText = isShared ? `Shared with ${shareCount} user${shareCount !== 1 ? "s" : ""}` : "Page not shared";
    setPageSharingStatus(isShared, statusText);
  } catch (error) {
    console.debug("[Popup] Error checking page sharing status:", error);
    setPageSharingStatus(false, "Page not shared");
  }
}

/**
 * Update site sharing status
 * @param {string} domain - Site domain
 */
async function updateSiteSharingStatus(domain) {
  try {
    const status = await ServerAPI.getSharingStatus("site", domain);
    const isShared = status.isShared || false;
    const shareCount = status.shareCount || 0;

    let statusText = isShared ? `Site shared with ${shareCount} user${shareCount !== 1 ? "s" : ""}` : "Site not shared";
    setSiteSharingStatus(isShared, statusText);
  } catch (error) {
    console.debug("[Popup] Error checking site sharing status:", error);
    setSiteSharingStatus(false, "Site not shared");
  }
}

/**
 * Set page sharing status display
 * @param {boolean} isShared - Whether page is shared
 * @param {string} statusText - Status text to display
 */
function setPageSharingStatus(isShared, statusText) {
  const indicator = document.getElementById("page-sharing-indicator");
  const text = document.getElementById("page-sharing-text");

  if (indicator) {
    indicator.className = `sharing-indicator ${isShared ? "shared" : "not-shared"}`;
  }
  if (text) {
    text.textContent = statusText;
  }
}

/**
 * Set site sharing status display
 * @param {boolean} isShared - Whether site is shared
 * @param {string} statusText - Status text to display
 */
function setSiteSharingStatus(isShared, statusText) {
  const indicator = document.getElementById("site-sharing-indicator");
  const text = document.getElementById("site-sharing-text");

  if (indicator) {
    indicator.className = `sharing-indicator ${isShared ? "shared" : "not-shared"}`;
  }
  if (text) {
    text.textContent = statusText;
  }
}

/**
 * Handle share page button click
 */
async function handleSharePageClick() {
  try {
    console.log("[Popup] Share page button clicked");

    // Get current tab
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs || tabs.length === 0) {
      showPopupMessage("No active tab found", "error");
      return;
    }

    const currentTab = tabs[0];

    // First inject content scripts if needed
    const response = await chrome.runtime.sendMessage({
      action: "injectContentScripts",
      tabId: currentTab.id,
    });

    if (!response || !response.success) {
      console.error("[Popup] Failed to inject content scripts");
      showPopupMessage("Failed to initialize page", "error");
      return;
    }

    // Send message to content script to open sharing dialog
    chrome.tabs
      .sendMessage(currentTab.id, {
        type: "shareCurrentPage",
      })
      .then(response => {
        if (response && response.success) {
          console.log("[Popup] Page sharing dialog opened successfully");
          // Close popup after slight delay
          setTimeout(() => window.close(), 500);
        } else {
          showPopupMessage("Failed to open sharing dialog", "error");
        }
      })
      .catch(error => {
        console.error("[Popup] Error sending share page message:", error);
        showPopupMessage("Failed to communicate with page", "error");
      });
  } catch (error) {
    logError("Error handling share page click", error);
    showPopupMessage("Failed to share page", "error");
  }
}

/**
 * Handle share site button click
 */
async function handleShareSiteClick() {
  try {
    console.log("[Popup] Share site button clicked");

    // Get current tab
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs || tabs.length === 0) {
      showPopupMessage("No active tab found", "error");
      return;
    }

    const currentTab = tabs[0];

    // First inject content scripts if needed
    const response = await chrome.runtime.sendMessage({
      action: "injectContentScripts",
      tabId: currentTab.id,
    });

    if (!response || !response.success) {
      console.error("[Popup] Failed to inject content scripts");
      showPopupMessage("Failed to initialize page", "error");
      return;
    }

    // Send message to content script to open sharing dialog
    chrome.tabs
      .sendMessage(currentTab.id, {
        type: "shareCurrentSite",
      })
      .then(response => {
        if (response && response.success) {
          console.log("[Popup] Site sharing dialog opened successfully");
          // Close popup after slight delay
          setTimeout(() => window.close(), 500);
        } else {
          showPopupMessage("Failed to open sharing dialog", "error");
        }
      })
      .catch(error => {
        console.error("[Popup] Error sending share site message:", error);
        showPopupMessage("Failed to communicate with page", "error");
      });
  } catch (error) {
    logError("Error handling share site click", error);
    showPopupMessage("Failed to share site", "error");
  }
}

/**
 * Handle manage shares button click
 */
async function handleManageSharesClick() {
  try {
    console.log("[Popup] Manage shares button clicked");

    // Get current tab
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs || tabs.length === 0) {
      showPopupMessage("No active tab found", "error");
      return;
    }

    const currentTab = tabs[0];
    const pageUrl = currentTab.url;
    const pageTitle = currentTab.title || pageUrl;

    // First inject content scripts if needed
    const response = await chrome.runtime.sendMessage({
      action: "injectContentScripts",
      tabId: currentTab.id,
    });

    if (!response || !response.success) {
      console.error("[Popup] Failed to inject content scripts");
      showPopupMessage("Failed to initialize page", "error");
      return;
    }

    // Send message to content script to open page sharing dialog (which includes management)
    chrome.tabs
      .sendMessage(currentTab.id, {
        type: "shareCurrentPage",
      })
      .then(response => {
        if (response && response.success) {
          console.log("[Popup] Manage shares dialog opened successfully");
          // Close popup after slight delay
          setTimeout(() => window.close(), 500);
        } else {
          showPopupMessage("Failed to open manage shares dialog", "error");
        }
      })
      .catch(error => {
        console.error("[Popup] Error sending manage shares message:", error);
        showPopupMessage("Failed to communicate with page", "error");
      });
  } catch (error) {
    logError("Error handling manage shares click", error);
    showPopupMessage("Failed to open manage shares", "error");
  }
}

/**
 * Show temporary message in popup
 * @param {string} message - Message to show
 * @param {string} type - Message type (success, error, info)
 */
function showPopupMessage(message, type = "info") {
  try {
    // Create or update message element
    let messageElement = document.getElementById("popup-message");

    if (!messageElement) {
      messageElement = document.createElement("div");
      messageElement.id = "popup-message";
      messageElement.style.cssText = `
        position: fixed;
        top: 10px;
        left: 10px;
        right: 10px;
        padding: 8px;
        border-radius: 4px;
        font-size: 12px;
        text-align: center;
        z-index: 1000;
        transition: opacity 0.3s ease;
      `;
      document.body.appendChild(messageElement);
    }

    // Set message content and styling based on type
    messageElement.textContent = message;

    switch (type) {
      case "success":
        messageElement.style.background = "rgba(76, 175, 80, 0.9)";
        messageElement.style.color = "white";
        break;
      case "error":
        messageElement.style.background = "rgba(244, 67, 54, 0.9)";
        messageElement.style.color = "white";
        break;
      default:
        messageElement.style.background = "rgba(33, 150, 243, 0.9)";
        messageElement.style.color = "white";
    }

    // Show message
    messageElement.style.opacity = "1";

    // Auto-hide after 3 seconds
    setTimeout(() => {
      if (messageElement) {
        messageElement.style.opacity = "0";
        setTimeout(() => {
          if (messageElement && messageElement.parentNode) {
            messageElement.parentNode.removeChild(messageElement);
          }
        }, 300);
      }
    }, 3000);
  } catch (error) {
    console.error("[Popup] Error showing popup message:", error);
  }
}

/**
 * Update sharing section when user authentication changes
 */
async function updateSharingOnAuthChange() {
  try {
    await initializeSharingSection();
  } catch (error) {
    console.error("[Popup] Error updating sharing on auth change:", error);
  }
}

// Storage listener already handles auth changes and updates sharing section

// Banner functions removed - functionality no longer needed

// ===== SYNC FUNCTIONALITY =====

/**
 * Initialize sync section in popup
 */
async function initializeSyncSection() {
  try {
    const syncSectionElement = document.getElementById("sync-section");
    const copyServerToLocalBtn = document.getElementById("copy-server-to-local-btn");
    const copyLocalToServerBtn = document.getElementById("copy-local-to-server-btn");
    const deleteAllServerDataBtn = document.getElementById("delete-all-server-data-btn");

    if (!syncSectionElement) {
      console.log("[Popup] Sync section not found in DOM");
      return;
    }

    // Check if sync is available (user authenticated and server configured)
    const canSync = await checkSyncCapability();

    if (canSync) {
      // Show sync section
      syncSectionElement.style.display = "block";

      // Set up event listeners (remove existing listeners first to avoid duplicates)
      if (copyServerToLocalBtn) {
        copyServerToLocalBtn.removeEventListener("click", handleCopyServerToLocal);
        copyServerToLocalBtn.addEventListener("click", handleCopyServerToLocal);
      }
      if (copyLocalToServerBtn) {
        copyLocalToServerBtn.removeEventListener("click", handleCopyLocalToServer);
        copyLocalToServerBtn.addEventListener("click", handleCopyLocalToServer);
      }
      if (deleteAllServerDataBtn) {
        // Enable the delete button
        deleteAllServerDataBtn.classList.remove("disabled");
        deleteAllServerDataBtn.removeAttribute("title");
        deleteAllServerDataBtn.removeEventListener("click", handleDeleteAllServerData);
        deleteAllServerDataBtn.addEventListener("click", handleDeleteAllServerData);
      }

      console.log("[Popup] Sync section initialized");
    } else {
      // Hide sync section if user not authenticated
      syncSectionElement.style.display = "none";
      console.log("[Popup] Sync section hidden - authentication required");
    }
  } catch (error) {
    logError("Error initializing sync section", error);
  }
}

/**
 * Check if sync capabilities are available
 * @returns {Promise<boolean>} True if sync is available
 */
async function checkSyncCapability() {
  try {
    // Check if user is authenticated via background script
    const authResponse = await chrome.runtime.sendMessage({
      action: "AUTHMANAGER_isAuthenticated",
    });

    if (!authResponse.success || !authResponse.data) {
      return false;
    }

    // Check if server sync is configured
    const config = await getWNConfig();
    if (!config.syncServerUrl) {
      return false;
    }

    // Check if ServerAPI is available
    if (typeof ServerAPI === "undefined") {
      return false;
    }

    return true;
  } catch (error) {
    console.error("[Popup] Error checking sync capability:", error);
    return false;
  }
}

/**
 * Handle copy server notes to local button click
 */
async function handleCopyServerToLocal() {
  try {
    console.log("[Popup] Copy server to local button clicked");

    const btn = document.getElementById("copy-server-to-local-btn");
    if (!btn) return;

    // Disable button during operation
    const originalText = btn.textContent;
    btn.textContent = "Copying...";
    btn.disabled = true;

    // Call server API to get all notes
    const result = await ServerAPI.copyServerNotesToLocal();

    if (result.success) {
      showPopupMessage(`Successfully copied ${result.notes_count} notes from server to local storage`, "success");
      console.log("[Popup] Server to local copy completed:", result);
    } else {
      showPopupMessage("Failed to copy notes: " + (result.error || "Unknown error"), "error");
    }
  } catch (error) {
    logError("Error copying server notes to local", error);
    showPopupMessage("Failed to copy notes: " + error.message, "error");
  } finally {
    const btn = document.getElementById("copy-server-to-local-btn");
    if (btn) {
      btn.textContent = "Copy Server Notes to Local";
      btn.disabled = false;
    }
  }
}

/**
 * Handle copy local notes to server button click
 */
async function handleCopyLocalToServer() {
  try {
    console.log("[Popup] Copy local to server button clicked");

    const btn = document.getElementById("copy-local-to-server-btn");
    if (!btn) return;

    // Disable button during operation
    const originalText = btn.textContent;
    btn.textContent = "Copying...";
    btn.disabled = true;

    // Call server API to copy all local notes to server
    const result = await ServerAPI.copyLocalNotesToServer();

    if (result.success) {
      showPopupMessage(`Successfully copied ${result.notes_count} notes from local to server storage`, "success");
      console.log("[Popup] Local to server copy completed:", result);
    } else {
      showPopupMessage("Failed to copy notes: " + (result.error || "Unknown error"), "error");
    }
  } catch (error) {
    logError("Error copying local notes to server", error);
    showPopupMessage("Failed to copy notes: " + error.message, "error");
  } finally {
    const btn = document.getElementById("copy-local-to-server-btn");
    if (btn) {
      btn.textContent = "Copy Local Notes to Server";
      btn.disabled = false;
    }
  }
}

/**
 * Handles delete all server data button click with typed confirmation
 * @returns {Promise<void>}
 */
async function handleDeleteAllServerData() {
  try {
    console.log("[Popup] Delete all server data button clicked");

    const btn = document.getElementById("delete-all-server-data-btn");
    if (!btn) return;

    // Single confirmation dialog requiring typed confirmation
    const confirmation = prompt(
      "WARNING: This will permanently delete ALL your data from the server:\n\n" +
        "• All sites\n" +
        "• All pages\n" +
        "• All notes\n" +
        "• All shares\n" +
        "• All artifacts\n\n" +
        "This action is IRREVERSIBLE and UNRECOVERABLE.\n\n" +
        'To confirm, type "DELETE ALL MY DATA" (without quotes):',
    );

    if (confirmation !== "DELETE ALL MY DATA") {
      console.log("[Popup] Delete cancelled by user - confirmation text did not match");
      if (confirmation !== null) {
        // User entered something but it didn't match (null means they clicked Cancel)
        showPopupMessage("Delete cancelled - confirmation text did not match", "info");
      }
      return;
    }

    // Disable button during operation
    const originalText = btn.textContent;
    btn.textContent = "Deleting...";
    btn.disabled = true;

    // Call server API to delete all user data
    const result = await ServerAPI.deleteAllUserData();

    if (result.success) {
      showPopupMessage("All server data has been permanently deleted. You have been signed out.", "success");
      console.log("[Popup] Delete all server data completed successfully");

      // Update UI to reflect signed-out state
      await updateUserStatus();
      await updateStatsDisplay();
    } else {
      showPopupMessage("Failed to delete server data: " + (result.error || "Unknown error"), "error");
    }
  } catch (error) {
    logError("Error deleting all server data", error);
    showPopupMessage("Failed to delete server data: " + error.message, "error");
  } finally {
    const btn = document.getElementById("delete-all-server-data-btn");
    if (btn) {
      btn.textContent = "Delete All Server Data";
      btn.disabled = false;
    }
  }
}
