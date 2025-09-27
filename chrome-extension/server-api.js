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

    // Add authentication headers if user is authenticated
    const authHeaders = await this.getAuthHeaders();

    const requestOptions = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...authHeaders,
        ...options.headers,
      },
    };

    try {
      console.log(`[Web Notes] API Request: ${options.method || "GET"} ${url}`);
      const response = await fetch(url, requestOptions);

      // Handle non-2xx status codes
      if (!response.ok) {
        // Handle 401 Unauthorized - try to refresh token
        if (response.status === 401 && typeof AuthManager !== "undefined") {
          console.log("[Web Notes] Received 401, attempting token refresh");
          const refreshed = await AuthManager.refreshTokenIfNeeded();

          // Retry the request once with new token if refresh was successful
          if (refreshed && retryCount === 0) {
            return this.makeRequest(endpoint, options, retryCount + 1);
          }
        }

        const errorText = await response.text().catch(() => "Unknown error");
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      return response;
    } catch (error) {
      console.error(`[Web Notes] API Request failed (attempt ${retryCount + 1}):`, error);

      // Retry logic for network errors (but not for 401 retries)
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
   * Get authentication headers for API requests
   * @returns {Promise<Object>} Authentication headers object
   */
  async getAuthHeaders() {
    try {
      // Check if AuthManager is available and user is authenticated
      if (typeof AuthManager !== "undefined" && AuthManager.isAuthenticated()) {
        const token = AuthManager.getCurrentToken();
        if (token) {
          return {
            Authorization: `Bearer ${token}`,
          };
        }
      }
      return {};
    } catch (error) {
      console.error("[Web Notes] Failed to get auth headers:", error);
      return {};
    }
  },

  /**
   * Check if current request should include authentication
   * @returns {Promise<boolean>} True if authenticated requests should be made
   */
  async isAuthenticatedMode() {
    try {
      return typeof AuthManager !== "undefined" && AuthManager.isAuthenticated();
    } catch (error) {
      console.error("[Web Notes] Failed to check auth mode:", error);
      return false;
    }
  },

  /**
   * Attempt to authenticate user for server operations
   * @param {boolean} interactive - Whether to show interactive auth UI
   * @returns {Promise<boolean>} True if authentication was successful
   */
  async ensureAuthenticated(interactive = true) {
    try {
      if (typeof AuthManager === "undefined") {
        console.log("[Web Notes] AuthManager not available, using local mode");
        return false;
      }

      if (AuthManager.isAuthenticated()) {
        return true;
      }

      console.log("[Web Notes] Attempting authentication for server sync");

      // Try auto-auth first
      let success = await AuthManager.attemptAutoAuth();

      // If auto-auth fails and interactive is allowed, try interactive auth
      if (!success && interactive) {
        const user = await AuthManager.signIn(true);
        success = !!user;
      }

      if (success) {
        console.log("[Web Notes] Authentication successful, server sync enabled");
      } else {
        console.log("[Web Notes] Authentication failed, continuing in local mode");
      }

      return success;
    } catch (error) {
      console.error("[Web Notes] Authentication attempt failed:", error);
      return false;
    }
  },

  /**
   * Clear configuration cache (force re-fetch on next request)
   */
  clearConfigCache() {
    this.cachedConfig = null;
    this.configLastFetched = 0;
    console.log("[Web Notes] Cleared configuration cache");
  },

  // ===== SHARING API ENDPOINTS =====

  /**
   * Share a note with a user
   * @param {string} noteId - Note ID
   * @param {string} userEmail - User email to share with
   * @param {string} permissionLevel - Permission level (VIEW, EDIT, ADMIN)
   * @returns {Promise<Object>} Created share
   */
  async shareNoteWithUser(noteId, userEmail, permissionLevel) {
    try {
      if (!noteId || !userEmail || !permissionLevel) {
        throw new Error("Note ID, user email, and permission level are required");
      }

      const response = await this.makeRequest("/shares/notes", {
        method: "POST",
        body: JSON.stringify({
          note_id: noteId,
          user_email: userEmail.toLowerCase().trim(),
          permission_level: permissionLevel.toUpperCase(),
        }),
      });

      const share = await response.json();
      console.log(`[Web Notes] Shared note ${noteId} with ${userEmail} (${permissionLevel})`);
      return share;
    } catch (error) {
      console.error("[Web Notes] Failed to share note:", error);
      throw error;
    }
  },

  /**
   * Share a page with a user
   * @param {string} pageUrl - Page URL
   * @param {string} userEmail - User email to share with
   * @param {string} permissionLevel - Permission level (VIEW, EDIT, ADMIN)
   * @returns {Promise<Object>} Created share
   */
  async sharePageWithUser(pageUrl, userEmail, permissionLevel) {
    try {
      if (!pageUrl || !userEmail || !permissionLevel) {
        throw new Error("Page URL, user email, and permission level are required");
      }

      const response = await this.makeRequest("/shares/pages", {
        method: "POST",
        body: JSON.stringify({
          page_url: pageUrl,
          user_email: userEmail.toLowerCase().trim(),
          permission_level: permissionLevel.toUpperCase(),
        }),
      });

      const share = await response.json();
      console.log(`[Web Notes] Shared page ${pageUrl} with ${userEmail} (${permissionLevel})`);
      return share;
    } catch (error) {
      console.error("[Web Notes] Failed to share page:", error);
      throw error;
    }
  },

  /**
   * Share a site with a user
   * @param {string} domain - Site domain
   * @param {string} userEmail - User email to share with
   * @param {string} permissionLevel - Permission level (VIEW, EDIT, ADMIN)
   * @returns {Promise<Object>} Created share
   */
  async shareSiteWithUser(domain, userEmail, permissionLevel) {
    try {
      if (!domain || !userEmail || !permissionLevel) {
        throw new Error("Domain, user email, and permission level are required");
      }

      const response = await this.makeRequest("/shares/sites", {
        method: "POST",
        body: JSON.stringify({
          domain: domain.toLowerCase(),
          user_email: userEmail.toLowerCase().trim(),
          permission_level: permissionLevel.toUpperCase(),
        }),
      });

      const share = await response.json();
      console.log(`[Web Notes] Shared site ${domain} with ${userEmail} (${permissionLevel})`);
      return share;
    } catch (error) {
      console.error("[Web Notes] Failed to share site:", error);
      throw error;
    }
  },

  /**
   * Get shares for a note
   * @param {string} noteId - Note ID
   * @returns {Promise<Array>} Array of shares
   */
  async getNoteShares(noteId) {
    try {
      if (!noteId) {
        throw new Error("Note ID is required");
      }

      const response = await this.makeRequest(`/shares/notes/${encodeURIComponent(noteId)}`);
      const shares = await response.json();

      console.log(`[Web Notes] Retrieved ${shares.length} shares for note ${noteId}`);
      return shares;
    } catch (error) {
      console.error("[Web Notes] Failed to get note shares:", error);
      throw error;
    }
  },

  /**
   * Get shares for a page
   * @param {string} pageUrl - Page URL
   * @returns {Promise<Array>} Array of shares
   */
  async getPageShares(pageUrl) {
    try {
      if (!pageUrl) {
        throw new Error("Page URL is required");
      }

      const encodedUrl = encodeURIComponent(pageUrl);
      const response = await this.makeRequest(`/shares/pages?url=${encodedUrl}`);
      const shares = await response.json();

      console.log(`[Web Notes] Retrieved ${shares.length} shares for page ${pageUrl}`);
      return shares;
    } catch (error) {
      console.error("[Web Notes] Failed to get page shares:", error);
      throw error;
    }
  },

  /**
   * Get shares for a site
   * @param {string} domain - Site domain
   * @returns {Promise<Array>} Array of shares
   */
  async getSiteShares(domain) {
    try {
      if (!domain) {
        throw new Error("Domain is required");
      }

      const response = await this.makeRequest(`/shares/sites/${encodeURIComponent(domain)}`);
      const shares = await response.json();

      console.log(`[Web Notes] Retrieved ${shares.length} shares for site ${domain}`);
      return shares;
    } catch (error) {
      console.error("[Web Notes] Failed to get site shares:", error);
      throw error;
    }
  },

  /**
   * Get all shares for current user
   * @returns {Promise<Object>} User shares organized by type
   */
  async getUserShares() {
    try {
      const response = await this.makeRequest("/shares/user");
      const shares = await response.json();

      console.log(
        `[Web Notes] Retrieved user shares: ${shares.notes?.length || 0} notes, ${shares.pages?.length || 0} pages, ${shares.sites?.length || 0} sites`
      );
      return shares;
    } catch (error) {
      console.error("[Web Notes] Failed to get user shares:", error);
      throw error;
    }
  },

  /**
   * Update share permission
   * @param {string} shareType - Type of share (note, page, site)
   * @param {string} resourceId - Resource identifier
   * @param {string} userId - User ID
   * @param {string} newPermission - New permission level
   * @returns {Promise<Object>} Updated share
   */
  async updateSharePermission(shareType, resourceId, userId, newPermission) {
    try {
      if (!shareType || !resourceId || !userId || !newPermission) {
        throw new Error("Share type, resource ID, user ID, and new permission are required");
      }

      let endpoint;
      let body;

      switch (shareType) {
        case "note":
          endpoint = `/shares/notes/${encodeURIComponent(resourceId)}/users/${encodeURIComponent(userId)}`;
          body = { permission_level: newPermission.toUpperCase() };
          break;
        case "page":
          endpoint = `/shares/pages/users/${encodeURIComponent(userId)}`;
          body = {
            page_url: resourceId,
            permission_level: newPermission.toUpperCase(),
          };
          break;
        case "site":
          endpoint = `/shares/sites/${encodeURIComponent(resourceId)}/users/${encodeURIComponent(userId)}`;
          body = { permission_level: newPermission.toUpperCase() };
          break;
        default:
          throw new Error(`Invalid share type: ${shareType}`);
      }

      const response = await this.makeRequest(endpoint, {
        method: "PUT",
        body: JSON.stringify(body),
      });

      const updatedShare = await response.json();
      console.log(`[Web Notes] Updated ${shareType} share permission for user ${userId} to ${newPermission}`);
      return updatedShare;
    } catch (error) {
      console.error("[Web Notes] Failed to update share permission:", error);
      throw error;
    }
  },

  /**
   * Remove a share
   * @param {string} shareType - Type of share (note, page, site)
   * @param {string} resourceId - Resource identifier
   * @param {string} userId - User ID
   * @returns {Promise<void>}
   */
  async removeShare(shareType, resourceId, userId) {
    try {
      if (!shareType || !resourceId || !userId) {
        throw new Error("Share type, resource ID, and user ID are required");
      }

      let endpoint;

      switch (shareType) {
        case "note":
          endpoint = `/shares/notes/${encodeURIComponent(resourceId)}/users/${encodeURIComponent(userId)}`;
          break;
        case "page":
          endpoint = `/shares/pages/users/${encodeURIComponent(userId)}?url=${encodeURIComponent(resourceId)}`;
          break;
        case "site":
          endpoint = `/shares/sites/${encodeURIComponent(resourceId)}/users/${encodeURIComponent(userId)}`;
          break;
        default:
          throw new Error(`Invalid share type: ${shareType}`);
      }

      await this.makeRequest(endpoint, {
        method: "DELETE",
      });

      console.log(`[Web Notes] Removed ${shareType} share for user ${userId}`);
    } catch (error) {
      console.error("[Web Notes] Failed to remove share:", error);
      throw error;
    }
  },

  /**
   * Generate shareable link for a resource
   * @param {string} shareType - Type of share (note, page, site)
   * @param {string} resourceId - Resource identifier
   * @returns {Promise<string>} Shareable link
   */
  async generateShareLink(shareType, resourceId) {
    try {
      if (!shareType || !resourceId) {
        throw new Error("Share type and resource ID are required");
      }

      let endpoint;
      let body;

      switch (shareType) {
        case "note":
          endpoint = "/shares/links/notes";
          body = { note_id: resourceId };
          break;
        case "page":
          endpoint = "/shares/links/pages";
          body = { page_url: resourceId };
          break;
        case "site":
          endpoint = "/shares/links/sites";
          body = { domain: resourceId };
          break;
        default:
          throw new Error(`Invalid share type: ${shareType}`);
      }

      const response = await this.makeRequest(endpoint, {
        method: "POST",
        body: JSON.stringify(body),
      });

      const result = await response.json();
      console.log(`[Web Notes] Generated share link for ${shareType}: ${resourceId}`);
      return result.share_link;
    } catch (error) {
      console.error("[Web Notes] Failed to generate share link:", error);
      throw error;
    }
  },

  /**
   * Check sharing status for a resource
   * @param {string} shareType - Type of share (note, page, site)
   * @param {string} resourceId - Resource identifier
   * @returns {Promise<Object>} Sharing status
   */
  async getSharingStatus(shareType, resourceId) {
    try {
      if (!shareType || !resourceId) {
        throw new Error("Share type and resource ID are required");
      }

      let endpoint;

      switch (shareType) {
        case "note":
          endpoint = `/shares/status/notes/${encodeURIComponent(resourceId)}`;
          break;
        case "page":
          endpoint = `/shares/status/pages?url=${encodeURIComponent(resourceId)}`;
          break;
        case "site":
          endpoint = `/shares/status/sites/${encodeURIComponent(resourceId)}`;
          break;
        default:
          throw new Error(`Invalid share type: ${shareType}`);
      }

      const response = await this.makeRequest(endpoint);
      const status = await response.json();

      console.log(`[Web Notes] Retrieved sharing status for ${shareType}: ${resourceId}`);
      return status;
    } catch (error) {
      console.error("[Web Notes] Failed to get sharing status:", error);
      throw error;
    }
  },

  /**
   * Validate user email for sharing
   * @param {string} email - Email to validate
   * @returns {Promise<Object>} Validation result
   */
  async validateUserEmail(email) {
    try {
      if (!email) {
        throw new Error("Email is required");
      }

      const response = await this.makeRequest("/users/validate-email", {
        method: "POST",
        body: JSON.stringify({
          email: email.toLowerCase().trim(),
        }),
      });

      const result = await response.json();
      console.log(`[Web Notes] Validated email ${email}: ${result.is_valid ? "valid" : "invalid"}`);
      return result;
    } catch (error) {
      console.error("[Web Notes] Failed to validate email:", error);
      throw error;
    }
  },
};

// Export for use in other scripts
if (typeof module !== "undefined" && module.exports) {
  module.exports = { ServerAPI };
}
