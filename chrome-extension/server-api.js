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
      console.error("[YAWN] Failed to get server config:", error);
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
   * Get base web URL (without /api suffix)
   * @returns {Promise<string>} Base web URL
   */
  async getBaseUrl() {
    const config = await this.getConfig();
    return config.serverUrl.replace(/\/api$/, "");
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
      const response = await fetch(url, requestOptions);

      // Handle non-2xx status codes
      if (!response.ok) {
        // Handle 401 Unauthorized - try to refresh token
        if (response.status === 401 && typeof AuthManager !== "undefined") {
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
      console.error(`[YAWN] API Request failed (attempt ${retryCount + 1}):`, error);

      // Retry logic for network errors (but not for 401 retries)
      if (retryCount < this.RETRY_ATTEMPTS && this.shouldRetry(error)) {
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
      // Check if user is authenticated before making the request
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        return [];
      }

      const encodedUrl = encodeURIComponent(url);
      const response = await this.makeRequest(`/notes/by-url?url=${encodedUrl}&is_active=true`);
      const notes = await response.json();

      console.log(`[YAWN] Fetched ${notes.length} notes for URL ${url}`);
      return notes;
    } catch (error) {
      // Handle authentication errors gracefully
      if (error.message && (error.message.includes("HTTP 401") || error.message.includes("HTTP 403"))) {
        console.log("[YAWN] Authentication failed, skipping server note fetch:", error.message);
        return [];
      }

      console.error("[YAWN] Failed to fetch notes for page:", error);
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
      // Check authentication before attempting to create note
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        throw new Error("User not authenticated - cannot create note on server");
      }

      const serverNoteData = this.convertToServerFormatWithURL(noteData, url);

      const response = await this.makeRequest("/notes/with-url", {
        method: "POST",
        body: JSON.stringify(serverNoteData),
      });

      const createdNote = await response.json();
      console.log(`[YAWN] Created note ${createdNote.id} on server`);

      return createdNote;
    } catch (error) {
      // Handle authentication errors gracefully
      if (
        error.message &&
        (error.message.includes("HTTP 401") ||
          error.message.includes("HTTP 403") ||
          error.message.includes("not authenticated"))
      ) {
        console.log("[YAWN] Authentication failed during note creation:", error.message);
        throw new Error("AUTHENTICATION_REQUIRED");
      }

      console.error("[YAWN] Failed to create note:", error);
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
      // Check authentication before attempting to update note
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        throw new Error("User not authenticated - cannot update note on server");
      }

      const serverNoteData = this.convertToServerUpdateFormat(noteData);

      const response = await this.makeRequest(`/notes/${serverId}`, {
        method: "PUT",
        body: JSON.stringify(serverNoteData),
      });

      const updatedNote = await response.json();
      console.log(`[YAWN] Updated note ${serverId} on server`);

      return updatedNote;
    } catch (error) {
      // Handle authentication errors gracefully
      if (
        error.message &&
        (error.message.includes("HTTP 401") ||
          error.message.includes("HTTP 403") ||
          error.message.includes("not authenticated"))
      ) {
        console.log("[YAWN] Authentication failed during note update:", error.message);
        throw new Error("AUTHENTICATION_REQUIRED");
      }

      console.error("[YAWN] Failed to update note:", error);
      throw error;
    }
  },

  /**
   * Delete a note
   * @param {string} serverId - Server note ID
   * @returns {Promise<void>}
   */
  async deleteNote(serverId) {
    console.log("[YAWN] Delete Note " + serverId);
    try {
      // Check authentication before attempting to delete note
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        throw new Error("User not authenticated - cannot delete note on server");
      }

      await this.makeRequest(`/notes/${serverId}`, {
        method: "DELETE",
      });

      console.log(`[YAWN] Deleted note ${serverId} from server`);
    } catch (error) {
      // Handle authentication errors gracefully
      if (
        error.message &&
        (error.message.includes("HTTP 401") ||
          error.message.includes("HTTP 403") ||
          error.message.includes("not authenticated"))
      ) {
        console.log("[YAWN] Authentication failed during note deletion:", error.message);
        throw new Error("AUTHENTICATION_REQUIRED");
      }

      console.error("[YAWN] Failed to delete note:", error);
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
      // Check authentication before attempting bulk sync
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        throw new Error("User not authenticated - cannot sync notes to server");
      }

      const serverNotesData = notes.map(note => this.convertToServerFormatWithURL(note, url));

      const response = await this.makeRequest("/notes/bulk-with-url", {
        method: "POST",
        body: JSON.stringify({
          notes: serverNotesData,
        }),
      });

      const result = await response.json();
      console.log(`[YAWN] Bulk synced ${result.created_notes.length} notes, ${result.errors.length} errors`);

      return result;
    } catch (error) {
      // Handle authentication errors gracefully
      if (
        error.message &&
        (error.message.includes("HTTP 401") ||
          error.message.includes("HTTP 403") ||
          error.message.includes("not authenticated"))
      ) {
        console.log("[YAWN] Authentication failed during bulk sync:", error.message);
        throw new Error("AUTHENTICATION_REQUIRED");
      }

      console.error("[YAWN] Failed to bulk sync notes:", error);
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
      position_x: Math.floor(extensionNote.fallbackPosition?.x || 0),
      position_y: Math.floor(extensionNote.fallbackPosition?.y || 0),
      anchor_data: {
        elementSelector: extensionNote.elementSelector || null,
        elementXPath: extensionNote.elementXPath || null,
        offsetX: Math.floor(extensionNote.offsetX || 0),
        offsetY: Math.floor(extensionNote.offsetY || 0),
        selectionData: extensionNote.selectionData || null,
        backgroundColor: extensionNote.backgroundColor || "light-yellow",
        isMarkdown: extensionNote.isMarkdown || false,
        contentHash: extensionNote.contentHash || null,
      },
      is_active: extensionNote.isVisible !== false,
      server_link_id: extensionNote.id, // Use extension ID as link ID
      url: url,
      page_title: url || "",
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
      position_x: Math.floor(extensionNote.fallbackPosition?.x || 0),
      position_y: Math.floor(extensionNote.fallbackPosition?.y || 0),
      anchor_data: {
        elementSelector: extensionNote.elementSelector || null,
        elementXPath: extensionNote.elementXPath || null,
        offsetX: Math.floor(extensionNote.offsetX || 0),
        offsetY: Math.floor(extensionNote.offsetY || 0),
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
      console.error("[YAWN] Failed to get auth headers:", error);
      return {};
    }
  },

  /**
   * Register a page without creating a note
   * @param {string} url - Page URL
   * @param {string} title - Page title
   * @returns {Promise<Object>} Created page data
   */
  async registerPage(url, title) {
    try {
      // Check authentication before attempting to register page
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        throw new Error("User not authenticated - cannot register page on server");
      }

      const pageData = {
        url: url,
        title: title || null,
      };

      const response = await this.makeRequest("/pages/with-url", {
        method: "POST",
        body: JSON.stringify(pageData),
      });

      const createdPage = await response.json();
      console.log("[YAWN] Page registered successfully:", createdPage);
      return createdPage;
    } catch (error) {
      console.error("[YAWN] Failed to register page:", error);
      throw error;
    }
  },

  /**
   * Generate auto notes with DOM content
   * @param {number} pageId - Page ID
   * @param {string} pageDom - Page DOM/HTML content
   * @returns {Promise<Object>} Generated notes response
   */
  async generateAutoNotesWithDOM(pageId, pageDom) {
    try {
      // Check authentication before attempting
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        throw new Error("User not authenticated - cannot generate auto notes");
      }

      const requestData = {
        llm_provider_id: 1, // Default to Gemini
        template_type: "study_guide",
        page_dom: pageDom, // Send DOM content in page_dom field
        custom_instructions:
          "Use the provided DOM content to generate precise study notes with exact text matches and accurate CSS selectors.",
      };

      const response = await this.makeRequest(`/auto-notes/pages/${pageId}/generate`, {
        method: "POST",
        body: JSON.stringify(requestData),
      });

      const result = await response.json();
      console.log(`[YAWN] Generated ${result.notes?.length || 0} auto notes with DOM`);
      return result;
    } catch (error) {
      console.error("[YAWN] Failed to generate auto notes with DOM:", error);
      throw error;
    }
  },

  /**
   * Generate auto notes with DOM chunk (for large pages)
   * Used in batched parallel processing - processes multiple chunks simultaneously
   * @param {number} pageId - Page ID (already registered)
   * @param {Object} chunkData - Chunk metadata and content
   * @returns {Promise<Object>} Generation response for this chunk
   */
  async generateAutoNotesWithDOMChunk(pageId, chunkData) {
    try {
      // Check authentication before attempting
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        throw new Error("User not authenticated - cannot generate auto notes");
      }

      const requestData = {
        llm_provider_id: 1, // Default to Gemini
        template_type: "study_guide",
        chunk_index: chunkData.chunk_index,
        total_chunks: chunkData.total_chunks,
        chunk_dom: chunkData.chunk_dom,
        parent_context: chunkData.parent_context,
        batch_id: chunkData.batch_id, // Frontend-generated batch ID
        position_offset: chunkData.position_offset, // Position offset for this chunk
        custom_instructions:
          "Use the provided DOM content chunk to generate precise study notes. " +
          `This is chunk ${chunkData.chunk_index + 1} of ${chunkData.total_chunks}.`,
      };

      const response = await this.makeRequest(`/auto-notes/pages/${pageId}/generate/chunked`, {
        method: "POST",
        body: JSON.stringify(requestData),
      });

      const result = await response.json();
      console.log(
        `[YAWN] Generated ${result.notes?.length || 0} notes ` +
          `from chunk ${chunkData.chunk_index + 1}/${chunkData.total_chunks}`,
      );
      return result;
    } catch (error) {
      console.error("[YAWN] Failed to generate auto notes with DOM chunk:", error);
      throw error;
    }
  },

  /**
   * Generate auto notes with server-side chunking
   * Server handles all chunking and parallel processing
   * @param {number} pageId - Page ID
   * @param {string} fullDOM - Complete DOM content
   * @param {string} templateType - Template type ('study_guide' or 'content_review')
   * @param {string|null} customInstructions - Optional custom instructions for generation
   * @returns {Promise<Object>} Generation response with all notes
   */
  async generateAutoNotesWithFullDOM(pageId, fullDOM, templateType = "study_guide", customInstructions = null) {
    try {
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        throw new Error("User not authenticated");
      }

      const requestData = {
        llm_provider_id: 1, // Default to Gemini
        template_type: templateType,
        full_dom: fullDOM,
        custom_instructions: customInstructions || undefined, // Let backend use default if null
      };

      // New endpoint that handles everything server-side
      const response = await this.makeRequest(`/auto-notes/pages/${pageId}/generate/full-dom`, {
        method: "POST",
        body: JSON.stringify(requestData),
        // Increase timeout for large pages
        signal: AbortSignal.timeout(180000), // 3 minutes
      });

      const result = await response.json();
      console.log(`[YAWN] Generated ${result.notes?.length || 0} notes from ${result.total_chunks} chunks`);
      return result;
    } catch (error) {
      console.error("[YAWN] Failed to generate auto notes:", error);
      throw error;
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
      console.error("[YAWN] Failed to check auth mode:", error);
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
        return false;
      }

      if (AuthManager.isAuthenticated()) {
        return true;
      }

      // Try auto-auth first
      let success = await AuthManager.attemptAutoAuth();

      // If auto-auth fails and interactive is allowed, try interactive auth
      if (!success && interactive) {
        const user = await AuthManager.signIn(true);
        success = !!user;
      }

      if (success) {
        console.log("[YAWN] Authentication successful, server sync enabled");
      } else {
        console.log("[YAWN] Authentication failed, continuing in local mode");
      }

      return success;
    } catch (error) {
      console.error("[YAWN] Authentication attempt failed:", error);
      return false;
    }
  },

  /**
   * Clear configuration cache (force re-fetch on next request)
   */
  clearConfigCache() {
    this.cachedConfig = null;
    this.configLastFetched = 0;
    console.log("[YAWN] Cleared configuration cache");
  },
  // ===== AI CONTEXT GENERATION API ENDPOINTS =====

  /**
   * Get list of active LLM providers
   * @returns {Promise<Array>} Array of LLM provider objects
   */
  async getLLMProviders() {
    try {
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        throw new Error("User not authenticated - cannot fetch LLM providers");
      }

      const response = await this.makeRequest("/llm/providers");
      const providers = await response.json();

      console.log(`[YAWN] Retrieved ${providers.length} LLM providers`);
      return providers;
    } catch (error) {
      console.error("[YAWN] Failed to get LLM providers:", error);
      throw error;
    }
  },

  /**
   * Get or create a page by URL
   * @param {string} url - Page URL
   * @param {string} title - Page title
   * @returns {Promise<Object>} Page object with ID
   */
  async getOrCreatePageByUrl(url, title) {
    try {
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        throw new Error("User not authenticated - cannot get/create page");
      }

      // Use the existing registerPage method which creates or gets a page
      return await this.registerPage(url, title);
    } catch (error) {
      console.error("[YAWN] Failed to get/create page:", error);
      throw error;
    }
  },

  /**
   * Generate AI context for a page
   * @param {number} pageId - Page ID
   * @param {number} llmProviderId - LLM provider ID
   * @param {string|null} customInstructions - Optional custom instructions
   * @param {string|null} pageSource - Optional alternate page source (for paywalled content)
   * @param {string|null} pageDom - Optional page DOM for content extraction
   * @returns {Promise<Object>} Generated context response
   */
  async generatePageContext(pageId, llmProviderId, customInstructions = null, pageSource = null, pageDom = null) {
    try {
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        throw new Error("User not authenticated - cannot generate page context");
      }

      const requestData = {
        llm_provider_id: llmProviderId,
        custom_instructions: customInstructions,
        page_source: pageSource,
        page_dom: pageDom,
      };

      const response = await this.makeRequest(`/pages/${pageId}/generate-context`, {
        method: "POST",
        body: JSON.stringify(requestData),
      });

      const result = await response.json();
      console.log(`[YAWN] Generated page context: ${result.detected_content_type}`);
      return result;
    } catch (error) {
      console.error("[YAWN] Failed to generate page context:", error);
      throw error;
    }
  },

  /**
   * Preview the context generation prompt
   * @param {number} pageId - Page ID
   * @param {string|null} customInstructions - Optional custom instructions
   * @param {string|null} pageSource - Optional alternate page source
   * @param {string|null} pageDom - Optional page DOM for content extraction
   * @returns {Promise<Object>} Preview response with prompt text
   */
  async previewContextPrompt(pageId, customInstructions = null, pageSource = null, pageDom = null) {
    try {
      const isAuthenticated = await this.isAuthenticatedMode();
      if (!isAuthenticated) {
        throw new Error("User not authenticated - cannot preview context prompt");
      }

      const requestData = {
        custom_instructions: customInstructions,
        page_source: pageSource,
        page_dom: pageDom,
      };

      const response = await this.makeRequest(`/pages/${pageId}/preview-context`, {
        method: "POST",
        body: JSON.stringify(requestData),
      });

      const result = await response.json();
      console.log(`[YAWN] Preview prompt generated: ${result.prompt.length} characters`);
      return result;
    } catch (error) {
      console.error("[YAWN] Failed to preview context prompt:", error);
      throw error;
    }
  },

  // ===== SHARING API ENDPOINTS =====

  /**
   * Share a page with a user
   * @param {number} pageId - Page ID
   * @param {string} userEmail - User email to share with
   * @param {string} permissionLevel - Permission level (view, edit, admin)
   * @returns {Promise<Object>} Created share
   */
  async sharePageWithUser(pageId, userEmail, permissionLevel) {
    try {
      if (!pageId || !userEmail || !permissionLevel) {
        throw new Error("Page ID, user email, and permission level are required");
      }

      const response = await this.makeRequest(`/pages/${pageId}/share`, {
        method: "POST",
        body: JSON.stringify({
          user_email: userEmail.toLowerCase().trim(),
          permission_level: permissionLevel.toLowerCase(),
        }),
      });

      const share = await response.json();
      console.log(`[YAWN] Shared page ${pageId} with ${userEmail} (${permissionLevel})`);
      return share;
    } catch (error) {
      console.error("[YAWN] Failed to share page:", error);
      throw error;
    }
  },

  /**
   * Share a site with a user
   * @param {number} siteId - Site ID
   * @param {string} userEmail - User email to share with
   * @param {string} permissionLevel - Permission level (view, edit, admin)
   * @returns {Promise<Object>} Created share
   */
  async shareSiteWithUser(siteId, userEmail, permissionLevel) {
    try {
      if (!siteId || !userEmail || !permissionLevel) {
        throw new Error("Site ID, user email, and permission level are required");
      }

      const response = await this.makeRequest(`/sites/${siteId}/share`, {
        method: "POST",
        body: JSON.stringify({
          user_email: userEmail.toLowerCase().trim(),
          permission_level: permissionLevel.toLowerCase(),
        }),
      });

      const share = await response.json();
      console.log(`[YAWN] Shared site ${siteId} with ${userEmail} (${permissionLevel})`);
      return share;
    } catch (error) {
      console.error("[YAWN] Failed to share site:", error);
      throw error;
    }
  },

  /**
   * Get shares for a page
   * @param {number} pageId - Page ID
   * @returns {Promise<Array>} Array of shares
   */
  async getPageShares(pageId) {
    try {
      if (!pageId) {
        throw new Error("Page ID is required");
      }

      const response = await this.makeRequest(`/pages/${pageId}/shares`);
      const shares = await response.json();

      console.log(`[YAWN] Retrieved ${shares.length} shares for page ${pageId}`);
      return shares;
    } catch (error) {
      console.error("[YAWN] Failed to get page shares:", error);
      throw error;
    }
  },

  /**
   * Get shares for a site
   * @param {number} siteId - Site ID
   * @returns {Promise<Array>} Array of shares
   */
  async getSiteShares(siteId) {
    try {
      if (!siteId) {
        throw new Error("Site ID is required");
      }

      const response = await this.makeRequest(`/sites/${siteId}/shares`);
      const shares = await response.json();

      console.log(`[YAWN] Retrieved ${shares.length} shares for site ${siteId}`);
      return shares;
    } catch (error) {
      console.error("[YAWN] Failed to get site shares:", error);
      throw error;
    }
  },

  /**
   * Get all shares for current user
   * @returns {Promise<Object>} User shares organized by type (shared_sites, shared_pages)
   */
  async getMyShares() {
    try {
      const response = await this.makeRequest("/my-shares");
      const shares = await response.json();
      return shares;
    } catch (error) {
      console.error("[YAWN] Failed to get user shares:", error);
      throw error;
    }
  },

  /**
   * Update share permission for a page
   * @param {number} pageId - Page ID
   * @param {number} userId - User ID
   * @param {string} newPermission - New permission level (view, edit, admin)
   * @param {boolean} isActive - Whether the share is active
   * @returns {Promise<Object>} Updated share
   */
  async updatePageSharePermission(pageId, userId, newPermission, isActive = true) {
    try {
      if (!pageId || !userId || !newPermission) {
        throw new Error("Page ID, user ID, and new permission are required");
      }

      const body = {
        permission_level: newPermission.toLowerCase(),
        is_active: isActive,
      };

      const response = await this.makeRequest(`/pages/${pageId}/share/${userId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });

      const updatedShare = await response.json();
      return updatedShare;
    } catch (error) {
      console.error("[YAWN] Failed to update page share permission:", error);
      throw error;
    }
  },

  /**
   * Update share permission for a site
   * @param {number} siteId - Site ID
   * @param {number} userId - User ID
   * @param {string} newPermission - New permission level (view, edit, admin)
   * @param {boolean} isActive - Whether the share is active
   * @returns {Promise<Object>} Updated share
   */
  async updateSiteSharePermission(siteId, userId, newPermission, isActive = true) {
    try {
      if (!siteId || !userId || !newPermission) {
        throw new Error("Site ID, user ID, and new permission are required");
      }

      const body = {
        permission_level: newPermission.toLowerCase(),
        is_active: isActive,
      };

      const response = await this.makeRequest(`/sites/${siteId}/share/${userId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });

      const updatedShare = await response.json();
      return updatedShare;
    } catch (error) {
      console.error("[YAWN] Failed to update site share permission:", error);
      throw error;
    }
  },

  /**
   * Remove a page share
   * @param {number} pageId - Page ID
   * @param {number} userId - User ID
   * @returns {Promise<void>}
   */
  async removePageShare(pageId, userId) {
    try {
      if (!pageId || !userId) {
        throw new Error("Page ID and user ID are required");
      }

      await this.makeRequest(`/pages/${pageId}/share/${userId}`, {
        method: "DELETE",
      });

      console.log(`[YAWN] Removed page share for user ${userId}`);
    } catch (error) {
      console.error("[YAWN] Failed to remove page share:", error);
      throw error;
    }
  },

  /**
   * Remove a site share
   * @param {number} siteId - Site ID
   * @param {number} userId - User ID
   * @returns {Promise<void>}
   */
  async removeSiteShare(siteId, userId) {
    try {
      if (!siteId || !userId) {
        throw new Error("Site ID and user ID are required");
      }

      await this.makeRequest(`/sites/${siteId}/share/${userId}`, {
        method: "DELETE",
      });

      console.log(`[YAWN] Removed site share for user ${userId}`);
    } catch (error) {
      console.error("[YAWN] Failed to remove site share:", error);
      throw error;
    }
  },

  /**
   * Invite a user to share a resource (pre-registration)
   * @param {string} userEmail - Email of user to invite
   * @param {string} resourceType - Type of resource (site or page)
   * @param {number} resourceId - Resource ID
   * @param {string} permissionLevel - Permission level (view, edit, admin)
   * @param {string} invitationMessage - Optional invitation message
   * @returns {Promise<Object>} Invitation response
   */
  async inviteUser(userEmail, resourceType, resourceId, permissionLevel, invitationMessage = null) {
    try {
      if (!userEmail || !resourceType || !resourceId || !permissionLevel) {
        throw new Error("Email, resource type, resource ID, and permission level are required");
      }

      const response = await this.makeRequest("/invite", {
        method: "POST",
        body: JSON.stringify({
          user_email: userEmail.toLowerCase().trim(),
          resource_type: resourceType.toLowerCase(),
          resource_id: resourceId,
          permission_level: permissionLevel.toLowerCase(),
          invitation_message: invitationMessage,
        }),
      });

      const invite = await response.json();
      console.log(`[YAWN] Invited ${userEmail} to ${resourceType} ${resourceId}`);
      return invite;
    } catch (error) {
      console.error("[YAWN] Failed to invite user:", error);
      throw error;
    }
  },

  /**
   * Bulk share a page with multiple users
   * @param {number} pageId - Page ID
   * @param {Array} shareRequests - Array of {user_email, permission_level} objects
   * @returns {Promise<Array>} Array of created shares
   */
  async bulkSharePage(pageId, shareRequests) {
    try {
      if (!pageId || !shareRequests || !Array.isArray(shareRequests)) {
        throw new Error("Page ID and share requests array are required");
      }

      const response = await this.makeRequest(`/pages/${pageId}/share/bulk`, {
        method: "POST",
        body: JSON.stringify(shareRequests),
      });

      const shares = await response.json();
      console.log(`[YAWN] Bulk shared page ${pageId} with ${shares.length} users`);
      return shares;
    } catch (error) {
      console.error("[YAWN] Failed to bulk share page:", error);
      throw error;
    }
  },

  /**
   * Bulk share a site with multiple users
   * @param {number} siteId - Site ID
   * @param {Array} shareRequests - Array of {user_email, permission_level} objects
   * @returns {Promise<Array>} Array of created shares
   */
  async bulkShareSite(siteId, shareRequests) {
    try {
      if (!siteId || !shareRequests || !Array.isArray(shareRequests)) {
        throw new Error("Site ID and share requests array are required");
      }

      const response = await this.makeRequest(`/sites/${siteId}/share/bulk`, {
        method: "POST",
        body: JSON.stringify(shareRequests),
      });

      const shares = await response.json();
      console.log(`[YAWN] Bulk shared site ${siteId} with ${shares.length} users`);
      return shares;
    } catch (error) {
      console.error("[YAWN] Failed to bulk share site:", error);
      throw error;
    }
  },
};

// Export for use in other scripts
if (typeof module !== "undefined" && module.exports) {
  module.exports = { ServerAPI };
}
