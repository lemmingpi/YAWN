/**
 * Popup script for Web Notes Chrome Extension
 * Handles popup UI interactions with comprehensive error handling
 * Uses shared utilities from shared-utils.js
 */

/* global EXTENSION_CONSTANTS, logError, getNotes, getConfig, setConfig, isTabValid */

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

// Banner functions removed - functionality no longer needed
