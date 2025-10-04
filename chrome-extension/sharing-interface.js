/**
 * Sharing Interface Module for Web Notes Chrome Extension
 * Provides Google Docs-style sharing functionality with comprehensive security and UX features
 */

/* global DOMPurify, ErrorHandler, isServerAuthenticated */

/**
 * Sharing Interface Manager
 * Handles all sharing-related UI and API interactions
 */
const SharingInterface = {
  // State management
  currentDialog: null,
  shareCache: new Map(),
  SHARE_CACHE_TTL: 5 * 60 * 1000, // 5 minutes

  // Permission levels
  PERMISSION_LEVELS: {
    VIEW: { value: "VIEW", label: "Can view", description: "Can view notes but not edit" },
    EDIT: { value: "EDIT", label: "Can edit", description: "Can view and edit notes" },
    ADMIN: { value: "ADMIN", label: "Can manage", description: "Can view, edit, and manage shares" },
  },

  // Email validation regex (RFC 5322 compliant)
  EMAIL_REGEX: new RegExp(
    /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?/.source +
      /(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/.source
  ),

  /**
   * Initialize sharing interface
   */
  init() {
    try {
      // Add CSS styles for sharing interface
      this.injectStyles();

      // Listen for escape key to close dialogs
      document.addEventListener("keydown", event => {
        if (event.key === "Escape" && this.currentDialog) {
          this.closeDialog();
        }
      });

      console.log("[Web Notes] Sharing interface initialized");
    } catch (error) {
      console.error("[Web Notes] Failed to initialize sharing interface:", error);
      if (typeof ErrorHandler !== "undefined") {
        ErrorHandler.logError("Sharing interface initialization failed", error);
      }
    }
  },

  /**
   * Create and show sharing dialog for a specific note
   * @param {Object} noteData - The note data object
   * @param {Object} pageData - Page information (url, title)
   * @returns {Promise<void>}
   */
  async createSharingDialog(noteData, pageData) {
    try {
      if (!this.validateInput(noteData, "object") || !this.validateInput(pageData, "object")) {
        throw new Error("Invalid note or page data provided");
      }

      // Ensure user is authenticated
      if (!(await this.ensureAuthenticated())) {
        return;
      }

      // Close any existing dialog
      this.closeDialog();

      const dialog = this.createDialogContainer("Share Note");

      // Create dialog content
      const content = document.createElement("div");
      content.className = "wn-sharing-content";

      // Note info section
      const noteInfo = this.createNoteInfoSection(noteData, pageData);
      content.appendChild(noteInfo);

      // Share form section
      const shareForm = this.createShareFormSection("note", noteData.id);
      content.appendChild(shareForm);

      // Current shares section
      const sharesSection = await this.createCurrentSharesSection("note", noteData.id);
      content.appendChild(sharesSection);

      dialog.querySelector(".wn-sharing-body").appendChild(content);

      // Show dialog
      this.showDialog(dialog);

      // Focus on email input
      const emailInput = dialog.querySelector("#wn-share-email");
      if (emailInput) {
        emailInput.focus();
      }
    } catch (error) {
      console.error("[Web Notes] Failed to create sharing dialog:", error);
      this.showErrorMessage("Failed to open sharing dialog. Please try again.");
      if (typeof ErrorHandler !== "undefined") {
        ErrorHandler.logError("Sharing dialog creation failed", error);
      }
    }
  },

  /**
   * Show page-level sharing dialog
   * @param {string} url - Page URL
   * @param {string} pageTitle - Page title
   * @returns {Promise<void>}
   */
  async showPageSharingDialog(url, pageTitle) {
    try {
      if (!this.validateInput(url, "string") || !this.validateInput(pageTitle, "string")) {
        throw new Error("Invalid URL or page title provided");
      }

      // Ensure user is authenticated
      if (!(await this.ensureAuthenticated())) {
        return;
      }

      // Close any existing dialog
      this.closeDialog();

      const dialog = this.createDialogContainer("Share Page");

      // Create dialog content
      const content = document.createElement("div");
      content.className = "wn-sharing-content";

      // Page info section
      const pageInfo = this.createPageInfoSection(url, pageTitle);
      content.appendChild(pageInfo);

      // Share form section
      const shareForm = this.createShareFormSection("page", url);
      content.appendChild(shareForm);

      // Current shares section
      const sharesSection = await this.createCurrentSharesSection("page", url);
      content.appendChild(sharesSection);

      dialog.querySelector(".wn-sharing-body").appendChild(content);

      // Show dialog
      this.showDialog(dialog);

      // Focus on email input
      const emailInput = dialog.querySelector("#wn-share-email");
      if (emailInput) {
        emailInput.focus();
      }
    } catch (error) {
      console.error("[Web Notes] Failed to show page sharing dialog:", error);
      this.showErrorMessage("Failed to open page sharing dialog. Please try again.");
      if (typeof ErrorHandler !== "undefined") {
        ErrorHandler.logError("Page sharing dialog failed", error);
      }
    }
  },

  /**
   * Show site-level sharing dialog
   * @param {string} domain - Site domain
   * @returns {Promise<void>}
   */
  async showSiteSharingDialog(domain) {
    try {
      if (!this.validateInput(domain, "string")) {
        throw new Error("Invalid domain provided");
      }

      // Ensure user is authenticated
      if (!(await this.ensureAuthenticated())) {
        return;
      }

      // Close any existing dialog
      this.closeDialog();

      const dialog = this.createDialogContainer("Share Site");

      // Create dialog content
      const content = document.createElement("div");
      content.className = "wn-sharing-content";

      // Site info section
      const siteInfo = this.createSiteInfoSection(domain);
      content.appendChild(siteInfo);

      // Share form section
      const shareForm = this.createShareFormSection("site", domain);
      content.appendChild(shareForm);

      // Current shares section
      const sharesSection = await this.createCurrentSharesSection("site", domain);
      content.appendChild(sharesSection);

      dialog.querySelector(".wn-sharing-body").appendChild(content);

      // Show dialog
      this.showDialog(dialog);

      // Focus on email input
      const emailInput = dialog.querySelector("#wn-share-email");
      if (emailInput) {
        emailInput.focus();
      }
    } catch (error) {
      console.error("[Web Notes] Failed to show site sharing dialog:", error);
      this.showErrorMessage("Failed to open site sharing dialog. Please try again.");
      if (typeof ErrorHandler !== "undefined") {
        ErrorHandler.logError("Site sharing dialog failed", error);
      }
    }
  },

  /**
   * Create dialog container with header and footer
   * @param {string} title - Dialog title
   * @returns {HTMLElement} Dialog element
   */
  createDialogContainer(title) {
    const overlay = document.createElement("div");
    overlay.className = "wn-sharing-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-labelledby", "wn-sharing-title");

    const dialog = document.createElement("div");
    dialog.className = "wn-sharing-dialog";

    // Header
    const header = document.createElement("div");
    header.className = "wn-sharing-header";

    const titleElement = document.createElement("h2");
    titleElement.id = "wn-sharing-title";
    titleElement.className = "wn-sharing-title";
    titleElement.textContent = this.sanitizeText(title);

    const closeButton = document.createElement("button");
    closeButton.className = "wn-sharing-close";
    closeButton.setAttribute("aria-label", "Close sharing dialog");
    closeButton.innerHTML = "&times;";
    closeButton.addEventListener("click", () => this.closeDialog());

    header.appendChild(titleElement);
    header.appendChild(closeButton);

    // Body
    const body = document.createElement("div");
    body.className = "wn-sharing-body";

    // Footer
    const footer = document.createElement("div");
    footer.className = "wn-sharing-footer";

    const cancelButton = document.createElement("button");
    cancelButton.className = "wn-sharing-button wn-sharing-button-secondary";
    cancelButton.textContent = "Close";
    cancelButton.addEventListener("click", () => this.closeDialog());

    footer.appendChild(cancelButton);

    dialog.appendChild(header);
    dialog.appendChild(body);
    dialog.appendChild(footer);
    overlay.appendChild(dialog);

    // Click outside to close
    overlay.addEventListener("click", event => {
      if (event.target === overlay) {
        this.closeDialog();
      }
    });

    return overlay;
  },

  /**
   * Create note info section
   * @param {Object} noteData - Note data
   * @param {Object} pageData - Page data
   * @returns {HTMLElement} Note info section
   */
  createNoteInfoSection(noteData, pageData) {
    const section = document.createElement("div");
    section.className = "wn-sharing-section";

    const title = document.createElement("h3");
    title.textContent = "Note Details";
    section.appendChild(title);

    const details = document.createElement("div");
    details.className = "wn-sharing-details";

    const notePreview = document.createElement("div");
    notePreview.className = "wn-note-preview";
    const previewText = noteData.content
      ? this.sanitizeText(noteData.content.substring(0, 100) + (noteData.content.length > 100 ? "..." : ""))
      : "Empty note";
    notePreview.textContent = previewText;

    const pageInfo = document.createElement("div");
    pageInfo.className = "wn-page-info";
    pageInfo.textContent = `On: ${this.sanitizeText(pageData.title || pageData.url)}`;

    details.appendChild(notePreview);
    details.appendChild(pageInfo);
    section.appendChild(details);

    return section;
  },

  /**
   * Create page info section
   * @param {string} url - Page URL
   * @param {string} pageTitle - Page title
   * @returns {HTMLElement} Page info section
   */
  createPageInfoSection(url, pageTitle) {
    const section = document.createElement("div");
    section.className = "wn-sharing-section";

    const title = document.createElement("h3");
    title.textContent = "Page Details";
    section.appendChild(title);

    const details = document.createElement("div");
    details.className = "wn-sharing-details";

    const titleElement = document.createElement("div");
    titleElement.className = "wn-page-title";
    titleElement.textContent = this.sanitizeText(pageTitle);

    const urlElement = document.createElement("div");
    urlElement.className = "wn-page-url";
    urlElement.textContent = this.sanitizeText(url);

    details.appendChild(titleElement);
    details.appendChild(urlElement);
    section.appendChild(details);

    return section;
  },

  /**
   * Create site info section
   * @param {string} domain - Site domain
   * @returns {HTMLElement} Site info section
   */
  createSiteInfoSection(domain) {
    const section = document.createElement("div");
    section.className = "wn-sharing-section";

    const title = document.createElement("h3");
    title.textContent = "Site Details";
    section.appendChild(title);

    const details = document.createElement("div");
    details.className = "wn-sharing-details";

    const domainElement = document.createElement("div");
    domainElement.className = "wn-site-domain";
    domainElement.textContent = this.sanitizeText(domain);

    const description = document.createElement("div");
    description.className = "wn-site-description";
    description.textContent = "Share all notes and pages on this domain";

    details.appendChild(domainElement);
    details.appendChild(description);
    section.appendChild(details);

    return section;
  },

  /**
   * Create share form section
   * @param {string} shareType - Type of share (note, page, site)
   * @param {string} resourceId - Resource identifier
   * @returns {HTMLElement} Share form section
   */
  createShareFormSection(shareType, resourceId) {
    const section = document.createElement("div");
    section.className = "wn-sharing-section";

    const title = document.createElement("h3");
    title.textContent = "Add People";
    section.appendChild(title);

    const form = document.createElement("form");
    form.className = "wn-sharing-form";
    form.addEventListener("submit", event => {
      event.preventDefault();
      this.handleShareSubmit(shareType, resourceId);
    });

    // Email input with validation
    const emailGroup = document.createElement("div");
    emailGroup.className = "wn-form-group";

    const emailLabel = document.createElement("label");
    emailLabel.textContent = "Email address";
    emailLabel.setAttribute("for", "wn-share-email");

    const emailInput = document.createElement("input");
    emailInput.type = "email";
    emailInput.id = "wn-share-email";
    emailInput.className = "wn-form-input";
    emailInput.placeholder = "Enter email address";
    emailInput.required = true;
    emailInput.setAttribute("aria-describedby", "wn-email-error");

    const emailError = document.createElement("div");
    emailError.id = "wn-email-error";
    emailError.className = "wn-form-error";
    emailError.setAttribute("role", "alert");
    emailError.style.display = "none";

    emailGroup.appendChild(emailLabel);
    emailGroup.appendChild(emailInput);
    emailGroup.appendChild(emailError);

    // Permission level dropdown
    const permissionGroup = document.createElement("div");
    permissionGroup.className = "wn-form-group";

    const permissionLabel = document.createElement("label");
    permissionLabel.textContent = "Permission level";
    permissionLabel.setAttribute("for", "wn-share-permission");

    const permissionSelect = document.createElement("select");
    permissionSelect.id = "wn-share-permission";
    permissionSelect.className = "wn-form-select";

    Object.values(this.PERMISSION_LEVELS).forEach(level => {
      const option = document.createElement("option");
      option.value = level.value;
      option.textContent = level.label;
      option.title = level.description;
      if (level.value === "VIEW") option.selected = true; // Default to VIEW
      permissionSelect.appendChild(option);
    });

    permissionGroup.appendChild(permissionLabel);
    permissionGroup.appendChild(permissionSelect);

    // Submit button
    const submitGroup = document.createElement("div");
    submitGroup.className = "wn-form-group";

    const submitButton = document.createElement("button");
    submitButton.type = "submit";
    submitButton.className = "wn-sharing-button wn-sharing-button-primary";
    submitButton.textContent = "Share";
    submitButton.id = "wn-share-submit";

    const loadingSpinner = document.createElement("span");
    loadingSpinner.className = "wn-loading-spinner";
    loadingSpinner.style.display = "none";
    loadingSpinner.textContent = "⟳";

    submitGroup.appendChild(submitButton);
    submitGroup.appendChild(loadingSpinner);

    form.appendChild(emailGroup);
    form.appendChild(permissionGroup);
    form.appendChild(submitGroup);
    section.appendChild(form);

    // Real-time email validation
    emailInput.addEventListener("input", () => {
      this.validateEmailInput(emailInput, emailError);
    });

    return section;
  },

  /**
   * Create current shares section
   * @param {string} shareType - Type of share (note, page, site)
   * @param {string} resourceId - Resource identifier
   * @returns {Promise<HTMLElement>} Current shares section
   */
  async createCurrentSharesSection(shareType, resourceId) {
    const section = document.createElement("div");
    section.className = "wn-sharing-section";

    const title = document.createElement("h3");
    title.textContent = "Current Shares";
    section.appendChild(title);

    const sharesList = document.createElement("div");
    sharesList.className = "wn-shares-list";
    sharesList.id = "wn-current-shares";

    try {
      // Load current shares
      const shares = await this.getCurrentShares(shareType, resourceId);

      if (shares.length === 0) {
        const emptyMessage = document.createElement("div");
        emptyMessage.className = "wn-shares-empty";
        emptyMessage.textContent = "No shares yet. Add people above to start sharing.";
        sharesList.appendChild(emptyMessage);
      } else {
        shares.forEach(share => {
          const shareItem = this.createShareItem(share, shareType, resourceId);
          sharesList.appendChild(shareItem);
        });
      }
    } catch (error) {
      console.error("[Web Notes] Failed to load current shares:", error);
      const errorMessage = document.createElement("div");
      errorMessage.className = "wn-shares-error";
      errorMessage.textContent = "Failed to load current shares.";
      sharesList.appendChild(errorMessage);
    }

    section.appendChild(sharesList);
    return section;
  },

  /**
   * Create individual share item
   * @param {Object} share - Share data
   * @param {string} shareType - Type of share
   * @param {string} resourceId - Resource identifier
   * @returns {HTMLElement} Share item element
   */
  createShareItem(share, shareType, resourceId) {
    const item = document.createElement("div");
    item.className = "wn-share-item";

    const userInfo = document.createElement("div");
    userInfo.className = "wn-share-user";

    const userName = document.createElement("div");
    userName.className = "wn-share-user-name";
    userName.textContent = this.sanitizeText(share.user_name || share.user_email);

    const userEmail = document.createElement("div");
    userEmail.className = "wn-share-user-email";
    userEmail.textContent = this.sanitizeText(share.user_email);

    userInfo.appendChild(userName);
    userInfo.appendChild(userEmail);

    const permissionInfo = document.createElement("div");
    permissionInfo.className = "wn-share-permission";

    const currentPermission = share.permission_level;
    const isOwner = share.is_owner;

    if (isOwner) {
      const ownerLabel = document.createElement("span");
      ownerLabel.className = "wn-permission-label wn-permission-owner";
      ownerLabel.textContent = "Owner";
      permissionInfo.appendChild(ownerLabel);
    } else {
      const permissionSelect = document.createElement("select");
      permissionSelect.className = "wn-permission-select";
      permissionSelect.value = currentPermission;

      Object.values(this.PERMISSION_LEVELS).forEach(level => {
        const option = document.createElement("option");
        option.value = level.value;
        option.textContent = level.label;
        if (level.value === currentPermission) option.selected = true;
        permissionSelect.appendChild(option);
      });

      permissionSelect.addEventListener("change", () => {
        this.updateSharePermission(shareType, resourceId, share.user_id, permissionSelect.value);
      });

      permissionInfo.appendChild(permissionSelect);

      // Remove button
      const removeButton = document.createElement("button");
      removeButton.className = "wn-share-remove";
      removeButton.textContent = "×";
      removeButton.title = "Remove access";
      removeButton.setAttribute("aria-label", `Remove access for ${share.user_email}`);
      removeButton.addEventListener("click", () => {
        this.removeShare(shareType, resourceId, share.user_id);
      });

      permissionInfo.appendChild(removeButton);
    }

    item.appendChild(userInfo);
    item.appendChild(permissionInfo);

    // Enhance accessibility for this share item
    this.enhanceShareItemAccessibility(item);

    return item;
  },

  /**
   * Handle share form submission with enhanced security
   * @param {string} shareType - Type of share
   * @param {string} resourceId - Resource identifier
   * @returns {Promise<void>}
   */
  async handleShareSubmit(shareType, resourceId) {
    try {
      const emailInput = document.getElementById("wn-share-email");
      const permissionSelect = document.getElementById("wn-share-permission");
      const submitButton = document.getElementById("wn-share-submit");
      const loadingSpinner = document.querySelector(".wn-loading-spinner");

      if (!emailInput || !permissionSelect || !submitButton) {
        throw new Error("Form elements not found");
      }

      const email = emailInput.value.trim();
      const permission = permissionSelect.value;

      // Enhanced security validation
      if (!this.validateSecureInput(shareType, "resourceId", { maxLength: 50 })) {
        this.showFieldError("wn-email-error", "Invalid share type");
        return;
      }

      if (!this.validateSecureInput(resourceId, shareType === "page" ? "url" : "resourceId")) {
        this.showFieldError("wn-email-error", "Invalid resource identifier");
        return;
      }

      if (!this.validateSecureInput(email, "email")) {
        this.showFieldError("wn-email-error", "Please enter a valid email address");
        emailInput.focus();
        return;
      }

      if (!this.validateSecureInput(permission, "permissionLevel")) {
        this.showFieldError("wn-email-error", "Invalid permission level");
        return;
      }

      // Rate limiting check
      if (!this.rateLimiter.isAllowed("shareCreate", email)) {
        this.showFieldError("wn-email-error", "Too many sharing requests. Please wait before trying again.");
        return;
      }

      // Permission check
      const hasPermission = await this.checkSharePermission(shareType, resourceId);
      if (!hasPermission) {
        this.showFieldError("wn-email-error", "You do not have permission to share this resource");
        return;
      }

      // Show loading state
      submitButton.disabled = true;
      loadingSpinner.style.display = "inline";

      // Create share
      await this.createShare(shareType, resourceId, email, permission);

      // Clear form
      emailInput.value = "";
      permissionSelect.value = "VIEW";

      // Refresh shares list
      await this.refreshCurrentShares(shareType, resourceId);

      // Show success message
      this.showSuccessMessage(`Successfully shared with ${email}`);
    } catch (error) {
      console.error("[Web Notes] Failed to create share:", error);
      this.showErrorMessage(error.message || "Failed to create share. Please try again.");
    } finally {
      // Hide loading state
      const submitButton = document.getElementById("wn-share-submit");
      const loadingSpinner = document.querySelector(".wn-loading-spinner");
      if (submitButton) submitButton.disabled = false;
      if (loadingSpinner) loadingSpinner.style.display = "none";
    }
  },

  /**
   * Validate email input in real-time
   * @param {HTMLInputElement} emailInput - Email input element
   * @param {HTMLElement} errorElement - Error display element
   */
  validateEmailInput(emailInput, errorElement) {
    const email = emailInput.value.trim();

    if (email && !this.validateEmail(email)) {
      this.showFieldError(errorElement.id, "Please enter a valid email address");
      emailInput.setAttribute("aria-invalid", "true");
    } else {
      this.hideFieldError(errorElement.id);
      emailInput.setAttribute("aria-invalid", "false");
    }
  },

  /**
   * Validate email address format
   * @param {string} email - Email to validate
   * @returns {boolean} True if valid
   */
  validateEmail(email) {
    return typeof email === "string" && this.EMAIL_REGEX.test(email) && email.length <= 254;
  },

  /**
   * Validate input parameters
   * @param {any} value - Value to validate
   * @param {string} expectedType - Expected type
   * @returns {boolean} True if valid
   */
  validateInput(value, expectedType) {
    if (expectedType === "string") {
      return typeof value === "string" && value.length > 0;
    }
    if (expectedType === "object") {
      return value !== null && typeof value === "object";
    }
    return false;
  },

  /**
   * Sanitize text content to prevent XSS
   * @param {string} text - Text to sanitize
   * @returns {string} Sanitized text
   */
  sanitizeText(text) {
    if (typeof text !== "string") return "";

    // Use DOMPurify if available, otherwise basic escaping
    if (typeof DOMPurify !== "undefined") {
      return DOMPurify.sanitize(text, { ALLOWED_TAGS: [] });
    }

    // Fallback: basic HTML escaping
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#x27;");
  },

  /**
   * Show dialog
   * @param {HTMLElement} dialog - Dialog element to show
   */
  showDialog(dialog) {
    // Remove any existing dialog
    this.closeDialog();

    // Add to DOM
    document.body.appendChild(dialog);
    this.currentDialog = dialog;

    // Prevent body scroll
    document.body.style.overflow = "hidden";

    // Focus trap
    this.setupFocusTrap(dialog);

    // Animate in
    requestAnimationFrame(() => {
      dialog.style.opacity = "1";
      dialog.style.transform = "scale(1)";
    });
  },

  /**
   * Close current dialog
   */
  closeDialog() {
    if (this.currentDialog) {
      // Animate out
      this.currentDialog.style.opacity = "0";
      this.currentDialog.style.transform = "scale(0.95)";

      setTimeout(() => {
        if (this.currentDialog && this.currentDialog.parentNode) {
          this.currentDialog.parentNode.removeChild(this.currentDialog);
        }
        this.currentDialog = null;

        // Restore body scroll
        document.body.style.overflow = "";
      }, 200);
    }
  },

  /**
   * Setup enhanced focus management and keyboard navigation
   * @param {HTMLElement} dialog - Dialog element
   */
  setupFocusTrap(dialog) {
    const focusableElements = dialog.querySelectorAll('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');

    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Enhanced keyboard navigation
    dialog.addEventListener("keydown", event => {
      switch (event.key) {
        case "Tab":
          if (event.shiftKey) {
            if (document.activeElement === firstElement) {
              event.preventDefault();
              lastElement.focus();
            }
          } else {
            if (document.activeElement === lastElement) {
              event.preventDefault();
              firstElement.focus();
            }
          }
          break;

        case "ArrowDown":
          // Navigate through form elements with arrow keys
          if (event.target.matches("input, select, button")) {
            event.preventDefault();
            const currentIndex = Array.from(focusableElements).indexOf(event.target);
            const nextIndex = (currentIndex + 1) % focusableElements.length;
            focusableElements[nextIndex].focus();
          }
          break;

        case "ArrowUp":
          // Navigate through form elements with arrow keys
          if (event.target.matches("input, select, button")) {
            event.preventDefault();
            const currentIndex = Array.from(focusableElements).indexOf(event.target);
            const prevIndex = currentIndex === 0 ? focusableElements.length - 1 : currentIndex - 1;
            focusableElements[prevIndex].focus();
          }
          break;

        case "Enter":
          // Enhanced enter key handling
          if (event.target.matches("select")) {
            // Allow native select behavior
            return;
          }
          if (event.target.matches('input[type="email"]')) {
            // Submit form when pressing enter in email field
            event.preventDefault();
            const form = event.target.closest("form");
            if (form) {
              const submitEvent = new Event("submit", { bubbles: true, cancelable: true });
              form.dispatchEvent(submitEvent);
            }
          }
          break;

        case "Home":
          // Jump to first focusable element
          if (event.ctrlKey) {
            event.preventDefault();
            firstElement.focus();
          }
          break;

        case "End":
          // Jump to last focusable element
          if (event.ctrlKey) {
            event.preventDefault();
            lastElement.focus();
          }
          break;
      }
    });

    // Add focus indicators for better visual feedback
    focusableElements.forEach(element => {
      element.addEventListener("focus", () => {
        element.setAttribute("data-wn-focused", "true");
      });

      element.addEventListener("blur", () => {
        element.removeAttribute("data-wn-focused");
      });
    });

    // Announce dialog opening to screen readers
    this.announceToScreenReader("Sharing dialog opened. Use Tab to navigate, Escape to close.");
  },

  /**
   * Announce messages to screen readers
   * @param {string} message - Message to announce
   * @param {string} priority - Priority level (polite, assertive)
   */
  announceToScreenReader(message, priority = "polite") {
    try {
      const announcement = document.createElement("div");
      announcement.setAttribute("aria-live", priority);
      announcement.setAttribute("aria-atomic", "true");
      announcement.className = "wn-sr-only";
      announcement.textContent = this.sanitizeText(message);

      // Add screen reader only styles
      announcement.style.cssText = `
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        padding: 0 !important;
        margin: -1px !important;
        overflow: hidden !important;
        clip: rect(0, 0, 0, 0) !important;
        white-space: nowrap !important;
        border: 0 !important;
      `;

      document.body.appendChild(announcement);

      // Remove after announcement
      setTimeout(() => {
        if (announcement.parentNode) {
          announcement.parentNode.removeChild(announcement);
        }
      }, 1000);
    } catch (error) {
      console.error("[Web Notes] Failed to announce to screen reader:", error);
    }
  },

  /**
   * Enhanced keyboard support for share list items
   * @param {HTMLElement} shareItem - Share item element
   */
  enhanceShareItemAccessibility(shareItem) {
    try {
      const permissionSelect = shareItem.querySelector(".wn-permission-select");
      const removeButton = shareItem.querySelector(".wn-share-remove");

      // Add keyboard navigation for permission changes
      if (permissionSelect) {
        permissionSelect.addEventListener("keydown", event => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            permissionSelect.click();
          }
        });

        permissionSelect.addEventListener("change", () => {
          const userEmail = shareItem.querySelector(".wn-share-user-email")?.textContent || "user";
          const newPermission = permissionSelect.value;
          this.announceToScreenReader(`Permission changed to ${newPermission} for ${userEmail}`);
        });
      }

      // Enhanced remove button accessibility
      if (removeButton) {
        removeButton.addEventListener("keydown", event => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            removeButton.click();
          }
        });

        removeButton.addEventListener("click", () => {
          const userEmail = shareItem.querySelector(".wn-share-user-email")?.textContent || "user";
          this.announceToScreenReader(`Removing access for ${userEmail}`);
        });
      }

      // Make share item focusable and add role
      shareItem.setAttribute("role", "listitem");
      shareItem.setAttribute("tabindex", "0");

      // Add focus styles
      shareItem.addEventListener("focus", () => {
        shareItem.style.outline = "2px solid #0969da";
        shareItem.style.outlineOffset = "2px";
      });

      shareItem.addEventListener("blur", () => {
        shareItem.style.outline = "";
        shareItem.style.outlineOffset = "";
      });
    } catch (error) {
      console.error("[Web Notes] Error enhancing share item accessibility:", error);
    }
  },

  /**
   * Show field-specific error message
   * @param {string} errorElementId - Error element ID
   * @param {string} message - Error message
   */
  showFieldError(errorElementId, message) {
    const errorElement = document.getElementById(errorElementId);
    if (errorElement) {
      errorElement.textContent = this.sanitizeText(message);
      errorElement.style.display = "block";
      errorElement.setAttribute("aria-live", "polite");
    }
  },

  /**
   * Hide field-specific error message
   * @param {string} errorElementId - Error element ID
   */
  hideFieldError(errorElementId) {
    const errorElement = document.getElementById(errorElementId);
    if (errorElement) {
      errorElement.style.display = "none";
      errorElement.textContent = "";
    }
  },

  /**
   * Show success message
   * @param {string} message - Success message
   */
  showSuccessMessage(message) {
    this.showToast(message, "success");
  },

  /**
   * Show error message
   * @param {string} message - Error message
   */
  showErrorMessage(message) {
    this.showToast(message, "error");
  },

  /**
   * Show toast notification
   * @param {string} message - Message to show
   * @param {string} type - Type (success, error, info)
   */
  showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `wn-toast wn-toast-${type}`;
    toast.textContent = this.sanitizeText(message);
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-live", "assertive");

    // Position toast
    toast.style.position = "fixed";
    toast.style.top = "20px";
    toast.style.right = "20px";
    toast.style.zIndex = "10001";

    document.body.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 5000);
  },

  /**
   * Ensure user is authenticated
   * @returns {Promise<boolean>} True if authenticated
   */
  async ensureAuthenticated() {
    try {
      // Check authentication via background script
      const isAuth = await isServerAuthenticated();

      if (!isAuth) {
        this.showErrorMessage("Please sign in to share notes.");
        return false;
      }

      return true;
    } catch (error) {
      console.error("[Web Notes] Authentication check failed:", error);
      this.showErrorMessage("Authentication check failed. Please try again.");
      return false;
    }
  },

  /**
   * Create share via API
   * @param {string} shareType - Type of share
   * @param {string} resourceId - Resource identifier
   * @param {string} email - User email
   * @param {string} permission - Permission level
   * @returns {Promise<Object>} Created share
   */
  async createShare(shareType, resourceId, email, permission) {
    try {
      let result;

      switch (shareType) {
        case "note":
          // Notes don't have direct sharing - they inherit from their page
          throw new Error("Individual notes cannot be shared. Share the page instead.");
          break;
        case "page":
          const sharePageResp = await chrome.runtime.sendMessage({
            action: "API_sharePageWithUser",
            pageId: resourceId,
            userEmail: email,
            permissionLevel: permission,
          });
          result = sharePageResp.success ? sharePageResp.data : null;
          break;
        case "site":
          const shareSiteResp = await chrome.runtime.sendMessage({
            action: "API_shareSiteWithUser",
            siteId: resourceId,
            userEmail: email,
            permissionLevel: permission,
          });
          result = shareSiteResp.success ? shareSiteResp.data : null;
          break;
        default:
          throw new Error(`Invalid share type: ${shareType}`);
      }

      // Clear cache
      this.shareCache.delete(`${shareType}:${resourceId}`);

      return result;
    } catch (error) {
      console.error("[Web Notes] Create share API call failed:", error);
      throw new Error(error.message || "Failed to create share");
    }
  },

  /**
   * Get current shares for resource
   * @param {string} shareType - Type of share
   * @param {string} resourceId - Resource identifier
   * @returns {Promise<Array>} Array of shares
   */
  async getCurrentShares(shareType, resourceId) {
    try {
      const cacheKey = `${shareType}:${resourceId}`;
      const cached = this.shareCache.get(cacheKey);

      if (cached && Date.now() - cached.timestamp < this.SHARE_CACHE_TTL) {
        return cached.data;
      }

      let shares;

      switch (shareType) {
        case "note":
          // Notes don't have direct sharing - they inherit from their page
          shares = [];
          break;
        case "page":
          const getPageSharesResp = await chrome.runtime.sendMessage({ action: "API_getPageShares", pageId: resourceId });
          shares = getPageSharesResp.success ? getPageSharesResp.data : [];
          break;
        case "site":
          const getSiteSharesResp = await chrome.runtime.sendMessage({ action: "API_getSiteShares", siteId: resourceId });
          shares = getSiteSharesResp.success ? getSiteSharesResp.data : [];
          break;
        default:
          throw new Error(`Invalid share type: ${shareType}`);
      }

      // Cache the result
      this.shareCache.set(cacheKey, {
        data: shares,
        timestamp: Date.now(),
      });

      return shares;
    } catch (error) {
      console.error("[Web Notes] Get shares API call failed:", error);
      throw error;
    }
  },

  /**
   * Update share permission with rate limiting
   * @param {string} shareType - Type of share
   * @param {string} resourceId - Resource identifier
   * @param {string} userId - User ID
   * @param {string} newPermission - New permission level
   * @returns {Promise<void>}
   */
  async updateSharePermission(shareType, resourceId, userId, newPermission) {
    try {
      // Enhanced validation
      if (
        !this.validateSecureInput(shareType, "resourceId", { maxLength: 50 }) ||
        !this.validateSecureInput(resourceId, shareType === "page" ? "url" : "resourceId") ||
        !this.validateSecureInput(userId, "resourceId") ||
        !this.validateSecureInput(newPermission, "permissionLevel")
      ) {
        throw new Error("Invalid input parameters");
      }

      // Rate limiting
      if (!this.rateLimiter.isAllowed("shareUpdate", userId)) {
        this.showErrorMessage("Too many update requests. Please wait before trying again.");
        return;
      }

      // Permission check
      const hasPermission = await this.checkSharePermission(shareType, resourceId);
      if (!hasPermission) {
        throw new Error("You do not have permission to modify this share");
      }

      // Route to appropriate API based on share type
      switch (shareType) {
        case "note":
          throw new Error("Individual notes cannot be shared");
          break;
        case "page":
          await chrome.runtime.sendMessage({
            action: "API_updatePageSharePermission",
            pageId: resourceId,
            userId: userId,
            newPermission: newPermission,
            isActive: true,
          });
          break;
        case "site":
          await chrome.runtime.sendMessage({
            action: "API_updateSiteSharePermission",
            siteId: resourceId,
            userId: userId,
            newPermission: newPermission,
            isActive: true,
          });
          break;
        default:
          throw new Error(`Invalid share type: ${shareType}`);
      }

      // Clear cache and refresh
      this.shareCache.delete(`${shareType}:${resourceId}`);
      await this.refreshCurrentShares(shareType, resourceId);

      this.showSuccessMessage("Permission updated successfully");
    } catch (error) {
      console.error("[Web Notes] Update permission failed:", error);
      this.showErrorMessage(error.message || "Failed to update permission. Please try again.");
    }
  },

  /**
   * Remove share with enhanced security
   * @param {string} shareType - Type of share
   * @param {string} resourceId - Resource identifier
   * @param {string} userId - User ID
   * @returns {Promise<void>}
   */
  async removeShare(shareType, resourceId, userId) {
    try {
      // Enhanced validation
      if (
        !this.validateSecureInput(shareType, "resourceId", { maxLength: 50 }) ||
        !this.validateSecureInput(resourceId, shareType === "page" ? "url" : "resourceId") ||
        !this.validateSecureInput(userId, "resourceId")
      ) {
        throw new Error("Invalid input parameters");
      }

      // Rate limiting
      if (!this.rateLimiter.isAllowed("shareDelete", userId)) {
        this.showErrorMessage("Too many delete requests. Please wait before trying again.");
        return;
      }

      // Permission check
      const hasPermission = await this.checkSharePermission(shareType, resourceId);
      if (!hasPermission) {
        throw new Error("You do not have permission to remove shares from this resource");
      }

      if (!confirm("Are you sure you want to remove this person's access?")) {
        return;
      }

      // Route to appropriate API based on share type
      switch (shareType) {
        case "note":
          throw new Error("Individual notes cannot be shared");
          break;
        case "page":
          await chrome.runtime.sendMessage({
            action: "API_removePageShare",
            pageId: resourceId,
            userId: userId,
          });
          break;
        case "site":
          await chrome.runtime.sendMessage({
            action: "API_removeSiteShare",
            siteId: resourceId,
            userId: userId,
          });
          break;
        default:
          throw new Error(`Invalid share type: ${shareType}`);
      }

      // Clear cache and refresh
      this.shareCache.delete(`${shareType}:${resourceId}`);
      await this.refreshCurrentShares(shareType, resourceId);

      this.showSuccessMessage("Access removed successfully");
    } catch (error) {
      console.error("[Web Notes] Remove share failed:", error);
      this.showErrorMessage(error.message || "Failed to remove access. Please try again.");
    }
  },

  /**
   * Refresh current shares display
   * @param {string} shareType - Type of share
   * @param {string} resourceId - Resource identifier
   * @returns {Promise<void>}
   */
  async refreshCurrentShares(shareType, resourceId) {
    try {
      const sharesList = document.getElementById("wn-current-shares");
      if (!sharesList) return;

      // Show loading
      sharesList.innerHTML = '<div class="wn-shares-loading">Loading...</div>';

      // Get updated shares
      const shares = await this.getCurrentShares(shareType, resourceId);

      // Clear and rebuild
      sharesList.innerHTML = "";

      if (shares.length === 0) {
        const emptyMessage = document.createElement("div");
        emptyMessage.className = "wn-shares-empty";
        emptyMessage.textContent = "No shares yet. Add people above to start sharing.";
        sharesList.appendChild(emptyMessage);
      } else {
        shares.forEach(share => {
          const shareItem = this.createShareItem(share, shareType, resourceId);
          sharesList.appendChild(shareItem);
        });
      }
    } catch (error) {
      console.error("[Web Notes] Failed to refresh shares:", error);
      const sharesList = document.getElementById("wn-current-shares");
      if (sharesList) {
        sharesList.innerHTML = '<div class="wn-shares-error">Failed to load shares.</div>';
      }
    }
  },

  /**
   * Get sharing status for a resource
   * @param {string} shareType - Type of share
   * @param {string} resourceId - Resource identifier
   * @returns {Promise<Object>} Sharing status
   */
  async getSharingStatus(shareType, resourceId) {
    try {
      const shares = await this.getCurrentShares(shareType, resourceId);
      return {
        isShared: shares.length > 0,
        shareCount: shares.length,
        hasAdminAccess: shares.some(share => share.is_owner || share.permission_level === "ADMIN"),
      };
    } catch (error) {
      console.error("[Web Notes] Failed to get sharing status:", error);
      return {
        isShared: false,
        shareCount: 0,
        hasAdminAccess: false,
      };
    }
  },

  /**
   * Copy share link to clipboard
   * @param {string} shareType - Type of share
   * @param {string} resourceId - Resource identifier
   * @returns {Promise<void>}
   */
  async copyShareLink(shareType, resourceId) {
    try {
      // TODO: Implement share link generation on backend
      throw new Error("Share link generation not yet implemented");
    } catch (error) {
      console.error("[Web Notes] Failed to copy share link:", error);
      this.showErrorMessage("Share link generation not yet implemented");
    }
  },

  /**
   * Enhanced input validation and rate limiting
   * @param {string} input - Input to validate
   * @param {string} type - Type of validation
   * @param {Object} options - Validation options
   * @returns {boolean} True if valid
   */
  validateSecureInput(input, type, options = {}) {
    try {
      switch (type) {
        case "email":
          return this.validateEmailSecurity(input, options);
        case "resourceId":
          return this.validateResourceId(input, options);
        case "permissionLevel":
          return this.validatePermissionLevel(input);
        case "url":
          return this.validateUrlSecurity(input, options);
        default:
          console.warn("[Web Notes] Unknown validation type:", type);
          return false;
      }
    } catch (error) {
      console.error("[Web Notes] Validation error:", error);
      return false;
    }
  },

  /**
   * Enhanced email validation with security checks
   * @param {string} email - Email to validate
   * @param {Object} options - Validation options
   * @returns {boolean} True if valid and secure
   */
  validateEmailSecurity(email, options = {}) {
    if (!email || typeof email !== "string") {
      return false;
    }

    const trimmedEmail = email.trim().toLowerCase();

    // Length check
    if (trimmedEmail.length === 0 || trimmedEmail.length > 254) {
      return false;
    }

    // Basic format validation (RFC 5322 compliant)
    if (!this.EMAIL_REGEX.test(trimmedEmail)) {
      return false;
    }

    // Security checks
    const securityPatterns = [
      /javascript:/i,
      /data:/i,
      /vbscript:/i,
      /<script/i,
      /on\w+\s*=/i,
      /[\x00-\x1f\x7f-\x9f]/, // Control characters
      /[<>'"&]/, // Potentially dangerous characters
    ];

    for (const pattern of securityPatterns) {
      if (pattern.test(trimmedEmail)) {
        console.warn("[Web Notes] Email contains potentially dangerous content");
        return false;
      }
    }

    // Domain validation
    const [localPart, domain] = trimmedEmail.split("@");
    if (!localPart || !domain || localPart.length > 64 || domain.length > 255) {
      return false;
    }

    return true;
  },

  /**
   * Validate resource identifiers for security
   * @param {string} resourceId - Resource ID to validate
   * @param {Object} options - Validation options
   * @returns {boolean} True if valid
   */
  validateResourceId(resourceId, options = {}) {
    if (!resourceId || typeof resourceId !== "string") {
      return false;
    }

    const trimmed = resourceId.trim();

    // Length check
    if (trimmed.length === 0 || trimmed.length > (options.maxLength || 2048)) {
      return false;
    }

    // Security patterns
    const dangerousPatterns = [
      /javascript:/i,
      /data:/i,
      /vbscript:/i,
      /<script/i,
      /on\w+\s*=/i,
      /[\x00-\x1f\x7f-\x9f]/, // Control characters
      /[<>'"&]/, // HTML/XML dangerous characters
    ];

    for (const pattern of dangerousPatterns) {
      if (pattern.test(trimmed)) {
        console.warn("[Web Notes] Resource ID contains potentially dangerous content");
        return false;
      }
    }

    return true;
  },

  /**
   * Validate permission levels
   * @param {string} permission - Permission level to validate
   * @returns {boolean} True if valid
   */
  validatePermissionLevel(permission) {
    if (!permission || typeof permission !== "string") {
      return false;
    }

    const validPermissions = Object.keys(this.PERMISSION_LEVELS);
    return validPermissions.includes(permission.toUpperCase());
  },

  /**
   * Validate URLs with security checks
   * @param {string} url - URL to validate
   * @param {Object} options - Validation options
   * @returns {boolean} True if valid and secure
   */
  validateUrlSecurity(url, options = {}) {
    if (!url || typeof url !== "string") {
      return false;
    }

    try {
      const parsedUrl = new URL(url);

      // Protocol validation
      const allowedProtocols = options.allowedProtocols || ["http:", "https:"];
      if (!allowedProtocols.includes(parsedUrl.protocol)) {
        console.warn("[Web Notes] URL protocol not allowed:", parsedUrl.protocol);
        return false;
      }

      // Length check
      if (url.length > (options.maxLength || 2048)) {
        return false;
      }

      // Security checks
      const dangerousPatterns = [/javascript:/i, /data:/i, /vbscript:/i, /<script/i, /on\w+\s*=/i];

      for (const pattern of dangerousPatterns) {
        if (pattern.test(url)) {
          console.warn("[Web Notes] URL contains potentially dangerous content");
          return false;
        }
      }

      return true;
    } catch (error) {
      console.warn("[Web Notes] Invalid URL format:", error);
      return false;
    }
  },

  /**
   * Rate limiting for sharing operations
   */
  rateLimiter: {
    operations: new Map(),
    limits: {
      shareCreate: { max: 10, window: 60000 }, // 10 shares per minute
      shareUpdate: { max: 20, window: 60000 }, // 20 updates per minute
      shareDelete: { max: 5, window: 60000 }, // 5 deletions per minute
    },

    isAllowed(operation, identifier = "global") {
      const key = `${operation}:${identifier}`;
      const now = Date.now();
      const limit = this.limits[operation];

      if (!limit) {
        console.warn("[Web Notes] Unknown rate limit operation:", operation);
        return false;
      }

      if (!this.operations.has(key)) {
        this.operations.set(key, []);
      }

      const operations = this.operations.get(key);

      // Clean old operations outside the window
      const windowStart = now - limit.window;
      while (operations.length > 0 && operations[0] < windowStart) {
        operations.shift();
      }

      // Check if we're under the limit
      if (operations.length >= limit.max) {
        console.warn(`[Web Notes] Rate limit exceeded for ${operation}`);
        return false;
      }

      // Record this operation
      operations.push(now);
      return true;
    },
  },

  /**
   * Check if current user has permission to share a resource
   * @param {string} shareType - Type of share
   * @param {string} resourceId - Resource identifier
   * @returns {Promise<boolean>} True if user can share
   */
  async checkSharePermission(shareType, resourceId) {
    try {
      // For now, assume authenticated users can share their own resources
      // This should be enhanced with proper server-side permission checks
      const isAuth = await isServerAuthenticated();
      if (!isAuth) {
        return false;
      }

      // Additional checks could be added here based on resource ownership
      return true;
    } catch (error) {
      console.error("[Web Notes] Error checking share permission:", error);
      return false;
    }
  },

  /**
   * Inject CSS styles for sharing interface
   */
  injectStyles() {
    if (document.getElementById("wn-sharing-styles")) {
      return; // Already injected
    }

    const style = document.createElement("style");
    style.id = "wn-sharing-styles";
    style.textContent = `
      /* Sharing Dialog Overlay */
      .wn-sharing-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.2s ease-in-out;
      }

      /* Dialog Container */
      .wn-sharing-dialog {
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        max-width: 500px;
        width: 90%;
        max-height: 80vh;
        overflow: hidden;
        transform: scale(0.95);
        transition: transform 0.2s ease-in-out;
      }

      /* Dialog Header */
      .wn-sharing-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 20px 24px 16px;
        border-bottom: 1px solid #e0e0e0;
      }

      .wn-sharing-title {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: #1a1a1a;
      }

      .wn-sharing-close {
        background: none;
        border: none;
        font-size: 24px;
        cursor: pointer;
        padding: 4px;
        line-height: 1;
        color: #666;
        border-radius: 4px;
        transition: background-color 0.2s ease;
      }

      .wn-sharing-close:hover {
        background-color: #f5f5f5;
      }

      /* Dialog Body */
      .wn-sharing-body {
        padding: 20px 24px;
        max-height: 60vh;
        overflow-y: auto;
      }

      /* Dialog Footer */
      .wn-sharing-footer {
        padding: 16px 24px 20px;
        border-top: 1px solid #e0e0e0;
        display: flex;
        justify-content: flex-end;
        gap: 12px;
      }

      /* Sections */
      .wn-sharing-section {
        margin-bottom: 24px;
      }

      .wn-sharing-section:last-child {
        margin-bottom: 0;
      }

      .wn-sharing-section h3 {
        margin: 0 0 12px 0;
        font-size: 14px;
        font-weight: 600;
        color: #333;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      /* Content Details */
      .wn-sharing-details {
        background: #f8f9fa;
        border-radius: 6px;
        padding: 12px;
        border: 1px solid #e9ecef;
      }

      .wn-note-preview, .wn-page-title, .wn-site-domain {
        font-weight: 500;
        color: #1a1a1a;
        margin-bottom: 4px;
      }

      .wn-page-info, .wn-page-url, .wn-site-description {
        font-size: 13px;
        color: #666;
      }

      /* Form Elements */
      .wn-sharing-form {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .wn-form-group {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .wn-form-group label {
        font-size: 13px;
        font-weight: 500;
        color: #333;
      }

      .wn-form-input, .wn-form-select {
        padding: 10px 12px;
        border: 1px solid #d0d7de;
        border-radius: 6px;
        font-size: 14px;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
      }

      .wn-form-input:focus, .wn-form-select:focus {
        outline: none;
        border-color: #0969da;
        box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.1);
      }

      .wn-form-input[aria-invalid="true"] {
        border-color: #d1242f;
      }

      .wn-form-error {
        font-size: 12px;
        color: #d1242f;
        padding: 4px 0;
      }

      /* Buttons */
      .wn-sharing-button {
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        border: 1px solid transparent;
        transition: all 0.2s ease;
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }

      .wn-sharing-button-primary {
        background: #0969da;
        color: white;
        border-color: #0969da;
      }

      .wn-sharing-button-primary:hover:not(:disabled) {
        background: #0860ca;
        border-color: #0860ca;
      }

      .wn-sharing-button-primary:disabled {
        background: #8c959f;
        border-color: #8c959f;
        cursor: not-allowed;
      }

      .wn-sharing-button-secondary {
        background: #f6f8fa;
        color: #24292f;
        border-color: #d0d7de;
      }

      .wn-sharing-button-secondary:hover {
        background: #f3f4f6;
        border-color: #d0d7de;
      }

      /* Loading Spinner */
      .wn-loading-spinner {
        animation: wn-spin 1s linear infinite;
        margin-left: 4px;
      }

      @keyframes wn-spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }

      /* Shares List */
      .wn-shares-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .wn-share-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px;
        background: #f8f9fa;
        border-radius: 6px;
        border: 1px solid #e9ecef;
      }

      .wn-share-user {
        flex: 1;
        min-width: 0;
      }

      .wn-share-user-name {
        font-weight: 500;
        color: #1a1a1a;
        margin-bottom: 2px;
      }

      .wn-share-user-email {
        font-size: 13px;
        color: #666;
      }

      .wn-share-permission {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .wn-permission-select {
        padding: 4px 8px;
        border: 1px solid #d0d7de;
        border-radius: 4px;
        font-size: 13px;
      }

      .wn-permission-label {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 13px;
        font-weight: 500;
      }

      .wn-permission-owner {
        background: #dbeafe;
        color: #1e40af;
      }

      .wn-share-remove {
        background: none;
        border: none;
        color: #dc2626;
        font-size: 16px;
        cursor: pointer;
        padding: 4px;
        border-radius: 4px;
        transition: background-color 0.2s ease;
      }

      .wn-share-remove:hover {
        background-color: #fee2e2;
      }

      /* Empty and Error States */
      .wn-shares-empty, .wn-shares-error, .wn-shares-loading {
        text-align: center;
        padding: 20px;
        color: #666;
        font-style: italic;
      }

      .wn-shares-error {
        color: #d1242f;
      }

      /* Toast Notifications */
      .wn-toast {
        background: white;
        border-radius: 6px;
        padding: 12px 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        border-left: 4px solid;
        max-width: 300px;
        word-wrap: break-word;
        animation: wn-toast-slide-in 0.3s ease-out;
      }

      .wn-toast-success {
        border-left-color: #059669;
        color: #065f46;
      }

      .wn-toast-error {
        border-left-color: #dc2626;
        color: #991b1b;
      }

      .wn-toast-info {
        border-left-color: #0969da;
        color: #1e40af;
      }

      @keyframes wn-toast-slide-in {
        from {
          transform: translateX(100%);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }

      /* Enhanced Responsive Design */
      @media (max-width: 600px) {
        .wn-sharing-dialog {
          width: 95%;
          margin: 10px;
          max-height: 90vh;
        }

        .wn-sharing-header, .wn-sharing-body, .wn-sharing-footer {
          padding-left: 16px;
          padding-right: 16px;
        }

        .wn-sharing-body {
          max-height: 70vh;
        }

        .wn-share-item {
          flex-direction: column;
          align-items: flex-start;
          gap: 8px;
        }

        .wn-share-permission {
          width: 100%;
          justify-content: space-between;
        }

        .wn-sharing-form {
          gap: 12px;
        }

        .wn-form-input, .wn-form-select {
          font-size: 16px; /* Prevent zoom on iOS */
        }

        .wn-toast {
          left: 5px;
          right: 5px;
          top: 5px;
          max-width: none;
        }
      }

      @media (max-width: 380px) {
        .wn-sharing-dialog {
          width: 98%;
          margin: 5px;
        }

        .wn-sharing-header {
          padding: 16px 12px 12px;
        }

        .wn-sharing-body {
          padding: 16px 12px;
        }

        .wn-sharing-footer {
          padding: 12px;
        }

        .wn-sharing-title {
          font-size: 16px;
        }

        .wn-form-input, .wn-form-select, .wn-sharing-button {
          padding: 12px;
          font-size: 16px;
        }
      }

      /* Tablet specific adjustments */
      @media (min-width: 481px) and (max-width: 768px) {
        .wn-sharing-dialog {
          width: 80%;
          max-width: 600px;
        }
      }

      /* Large screen optimizations */
      @media (min-width: 1200px) {
        .wn-sharing-dialog {
          max-width: 600px;
        }
      }

      /* Enhanced Focus Indicators */
      .wn-form-input:focus,
      .wn-form-select:focus,
      .wn-sharing-button:focus,
      .wn-sharing-close:focus,
      .wn-permission-select:focus,
      .wn-share-remove:focus,
      [data-wn-focused="true"] {
        outline: 2px solid #0969da !important;
        outline-offset: 2px !important;
      }

      /* Screen Reader Only Content */
      .wn-sr-only {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        padding: 0 !important;
        margin: -1px !important;
        overflow: hidden !important;
        clip: rect(0, 0, 0, 0) !important;
        white-space: nowrap !important;
        border: 0 !important;
      }

      /* Skip Links for Keyboard Users */
      .wn-skip-link {
        position: absolute;
        top: -40px;
        left: 6px;
        background: #0969da;
        color: white;
        padding: 8px;
        text-decoration: none;
        border-radius: 4px;
        z-index: 10002;
        transition: top 0.3s ease;
      }

      .wn-skip-link:focus {
        top: 6px;
      }

      /* High Contrast Mode */
      @media (prefers-contrast: high) {
        .wn-sharing-overlay {
          background: rgba(0, 0, 0, 0.9);
        }

        .wn-sharing-dialog {
          border: 3px solid #000;
          background: #fff;
        }

        .wn-form-input:focus, .wn-form-select:focus, .wn-sharing-button:focus {
          border-color: #000 !important;
          box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.5) !important;
        }

        .wn-sharing-button-primary {
          background: #000 !important;
          border-color: #000 !important;
          color: #fff !important;
        }

        .wn-sharing-button-secondary {
          background: #fff !important;
          border-color: #000 !important;
          color: #000 !important;
        }

        .wn-share-item {
          border: 1px solid #000 !important;
        }
      }

      /* Forced Colors Mode (Windows High Contrast) */
      @media (forced-colors: active) {
        .wn-sharing-dialog {
          border: 1px solid ButtonBorder;
          background: ButtonFace;
        }

        .wn-form-input, .wn-form-select {
          border: 1px solid ButtonBorder;
          background: Field;
          color: FieldText;
        }

        .wn-sharing-button {
          border: 1px solid ButtonBorder;
          background: ButtonFace;
          color: ButtonText;
        }

        .wn-sharing-button:hover {
          background: Highlight;
          color: HighlightText;
        }
      }

      /* Reduced Motion */
      @media (prefers-reduced-motion: reduce) {
        .wn-sharing-overlay, .wn-sharing-dialog, .wn-loading-spinner {
          transition: none;
          animation: none;
        }
      }
    `;

    document.head.appendChild(style);
  },
};

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => SharingInterface.init());
} else {
  SharingInterface.init();
}

// Export for use in other scripts
if (typeof window !== "undefined") {
  window.SharingInterface = SharingInterface;
}
