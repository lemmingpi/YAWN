/**
 * Create a custom styled confirmation dialog
 * @param {string} title - Dialog title
 * @param {string} message - Dialog message
 * @param {string} confirmText - Confirm button text
 * @param {string} cancelText - Cancel button text
 * @returns {Promise<boolean>} Promise resolving to user choice
 */
function createCustomConfirmDialog(title, message, confirmText, cancelText) {
  return new Promise(resolve => {
    // Create overlay
    const overlay = document.createElement("div");
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      z-index: 10002;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: opacity 0.2s ease;
    `;

    // Create dialog
    const dialog = document.createElement("div");
    dialog.style.cssText = `
      background: white;
      border-radius: 12px;
      padding: 24px;
      min-width: 320px;
      max-width: 400px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      transform: scale(0.8);
      transition: transform 0.2s ease;
    `;

    // Create title
    const titleElement = document.createElement("h3");
    titleElement.textContent = title;
    titleElement.style.cssText = `
      margin: 0 0 12px 0;
      font-size: 18px;
      font-weight: 600;
      color: #333;
    `;

    // Create message
    const messageElement = document.createElement("p");
    messageElement.textContent = message;
    messageElement.style.cssText = `
      margin: 0 0 24px 0;
      font-size: 14px;
      line-height: 1.5;
      color: #666;
    `;

    // Create button container
    const buttonContainer = document.createElement("div");
    buttonContainer.style.cssText = `
      display: flex;
      gap: 12px;
      justify-content: flex-end;
    `;

    // Create cancel button
    const cancelButton = document.createElement("button");
    cancelButton.textContent = cancelText;
    cancelButton.style.cssText = `
      padding: 10px 20px;
      border: 1px solid #ddd;
      background: white;
      color: #666;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    `;

    // Create confirm button
    const confirmButton = document.createElement("button");
    confirmButton.textContent = confirmText;
    confirmButton.style.cssText = `
      padding: 10px 20px;
      border: none;
      background: #f44336;
      color: white;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    `;

    // Add hover effects
    cancelButton.addEventListener("mouseenter", () => {
      cancelButton.style.background = "#f5f5f5";
      cancelButton.style.borderColor = "#ccc";
    });

    cancelButton.addEventListener("mouseleave", () => {
      cancelButton.style.background = "white";
      cancelButton.style.borderColor = "#ddd";
    });

    confirmButton.addEventListener("mouseenter", () => {
      confirmButton.style.background = "#d32f2f";
    });

    confirmButton.addEventListener("mouseleave", () => {
      confirmButton.style.background = "#f44336";
    });

    // Handle responses
    function handleResponse(result) {
      overlay.style.opacity = "0";
      dialog.style.transform = "scale(0.8)";

      setTimeout(() => {
        if (overlay.parentNode) {
          overlay.remove();
        }
        resolve(result);
      }, 200);
    }

    cancelButton.addEventListener("click", e => {
      e.preventDefault();
      e.stopPropagation();
      handleResponse(false);
    });

    confirmButton.addEventListener("click", e => {
      e.preventDefault();
      e.stopPropagation();
      handleResponse(true);
    });

    // Handle overlay click (cancel)
    overlay.addEventListener("click", e => {
      if (e.target === overlay) {
        handleResponse(false);
      }
    });

    // Handle escape key
    function handleEscapeKey(e) {
      if (e.key === "Escape") {
        e.preventDefault();
        document.removeEventListener("keydown", handleEscapeKey);
        handleResponse(false);
      }
    }
    document.addEventListener("keydown", handleEscapeKey);

    // Assemble dialog
    buttonContainer.appendChild(cancelButton);
    buttonContainer.appendChild(confirmButton);
    dialog.appendChild(titleElement);
    dialog.appendChild(messageElement);
    dialog.appendChild(buttonContainer);
    overlay.appendChild(dialog);

    // Add to page and animate in
    document.body.appendChild(overlay);

    // Animate in
    requestAnimationFrame(() => {
      overlay.style.opacity = "1";
      dialog.style.transform = "scale(1)";
    });

    // Focus confirm button for accessibility
    setTimeout(() => {
      confirmButton.focus();
    }, 100);
  });
}

/**
 * Show a temporary message to the user
 * @param {string} message - Message to show
 * @param {string} type - Message type ('error', 'success', 'info')
 */
function showTemporaryMessage(message, type = "info") {
  try {
    const messageElement = document.createElement("div");
    messageElement.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: ${type === "error" ? "#f44336" : type === "success" ? "#4caf50" : "#2196f3"};
      color: white;
      padding: 12px 16px;
      border-radius: 6px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      font-weight: 500;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
      z-index: 10003;
      max-width: 300px;
      opacity: 0;
      transform: translateX(100%);
      transition: all 0.3s ease;
    `;

    messageElement.textContent = message;
    document.body.appendChild(messageElement);

    // Animate in
    requestAnimationFrame(() => {
      messageElement.style.opacity = "1";
      messageElement.style.transform = "translateX(0)";
    });

    // Remove after 4 seconds
    setTimeout(() => {
      messageElement.style.opacity = "0";
      messageElement.style.transform = "translateX(100%)";
      setTimeout(() => {
        if (messageElement.parentNode) {
          messageElement.remove();
        }
      }, 300);
    }, 4000);
  } catch (error) {
    console.error("[Web Notes] Error showing temporary message:", error);
    // Fallback to alert if custom message fails
    alert(message);
  }
}
