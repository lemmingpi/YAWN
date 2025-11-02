/**
 * Permission Manager for YAWN Extension
 * Handles optional host permissions with cross-device sync
 */

const PermissionManager = {
  STORAGE_KEY: "grantedDomains",
  PENDING_DOMAINS_KEY: "pendingDomainPermissions",

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
    if (!origin) return false;

    return new Promise(resolve => {
      chrome.permissions.contains({ origins: [origin] }, resolve);
    });
  },

  /**
   * Request permission for a domain with user-friendly prompt
   * @param {string} url - URL to request permission for
   * @param {boolean} showPrompt - Whether to show confirmation dialog
   * @returns {Promise<boolean>} True if permission granted
   */
  async requestPermission(url, showPrompt = true) {
    const origin = this.getOriginPattern(url);
    if (!origin) return false;

    // Check if already have permission
    const hasPermission = await this.hasPermission(url);
    if (hasPermission) {
      console.log(`[YAWN] Already have permission for ${origin}`);
      return true;
    }

    console.log(`[YAWN] Requesting permission for ${origin}`);

    // Request from Chrome
    const granted = await new Promise(resolve => {
      chrome.permissions.request({ origins: [origin] }, resolve);
    });

    if (granted) {
      console.log(`[YAWN] Permission granted for ${origin}`);
      // Store in sync for other devices
      await this.syncPermission(origin);
    } else {
      console.log(`[YAWN] Permission denied for ${origin}`);
    }

    return granted;
  },

  /**
   * Store granted permission in sync storage for other devices
   * @param {string} origin - Origin pattern
   */
  async syncPermission(origin) {
    const { [this.STORAGE_KEY]: grantedDomains = [] } = await chrome.storage.sync.get(this.STORAGE_KEY);

    if (!grantedDomains.includes(origin)) {
      grantedDomains.push(origin);
      await chrome.storage.sync.set({ [this.STORAGE_KEY]: grantedDomains });
      console.log(`[YAWN] Synced permission for ${origin}`);
    }
  },

  /**
   * Get all synced domains (from other devices)
   * @returns {Promise<string[]>}
   */
  async getSyncedDomains() {
    const { [this.STORAGE_KEY]: grantedDomains = [] } = await chrome.storage.sync.get(this.STORAGE_KEY);
    return grantedDomains;
  },

  /**
   * Check if a domain was granted on another device but not locally
   * @param {string} url - URL to check
   * @returns {Promise<boolean>}
   */
  async isPendingFromSync(url) {
    const origin = this.getOriginPattern(url);
    if (!origin) return false;

    const syncedDomains = await this.getSyncedDomains();
    const hasLocalPermission = await this.hasPermission(url);

    return syncedDomains.includes(origin) && !hasLocalPermission;
  },

  /**
   * Mark a domain as pending re-request (shown on badge)
   * @param {string} url - URL
   */
  async markPendingPermission(url) {
    const origin = this.getOriginPattern(url);
    if (!origin) return;

    const { [this.PENDING_DOMAINS_KEY]: pending = [] } = await chrome.storage.local.get(this.PENDING_DOMAINS_KEY);

    if (!pending.includes(origin)) {
      pending.push(origin);
      await chrome.storage.local.set({ [this.PENDING_DOMAINS_KEY]: pending });
    }
  },

  /**
   * Clear pending permission for a domain
   * @param {string} url - URL
   */
  async clearPendingPermission(url) {
    const origin = this.getOriginPattern(url);
    if (!origin) return;

    const { [this.PENDING_DOMAINS_KEY]: pending = [] } = await chrome.storage.local.get(this.PENDING_DOMAINS_KEY);

    const filtered = pending.filter(p => p !== origin);
    await chrome.storage.local.set({ [this.PENDING_DOMAINS_KEY]: filtered });
  },

  /**
   * Check if domain has pending permission
   * @param {string} url - URL
   * @returns {Promise<boolean>}
   */
  async hasPendingPermission(url) {
    const origin = this.getOriginPattern(url);
    if (!origin) return false;

    const { [this.PENDING_DOMAINS_KEY]: pending = [] } = await chrome.storage.local.get(this.PENDING_DOMAINS_KEY);

    return pending.includes(origin);
  },

  /**
   * Remove permission and unsync
   * @param {string} url - URL
   */
  async revokePermission(url) {
    const origin = this.getOriginPattern(url);
    if (!origin) return;

    // Remove from Chrome
    await new Promise(resolve => {
      chrome.permissions.remove({ origins: [origin] }, resolve);
    });

    // Remove from sync
    const { [this.STORAGE_KEY]: grantedDomains = [] } = await chrome.storage.sync.get(this.STORAGE_KEY);

    const filtered = grantedDomains.filter(d => d !== origin);
    await chrome.storage.sync.set({ [this.STORAGE_KEY]: filtered });

    console.log(`[YAWN] Revoked and unsynced permission for ${origin}`);
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
   * Initialize on extension startup - check for synced domains
   */
  async initialize() {
    console.log("[YAWN] Initializing PermissionManager");

    const syncedDomains = await this.getSyncedDomains();
    const localPermissions = await this.getAllGrantedOrigins();

    console.log("[YAWN] Synced domains:", syncedDomains);
    console.log("[YAWN] Local permissions:", localPermissions);

    // Find domains that are synced but not locally granted
    for (const origin of syncedDomains) {
      if (!localPermissions.includes(origin)) {
        console.log(`[YAWN] Domain ${origin} was granted on another device`);
        // Mark as pending - will show indicator on next visit
        const url = origin.replace("/*", "/");
        await this.markPendingPermission(url);
      }
    }
  },
};

// Make available globally for background script
if (typeof window !== "undefined") {
  window.PermissionManager = PermissionManager;
}
