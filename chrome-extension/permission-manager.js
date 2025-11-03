/**
 * Permission Manager for YAWN Extension
 * Handles optional host permissions
 */

const PermissionManager = {
  /**
   * Get the origin pattern for a URL
   * @param {string} url - Full URL
   * @returns {string} Origin pattern (e.g., "https://example.com/*")
   */
  getOriginPattern(url) {
    try {
      const urlObj = new URL(url);
      return `${urlObj.origin}/*`;
    } catch (error) {
      console.error("[YAWN] Invalid URL:", url);
      return null;
    }
  },

  /**
   * Check if we have permission for a URL
   * @param {string} url - URL to check
   * @returns {Promise<boolean>}
   */
  async hasPermission(url) {
    const origin = this.getOriginPattern(url);
    if (!origin) {
      console.log(`[YAWN] hasPermission: Invalid origin for ${url}`);
      return false;
    }

    const hasIt = await new Promise(resolve => {
      chrome.permissions.contains({ origins: [origin] }, resolve);
    });

    console.log(`[YAWN] hasPermission check for ${origin}: ${hasIt}`);
    return hasIt;
  },

  /**
   * Request permission for a domain
   * MUST be called during a user gesture (context menu click, button click, etc.)
   * Chrome handles "already granted" gracefully - won't show dialog if already approved
   * @param {string} url - URL to request permission for
   * @returns {Promise<boolean>} True if permission granted
   */
  async requestPermission(url) {
    const origin = this.getOriginPattern(url);
    if (!origin) {
      console.error(`[YAWN] requestPermission: Invalid origin for ${url}`);
      return false;
    }

    console.log(`[YAWN] Requesting permission for ${origin}...`);

    try {
      // CRITICAL: Call chrome.permissions.request() IMMEDIATELY without any await before it
      // This is the FIRST await in the user gesture chain to preserve gesture context
      const granted = await new Promise((resolve, reject) => {
        chrome.permissions.request({ origins: [origin] }, result => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(result);
          }
        });
      });

      if (granted) {
        console.log(`[YAWN] ✓ Permission GRANTED for ${origin}`);
      } else {
        console.log(`[YAWN] ✗ Permission DENIED for ${origin}`);
      }

      return granted;
    } catch (error) {
      console.error(`[YAWN] ✗ Permission request FAILED for ${origin}:`, error);
      return false;
    }
  },

  /**
   * Remove permission
   * @param {string} url - URL
   */
  async revokePermission(url) {
    const origin = this.getOriginPattern(url);
    if (!origin) return;

    await new Promise(resolve => {
      chrome.permissions.remove({ origins: [origin] }, resolve);
    });

    console.log(`[YAWN] Revoked permission for ${origin}`);
  },

  /**
   * Get all currently granted permissions
   * @returns {Promise<string[]>}
   */
  async getAllGrantedOrigins() {
    return new Promise(resolve => {
      chrome.permissions.getAll(permissions => {
        resolve(permissions.origins || []);
      });
    });
  },

  /**
   * Initialize on extension startup
   */
  async initialize() {
    console.log("[YAWN] Initializing PermissionManager");
    const permissions = await this.getAllGrantedOrigins();
    console.log("[YAWN] Current permissions:", permissions);
  },

  /**
   * Request permission if needed
   * MUST be called during user gesture (e.g., popup open, context menu click)
   * Chrome will not show dialog if permission already granted
   * @param {string} url - Page URL
   * @param {number} tabId - Tab ID (currently unused, kept for API compatibility)
   * @returns {Promise<boolean>} True if permission exists or was granted
   */
  async checkAndRequestIfNeeded(url, tabId) {
    console.log(`[YAWN] checkAndRequestIfNeeded for ${url}`);

    // CRITICAL: Call requestPermission() IMMEDIATELY without any await before it
    // Chrome handles "already granted" gracefully - won't show dialog if approved
    // This preserves the user gesture context
    const granted = await this.requestPermission(url);

    return granted;
  },
};

// Make available globally for background script
if (typeof window !== "undefined") {
  window.PermissionManager = PermissionManager;
}
