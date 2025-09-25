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
    "teal": "#a7f3d0",
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
};

// Export for use in other scripts
if (typeof window !== "undefined") {
  window.NoteColorUtils = NoteColorUtils;
}

// Node.js compatibility
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    NoteColorUtils,
  };
}