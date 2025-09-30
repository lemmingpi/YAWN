/**
 * Authentication Manager for Web Notes Chrome Extension
 * Handles Chrome Identity API integration, JWT token management, and user session
 * Provides seamless authentication with Google OAuth2 and backend API integration
 */

/* eslint-env webextensions */

/**
 * Authentication Manager - Handles all authentication operations
 */
const AuthManager = {
  // Storage keys for authentication data
  STORAGE_KEYS: {
    JWT_TOKEN: "webNotesJWT",
    USER_INFO: "webNotesUser",
    AUTH_STATE: "webNotesAuthState",
    LAST_AUTH_CHECK: "webNotesLastAuthCheck",
  },

  // Authentication configuration
  CONFIG: {
    SCOPES: ["openid", "email", "profile"],
    TOKEN_REFRESH_THRESHOLD: 5 * 60 * 1000, // 5 minutes in milliseconds
    AUTH_CHECK_INTERVAL: 10 * 60 * 1000, // 10 minutes
    MAX_RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000, // 1 second
  },

  // Cache for authentication state
  _authCache: {
    isAuthenticated: null,
    user: null,
    jwtToken: null,
    lastCheck: 0,
  },

  // Event listeners for authentication state changes
  _listeners: new Set(),

  // Initialization promise
  _initPromise: null,

  /**
   * Initialize authentication manager
   * @returns {Promise<void>}
   */
  async initialize() {
    // Return existing promise if already initializing
    if (this._initPromise) {
      return this._initPromise;
    }

    this._initPromise = this._doInitialize();
    return this._initPromise;
  },

  /**
   * Internal initialization implementation
   * @returns {Promise<void>}
   */
  async _doInitialize() {
    try {
      console.log("[Auth] Initializing authentication manager");

      // Load cached authentication state
      await this.loadAuthState();

      // Set up periodic token validation
      this.setupTokenValidation();

      console.log("[Auth] Authentication manager initialized");
    } catch (error) {
      console.error("[Auth] Failed to initialize authentication manager:", error);
      throw error;
    }
  },

  /**
   * Load authentication state from storage
   * @returns {Promise<void>}
   */
  async loadAuthState() {
    try {
      const result = await new Promise(resolve => {
        chrome.storage.sync.get(
          [
            this.STORAGE_KEYS.JWT_TOKEN,
            this.STORAGE_KEYS.USER_INFO,
            this.STORAGE_KEYS.AUTH_STATE,
            this.STORAGE_KEYS.LAST_AUTH_CHECK,
          ],
          resolve
        );
      });

      this._authCache = {
        isAuthenticated: result[this.STORAGE_KEYS.AUTH_STATE] || false,
        user: result[this.STORAGE_KEYS.USER_INFO] || null,
        jwtToken: result[this.STORAGE_KEYS.JWT_TOKEN] || null,
        lastCheck: result[this.STORAGE_KEYS.LAST_AUTH_CHECK] || 0,
      };

      // Validate token if present
      if (this._authCache.jwtToken) {
        const isValid = await this.validateToken(this._authCache.jwtToken);
        if (!isValid) {
          await this.clearAuthState();
        }
      }

      console.log("[Auth] Loaded auth state:", {
        isAuthenticated: this._authCache.isAuthenticated,
        hasUser: !!this._authCache.user,
        hasToken: !!this._authCache.jwtToken,
        userEmail: this._authCache.user?.email || "none",
        tokenExpiry: this._authCache.jwtToken ? this.getTokenExpiry(this._authCache.jwtToken) : "none",
      });
    } catch (error) {
      console.error("[Auth] Failed to load auth state:", error);
      await this.clearAuthState();
    }
  },

  /**
   * Save authentication state to storage
   * @returns {Promise<void>}
   */
  async saveAuthState() {
    try {
      const data = {
        [this.STORAGE_KEYS.JWT_TOKEN]: this._authCache.jwtToken,
        [this.STORAGE_KEYS.USER_INFO]: this._authCache.user,
        [this.STORAGE_KEYS.AUTH_STATE]: this._authCache.isAuthenticated,
        [this.STORAGE_KEYS.LAST_AUTH_CHECK]: Date.now(),
      };

      await new Promise((resolve, reject) => {
        chrome.storage.sync.set(data, () => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve();
          }
        });
      });

      console.log("[Auth] Saved auth state to storage");
    } catch (error) {
      console.error("[Auth] Failed to save auth state:", error);
      throw error;
    }
  },

  /**
   * Clear authentication state
   * @returns {Promise<void>}
   */
  async clearAuthState() {
    try {
      this._authCache = {
        isAuthenticated: false,
        user: null,
        jwtToken: null,
        lastCheck: 0,
      };

      await new Promise((resolve, reject) => {
        chrome.storage.sync.remove(
          [
            this.STORAGE_KEYS.JWT_TOKEN,
            this.STORAGE_KEYS.USER_INFO,
            this.STORAGE_KEYS.AUTH_STATE,
            this.STORAGE_KEYS.LAST_AUTH_CHECK,
          ],
          () => {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
            } else {
              resolve();
            }
          }
        );
      });

      this.notifyListeners("signOut", null);
      console.log("[Auth] Cleared auth state");
    } catch (error) {
      console.error("[Auth] Failed to clear auth state:", error);
      throw error;
    }
  },

  /**
   * Sign in user using Chrome Identity API
   * @param {boolean} interactive - Whether to show interactive UI
   * @returns {Promise<Object>} User information
   */
  async signIn(interactive = true) {
    try {
      console.log("[Auth] Starting sign-in process");

      // Get Google ID token using Chrome Identity API
      const googleToken = await this.getGoogleToken(interactive);
      if (!googleToken) {
        throw new Error("Failed to get Google authentication token");
      }

      // Register/login with backend using Google token
      const authResult = await this.authenticateWithBackend(googleToken);

      // Update authentication state
      this._authCache = {
        isAuthenticated: true,
        user: authResult.user,
        jwtToken: authResult.access_token,
        lastCheck: Date.now(),
      };

      // Save state to storage
      await this.saveAuthState();

      // Notify listeners
      this.notifyListeners("signIn", this._authCache.user);

      console.log("[Auth] Sign-in successful:", this._authCache.user);
      return this._authCache.user;
    } catch (error) {
      console.error("[Auth] Sign-in failed:", error);
      await this.clearAuthState();
      throw error;
    }
  },

  /**
   * Sign out user
   * @returns {Promise<void>}
   */
  async signOut() {
    try {
      console.log("[Auth] Starting sign-out process");

      // Remove cached Chrome token
      await new Promise(resolve => {
        chrome.identity.removeCachedAuthToken({ token: this._authCache.jwtToken || "" }, resolve);
      });

      // Clear local authentication state
      await this.clearAuthState();

      console.log("[Auth] Sign-out successful");
    } catch (error) {
      console.error("[Auth] Sign-out failed:", error);
      // Still clear local state even if remote sign-out fails
      await this.clearAuthState();
      throw error;
    }
  },

  /**
   * Get Google authentication token using Chrome Identity API
   * @param {boolean} interactive - Whether to show interactive UI
   * @returns {Promise<string|null>} Google ID token
   */
  async getGoogleToken(interactive = true) {
    return new Promise(resolve => {
      chrome.identity.getAuthToken(
        {
          interactive: interactive,
          scopes: this.CONFIG.SCOPES,
        },
        token => {
          if (chrome.runtime.lastError) {
            console.error(
              "[Auth] Failed to get Google token:",
              chrome.runtime.lastError.message || chrome.runtime.lastError
            );
            console.error("[Auth] Full error object:", chrome.runtime.lastError);
            resolve(null);
          } else {
            console.log("[Auth] Got Google token successfully");
            resolve(token);
          }
        }
      );
    });
  },

  /**
   * Authenticate with backend API using Google token
   * @param {string} googleToken - Google ID token
   * @returns {Promise<Object>} Authentication result with JWT and user info
   */
  async authenticateWithBackend(googleToken) {
    try {
      // Get server configuration
      const config = await ServerAPI.getConfig();
      const serverUrl = config.serverUrl;

      // First try to register (handles both new users and existing users)
      let response;
      try {
        response = await fetch(`${serverUrl}/users/register`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            chrome_token: googleToken,
          }),
        });
      } catch (error) {
        // If register fails, try login
        response = await fetch(`${serverUrl}/users/login`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            google_token: googleToken,
          }),
        });
      }

      if (!response.ok) {
        const errorText = await response.text().catch(() => "Unknown error");
        throw new Error(`Authentication failed: ${response.status} ${errorText}`);
      }

      const result = await response.json();

      if (!result.access_token || !result.user) {
        throw new Error("Invalid authentication response from server");
      }

      return {
        access_token: result.access_token,
        user: result.user,
      };
    } catch (error) {
      console.error("[Auth] Backend authentication failed:", error);
      throw error;
    }
  },

  /**
   * Validate JWT token with backend
   * @param {string} token - JWT token to validate
   * @returns {Promise<boolean>} True if token is valid
   */
  async validateToken(token) {
    try {
      if (!token) return false;

      // Check if token is expired locally first (if it's a standard JWT)
      if (this.isTokenExpired(token)) {
        return false;
      }

      // Validate with backend
      const config = await ServerAPI.getConfig();
      const response = await fetch(`${config.serverUrl}/users/me`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      });

      const isValid = response.ok;
      console.log("[Auth] Token validation result:", isValid);
      return isValid;
    } catch (error) {
      console.error("[Auth] Token validation failed:", error);
      return false;
    }
  },

  /**
   * Check if JWT token is expired (basic check)
   * @param {string} token - JWT token
   * @returns {boolean} True if token appears expired
   */
  isTokenExpired(token) {
    try {
      if (!token) return true;

      const parts = token.split(".");
      if (parts.length !== 3) return true;

      const payload = JSON.parse(atob(parts[1]));
      const now = Math.floor(Date.now() / 1000);

      return payload.exp && payload.exp < now;
    } catch (error) {
      console.error("[Auth] Failed to parse token:", error);
      return true;
    }
  },

  /**
   * Get token expiry time as readable string
   * @param {string} token - JWT token
   * @returns {string} Human readable expiry time or "invalid"
   */
  getTokenExpiry(token) {
    try {
      if (!token) return "invalid";

      const parts = token.split(".");
      if (parts.length !== 3) return "invalid";

      const payload = JSON.parse(atob(parts[1]));
      if (!payload.exp) return "no expiry";

      const expiryDate = new Date(payload.exp * 1000);
      return expiryDate.toLocaleString();
    } catch (error) {
      return "invalid";
    }
  },

  /**
   * Get current authentication state
   * @returns {Object} Authentication state
   */
  getAuthState() {
    return {
      isAuthenticated: this._authCache.isAuthenticated,
      user: this._authCache.user,
      hasValidToken: !!this._authCache.jwtToken,
    };
  },

  /**
   * Get current user information
   * @returns {Object|null} User information or null if not authenticated
   */
  getCurrentUser() {
    return this._authCache.user;
  },

  /**
   * Get current JWT token
   * @returns {string|null} JWT token or null if not authenticated
   */
  getCurrentToken() {
    return this._authCache.jwtToken;
  },

  /**
   * Check if user is currently authenticated
   * @returns {boolean} True if authenticated
   */
  isAuthenticated() {
    return this._authCache.isAuthenticated && !!this._authCache.jwtToken;
  },

  /**
   * Refresh authentication token if needed
   * @returns {Promise<boolean>} True if token was refreshed successfully
   */
  async refreshTokenIfNeeded() {
    try {
      if (!this.isAuthenticated()) {
        return false;
      }

      const now = Date.now();
      const timeSinceLastCheck = now - this._authCache.lastCheck;

      // Check if we need to validate the token
      if (timeSinceLastCheck > this.CONFIG.TOKEN_REFRESH_THRESHOLD) {
        const isValid = await this.validateToken(this._authCache.jwtToken);

        if (!isValid) {
          console.log("[Auth] Token expired, attempting refresh");
          // Try to get a new token silently
          try {
            await this.signIn(false); // Non-interactive
            return true;
          } catch (error) {
            console.log("[Auth] Silent refresh failed, clearing auth state");
            await this.clearAuthState();
            return false;
          }
        }

        this._authCache.lastCheck = now;
        await this.saveAuthState();
      }

      return true;
    } catch (error) {
      console.error("[Auth] Token refresh failed:", error);
      return false;
    }
  },

  /**
   * Setup periodic token validation
   */
  setupTokenValidation() {
    setInterval(async () => {
      if (this.isAuthenticated()) {
        await this.refreshTokenIfNeeded();
      }
    }, this.CONFIG.AUTH_CHECK_INTERVAL);
  },

  /**
   * Add authentication state change listener
   * @param {Function} listener - Callback function
   */
  addAuthListener(listener) {
    this._listeners.add(listener);
  },

  /**
   * Remove authentication state change listener
   * @param {Function} listener - Callback function
   */
  removeAuthListener(listener) {
    this._listeners.delete(listener);
  },

  /**
   * Notify all listeners of authentication state changes
   * @param {string} event - Event type ('signIn' or 'signOut')
   * @param {Object|null} data - Event data
   */
  notifyListeners(event, data) {
    this._listeners.forEach(listener => {
      try {
        listener(event, data);
      } catch (error) {
        console.error("[Auth] Listener error:", error);
      }
    });
  },

  /**
   * Attempt automatic authentication if user has previously signed in
   * @returns {Promise<boolean>} True if auto-authentication was successful
   */
  async attemptAutoAuth() {
    try {
      if (this.isAuthenticated()) {
        return true;
      }

      // Try to get a token silently (non-interactive)
      const googleToken = await this.getGoogleToken(false);
      if (!googleToken) {
        return false;
      }

      // Authenticate with backend
      const authResult = await this.authenticateWithBackend(googleToken);

      // Update authentication state
      this._authCache = {
        isAuthenticated: true,
        user: authResult.user,
        jwtToken: authResult.access_token,
        lastCheck: Date.now(),
      };

      await this.saveAuthState();
      this.notifyListeners("signIn", this._authCache.user);

      console.log("[Auth] Auto-authentication successful");
      return true;
    } catch (error) {
      console.log("[Auth] Auto-authentication failed:", error);
      return false;
    }
  },
};

// Initialize auth manager when script loads
if (typeof window !== "undefined") {
  // Only initialize in browser context
  AuthManager.initialize().catch(error => {
    console.error("[Auth] Failed to initialize:", error);
  });
}

// Export for use in other scripts
if (typeof module !== "undefined" && module.exports) {
  module.exports = { AuthManager };
}
