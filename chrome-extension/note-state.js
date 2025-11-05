/**
 * Note State & Constants
 * Global state and timing constants for note functionality
 */

// Timing constants for better maintainability
const TIMING = {
  DOM_UPDATE_DELAY: 100, // Time to allow DOM updates to complete
  FADE_ANIMATION_DELAY: 250, // Time for fade-in animation to complete
  RESIZE_DEBOUNCE: 300, // Debounce delay for resize events
  URL_MONITOR_INTERVAL: 2000, // Interval for URL change monitoring (2 seconds)
  AUTOSAVE_DELAY: 1000, // Auto-save delay during editing (1 second)
  DOUBLE_CLICK_DELAY: 300, // Max time between clicks for double-click (300ms)
};

// Editing state management
const EditingState = {
  currentlyEditingNote: null,
  lastClickTime: 0,
  lastClickedNote: null,
  autosaveTimeouts: new Map(), // Map of noteId -> timeout
};

// Map to store highlighting elements by note ID
const noteHighlights = new Map();
const MAX_HIGHLIGHTS = 1000;
const MAX_SELECTION_LENGTH = 50000;

// Store the last right-click coordinates for note positioning
let lastRightClickCoords = null;

// Cache for DOM queries to improve performance
const elementCache = new Map();
