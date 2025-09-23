/**
 * Popup script for Web Notes Chrome Extension
 * Handles popup UI interactions with comprehensive error handling
 * Uses shared utilities from shared-utils.js
 */

/* global EXTENSION_CONSTANTS, logError, getStats, setStats, isTabValid */

// Use shared constants and functions
// EXTENSION_CONSTANTS, logError, getStats, setStats, isTabValid are imported

// All storage and logging functions now imported from shared-utils.js

/**
 * Updates stats display in the popup
 */
async function updateStatsDisplay() {
  try {
    const statsContentElement = document.getElementById("stats-content");
    if (!statsContentElement) {
      logError("Stats display update failed", "stats-content element not found");
      return;
    }

    const stats = await getStats();

    const installDate = new Date(stats.installDate).toLocaleDateString();
    const lastSeen = new Date(stats.lastSeen).toLocaleString();

    // Clear existing content first
    while (statsContentElement.firstChild) {
      statsContentElement.removeChild(statsContentElement.firstChild);
    }

    // Create stats display safely using DOM methods
    const statsDiv = document.createElement("div");
    statsDiv.style.cssText = "font-size: 11px; line-height: 1.4;";

    const statsData = [
      `• Installed: ${installDate}`,
      `• Banner shows: ${stats.bannerShows}`,
      `• Context menu clicks: ${stats.contextMenuClicks}`,
      `• Popup opens: ${stats.popupOpens}`,
      `• Last seen: ${lastSeen}`,
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
 * Increments popup open counter
 */
async function incrementPopupCount() {
  try {
    const stats = await getStats();
    const updatedStats = {
      ...stats,
      popupOpens: stats.popupOpens + 1,
      lastSeen: Date.now(),
    };

    const success = await setStats(updatedStats);
    if (success) {
      await updateStatsDisplay();
    }
  } catch (error) {
    logError("Error incrementing popup count", error);
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
      setTimeout(
        () => reject(new Error("Script injection timeout")),
        EXTENSION_CONSTANTS.SCRIPT_INJECTION_TIMEOUT,
      );
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
    const showBannerBtn = document.getElementById("show-banner");
    const hideBannerBtn = document.getElementById("hide-banner");
    const clearStatsBtn = document.getElementById("clear-stats");

    if (!showBannerBtn || !hideBannerBtn || !clearStatsBtn) {
      logError("DOM initialization failed", "Required buttons not found");
      return;
    }

    // Show Banner Button
    showBannerBtn.addEventListener("click", async function () {
      try {
        const tab = await getCurrentTab();

        if (!tab) {
          showUserError("Cannot access current tab");
          return;
        }

        if (!isTabValid(tab)) {
          showUserError("Cannot show banner on this page type");
          return;
        }

        const success = await executeScriptInTab(tab.id, showHelloWorldBanner);

        if (success) {
          // Update stats
          const stats = await getStats();
          await setStats({
            ...stats,
            bannerShows: stats.bannerShows + 1,
            lastSeen: Date.now(),
          });
          await updateStatsDisplay();
        } else {
          showUserError("Failed to show banner");
        }
      } catch (error) {
        logError("Error in show banner click handler", error);
        showUserError("Unexpected error occurred");
      }
    });

    // Hide Banner Button
    hideBannerBtn.addEventListener("click", async function () {
      try {
        const tab = await getCurrentTab();

        if (!tab) {
          showUserError("Cannot access current tab");
          return;
        }

        if (!isTabValid(tab)) {
          showUserError("Cannot hide banner on this page type");
          return;
        }

        const success = await executeScriptInTab(tab.id, hideHelloWorldBanner);

        if (!success) {
          showUserError("Failed to hide banner");
        }
      } catch (error) {
        logError("Error in hide banner click handler", error);
        showUserError("Unexpected error occurred");
      }
    });

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

    // Initialize popup
    await incrementPopupCount();
  } catch (error) {
    logError("Error during popup initialization", error);
  }
});

/**
 * Function to be injected for showing banner (popup variant)
 */
function showHelloWorldBanner() {
  try {
    const BANNER_ID = "web-notes-hello-banner";
    const BANNER_STYLE_ID = "web-notes-banner-styles";

    // Check if banner already exists
    const existingBanner = document.getElementById(BANNER_ID);
    if (existingBanner) {
      existingBanner.style.animation = "pulse 0.5s ease-in-out";
      setTimeout(() => {
        if (existingBanner.parentNode) {
          existingBanner.style.animation = "";
        }
      }, 500);
      return;
    }

    // Create banner element safely
    const banner = document.createElement("div");
    banner.id = BANNER_ID;
    banner.style.cssText = `
      position: fixed;
      top: 10px;
      right: 10px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      font-weight: 600;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
      z-index: 10000;
      cursor: pointer;
      animation: slideIn 0.3s ease-out;
      transition: all 0.3s ease;
    `;

    // Create banner content safely using DOM methods
    const container = document.createElement("div");
    container.style.cssText = "display: flex; align-items: center; gap: 8px;";

    const icon = document.createElement("span");
    icon.textContent = "🗒️";

    const message = document.createElement("span");
    message.className = "banner-message";
    message.textContent = "Web Notes - Popup Triggered!";

    const closeButton = document.createElement("span");
    closeButton.className = "banner-close";
    closeButton.textContent = "×";
    closeButton.style.cssText =
      "margin-left: 8px; opacity: 0.7; font-size: 18px; cursor: pointer; padding: 4px;";

    container.appendChild(icon);
    container.appendChild(message);
    container.appendChild(closeButton);
    banner.appendChild(container);

    // Add styles if not already present
    if (!document.getElementById(BANNER_STYLE_ID)) {
      const style = document.createElement("style");
      style.id = BANNER_STYLE_ID;
      style.textContent = `
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
          from { transform: translateX(0); opacity: 1; }
          to { transform: translateX(100%); opacity: 0; }
        }
        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.05); }
        }
        #${BANNER_ID}:hover {
          transform: scale(1.05);
          box-shadow: 0 6px 25px rgba(0, 0, 0, 0.2);
        }
        .banner-close:hover {
          opacity: 1 !important;
          background: rgba(255, 255, 255, 0.2);
          border-radius: 50%;
        }
      `;

      if (document.head) {
        document.head.appendChild(style);
      }
    }

    // Safely append to body
    if (document.body) {
      document.body.appendChild(banner);
    } else {
      console.error("[Web Notes] Cannot add banner: document.body not available");
      return;
    }

    // Add event listeners with error handling
    try {
      message.addEventListener("click", function (e) {
        e.stopPropagation();
        alert(
          "Hello from Web Notes Chrome Extension!\\n\\nTriggered from popup button.",
        );
      });

      closeButton.addEventListener("click", function (e) {
        e.stopPropagation();
        banner.style.animation = "slideOut 300ms ease-in forwards";
        setTimeout(() => {
          if (banner.parentNode) {
            banner.remove();
          }
        }, 300);
      });
    } catch (error) {
      console.error("[Web Notes] Error adding event listeners:", error);
    }
  } catch (error) {
    console.error("[Web Notes] Error creating banner from popup:", error);
  }
}

/**
 * Function to be injected for hiding banner
 */
function hideHelloWorldBanner() {
  try {
    const banner = document.getElementById("web-notes-hello-banner");
    if (banner) {
      banner.style.animation = "slideOut 300ms ease-in forwards";
      setTimeout(() => {
        if (banner.parentNode) {
          banner.remove();
        }
      }, 300);
    }
  } catch (error) {
    console.error("[Web Notes] Error hiding banner:", error);
  }
}
