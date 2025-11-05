/**
 * AI/Auto-Note Generation Functionality
 * Handles DOM extraction, chunking, and AI-based note generation
 */

/* global isServerAuthenticated, createAutoNotesConfigDialog, showAIContextGeneratorDialog */

/**
 * Configuration constant for rate limiting parallel chunk processing.
 * This controls how many chunks are processed simultaneously to avoid
 * overwhelming the backend or hitting rate limits.
 */
const MAX_CONCURRENT_CHUNKS = 3; // Process 3 chunks at a time

/**
 * Extract page DOM content for auto-note generation
 * @returns {string} Cleaned HTML content with structure preserved
 */
function extractPageDOM() {
  try {
    // Clone the document to work with
    const clonedDoc = document.documentElement.cloneNode(true);

    // Remove scripts, styles, and other non-content elements
    const removeSelectors = ["script", "style", "noscript", "iframe", "object", "embed", "svg", ".web-note"];
    removeSelectors.forEach(selector => {
      clonedDoc.querySelectorAll(selector).forEach(el => el.remove());
    });

    // Remove all attributes except for semantic ones
    const preserveAttrs = ["id", "class", "data-section", "data-paragraph", "role", "aria-label"];
    clonedDoc.querySelectorAll("*").forEach(el => {
      const attrs = Array.from(el.attributes);
      attrs.forEach(attr => {
        if (!preserveAttrs.includes(attr.name)) {
          el.removeAttribute(attr.name);
        }
      });
    });

    // Get the body content
    const bodyElement = clonedDoc.querySelector("body");
    if (!bodyElement) {
      console.warn("[YAWN] No body element found");
      return document.body.innerHTML; // Return full content, server will chunk
    }

    let contentHTML = bodyElement.innerHTML;

    // Clean up excessive whitespace
    contentHTML = contentHTML.replace(/\s+/g, " ").trim();

    // Log size but DO NOT truncate - server handles chunking
    const contentSize = Math.round(contentHTML.length / 1000);
    console.log(`[YAWN] Extracted ${contentSize}KB of DOM content (server will chunk if needed)`);

    return contentHTML;
  } catch (error) {
    console.error("[YAWN] Error extracting page DOM:", error);
    throw error;
  }
}

/**
 * Estimate token count from text using a conservative heuristic.
 * HTML typically uses ~4 characters per token due to markup overhead.
 *
 * @param {string} text - Text content to estimate tokens for
 * @returns {number} Estimated token count
 */
function estimateTokenCount(text) {
  // Conservative estimate: 1 token ≈ 4 characters for HTML
  return Math.ceil(text.length / 4);
}

/**
 * Handle DOM auto-notes generation with server-side chunking
 * Shows configuration modal, then sends full DOM to backend
 */
async function handleGenerateDOMNotes() {
  try {
    // Check authentication
    const isAuth = await isServerAuthenticated();
    if (!isAuth) {
      alert("Please sign in to generate auto notes");
      return;
    }

    // Extract full DOM (reuse existing function but without size limit)
    const fullDOM = extractPageDOM();

    if (!fullDOM) {
      alert("Failed to extract page content");
      return;
    }

    const domSize = fullDOM.length;

    // Show configuration modal
    const config = await createAutoNotesConfigDialog(domSize);

    // If user cancelled, exit
    if (!config) {
      console.log("[YAWN] User cancelled auto notes generation");
      return;
    }

    // Register page
    const pageUrl = window.location.href;
    const pageTitle = document.title || "Untitled";

    const pageData = await chrome.runtime.sendMessage({
      action: "API_registerPage",
      url: pageUrl,
      title: pageTitle,
    });

    if (!pageData || !pageData.data || !pageData.data.id) {
      alert("Failed to register page. Please try again.");
      return;
    }

    console.log(`[YAWN] Page registered with ID: ${pageData.data.id}`);

    // Single request with full DOM and configuration
    const response = await chrome.runtime.sendMessage({
      action: "API_generateAutoNotesFullDOM",
      pageId: pageData.data.id,
      fullDOM: fullDOM,
      templateType: config.templateType,
      customInstructions: config.customInstructions || null,
    });

    // Handle response
    if (response.success && response.data) {
      /* eslint-disable camelcase */
      const { notes, total_chunks, successful_chunks, cost_usd, tokens_used, batch_id } = response.data;

      let message =
        `Successfully generated ${notes.length} notes!\n\n` +
        `Processed ${successful_chunks}/${total_chunks} chunks\n` +
        `Batch ID: ${batch_id}\n` +
        `Total Cost: $${cost_usd.toFixed(4)}\n` +
        `Total Tokens: ${tokens_used.toLocaleString()}`;

      if (successful_chunks < total_chunks) {
        message += `\n\nWarning: ${total_chunks - successful_chunks} chunk(s) failed to process.`;
      }
      /* eslint-enable camelcase */

      alert(message);

      // Refresh to show notes
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } else {
      alert(`Failed to generate auto notes: ${response.error || "Unknown error"}`);
    }
  } catch (error) {
    console.error("[YAWN] Error generating auto notes:", error);
    alert(`Failed to generate auto notes: ${error.message}`);
  }
}

/**
 * Handle showing AI context generation dialog
 */
async function handleShowAIContextDialog() {
  try {
    // Check authentication
    const isAuth = await isServerAuthenticated();
    if (!isAuth) {
      alert("Please sign in to generate AI context");
      return;
    }

    // Extract the page DOM
    const pageDom = extractPageDOM();
    if (!pageDom) {
      alert("Failed to extract page content");
      return;
    }

    // Get page info
    const pageUrl = window.location.href;
    const pageTitle = document.title || "Untitled";

    // Show the AI context dialog (will be implemented in contextGeneratorDialog.js)
    if (typeof showAIContextGeneratorDialog === "function") {
      await showAIContextGeneratorDialog(pageUrl, pageTitle, pageDom);
    } else {
      console.error("[YAWN] AI context dialog not available");
      alert("AI context generation dialog not loaded. Please try again.");
    }
  } catch (error) {
    console.error("[YAWN] Error showing AI context dialog:", error);
    alert(`Failed to show AI context dialog: ${error.message}`);
  }
}
