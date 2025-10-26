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
    console.error("[YAWN] Error showing temporary message:", error);
    // Fallback to alert if custom message fails
    alert(message);
  }
}

/**
 * Create auto notes configuration modal
 * @param {number} domSizeKB - Size of DOM content in KB
 * @returns {Promise<Object|null>} Promise resolving to config object or null if cancelled
 * Config object: { templateType: 'study_guide' | 'content_review_expansion', customInstructions: string }
 */
function createAutoNotesConfigDialog(domSizeKB) {
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
      min-width: 450px;
      max-width: 500px;
      max-height: 80vh;
      overflow-y: auto;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      transform: scale(0.8);
      transition: transform 0.2s ease;
    `;

    // Create title
    const titleElement = document.createElement("h3");
    titleElement.textContent = "🤖 Generate Auto Notes";
    titleElement.style.cssText = `
      margin: 0 0 16px 0;
      font-size: 20px;
      font-weight: 600;
      color: #333;
    `;

    // Create warning message if DOM is large
    const estimatedTime = domSizeKB > 100 ? Math.ceil(domSizeKB / 50) : 1;
    const warningElement = document.createElement("div");
    warningElement.style.cssText = `
      margin: 0 0 20px 0;
      padding: 12px;
      background: #fff3cd;
      border: 1px solid #ffc107;
      border-radius: 6px;
      font-size: 13px;
      line-height: 1.5;
      color: #856404;
    `;
    warningElement.innerHTML = `
      <strong>Processing Info:</strong><br>
      Page size: ${domSizeKB}KB<br>
      Estimated time: ${estimatedTime} minute(s)<br>
      The server will chunk and process content in parallel.
    `;

    // Create copyright/TOS warning
    const copyrightWarningElement = document.createElement("div");
    copyrightWarningElement.style.cssText = `
      margin: 0 0 20px 0;
      padding: 12px;
      background: #f8d7da;
      border: 1px solid #dc3545;
      border-radius: 6px;
      font-size: 13px;
      line-height: 1.5;
      color: #721c24;
    `;
    copyrightWarningElement.innerHTML = `
      <strong>⚠️ Important:</strong><br>
      This action will scrape the page content and send it to an AI for processing.<br>
      Please ensure you follow all copyright laws and the Terms of Service of the target page.
    `;

    // Create note type section
    const noteTypeLabel = document.createElement("label");
    noteTypeLabel.textContent = "Select Note Type:";
    noteTypeLabel.style.cssText = `
      display: block;
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: #333;
    `;

    // Create radio button container
    const radioContainer = document.createElement("div");
    radioContainer.style.cssText = `
      margin: 0 0 20px 0;
      display: flex;
      flex-direction: column;
      gap: 12px;
    `;

    // Create study guide option
    const studyOption = createRadioOption(
      "study_guide",
      "Research/Study Notes",
      "Identifies key concepts and provides educational insights for college-level learning (3-10 notes)",
      true,
    );

    // Create review/brainstorm option
    const reviewOption = createRadioOption(
      "content_review",
      "Review/Brainstorm",
      "Offers editorial feedback and creative expansion suggestions for user content (5-15 notes)",
      false,
    );

    radioContainer.appendChild(studyOption);
    radioContainer.appendChild(reviewOption);

    // Create custom instructions section
    const instructionsLabel = document.createElement("label");
    instructionsLabel.textContent = "Additional Instructions (Optional):";
    instructionsLabel.style.cssText = `
      display: block;
      margin: 0 0 8px 0;
      font-size: 14px;
      font-weight: 600;
      color: #333;
    `;

    const instructionsTextarea = document.createElement("textarea");
    instructionsTextarea.placeholder = "Add any specific instructions for note generation...";
    instructionsTextarea.style.cssText = `
      width: 100%;
      min-height: 80px;
      padding: 10px;
      border: 1px solid #ddd;
      border-radius: 6px;
      font-size: 14px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      resize: vertical;
      box-sizing: border-box;
      margin-bottom: 20px;
    `;
    instructionsTextarea.addEventListener("focus", () => {
      instructionsTextarea.style.borderColor = "#4caf50";
      instructionsTextarea.style.outline = "none";
    });
    instructionsTextarea.addEventListener("blur", () => {
      instructionsTextarea.style.borderColor = "#ddd";
    });

    // Create button container
    const buttonContainer = document.createElement("div");
    buttonContainer.style.cssText = `
      display: flex;
      gap: 12px;
      justify-content: flex-end;
    `;

    // Create cancel button
    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
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

    // Create generate button
    const generateButton = document.createElement("button");
    generateButton.textContent = "Generate Notes";
    generateButton.style.cssText = `
      padding: 10px 20px;
      border: none;
      background: #4caf50;
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

    generateButton.addEventListener("mouseenter", () => {
      generateButton.style.background = "#45a049";
    });

    generateButton.addEventListener("mouseleave", () => {
      generateButton.style.background = "#4caf50";
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
      handleResponse(null);
    });

    generateButton.addEventListener("click", e => {
      e.preventDefault();
      e.stopPropagation();

      // Get selected template type
      const selectedRadio = dialog.querySelector('input[name="noteType"]:checked');
      const templateType = selectedRadio ? selectedRadio.value : "study_guide";
      const customInstructions = instructionsTextarea.value.trim();

      handleResponse({
        templateType,
        customInstructions,
      });
    });

    // Handle overlay click (cancel)
    overlay.addEventListener("click", e => {
      if (e.target === overlay) {
        handleResponse(null);
      }
    });

    // Handle escape key
    function handleEscapeKey(e) {
      if (e.key === "Escape") {
        e.preventDefault();
        document.removeEventListener("keydown", handleEscapeKey);
        handleResponse(null);
      }
    }
    document.addEventListener("keydown", handleEscapeKey);

    // Assemble dialog
    dialog.appendChild(titleElement);
    dialog.appendChild(warningElement);
    dialog.appendChild(copyrightWarningElement);
    dialog.appendChild(noteTypeLabel);
    dialog.appendChild(radioContainer);
    dialog.appendChild(instructionsLabel);
    dialog.appendChild(instructionsTextarea);
    buttonContainer.appendChild(cancelButton);
    buttonContainer.appendChild(generateButton);
    dialog.appendChild(buttonContainer);
    overlay.appendChild(dialog);

    // Add to page and animate in
    document.body.appendChild(overlay);

    // Animate in
    requestAnimationFrame(() => {
      overlay.style.opacity = "1";
      dialog.style.transform = "scale(1)";
    });

    // Focus first radio button for accessibility
    setTimeout(() => {
      const firstRadio = dialog.querySelector('input[name="noteType"]');
      if (firstRadio) {
        firstRadio.focus();
      }
    }, 100);
  });
}

