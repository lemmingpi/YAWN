/**
 * Note Positioning & Layout
 * Functions for positioning, repositioning, and calculating note locations
 */

/* global TIMING, tryBothSelectors, getNotes, getNotesForUrl, findMatchingUrlsInStorage, setNotes */

/**
 * Debounce utility to limit function execution frequency
 * @param {Function} func - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, delay) {
  let timeoutId;
  return function (...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
}

/**
 * Ensure a note is accessible by repositioning if it's outside page boundaries
 * Only repositions notes that are truly inaccessible (beyond scrollable area)
 * @param {Element} noteElement - The note DOM element
 * @param {Object} noteData - The note data object
 * @returns {boolean} True if note was repositioned
 */
function ensureNoteVisibility(noteElement, noteData) {
  const noteRect = noteElement.getBoundingClientRect();
  const noteX = noteRect.left + window.scrollX;
  const noteY = noteRect.top + window.scrollY;

  // Get page dimensions (scrollable area)
  const pageWidth = document.documentElement.scrollWidth;
  const pageHeight = document.documentElement.scrollHeight;
  const minVisible = 50; // Minimum pixels that must be visible on page

  let newX = noteX;
  let newY = noteY;
  let wasRepositioned = false;

  // Only reposition if note is outside the scrollable page boundaries
  // (not just outside the current viewport)

  if (noteX + noteRect.width < 0) {
    // Note is completely off the left edge of the page
    newX = minVisible;
    wasRepositioned = true;
  } else if (noteX > pageWidth) {
    // Note is completely off the right edge of the page
    newX = pageWidth - noteRect.width - minVisible;
    wasRepositioned = true;
  }

  if (noteY + noteRect.height < 0) {
    // Note is completely off the top edge of the page
    newY = minVisible;
    wasRepositioned = true;
  } else if (noteY > pageHeight) {
    // Note is completely off the bottom edge of the page
    newY = pageHeight - noteRect.height - minVisible;
    wasRepositioned = true;
  }

  if (wasRepositioned) {
    // Update note position
    noteElement.style.left = `${newX}px`;
    noteElement.style.top = `${newY}px`;

    // Update stored offset based on note type
    if (noteData.elementSelector || noteData.elementXPath) {
      // For anchored notes, calculate new offset from target element
      const selectorResults = tryBothSelectors(noteData, `${noteData.elementSelector || ""}-${noteData.elementXPath || ""}`);
      const targetElement = selectorResults.element;

      if (targetElement) {
        const rect = targetElement.getBoundingClientRect();
        const elementX = rect.left + window.scrollX;
        const elementY = rect.top + window.scrollY - 30;

        const newOffsetX = newX - elementX;
        const newOffsetY = newY - elementY;

        updateNoteOffset(noteData.id, newOffsetX, newOffsetY);
        noteData.offsetX = newOffsetX;
        noteData.offsetY = newOffsetY;
      }
    } else {
      // For fallback notes, update fallback position
      noteData.fallbackPosition.x = newX;
      noteData.fallbackPosition.y = newY;
    }
  }

  return wasRepositioned;
}

/**
 * Reposition all existing notes after window resize
 */
function repositionAllNotes() {
  const notes = document.querySelectorAll(".web-note");

  if (notes.length === 0) {
    return;
  }

  // Batch storage operation - fetch all notes once
  getNotes().then(function (result) {
    if (chrome.runtime.lastError) {
      return;
    }

    const allNotes = result || {};
    const urlNotes = getNotesForUrl(window.location.href, allNotes);

    notes.forEach(noteElement => {
      const noteId = noteElement.id;

      // Find the note data
      const noteData = urlNotes.find(note => note.id === noteId);
      if (!noteData) {
        return;
      }

      // Find target element if note is anchored
      let targetElement = null;
      if (noteData.elementSelector || noteData.elementXPath) {
        const selectorResults = tryBothSelectors(
          noteData,
          `${noteData.elementSelector || ""}-${noteData.elementXPath || ""}`,
        );
        targetElement = selectorResults.element;
      }

      // Recalculate position
      const newPosition = calculateNotePosition(noteData, targetElement);

      // Update note position with smooth transition
      noteElement.style.left = `${newPosition.x}px`;
      noteElement.style.top = `${newPosition.y}px`;
    });

    // Ensure all notes have minimum visibility after repositioning
    setTimeout(() => {
      ensureAllNotesVisibleBatched(allNotes, urlNotes);
    }, TIMING.DOM_UPDATE_DELAY);
  });
}

