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
function extractPageDOMForTest() {
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
 * Find semantic boundaries in HTML for intelligent chunking.
 * Prioritizes meaningful HTML boundaries to avoid splitting mid-content.
 *
 * Priority order:
 * 1. <section> elements with IDs or classes
 * 2. <article> elements
 * 3. <div> elements with semantic classes (content, main, article)
 * 4. <div> elements with IDs
 * 5. Major headings (h1, h2)
 * 6. Fallback to paragraphs and divs
 *
 * @param {HTMLElement} element - Root element to analyze for boundaries
 * @returns {Array<HTMLElement>} Array of boundary elements to use for chunking
 */
function findSemanticBoundaries(element) {
  // Priority order for splitting - try each until we find multiple boundaries
  const selectors = [
    "section[id], section[class]", // Semantic sections with IDs/classes
    "article", // Article elements
    'div[class*="content"], div[class*="main"], div[class*="article"]', // Content containers
    "div[id]", // Divs with IDs
    "h1, h2", // Major headings
  ];

  // Try each selector until we find at least 2 boundaries
  for (const selector of selectors) {
    const boundaries = Array.from(element.querySelectorAll(selector));
    if (boundaries.length > 1) {
      return boundaries;
    }
  }

  // Fallback: split by paragraphs and divs if no semantic boundaries found
  return Array.from(element.querySelectorAll("p, div"));
}

/**
 * Extract parent context metadata for selector accuracy.
 * This context helps the LLM generate accurate CSS selectors relative
 * to the full document structure, even when processing a chunk.
 *
 * @param {HTMLElement} element - Root element (typically documentElement)
 * @returns {Object} Context metadata including body classes, IDs, and structure
 */
function extractParentContext(element) {
  const body = element.querySelector("body") || element;
  return {
    body_classes: Array.from(body.classList || []),
    body_id: body.id || null,
    main_container: body.querySelector('main, [role="main"]')?.tagName.toLowerCase(),
    document_title: element.querySelector("title")?.textContent || "",
  };
}

/**
 * Chunk DOM content into semantic pieces that fit within token limits.
 * Uses intelligent boundary detection to avoid splitting mid-content.
 *
 * Algorithm:
 * 1. If content fits in one chunk, return single chunk
 * 2. Parse HTML and find semantic boundaries
 * 3. Group boundaries into chunks staying under maxTokensPerChunk
 * 4. Merge small chunks to meet minimum size requirement
 * 5. Build chunk objects with metadata
 *
 * @param {string} htmlContent - Full HTML content to chunk
 * @param {number} maxTokensPerChunk - Maximum tokens per chunk (default: 10000)
 * @returns {Array<Object>} Array of chunk objects with metadata
 */
function chunkDOMContent(htmlContent, maxTokensPerChunk = 10000) {
  const maxCharsPerChunk = maxTokensPerChunk * 4; // ~4 chars per token
  const minCharsPerChunk = 10000; // Minimum ~2500 tokens to avoid tiny chunks

  // If small enough, return as single chunk
  if (htmlContent.length <= maxCharsPerChunk) {
    return [
      {
        chunk_index: 0,
        total_chunks: 1,
        chunk_dom: htmlContent,
        parent_context: null,
        is_final_chunk: true,
      },
    ];
  }

  // Parse HTML into DOM for analysis
  const parser = new DOMParser();
  const doc = parser.parseFromString(htmlContent, "text/html");
  const body = doc.body;

  // Extract parent context once for all chunks
  const parentContext = extractParentContext(doc.documentElement);

  // Find semantic boundaries for intelligent splitting
  const boundaries = findSemanticBoundaries(body);

  // Group boundaries into chunks staying under size limit
  const chunks = [];
  let currentChunk = [];
  let currentSize = 0;

  for (const element of boundaries) {
    const elementHTML = element.outerHTML;
    const elementSize = elementHTML.length;

    // If adding this element would exceed limit and we have content, start new chunk
    if (currentSize + elementSize > maxCharsPerChunk && currentChunk.length > 0) {
      chunks.push(currentChunk);
      currentChunk = [element];
      currentSize = elementSize;
    } else {
      currentChunk.push(element);
      currentSize += elementSize;
    }
  }

  // Add final chunk
  if (currentChunk.length > 0) {
    chunks.push(currentChunk);
  }

  // Merge small chunks to meet minimum size requirement
  const mergedChunks = [];
  let currentMerged = [];
  let currentMergedSize = 0;

  for (const chunk of chunks) {
    const chunkSize = chunk.reduce((sum, el) => sum + el.outerHTML.length, 0);

    // If current merged chunk is empty, start with this chunk
    if (currentMerged.length === 0) {
      currentMerged = chunk;
      currentMergedSize = chunkSize;
    } else if (
      // If current merged is too small and adding this won't exceed max, merge
      currentMergedSize < minCharsPerChunk &&
      currentMergedSize + chunkSize <= maxCharsPerChunk
    ) {
      currentMerged = currentMerged.concat(chunk);
      currentMergedSize += chunkSize;
    } else {
      // Otherwise, finalize current merged chunk and start new one
      mergedChunks.push(currentMerged);
      currentMerged = chunk;
      currentMergedSize = chunkSize;
    }
  }

  // Add final merged chunk
  if (currentMerged.length > 0) {
    mergedChunks.push(currentMerged);
  }

  // Build chunk objects with metadata
  const totalChunks = mergedChunks.length;
  return mergedChunks.map((elements, index) => {
    const chunkDOM = elements.map(el => el.outerHTML).join("\n");
    return {
      chunk_index: index,
      total_chunks: totalChunks,
      chunk_dom: chunkDOM,
      parent_context: parentContext,
      is_final_chunk: index === totalChunks - 1,
    };
  });
}

/**
 * Extract page DOM in chunks for large pages.
 * This is the main entry point for chunked DOM extraction.
 *
 * Process:
 * 1. Clone and clean document (same as extractPageDOMForTest)
 * 2. Remove non-content elements (scripts, styles, etc.)
 * 3. Remove non-semantic attributes
 * 4. Chunk the content intelligently using semantic boundaries
 *
 * @returns {Array<Object>} Array of chunk objects with metadata
 */
function extractPageDOMInChunks() {
  try {
    // Clone and clean document (same as extractPageDOMForTest)
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
      return [
        {
          chunk_index: 0,
          total_chunks: 1,
          chunk_dom: document.body.innerHTML.substring(0, 50000),
          parent_context: null,
          is_final_chunk: true,
        },
      ];
    }

    let contentHTML = bodyElement.innerHTML;
    // Clean up excessive whitespace
    contentHTML = contentHTML.replace(/\s+/g, " ").trim();

    // Chunk the content
    const chunks = chunkDOMContent(contentHTML);

    return chunks;
  } catch (error) {
    console.error("[YAWN] Error extracting page DOM in chunks:", error);
    throw error;
  }
}

/**
 * Handle DOM auto-notes generation with server-side chunking
 * Shows configuration modal, then sends full DOM to backend
 */
async function handleGenerateDOMTestNotes() {
  try {
    // Check authentication
    const isAuth = await isServerAuthenticated();
    if (!isAuth) {
      alert("Please sign in to generate auto notes");
      return;
    }

    // Extract full DOM (reuse existing function but without size limit)
    const fullDOM = extractPageDOMForTest();

    if (!fullDOM) {
      alert("Failed to extract page content");
      return;
    }

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
 * Keep the old chunking function for reference but mark as deprecated
 * @deprecated Now handled server-side
 */
async function handleGenerateDOMTestNotesOld() {
  // [Previous implementation kept for reference]
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
    const pageDom = extractPageDOMForTest();
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