/**
 * Helper function to create a radio option
 * @param {string} value - Radio button value
 * @param {string} label - Option label
 * @param {string} description - Option description
 * @param {boolean} checked - Whether this option is checked by default
 * @returns {HTMLElement} Radio option element
 */
function createRadioOption(value, label, description, checked = false) {
  const container = document.createElement("label");
  container.style.cssText = `
    display: flex;
    align-items: flex-start;
    padding: 12px;
    border: 2px solid ${checked ? "#4caf50" : "#ddd"};
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    background: ${checked ? "#f1f8f4" : "white"};
  `;

  const radio = document.createElement("input");
  radio.type = "radio";
  radio.name = "noteType";
  radio.value = value;
  radio.checked = checked;
  radio.style.cssText = `
    margin: 4px 12px 0 0;
    cursor: pointer;
    width: 18px;
    height: 18px;
    flex-shrink: 0;
  `;

  const textContainer = document.createElement("div");
  textContainer.style.cssText = `
    flex: 1;
  `;

  const labelElement = document.createElement("div");
  labelElement.textContent = label;
  labelElement.style.cssText = `
    font-size: 14px;
    font-weight: 600;
    color: #333;
    margin-bottom: 4px;
  `;

  const descElement = document.createElement("div");
  descElement.textContent = description;
  descElement.style.cssText = `
    font-size: 13px;
    color: #666;
    line-height: 1.4;
  `;

  textContainer.appendChild(labelElement);
  textContainer.appendChild(descElement);
  container.appendChild(radio);
  container.appendChild(textContainer);

  // Handle selection styling
  radio.addEventListener("change", () => {
    // Remove highlight from all options
    const allOptions = document.querySelectorAll('input[name="noteType"]');
    allOptions.forEach(opt => {
      const label = opt.closest("label");
      if (label) {
        label.style.borderColor = "#ddd";
        label.style.background = "white";
      }
    });

    // Highlight selected option
    if (radio.checked) {
      container.style.borderColor = "#4caf50";
      container.style.background = "#f1f8f4";
    }
  });

  // Hover effect
  container.addEventListener("mouseenter", () => {
    if (!radio.checked) {
      container.style.borderColor = "#bbb";
    }
  });

  container.addEventListener("mouseleave", () => {
    if (!radio.checked) {
      container.style.borderColor = "#ddd";
    }
  });

  return container;
}
