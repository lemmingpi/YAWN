/**
 * Error Handling Utilities for Web Notes Extension
 * Provides centralized error handling and user feedback for server integration
 */

/* eslint-env webextensions */

/**
 * Error handling utilities for graceful degradation
 */
const ErrorHandler = {
  // Error types
  ERROR_TYPES: {
    NETWORK: "network",
    SERVER: "server",
    LOCAL_STORAGE: "local_storage",
    UNKNOWN: "unknown",
  },

  // In-memory error tracking
  errorCounts: new Map(),
  lastErrors: new Map(),
  maxRetries: 3,

  /**
   * Determine error type from error object
   * @param {Error} error - The error to classify
   * @returns {string} Error type constant
   */
  classifyError(error) {
    if (!error) return this.ERROR_TYPES.UNKNOWN;

    const message = error.message?.toLowerCase() || "";

    if (error.name === "TypeError" || message.includes("fetch")) {
      return this.ERROR_TYPES.NETWORK;
    }

    if (message.includes("http") || message.includes("server")) {
      return this.ERROR_TYPES.SERVER;
    }

    if (message.includes("storage") || message.includes("chrome.runtime")) {
      return this.ERROR_TYPES.LOCAL_STORAGE;
    }

    return this.ERROR_TYPES.UNKNOWN;
  },

  /**
   * Handle an error with appropriate user feedback
   * @param {string} operation - The operation that failed
   * @param {Error} error - The error that occurred
   * @param {Object} options - Error handling options
   * @returns {boolean} Whether operation should be retried
   */
  handleError(operation, error, options = {}) {
    const errorType = this.classifyError(error);
    const errorKey = `${operation}_${errorType}`;

    // Track error frequency
    const currentCount = this.errorCounts.get(errorKey) || 0;
    this.errorCounts.set(errorKey, currentCount + 1);
    this.lastErrors.set(errorKey, {
      error: error,
      timestamp: Date.now(),
      operation: operation,
    });

    console.error(`[YAWN] ${operation} failed (${errorType}):`, error);

    // Determine if operation should be retried
    const shouldRetry =
      currentCount < this.maxRetries && (errorType === this.ERROR_TYPES.NETWORK || errorType === this.ERROR_TYPES.SERVER);

    // Show user feedback for certain error types
    if (!shouldRetry && options.showUserFeedback !== false) {
      this.showUserFeedback(operation, errorType, options);
    }

    return shouldRetry;
  },

  /**
   * Show user feedback for errors
   * @param {string} operation - The failed operation
   * @param {string} errorType - The type of error
   * @param {Object} options - Feedback options
   */
  showUserFeedback(operation, errorType, options = {}) {
    let message = "";
    let isTemporary = true;

    switch (errorType) {
      case this.ERROR_TYPES.NETWORK:
        message = "Network connection failed. Notes saved locally.";
        break;
      case this.ERROR_TYPES.SERVER:
        message = "Server sync failed. Notes saved locally.";
        break;
      case this.ERROR_TYPES.LOCAL_STORAGE:
        message = "Storage error. Please try again.";
        isTemporary = false;
        break;
      default:
        message = "An error occurred. Please try again.";
        isTemporary = false;
        break;
    }

    // Only show feedback in contexts where we have access to DOM
    if (typeof document !== "undefined" && document.body) {
      this.showTemporaryMessage(message, "warning", isTemporary ? 3000 : 5000);
    }
  },

  /**
   * Show a temporary message to the user
   * @param {string} message - Message to display
   * @param {string} type - Message type ('error', 'warning', 'success')
   * @param {number} duration - Duration in milliseconds
   */
  showTemporaryMessage(message, type = "error", duration = 3000) {
    try {
      // Create message element
      const messageEl = document.createElement("div");
      messageEl.className = "web-notes-message";
      messageEl.textContent = message;

      // Style the message
      const backgroundColor = type === "error" ? "#f44336" : type === "warning" ? "#ff9800" : "#4caf50";

      messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${backgroundColor};
        color: white;
        padding: 12px 16px;
        border-radius: 4px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 10002;
        max-width: 300px;
        word-wrap: break-word;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      `;

      document.body.appendChild(messageEl);

      // Animate in
      requestAnimationFrame(() => {
        messageEl.style.opacity = "1";
        messageEl.style.transform = "translateX(0)";
      });

      // Remove after duration
      setTimeout(() => {
        messageEl.style.opacity = "0";
        messageEl.style.transform = "translateX(100%)";

        setTimeout(() => {
          if (messageEl.parentNode) {
            messageEl.parentNode.removeChild(messageEl);
          }
        }, 300);
      }, duration);
    } catch (error) {
      console.error("[YAWN] Error showing user message:", error);
    }
  },

  /**
   * Clear error tracking for an operation
   * @param {string} operation - Operation to clear
   */
  clearErrorTracking(operation) {
    for (const [key] of this.errorCounts) {
      if (key.startsWith(operation)) {
        this.errorCounts.delete(key);
        this.lastErrors.delete(key);
      }
    }
  },

  /**
   * Get error statistics
   * @returns {Object} Error statistics
   */
  getErrorStats() {
    const stats = {};
    for (const [key, count] of this.errorCounts) {
      stats[key] = {
        count: count,
        lastError: this.lastErrors.get(key),
      };
    }
    return stats;
  },

  /**
   * Wrapper for async operations with error handling
   * @param {string} operation - Operation name
   * @param {Function} asyncFn - Async function to execute
   * @param {Object} options - Error handling options
   * @returns {Promise} Result or null if failed
   */
  async withErrorHandling(operation, asyncFn, options = {}) {
    try {
      const result = await asyncFn();
      // Clear error tracking on success
      this.clearErrorTracking(operation);
      return result;
    } catch (error) {
      const shouldRetry = this.handleError(operation, error, options);

      if (shouldRetry && options.retryFn) {
        // Retry with exponential backoff
        const retryCount = this.errorCounts.get(`${operation}_retry`) || 0;
        const delay = Math.min(1000 * Math.pow(2, retryCount), 10000); // Max 10 seconds

        console.log(`[YAWN] Retrying ${operation} in ${delay}ms...`);

        setTimeout(async () => {
          this.errorCounts.set(`${operation}_retry`, retryCount + 1);
          return this.withErrorHandling(operation, options.retryFn, {
            ...options,
            retryFn: null, // Prevent infinite retries
          });
        }, delay);

        return null;
      }

      // Return null on failure, let calling code handle graceful degradation
      return null;
    }
  },
};

// Global error handler for unhandled promise rejections
if (typeof window !== "undefined") {
  window.addEventListener("unhandledrejection", event => {
    console.error("[YAWN] Unhandled promise rejection:", event.reason);
    ErrorHandler.handleError("unhandled_promise", event.reason);
  });
}

// Export for use in other scripts
if (typeof module !== "undefined" && module.exports) {
  module.exports = { ErrorHandler };
}