/**
 * Handle window resize events
 */
function handleWindowResize() {
  repositionAllNotes();
}

/**
 * Batched version of ensureAllNotesVisible that uses pre-fetched data
 * @param {Object} allNotes - All notes from storage
 * @param {Array} urlNotes - Notes for current URL
 */
function ensureAllNotesVisibleBatched(allNotes, urlNotes) {
  const notes = document.querySelectorAll(".web-note");
  let notesRepositioned = 0;

  notes.forEach((noteElement, index) => {
    const noteData = urlNotes.find(note => note.id === noteElement.id);

    if (noteData) {
      const wasRepositioned = ensureNoteVisibility(noteElement, noteData);
      if (wasRepositioned) {
        notesRepositioned++;
      }
    } else {
      console.warn(`[YAWN] Note data not found for ${noteElement.id}`);
    }
  });
}

/**
 * Calculate note position based on target element or fallback coordinates with offset
 * Notes can be positioned anywhere including off-screen - no restrictions applied
 * @param {Object} noteData - The note data object
 * @param {Element|null} targetElement - The target DOM element (if found)
 * @returns {Object} Position object with x, y coordinates and anchoring status
 */
function calculateNotePosition(noteData, targetElement) {
  const offsetX = noteData.offsetX || 0;
  const offsetY = noteData.offsetY || 0;

  if (targetElement) {
    // Position relative to found DOM element with offset
    const rect = targetElement.getBoundingClientRect();
    return {
      x: rect.left + window.scrollX + offsetX,
      y: rect.top + window.scrollY - 30 + offsetY,
      isAnchored: true,
    };
  } else {
    // Use fallback position with offset
    return {
      x: noteData.fallbackPosition.x + offsetX,
      y: noteData.fallbackPosition.y + offsetY,
      isAnchored: false,
    };
  }
}

/**
 * Update note offset in storage with enhanced URL matching
 * @param {string} noteId - The note ID
 * @param {number} newOffsetX - New X offset
 * @param {number} newOffsetY - New Y offset
 */
function updateNoteOffset(noteId, newOffsetX, newOffsetY) {
  try {
    getNotes().then(function (result) {
      if (chrome.runtime.lastError) {
        return;
      }

      const notes = result || {};
      const matchingUrls = findMatchingUrlsInStorage(window.location.href, notes);
      let noteFound = false;

      // Find and update the specific note in any of the matching URLs
      for (const matchingUrl of matchingUrls) {
        const urlNotes = notes[matchingUrl] || [];
        const noteIndex = urlNotes.findIndex(note => note.id === noteId);

        if (noteIndex !== -1) {
          urlNotes[noteIndex].offsetX = newOffsetX;
          urlNotes[noteIndex].offsetY = newOffsetY;

          // Save back to storage
          notes[matchingUrl] = urlNotes;
          setNotes(notes, matchingUrl).then(function () {
            if (chrome.runtime.lastError) {
              console.log("[YAWN] Failed to save note offset:", chrome.runtime.lastError);
            }
          });
          noteFound = true;
          break;
        }
      }

      if (!noteFound) {
        console.log(`[YAWN] Note ${noteId} not found for offset update`);
      }
    });
  } catch (error) {
    console.log("[YAWN] Error updating note offset:", error);
  }
}
