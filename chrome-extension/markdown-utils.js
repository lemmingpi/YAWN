/**
 * Markdown utilities for Web Notes Chrome Extension
 * Handles markdown parsing, rendering, and content sanitization
 */

/* eslint-env webextensions */
/* global marked, DOMPurify, updateNote */

/**
 * Markdown utility class with security and performance optimizations
 */
class MarkdownRenderer {
  constructor() {
    this.isInitialized = false;
    this.renderCache = new Map();
    this.maxCacheSize = 100; // Prevent memory leaks

    // Configure marked.js when it becomes available
    this.initializeMarked();
  }

  /**
   * Initialize marked.js with secure configuration
   */
  initializeMarked() {
    if (typeof marked !== "undefined" && !this.isInitialized) {
      // Configure marked for security and performance
      marked.setOptions({
        breaks: true, // Convert \n to <br>
        gfm: true, // GitHub Flavored Markdown
        sanitize: false, // We'll use DOMPurify instead
        smartypants: false, // Disable smart quotes for simplicity
        xhtml: false, // HTML5 output
      });

      // Custom renderer for additional security
      const renderer = new marked.Renderer();

      // Limit allowed HTML elements for security
      renderer.html = () => ""; // Block raw HTML

      // Customize link rendering for security
      renderer.link = (href, title, text) => {
        // Only allow safe protocols
        const safeProtocols = ["http:", "https:", "mailto:"];
        try {
          const url = new URL(href);
          if (!safeProtocols.includes(url.protocol)) {
            return text; // Return text only for unsafe links
          }
        } catch {
          return text; // Invalid URL, return text only
        }

        const titleAttr = title ? ` title="${this.escapeHtml(title)}"` : "";
        // eslint-disable-next-line max-len
        return `<a href="${this.escapeHtml(href)}"${titleAttr} target="_blank" rel="noopener noreferrer">${text}</a>`;
      };

      marked.use({ renderer });
      this.isInitialized = true;
      console.log("[Web Notes] Markdown renderer initialized");
    }
  }

