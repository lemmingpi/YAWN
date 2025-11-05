// AI Context Generator Dialog
// This module handles the UI for generating AI-powered page context

/**
 * Show AI Context Generator Dialog
 * @param {string} pageUrl - Current page URL
 * @param {string} pageTitle - Current page title
 * @param {string} pageDom - Extracted page DOM content
 */
async function showAIContextGeneratorDialog(pageUrl, pageTitle, pageDom) {
  try {
    // Create overlay
    const overlay = document.createElement("div");
    overlay.className = "wn-modal-overlay";
    overlay.id = "ai-context-dialog-overlay";
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      z-index: 999999;
      display: flex;
      align-items: center;
      justify-content: center;
      backdrop-filter: blur(4px);
    `;

    // Create dialog
    const dialog = document.createElement("div");
    dialog.className = "wn-modal-dialog";
    dialog.style.cssText = `
      background: white;
      border-radius: 12px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      max-width: 600px;
      width: 90%;
      max-height: 80vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    `;

    // Header
    const header = document.createElement("div");
    header.className = "wn-modal-header";
    header.style.cssText = `
      padding: 20px;
      border-bottom: 1px solid #e0e0e0;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    `;

    const headerTitle = document.createElement("h3");
    headerTitle.textContent = "Generate AI Context";
    headerTitle.style.cssText = `
      margin: 0;
      font-size: 20px;
      font-weight: 600;
    `;

    const closeBtn = document.createElement("button");
    closeBtn.className = "wn-close-btn";
    closeBtn.innerHTML = "&times;";
    closeBtn.style.cssText = `
      background: none;
      border: none;
      color: white;
      font-size: 32px;
      cursor: pointer;
      padding: 0;
      line-height: 1;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      transition: background 0.2s;
    `;
    closeBtn.addEventListener("mouseenter", () => {
      closeBtn.style.background = "rgba(255, 255, 255, 0.2)";
    });
    closeBtn.addEventListener("mouseleave", () => {
      closeBtn.style.background = "none";
    });
    closeBtn.addEventListener("click", () => {
      document.body.removeChild(overlay);
    });

    header.appendChild(headerTitle);
    header.appendChild(closeBtn);

    // Body
    const body = document.createElement("div");
    body.className = "wn-modal-body";
    body.style.cssText = `
      padding: 20px;
      overflow-y: auto;
      flex: 1;
    `;

    // Page info
    const pageInfo = document.createElement("div");
    pageInfo.style.cssText = `
      background: #f5f7fa;
      padding: 12px;
      border-radius: 8px;
      margin-bottom: 20px;
      font-size: 14px;
    `;
    pageInfo.innerHTML = `
      <div style="font-weight: 600; color: #2c3e50; margin-bottom: 4px;">Page:</div>
      <div style="color: #5a6c7d; word-break: break-word;">${pageTitle}</div>
    `;

    // LLM Provider dropdown
    const providerGroup = document.createElement("div");
    providerGroup.className = "wn-form-group";
    providerGroup.style.cssText = "margin-bottom: 16px;";

    const providerLabel = document.createElement("label");
    providerLabel.textContent = "LLM Provider:";
    providerLabel.style.cssText = `
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
      color: #2c3e50;
      font-size: 14px;
    `;

    const providerSelect = document.createElement("select");
    providerSelect.id = "llm-provider";
    providerSelect.style.cssText = `
      width: 100%;
      padding: 10px;
      border: 1px solid #d0d7de;
      border-radius: 6px;
      font-size: 14px;
      background: white;
      cursor: pointer;
    `;
    providerSelect.innerHTML = '<option value="">Loading providers...</option>';

    providerGroup.appendChild(providerLabel);
    providerGroup.appendChild(providerSelect);

    // Paywalled checkbox
    const paywalledGroup = document.createElement("div");
    paywalledGroup.className = "wn-form-group";
    paywalledGroup.style.cssText = "margin-bottom: 16px;";

    const paywalledLabel = document.createElement("label");
    paywalledLabel.style.cssText = `
      display: flex;
      align-items: center;
      font-size: 14px;
      color: #2c3e50;
      cursor: pointer;
    `;

    const paywalledCheckbox = document.createElement("input");
    paywalledCheckbox.type = "checkbox";
    paywalledCheckbox.id = "paywalled-checkbox";
    paywalledCheckbox.style.cssText = `
      margin-right: 8px;
      width: 18px;
      height: 18px;
      cursor: pointer;
    `;

    const paywalledText = document.createTextNode("Page is Paywalled (provide manual content)");
    paywalledLabel.appendChild(paywalledCheckbox);
    paywalledLabel.appendChild(paywalledText);
    paywalledGroup.appendChild(paywalledLabel);

    // Manual source textarea (hidden by default)
    const manualSourceGroup = document.createElement("div");
    manualSourceGroup.id = "manual-source-group";
    manualSourceGroup.className = "wn-form-group";
    manualSourceGroup.style.cssText = "margin-bottom: 16px; display: none;";

    const manualSourceLabel = document.createElement("label");
    manualSourceLabel.textContent = "Manual Page Source:";
    manualSourceLabel.style.cssText = `
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
      color: #2c3e50;
      font-size: 14px;
    `;

    const manualSourceTextarea = document.createElement("textarea");
    manualSourceTextarea.id = "manual-source";
    manualSourceTextarea.placeholder = "Paste the full page content here...";
    manualSourceTextarea.style.cssText = `
      width: 100%;
      min-height: 120px;
      padding: 10px;
      border: 1px solid #d0d7de;
      border-radius: 6px;
      font-size: 14px;
      font-family: monospace;
      resize: vertical;
    `;

    manualSourceGroup.appendChild(manualSourceLabel);
    manualSourceGroup.appendChild(manualSourceTextarea);

    // Custom instructions textarea
    const instructionsGroup = document.createElement("div");
    instructionsGroup.className = "wn-form-group";
    instructionsGroup.style.cssText = "margin-bottom: 16px;";

    const instructionsLabel = document.createElement("label");
    instructionsLabel.textContent = "Custom Instructions (optional):";
    instructionsLabel.style.cssText = `
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
      color: #2c3e50;
      font-size: 14px;
    `;

    const instructionsTextarea = document.createElement("textarea");
    instructionsTextarea.id = "custom-instructions";
    instructionsTextarea.placeholder = "Enter any specific instructions for context generation...";
    instructionsTextarea.style.cssText = `
      width: 100%;
      min-height: 80px;
      padding: 10px;
      border: 1px solid #d0d7de;
      border-radius: 6px;
      font-size: 14px;
      resize: vertical;
    `;

    instructionsGroup.appendChild(instructionsLabel);
    instructionsGroup.appendChild(instructionsTextarea);

    // Add all form groups to body
    body.appendChild(pageInfo);
    body.appendChild(providerGroup);
    body.appendChild(paywalledGroup);
    body.appendChild(manualSourceGroup);
    body.appendChild(instructionsGroup);

    // Footer
    const footer = document.createElement("div");
    footer.className = "wn-modal-footer";
    footer.style.cssText = `
      padding: 16px 20px;
      border-top: 1px solid #e0e0e0;
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      background: #f9fafb;
    `;

    const previewBtn = document.createElement("button");
    previewBtn.id = "preview-btn";
    previewBtn.textContent = "Preview Prompt";
    previewBtn.style.cssText = `
      padding: 10px 20px;
      border: 1px solid #d0d7de;
      background: white;
      color: #24292f;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    `;
    previewBtn.addEventListener("mouseenter", () => {
      previewBtn.style.background = "#f3f4f6";
    });
    previewBtn.addEventListener("mouseleave", () => {
      previewBtn.style.background = "white";
    });

    const generateBtn = document.createElement("button");
    generateBtn.id = "generate-btn";
    generateBtn.textContent = "Generate Context";
    generateBtn.style.cssText = `
      padding: 10px 20px;
      border: none;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    `;
    generateBtn.addEventListener("mouseenter", () => {
      generateBtn.style.transform = "translateY(-1px)";
      generateBtn.style.boxShadow = "0 4px 12px rgba(102, 126, 234, 0.4)";
    });
    generateBtn.addEventListener("mouseleave", () => {
      generateBtn.style.transform = "translateY(0)";
      generateBtn.style.boxShadow = "none";
    });

    footer.appendChild(previewBtn);
    footer.appendChild(generateBtn);

    // Assemble dialog
    dialog.appendChild(header);
    dialog.appendChild(body);
    dialog.appendChild(footer);
    overlay.appendChild(dialog);

    // Add to page
    document.body.appendChild(overlay);

    // Load LLM providers
    try {
      const providersResponse = await chrome.runtime.sendMessage({
        action: "API_getLLMProviders",
      });

      if (!providersResponse || !providersResponse.success) {
        throw new Error("Failed to fetch LLM providers");
      }

      const providers = providersResponse.data;
      if (providers && providers.length > 0) {
        providerSelect.innerHTML = providers
          .map(p => `<option value="${p.id}">${p.name} (max ${p.max_tokens.toLocaleString()} tokens)</option>`)
          .join("");
      } else {
        providerSelect.innerHTML = '<option value="">No providers available</option>';
        generateBtn.disabled = true;
      }
    } catch (error) {
      console.error("[YAWN] Failed to load LLM providers:", error);
      providerSelect.innerHTML = '<option value="">Error loading providers</option>';
      generateBtn.disabled = true;
    }

    // Toggle manual source visibility
    paywalledCheckbox.addEventListener("change", () => {
      manualSourceGroup.style.display = paywalledCheckbox.checked ? "block" : "none";
    });

    // Preview button handler
    previewBtn.addEventListener("click", async () => {
      try {
        const selectedProviderId = parseInt(providerSelect.value);
        if (!selectedProviderId) {
          alert("Please select an LLM provider");
          return;
        }

        previewBtn.disabled = true;
        previewBtn.textContent = "Loading...";

        // Get or create page
        const pageResponse = await chrome.runtime.sendMessage({
          action: "API_getOrCreatePageByUrl",
          url: pageUrl,
          title: pageTitle,
        });

        if (!pageResponse || !pageResponse.success || !pageResponse.data || !pageResponse.data.id) {
          alert("Failed to get/create page");
          return;
        }

        const page = pageResponse.data;

        // Prepare request data
        const customInstructions = instructionsTextarea.value.trim() || null;
        const pageSource = paywalledCheckbox.checked ? manualSourceTextarea.value.trim() : null;
        const domToUse = paywalledCheckbox.checked ? null : pageDom;

        // Call preview API
        const previewResponse = await chrome.runtime.sendMessage({
          action: "API_previewContextPrompt",
          pageId: page.id,
          customInstructions,
          pageSource,
          pageDom: domToUse,
        });

        if (!previewResponse || !previewResponse.success) {
          throw new Error("Failed to preview prompt");
        }

        const result = previewResponse.data;

        // Show preview in alert (or could create a better modal)
        const truncatedPrompt =
          result.prompt.length > 2000 ? result.prompt.substring(0, 2000) + "\n\n... (truncated)" : result.prompt;

        alert(`Preview Prompt (${result.prompt.length} characters):\n\n${truncatedPrompt}`);
      } catch (error) {
        console.error("[YAWN] Failed to preview prompt:", error);
        alert(`Failed to preview prompt: ${error.message}`);
      } finally {
        previewBtn.disabled = false;
        previewBtn.textContent = "Preview Prompt";
      }
    });

    // Generate button handler
    generateBtn.addEventListener("click", async () => {
      try {
        const selectedProviderId = parseInt(providerSelect.value);
        if (!selectedProviderId) {
          alert("Please select an LLM provider");
          return;
        }

        if (paywalledCheckbox.checked && !manualSourceTextarea.value.trim()) {
          alert("Please provide manual page source for paywalled content");
          return;
        }

        generateBtn.disabled = true;
        generateBtn.textContent = "Generating...";

        // Get or create page
        const pageResponse = await chrome.runtime.sendMessage({
          action: "API_getOrCreatePageByUrl",
          url: pageUrl,
          title: pageTitle,
        });

        if (!pageResponse || !pageResponse.success || !pageResponse.data || !pageResponse.data.id) {
          alert("Failed to get/create page");
          return;
        }

        const page = pageResponse.data;

        // Prepare request data
        const customInstructions = instructionsTextarea.value.trim() || null;
        const pageSource = paywalledCheckbox.checked ? manualSourceTextarea.value.trim() : null;
        const domToUse = paywalledCheckbox.checked ? null : pageDom;

        // Call generation API
        const generateResponse = await chrome.runtime.sendMessage({
          action: "API_generatePageContext",
          pageId: page.id,
          llmProviderId: selectedProviderId,
          customInstructions,
          pageSource,
          pageDom: domToUse,
        });

        if (!generateResponse || !generateResponse.success) {
          throw new Error(generateResponse?.error || "Failed to generate context");
        }

        const result = generateResponse.data;

        // Show success message
        const message =
          "✓ AI Context Generated Successfully!\n\n" +
          `Content Type: ${result.detected_content_type}\n` +
          `Tokens Used: ${result.tokens_used.toLocaleString()}\n` +
          `Cost: $${result.cost_usd.toFixed(4)}\n` +
          `Generation Time: ${(result.generation_time_ms / 1000).toFixed(2)}s\n\n` +
          "The context has been saved to the page.";

        alert(message);

        // Close dialog
        document.body.removeChild(overlay);
      } catch (error) {
        console.error("[YAWN] Failed to generate context:", error);
        alert(`Failed to generate context: ${error.message}`);
        generateBtn.disabled = false;
        generateBtn.textContent = "Generate Context";
      }
    });

    // Close on overlay click
    overlay.addEventListener("click", e => {
      if (e.target === overlay) {
        document.body.removeChild(overlay);
      }
    });

    // Close on Escape key
    const handleEscape = e => {
      if (e.key === "Escape") {
        document.body.removeChild(overlay);
        document.removeEventListener("keydown", handleEscape);
      }
    };
    document.addEventListener("keydown", handleEscape);
  } catch (error) {
    console.error("[YAWN] Error showing AI context dialog:", error);
    throw error;
  }
}

// Export function to global scope
window.showAIContextGeneratorDialog = showAIContextGeneratorDialog;
