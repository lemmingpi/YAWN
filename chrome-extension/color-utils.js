/**
 * Color utilities for Web Notes Chrome Extension
 * Centralized color management system
 */

/* global module */

/**
 * Centralized color mapping system for note background colors
 */
const NoteColorUtils = {
  // Light colors mapped to user-friendly names
  colors: {
    "light-yellow": "#fff3cd",
    "light-blue": "#d1ecf1",
    "light-green": "#d4edda",
    "light-red": "#f8d7da",
    "light-purple": "#e2e3f3",
    "light-orange": "#ffeaa7",
    "light-gray": "#e9ecef",
    teal: "#a7f3d0",
  },

  /**
   * Get all available color options
   * @returns {Array<{name: string, value: string, displayName: string}>} Array of color options
   */
  getColorOptions() {
    return Object.entries(this.colors).map(([name, value]) => ({
      name,
      value,
      displayName: name.replace("-", " ").replace(/\b\w/g, l => l.toUpperCase()),
    }));
  },

  /**
   * Get background color value from color name
   * @param {string} colorName - Color name (e.g., 'light-blue')
   * @returns {string} Hex color value or default
   */
  getColorValue(colorName) {
    return this.colors[colorName] || this.colors["light-yellow"]; // Default to light yellow
  },

  /**
   * Validate if a color name exists
   * @param {string} colorName - Color name to validate
   * @returns {boolean} Whether color name is valid
   */
  isValidColor(colorName) {
    return Object.prototype.hasOwnProperty.call(this.colors, colorName);
  },

  /**
   * Get the default background color name
   * @returns {string} Default color name
   */
  getDefaultColor() {
    return "light-yellow";
  },

  /**
   * Validate and sanitize color values to prevent CSS injection
   * @param {string} color - Color value to validate
   * @returns {string} Safe color value or fallback
   */
  sanitizeColor(color) {
    if (!color || typeof color !== "string") {
      return "#fff3cd"; // Default light yellow
    }

    // Allow hex colors (3 or 6 digits)
    const hexPattern = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;
    if (hexPattern.test(color)) {
      return color;
    }

    // Allow rgb() values with basic validation
    const rgbPattern = /^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/;
    const rgbMatch = color.match(rgbPattern);
    if (rgbMatch) {
      const [, r, g, b] = rgbMatch;
      // Validate RGB values are within 0-255 range
      if (parseInt(r) <= 255 && parseInt(g) <= 255 && parseInt(b) <= 255) {
        return color;
      }
    }

    // Allow rgba() values with basic validation
    const rgbaPattern = /^rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*([01]?\.?\d*)\s*\)$/;
    const rgbaMatch = color.match(rgbaPattern);
    if (rgbaMatch) {
      const [, r, g, b, a] = rgbaMatch;
      // Validate RGB values are within 0-255 range and alpha is 0-1
      if (parseInt(r) <= 255 && parseInt(g) <= 255 && parseInt(b) <= 255 && parseFloat(a) <= 1) {
        return color;
      }
    }

    // Allow named colors (basic set for security)
    const namedColors = [
      "transparent",
      "white",
      "black",
      "red",
      "green",
      "blue",
      "yellow",
      "orange",
      "purple",
      "pink",
      "gray",
      "grey",
      "brown",
      "cyan",
      "magenta",
      "lime",
    ];
    if (namedColors.includes(color.toLowerCase())) {
      return color.toLowerCase();
    }

    console.warn(`[YAWN] Invalid color value: ${color}, using fallback`);
    return "#fff3cd"; // Fallback to default
  },
};

// Export for use in other scripts
if (typeof window !== "undefined") {
  window.NoteColorUtils = NoteColorUtils;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { NoteColorUtils };
}