  /**
   * Escape HTML to prevent XSS
   * @param {string} text - Text to escape
   * @returns {string} Escaped text
   */
  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Convert markdown to safe HTML
   * @param {string} markdown - Markdown content
   * @returns {string} Sanitized HTML
   */
  renderMarkdown(markdown) {
    if (!markdown || typeof markdown !== "string") {
      return "";
    }

    // Check cache first
    if (this.renderCache.has(markdown)) {
      return this.renderCache.get(markdown);
    }

    try {
      // Ensure marked is available
      if (typeof marked === "undefined") {
        console.warn("[Web Notes] Marked.js not available, returning plain text");
        return this.escapeHtml(markdown);
      }

      this.initializeMarked();

      // Convert markdown to HTML
      let html = marked.parse(markdown);

      // Sanitize with DOMPurify if available
      if (typeof DOMPurify !== "undefined") {
        html = DOMPurify.sanitize(html, {
          ALLOWED_TAGS: [
            "p",
            "br",
            "strong",
            "b",
            "em",
            "i",
            "u",
            "ul",
            "ol",
            "li",
            "blockquote",
            "pre",
            "code",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "a",
            "del",
            "ins",
          ],
          ALLOWED_ATTR: ["href", "title", "target", "rel", "style"],
          ALLOW_DATA_ATTR: false,
          FORBID_CONTENTS: ["script", "style"],
          FORBID_TAGS: ["script", "style", "iframe", "object", "embed", "form"],
        });
      } else {
        console.warn("[Web Notes] DOMPurify not available, using basic escaping");
        // Fallback: escape any remaining scripts
        html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "");
      }

      // Apply inline styles to override page CSS
      html = this.applyInlineStyles(html);

      // Cache the result
      if (this.renderCache.size >= this.maxCacheSize) {
        // Clear half the cache to prevent memory issues
        const entries = Array.from(this.renderCache.entries());
        entries.slice(0, Math.floor(this.maxCacheSize / 2)).forEach(([key]) => {
          this.renderCache.delete(key);
        });
      }
      this.renderCache.set(markdown, html);

      return html;
    } catch (error) {
      console.error("[Web Notes] Error rendering markdown:", error);
      return this.escapeHtml(markdown);
    }
  }

  /**
   * Apply inline styles to rendered HTML to override page CSS
   * @param {string} html - Sanitized HTML content
   * @returns {string} HTML with inline styles applied
   */
  applyInlineStyles(html) {
    try {
      // Create a temporary DOM element to parse and manipulate the HTML
      const tempDiv = document.createElement("div");
      tempDiv.innerHTML = html;

      // Define compact, readable styles that override page CSS
      const styles = {
        // Headers with clear hierarchy and compact spacing
        h1: "font-size: 16px !important; font-weight: bold !important; margin: 4px 0 2px 0 !important; padding: 0 !important; line-height: 1.2 !important; color: #2c3e50 !important; border: none !important; background: none !important; text-decoration: none !important; display: block !important;",
        h2: "font-size: 15px !important; font-weight: bold !important; margin: 3px 0 2px 0 !important; padding: 0 !important; line-height: 1.2 !important; color: #34495e !important; border: none !important; background: none !important; text-decoration: none !important; display: block !important;",
        h3: "font-size: 14px !important; font-weight: bold !important; margin: 3px 0 1px 0 !important; padding: 0 !important; line-height: 1.2 !important; color: #34495e !important; border: none !important; background: none !important; text-decoration: none !important; display: block !important;",

        // Lists with proper indentation and compact spacing
        ul: "margin: 2px 0 2px 16px !important; padding: 0 !important; list-style-type: disc !important; background: none !important; border: none !important;",
        ol: "margin: 2px 0 2px 16px !important; padding: 0 !important; list-style-type: decimal !important; background: none !important; border: none !important;",
        li: "margin: 1px 0 !important; padding: 0 0 0 2px !important; line-height: 1.3 !important; background: none !important; border: none !important; display: list-item !important;",

        // Links with clear distinction and hover effects
        a: "color: #3498db !important; text-decoration: underline !important; background: none !important; border: none !important; padding: 0 !important; margin: 0 !important; font-weight: normal !important; cursor: pointer !important;",

        // Paragraphs and basic text formatting
        p: "margin: 2px 0 !important; padding: 0 !important; line-height: 1.4 !important; background: none !important; border: none !important; display: block !important;",
        strong:
          "font-weight: bold !important; background: none !important; border: none !important; padding: 0 !important; margin: 0 !important;",
        b: "font-weight: bold !important; background: none !important; border: none !important; padding: 0 !important; margin: 0 !important;",
        em: "font-style: italic !important; background: none !important; border: none !important; padding: 0 !important; margin: 0 !important;",
        i: "font-style: italic !important; background: none !important; border: none !important; padding: 0 !important; margin: 0 !important;",
        code: "font-family: monospace !important; background: rgba(0,0,0,0.05) !important; padding: 1px 3px !important; border-radius: 2px !important; font-size: 12px !important; border: none !important; margin: 0 !important;",
        blockquote:
          "border-left: 2px solid #bdc3c7 !important; margin: 2px 0 !important; padding: 2px 0 2px 8px !important; background: rgba(0,0,0,0.02) !important; font-style: italic !important; color: #7f8c8d !important;",
      };

      // Apply styles to each element type
      for (const [selector, styleString] of Object.entries(styles)) {
        const elements = tempDiv.querySelectorAll(selector);
        elements.forEach(element => {
          // Preserve any existing inline styles and add our override styles
          const existingStyle = element.getAttribute("style") || "";
          element.setAttribute("style", existingStyle + styleString);
        });
      }

      return tempDiv.innerHTML;
    } catch (error) {
      console.error("[Web Notes] Error applying inline styles:", error);
      return html; // Return original HTML if styling fails
    }
  }

  /**
   * Check if content appears to be markdown
   * @param {string} content - Content to check
   * @returns {boolean} True if content looks like markdown
   */
  isMarkdownContent(content) {
    if (!content || typeof content !== "string") return false;

    // Simple heuristics to detect markdown
    const markdownIndicators = [
      /^\s*#{1,6}\s+/m, // Headers
      /\*\*.*?\*\*/, // Bold
      /\*.*?\*/, // Italic
      /^\s*[-*+]\s+/m, // Unordered lists
      /^\s*\d+\.\s+/m, // Ordered lists
      /^\s*>\s+/m, // Blockquotes
      /`.*?`/, // Inline code
      /```[\s\S]*?```/, // Code blocks
      /\[.*?\]\(.*?\)/, // Links
    ];

    return markdownIndicators.some(pattern => pattern.test(content));
  }

  /**
   * Clear the render cache
   */
  clearCache() {
    this.renderCache.clear();
  }
}

