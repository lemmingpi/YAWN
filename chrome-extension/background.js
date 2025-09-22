/**
 * Background script for Web Notes Chrome Extension
 * Handles context menu creation, click events, and error handling
 */

// Constants
const EXTENSION_ID = 'show-web-notes-banner';
const MENU_TITLE = '🗒️ Show Web Notes Banner';
const STATS_KEY = 'extensionStats';
const SCRIPT_INJECTION_TIMEOUT = 5000; // 5 seconds

// Default stats object
const DEFAULT_STATS = {
  installDate: Date.now(),
  bannerShows: 0,
  popupOpens: 0,
  contextMenuClicks: 0,
  lastSeen: Date.now()
};

/**
 * Logs errors with context information
 * @param {string} context - Where the error occurred
 * @param {Error|any} error - The error object or message
 */
function logError(context, error) {
  console.error(`[Web Notes Extension] ${context}:`, error);
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

/**
 * Gets extension stats from storage with error handling
 * @returns {Promise<Object>} Promise resolving to stats object
 */
async function getStats() {
  try {
    return new Promise((resolve) => {
      chrome.storage.local.get([STATS_KEY], (result) => {
        if (chrome.runtime.lastError) {
          logError('Failed to get stats', chrome.runtime.lastError);
          resolve(DEFAULT_STATS);
        } else {
          resolve(result[STATS_KEY] || DEFAULT_STATS);
        }
      });
    });
  } catch (error) {
    logError('Error in getStats', error);
    return DEFAULT_STATS;
  }
}

/**
 * Sets extension stats in storage with error handling
 * @param {Object} stats - Stats object to save
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function setStats(stats) {
  try {
    return new Promise((resolve) => {
      chrome.storage.local.set({[STATS_KEY]: stats}, () => {
        if (chrome.runtime.lastError) {
          logError('Failed to set stats', chrome.runtime.lastError);
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });
  } catch (error) {
    logError('Error in setStats', error);
    return false;
  }
}

/**
 * Creates context menu with error handling
 */
async function createContextMenu() {
  try {
    await safeApiCall(() => {
      chrome.contextMenus.create({
        id: EXTENSION_ID,
        title: MENU_TITLE,
        contexts: ['page', 'selection', 'link', 'image']
      });
    }, 'Creating context menu');

    console.log('[Web Notes Extension] Context menu created successfully');
  } catch (error) {
    logError('Failed to create context menu', error);
  }
}

/**
 * Initializes extension stats
 */
async function initializeStats() {
  try {
    // Check if stats exist in storage directly, not via getStats()
    const result = await new Promise((resolve) => {
      chrome.storage.local.get([STATS_KEY], (result) => {
        if (chrome.runtime.lastError) {
          logError('Failed to check stats existence', chrome.runtime.lastError);
          resolve(null);
        } else {
          resolve(result);
        }
      });
    });

    if (!result || !result[STATS_KEY]) {
      await setStats(DEFAULT_STATS);
      console.log('[Web Notes Extension] Stats initialized');
    }
  } catch (error) {
    logError('Failed to initialize stats', error);
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
  const restrictedProtocols = ['chrome:', 'chrome-extension:', 'edge:', 'moz-extension:'];
  const url = tab.url || '';

  return !restrictedProtocols.some(protocol => url.startsWith(protocol));
}

/**
 * Injects banner script with timeout and error handling
 * @param {number} tabId - Tab ID to inject into
 * @returns {Promise<boolean>} Promise resolving to success status
 */
async function injectBannerScript(tabId) {
  try {
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Script injection timeout')), SCRIPT_INJECTION_TIMEOUT);
    });

    const injectionPromise = new Promise((resolve, reject) => {
      chrome.scripting.executeScript({
        target: { tabId: tabId },
        function: showWebNotesBanner
      }, (result) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(result);
        }
      });
    });

    await Promise.race([injectionPromise, timeoutPromise]);
    return true;
  } catch (error) {
    logError(`Failed to inject script into tab ${tabId}`, error);
    return false;
  }
}


// Event Listeners

