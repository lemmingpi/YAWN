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

  // Note: pageIdCache removed - no longer needed with direct URL queries

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
      console.error(`[Web Notes] API Request failed (attempt ${retryCount + 1}):`, error);

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

  // Note: getOrCreatePage and getOrCreateSite methods removed
  // Notes are now created directly with URLs, and pages/sites are auto-created by the server

  /**
   * Fetch notes for a page by URL directly
   * @param {string} url - The page URL
   * @returns {Promise<Array>} Array of notes
   */
  async fetchNotesForPage(url) {
    try {
      const encodedUrl = encodeURIComponent(url);
      const response = await this.makeRequest(`/notes/by-url?url=${encodedUrl}&is_active=true`);
      const notes = await response.json();

      console.log(`[Web Notes] Fetched ${notes.length} notes for URL ${url}`);
      return notes;
    } catch (error) {
      console.error("[Web Notes] Failed to fetch notes for page:", error);
      throw error;
    }
  },

  /**
   * Create a new note with URL (auto-creates page/site)
   * @param {string} url - The page URL
   * @param {Object} noteData - Note data
   * @returns {Promise<Object>} Created note
   */
  async createNote(url, noteData) {
    try {
      const serverNoteData = this.convertToServerFormatWithURL(noteData, url);

      const response = await this.makeRequest("/notes/with-url", {
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
   * Bulk create/update notes with URL (auto-creates pages/sites)
   * @param {string} url - The page URL
   * @param {Array} notes - Array of notes to create/update
   * @returns {Promise<Object>} Bulk operation result
   */
  async bulkSyncNotes(url, notes) {
    try {
      const serverNotesData = notes.map(note => this.convertToServerFormatWithURL(note, url));

      const response = await this.makeRequest("/notes/bulk-with-url", {
        method: "POST",
        body: JSON.stringify({
          notes: serverNotesData,
        }),
      });

      const result = await response.json();
      console.log(`[Web Notes] Bulk synced ${result.created_notes.length} notes, ${result.errors.length} errors`);

      return result;
    } catch (error) {
      console.error("[Web Notes] Failed to bulk sync notes:", error);
      throw error;
    }
  },

  /**
   * Convert extension note format to server format with URL
   * @param {Object} extensionNote - Note in extension format
   * @param {string} url - Page URL
   * @returns {Object} Note in server format with URL
   */
  convertToServerFormatWithURL(extensionNote, url) {
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
      url: url,
      page_title: document.title || "",
    };
  },

  /**
   * Convert extension note format to server format (legacy - for compatibility)
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