// Create global instance
const markdownRenderer = new MarkdownRenderer();

/**
 * Simplified note data structure utilities
 */
const NoteDataUtils = {
  /**
   * Create note data with markdown support
   * @param {Object} baseData - Base note data
   * @param {string} content - Note content (markdown or plain text)
   * @returns {Object} Enhanced note data
   */
  createNoteData(baseData, content = "") {
    const isMarkdown = markdownRenderer.isMarkdownContent(content);

    return {
      ...baseData,
      content: content,
      contentType: isMarkdown ? "markdown" : "plain",
      lastEdited: Date.now(),
      // Keep existing fields
      timestamp: baseData.timestamp || Date.now(),
      isVisible: baseData.isVisible !== undefined ? baseData.isVisible : true,
    };
  },

  /**
   * Migrate legacy note and save to storage if needed
   * @param {Object} noteData - Legacy note data
   * @param {boolean} saveIfMigrated - Whether to save to storage if migration occurred
   * @returns {Promise<Object>} Promise resolving to migrated note data
   */
  async migrateLegacyNote(noteData, saveIfMigrated = false) {
    // If note already has content field, just clean up any legacy text field
    if (noteData.content !== undefined) {
      if (noteData.text !== undefined) {
        // Remove legacy text field but keep existing content
        const cleanedNote = { ...noteData };
        delete cleanedNote.text;
        return cleanedNote;
      }
      return noteData; // Already has content and no legacy text field
    }

    // Legacy note without content field - migrate from text or create default
    const content = noteData.text || `Note #${noteData.id.split("-").pop()}`;

    // eslint-disable-next-line max-len
    console.log(
      `[Web Notes] Migrating note ${noteData.id}: "${noteData.text}" -> "${content}"`,
    );

    // Create migrated note data
    const migratedNote = this.createNoteData(noteData, content);

    // Remove legacy text field
    delete migratedNote.text;

    // Save to storage if requested
    if (saveIfMigrated && typeof updateNote === "function") {
      try {
        // eslint-disable-next-line max-len
        await updateNote(
          noteData.url || window.location.href,
          noteData.id,
          migratedNote,
        );
        // eslint-disable-next-line max-len
        console.log(`[Web Notes] Migrated and saved note ${noteData.id}`);
      } catch (error) {
        // eslint-disable-next-line max-len
        console.error(
          `[Web Notes] Failed to save migrated note ${noteData.id}:`,
          error,
        );
      }
    }

    return migratedNote;
  },

  /**
   * Get display content for a note
   * @param {Object} noteData - Note data
   * @returns {Object} {html, isMarkdown}
   */
  getDisplayContent(noteData) {
    // Assume content exists (migration should have handled this)
    const content = noteData.content || "";

    if (noteData.contentType === "markdown") {
      return {
        html: markdownRenderer.renderMarkdown(content),
        isMarkdown: true,
      };
    }

    return {
      html: markdownRenderer.escapeHtml(content),
      isMarkdown: false,
    };
  },
};

// Export for use in other scripts
if (typeof window !== "undefined") {
  window.MarkdownRenderer = MarkdownRenderer;
  window.markdownRenderer = markdownRenderer;
  window.NoteDataUtils = NoteDataUtils;
}

// Node.js compatibility
/* eslint-disable no-undef */
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    MarkdownRenderer,
    markdownRenderer,
    NoteDataUtils,
  };
}
/* eslint-enable no-undef */
