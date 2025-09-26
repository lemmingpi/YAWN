/**
 * Server API Communication Module
 * Handles all HTTP requests to the Web Notes server API
 * Provides clean interface for Chrome extension server sync
 */

/* eslint-env webextensions */

/**
 * Server API configuration and utilities
 */
const ServerAPI = {
  // Default configuration
  DEFAULT_SERVER_URL: "http://localhost:8000/api",
  REQUEST_TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1 second

  // Cache for page ID resolution
  pageIdCache: new Map(),

  // In-memory cache for server configuration
  cachedConfig: null,
  configLastFetched: 0,
  CONFIG_CACHE_TTL: 5 * 60 * 1000, // 5 minutes

  /**
   * Get server configuration from storage with caching
   * @returns {Promise<Object>} Server configuration
   */
  async getConfig() {
    const now = Date.now();

    // Return cached config if still valid
    if (this.cachedConfig && now - this.configLastFetched < this.CONFIG_CACHE_TTL) {
      return this.cachedConfig;
    }

    try {
      const config = await getWNConfig();
      this.cachedConfig = {
        serverUrl: config.syncServerUrl || this.DEFAULT_SERVER_URL,
        enabled: !!config.syncServerUrl, // Enable server sync if URL is configured
      };
      this.configLastFetched = now;
      return this.cachedConfig;
    } catch (error) {
      console.error("[Web Notes] Failed to get server config:", error);
      return {
        serverUrl: this.DEFAULT_SERVER_URL,
        enabled: false,
      };
    }
  },

  /**
   * Check if server sync is enabled
   * @returns {Promise<boolean>} True if server sync is enabled
   */
  async isEnabled() {
    const config = await this.getConfig();
    return config.enabled;
  },

  /**
   * Make HTTP request with error handling and retries
   * @param {string} endpoint - API endpoint (relative to server URL)
   * @param {Object} options - Fetch options
   * @param {number} retryCount - Current retry attempt
   * @returns {Promise<Response>} Fetch response
   */
  async makeRequest(endpoint, options = {}, retryCount = 0) {
    const config = await this.getConfig();
    const url = `${config.serverUrl}${endpoint}`;

    const defaultOptions = {
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      signal: AbortSignal.timeout(this.REQUEST_TIMEOUT),
    };

    const requestOptions = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers,
      },
    };

    try {
      console.log(`[Web Notes] API Request: ${options.method || "GET"} ${url}`);
      const response = await fetch(url, requestOptions);

      // Handle non-2xx status codes
      if (!response.ok) {
        const errorText = await response.text().catch(() => "Unknown error");
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      return response;
    } catch (error) {
      console.error(
        `[Web Notes] API Request failed (attempt ${retryCount + 1}):`,
        error
      );

      // Retry logic for network errors
      if (retryCount < this.RETRY_ATTEMPTS && this.shouldRetry(error)) {
        console.log(`[Web Notes] Retrying request in ${this.RETRY_DELAY}ms...`);
        await this.delay(this.RETRY_DELAY);
        return this.makeRequest(endpoint, options, retryCount + 1);
      }

      throw error;
    }
  },

  /**
   * Determine if an error should trigger a retry
   * @param {Error} error - The error to check
   * @returns {boolean} True if should retry
   */
  shouldRetry(error) {
    // Retry on network errors, timeouts, and 5xx server errors
    return (
      error.name === "TypeError" || // Network error
      error.name === "AbortError" || // Timeout
      (error.message && error.message.includes("HTTP 5")) // 5xx server error
    );
  },

  /**
   * Delay utility for retries
   * @param {number} ms - Milliseconds to delay
   * @returns {Promise} Promise that resolves after delay
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  },

  /**
   * Get or create a page by URL
   * @param {string} url - The page URL
   * @returns {Promise<Object>} Page object with ID
   */
  async getOrCreatePage(url) {
    try {
      const normalizedUrl = normalizeUrlForNoteStorage(url);

      // Check cache first
      if (this.pageIdCache.has(normalizedUrl)) {
        return this.pageIdCache.get(normalizedUrl);
      }

      // Try to find existing page
      const encodedUrl = encodeURIComponent(normalizedUrl);
      let response = await this.makeRequest(`/pages/?search=${encodedUrl}&limit=1`);
      let pages = await response.json();

      if (pages.length > 0) {
        const page = pages[0];
        this.pageIdCache.set(normalizedUrl, page);
        return page;
      }

      // Create new page if not found
      const domain = new URL(normalizedUrl).hostname;

      // First, get or create the site
      const site = await this.getOrCreateSite(domain);

      const pageData = {
        url: normalizedUrl,
        title: document.title || "",
        site_id: site.id,
      };

      response = await this.makeRequest("/pages/", {
        method: "POST",
        body: JSON.stringify(pageData),
      });

      const newPage = await response.json();
      this.pageIdCache.set(normalizedUrl, newPage);
      console.log(`[Web Notes] Created new page: ${newPage.id} for ${normalizedUrl}`);

      return newPage;
    } catch (error) {
      console.error("[Web Notes] Failed to get/create page:", error);
      throw error;
    }
  },

  /**
   * Get or create a site by domain
   * @param {string} domain - The site domain
   * @returns {Promise<Object>} Site object with ID
   */
  async getOrCreateSite(domain) {
    try {
      // Try to find existing site
      const encodedDomain = encodeURIComponent(domain);
      let response = await this.makeRequest(`/sites/?search=${encodedDomain}&limit=1`);
      let sites = await response.json();

      if (sites.length > 0) {
        return sites[0];
      }

      // Create new site if not found
      const siteData = {
        domain: domain,
        user_context: "",
      };

      response = await this.makeRequest("/sites/", {
        method: "POST",
        body: JSON.stringify(siteData),
      });

      const newSite = await response.json();
      console.log(`[Web Notes] Created new site: ${newSite.id} for ${domain}`);

      return newSite;
    } catch (error) {
      console.error("[Web Notes] Failed to get/create site:", error);
      throw error;
    }
  },

  /**
   * Fetch notes for a page
   * @param {string} url - The page URL
   * @returns {Promise<Array>} Array of notes
   */
  async fetchNotesForPage(url) {
    try {
      const page = await this.getOrCreatePage(url);
      const response = await this.makeRequest(
        `/notes/?page_id=${page.id}&is_active=true`
      );
      const notes = await response.json();

      console.log(`[Web Notes] Fetched ${notes.length} notes for page ${page.id}`);
      return notes;
    } catch (error) {
      console.error("[Web Notes] Failed to fetch notes for page:", error);
      throw error;
    }
  },

  /**
   * Create a new note
   * @param {string} url - The page URL
   * @param {Object} noteData - Note data
   * @returns {Promise<Object>} Created note
   */
  async createNote(url, noteData) {
    try {
      const page = await this.getOrCreatePage(url);

      const serverNoteData = this.convertToServerFormat(noteData, page.id);

      const response = await this.makeRequest("/notes/", {
        method: "POST",
        body: JSON.stringify(serverNoteData),
      });

      const createdNote = await response.json();
      console.log(`[Web Notes] Created note ${createdNote.id} on server`);

      return createdNote;
    } catch (error) {
      console.error("[Web Notes] Failed to create note:", error);
      throw error;
    }
  },

  /**
   * Update an existing note
   * @param {string} serverId - Server note ID
   * @param {Object} noteData - Updated note data
   * @returns {Promise<Object>} Updated note
   */
  async updateNote(serverId, noteData) {
    try {
      const serverNoteData = this.convertToServerUpdateFormat(noteData);

      const response = await this.makeRequest(`/notes/${serverId}`, {
        method: "PUT",
        body: JSON.stringify(serverNoteData),
      });

      const updatedNote = await response.json();
      console.log(`[Web Notes] Updated note ${serverId} on server`);

      return updatedNote;
    } catch (error) {
      console.error("[Web Notes] Failed to update note:", error);
      throw error;
    }
  },

  /**
   * Delete a note
   * @param {string} serverId - Server note ID
   * @returns {Promise<void>}
   */
  async deleteNote(serverId) {
    try {
      await this.makeRequest(`/notes/${serverId}`, {
        method: "DELETE",
      });

      console.log(`[Web Notes] Deleted note ${serverId} from server`);
    } catch (error) {
      console.error("[Web Notes] Failed to delete note:", error);
      throw error;
    }
  },

  /**
   * Bulk create/update notes
   * @param {string} url - The page URL
   * @param {Array} notes - Array of notes to create/update
   * @returns {Promise<Object>} Bulk operation result
   */
  async bulkSyncNotes(url, notes) {
    try {
      const page = await this.getOrCreatePage(url);

      const serverNotesData = notes.map(note =>
        this.convertToServerFormat(note, page.id)
      );

      const response = await this.makeRequest("/notes/bulk", {
        method: "POST",
        body: JSON.stringify({
          notes: serverNotesData,
        }),
      });

      const result = await response.json();
      console.log(
        `[Web Notes] Bulk synced ${result.created_notes.length} notes, ${result.errors.length} errors`
      );

      return result;
    } catch (error) {
      console.error("[Web Notes] Failed to bulk sync notes:", error);
      throw error;
    }
  },

  /**
   * Convert extension note format to server format
   * @param {Object} extensionNote - Note in extension format
   * @param {number} pageId - Server page ID
   * @returns {Object} Note in server format
   */
  convertToServerFormat(extensionNote, pageId) {
    return {
      content: extensionNote.content || "",
      position_x: extensionNote.fallbackPosition?.x || 0,
      position_y: extensionNote.fallbackPosition?.y || 0,
      anchor_data: {
        elementSelector: extensionNote.elementSelector || null,
        elementXPath: extensionNote.elementXPath || null,
        offsetX: extensionNote.offsetX || 0,
        offsetY: extensionNote.offsetY || 0,
        selectionData: extensionNote.selectionData || null,
        backgroundColor: extensionNote.backgroundColor || "light-yellow",
        isMarkdown: extensionNote.isMarkdown || false,
        contentHash: extensionNote.contentHash || null,
      },
      is_active: extensionNote.isVisible !== false,
      server_link_id: extensionNote.id, // Use extension ID as link ID
      page_id: pageId,
    };
  },

  /**
   * Convert extension note format to server update format
   * @param {Object} extensionNote - Note in extension format
   * @returns {Object} Note update data in server format
   */
  convertToServerUpdateFormat(extensionNote) {
    const updateData = {
      content: extensionNote.content,
    };

    if (extensionNote.fallbackPosition) {
      updateData.position_x = extensionNote.fallbackPosition.x;
      updateData.position_y = extensionNote.fallbackPosition.y;
    }

    updateData.anchor_data = {
      elementSelector: extensionNote.elementSelector || null,
      elementXPath: extensionNote.elementXPath || null,
      offsetX: extensionNote.offsetX || 0,
      offsetY: extensionNote.offsetY || 0,
      selectionData: extensionNote.selectionData || null,
      backgroundColor: extensionNote.backgroundColor || "light-yellow",
      isMarkdown: extensionNote.isMarkdown || false,
      contentHash: extensionNote.contentHash || null,
    };

    if (extensionNote.isVisible !== undefined) {
      updateData.is_active = extensionNote.isVisible;
    }

    return updateData;
  },

  /**
   * Convert server note format to extension format
   * @param {Object} serverNote - Note in server format
   * @returns {Object} Note in extension format
   */
  convertFromServerFormat(serverNote) {
    const anchorData = serverNote.anchor_data || {};

    return {
      id: serverNote.server_link_id || `server-${serverNote.id}`,
      serverId: serverNote.id, // Store server ID for updates
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
  },

  /**
   * Clear page ID cache (useful for testing or when URLs change)
   */
  clearPageCache() {
    this.pageIdCache.clear();
    console.log("[Web Notes] Cleared page ID cache");
  },

  /**
   * Clear configuration cache (force re-fetch on next request)
   */
  clearConfigCache() {
    this.cachedConfig = null;
    this.configLastFetched = 0;
    console.log("[Web Notes] Cleared configuration cache");
  },
};

// Export for use in other scripts
if (typeof module !== "undefined" && module.exports) {
  module.exports = { ServerAPI };
}