chrome.runtime.onInstalled.addListener(async () => {
  console.log('[Web Notes Extension] Extension installed/updated');

  try {
    await createContextMenu();
    await initializeStats();
  } catch (error) {
    logError('Error during extension initialization', error);
  }
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== EXTENSION_ID) {
    return;
  }

  try {
    // Validate tab
    if (!isTabValid(tab)) {
      logError('Invalid tab for script injection', `Tab ID: ${tab?.id}, URL: ${tab?.url}`);
      return;
    }

    // Inject banner script
    const success = await injectBannerScript(tab.id);

    if (success) {
      // Update stats only on successful injection
      const stats = await getStats();
      await setStats({
        ...stats,
        contextMenuClicks: stats.contextMenuClicks + 1,
        bannerShows: stats.bannerShows + 1,
        lastSeen: Date.now()
      });
    }
  } catch (error) {
    logError('Error handling context menu click', error);
  }
});

// Handle extension errors
chrome.runtime.onStartup.addListener(() => {
  console.log('[Web Notes Extension] Extension startup');
});

/**
 * Function to be injected into web pages
 * This function is executed in the page context, not the extension context
 */
function showWebNotesBanner() {
  try {
    // Constants for banner creation
    const BANNER_ID = 'web-notes-hello-banner';
    const BANNER_STYLE_ID = 'web-notes-banner-styles';
    const PULSE_DURATION = 500;
    const AUTO_FADE_DELAY = 5000;
    const CLOSE_ANIMATION_DURATION = 300;

    // Check if banner already exists
    const existingBanner = document.getElementById(BANNER_ID);
    if (existingBanner) {
      // Add pulse effect to existing banner
      existingBanner.style.animation = 'pulse 0.5s ease-in-out';
      setTimeout(() => {
        if (existingBanner.parentNode) {
          existingBanner.style.animation = '';
        }
      }, PULSE_DURATION);
      return;
    }

    // Create banner element safely
    const banner = document.createElement('div');
    banner.id = BANNER_ID;

    // Set styles via cssText to avoid CSP issues
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
    const container = document.createElement('div');
    container.style.cssText = 'display: flex; align-items: center; gap: 8px;';

    const icon = document.createElement('span');
    icon.textContent = '🗒️';

    const message = document.createElement('span');
    message.className = 'banner-message';
    message.textContent = 'Web Notes - Context Menu!';

    const closeButton = document.createElement('span');
    closeButton.className = 'banner-close';
    closeButton.textContent = '×';
    closeButton.style.cssText = 'margin-left: 8px; opacity: 0.7; font-size: 18px; cursor: pointer; padding: 4px;';

    container.appendChild(icon);
    container.appendChild(message);
    container.appendChild(closeButton);
    banner.appendChild(container);

    // Add styles if not already present
    if (!document.getElementById(BANNER_STYLE_ID)) {
      const style = document.createElement('style');
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

      // Safely append to head
      if (document.head) {
        document.head.appendChild(style);
      }
    }

    // Safely append to body
    if (document.body) {
      document.body.appendChild(banner);
    } else {
      console.error('[Web Notes] Cannot add banner: document.body not available');
      return;
    }

    // Add event listeners with error handling
    try {
      // Message click handler
      message.addEventListener('click', function(e) {
        e.stopPropagation();
        alert('Hello from Web Notes Chrome Extension!\\n\\nTriggered from right-click context menu.');
      });

      // Close button handler
      closeButton.addEventListener('click', function(e) {
        e.stopPropagation();
        banner.style.animation = `slideOut ${CLOSE_ANIMATION_DURATION}ms ease-in forwards`;
        setTimeout(() => {
          if (banner.parentNode) {
            banner.remove();
          }
        }, CLOSE_ANIMATION_DURATION);
      });
    } catch (error) {
      console.error('[Web Notes] Error adding event listeners:', error);
    }

    // Auto-fade after delay
    setTimeout(() => {
      if (banner.parentNode) {
        banner.style.opacity = '0.8';
      }
    }, AUTO_FADE_DELAY);

  } catch (error) {
    console.error('[Web Notes] Error creating banner:', error);
  }
}