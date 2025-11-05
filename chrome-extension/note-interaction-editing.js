/**
 * Note Interaction & Editing
 * Functions for drag interactions, editing mode, and markdown toolbar
 */

/* global TIMING, EditingState, NoteDataUtils, NoteColorUtils */
/* global calculateNotePosition, ensureNoteVisibility, updateNoteOffset */
/* global updateNote, deleteNote, createCustomConfirmDialog, showTemporaryMessage */
/* global handleNoteDelete, handleNoteSharing */

/**
 * Update note cursor based on current state (edit mode vs drag mode)
 * @param {Element} noteElement - The note DOM element
 */
function updateNoteCursor(noteElement) {
  if (noteElement.classList.contains("editing")) {
    noteElement.style.cursor = "text";
  } else if (noteElement.classList.contains("dragging")) {
    noteElement.style.cursor = "grabbing";
  } else {
    noteElement.style.cursor = "move";
  }
}

/**
 * Add interactive hover and focus effects to a note element
 * @param {Element} noteElement - The note DOM element
 * @param {boolean} isAnchored - Whether the note is anchored to a DOM element
 */
function addInteractiveEffects(noteElement, isAnchored) {
  // Hover effects
  noteElement.addEventListener("mouseenter", () => {
    if (!noteElement.classList.contains("dragging") && !noteElement.classList.contains("editing")) {
      noteElement.style.transform = "scale(1.02) translateZ(0)";
      noteElement.style.boxShadow = "0 5px 20px rgba(0, 0, 0, 0.15), 0 2px 6px rgba(0, 0, 0, 0.1)";
      noteElement.style.borderColor = isAnchored ? "rgba(33, 150, 243, 0.4)" : "rgba(233, 30, 99, 0.4)";
    }
  });

  noteElement.addEventListener("mouseleave", () => {
    if (!noteElement.classList.contains("dragging") && !noteElement.classList.contains("editing")) {
      noteElement.style.transform = "scale(1) translateZ(0)";
      noteElement.style.boxShadow = "0 3px 12px rgba(0, 0, 0, 0.12), 0 1px 3px rgba(0, 0, 0, 0.08)";
      noteElement.style.borderColor = isAnchored ? "rgba(33, 150, 243, 0.2)" : "rgba(233, 30, 99, 0.2)";
    }
  });

  // Focus effects for accessibility
  noteElement.setAttribute("tabindex", "0");
  noteElement.setAttribute("role", "button");
  noteElement.setAttribute("aria-label", `Draggable note: ${noteElement.textContent}`);

  noteElement.addEventListener("focus", () => {
    noteElement.style.outline = `2px solid ${isAnchored ? "#2196F3" : "#E91E63"}`;
    noteElement.style.outlineOffset = "2px";
  });

  noteElement.addEventListener("blur", () => {
    noteElement.style.outline = "none";
    noteElement.style.outlineOffset = "0";
  });
}

/**
 * Make a note element draggable
 * @param {Element} noteElement - The note DOM element
 * @param {Object} noteData - The note data object
 * @param {Element|null} targetElement - The target element the note is anchored to
 */
function makeDraggable(noteElement, noteData, targetElement) {
  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let startOffsetX = noteData.offsetX || 0;
  let startOffsetY = noteData.offsetY || 0;

  function handleDragStart(e) {
    // CRITICAL: Prevent drag operations when note is in edit mode
    if (noteElement.classList.contains("editing")) {
      return; // Allow normal text selection and cursor behavior in edit mode
    }

    // Prevent default drag behavior and text selection
    e.preventDefault();
    e.stopPropagation();

    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    startOffsetX = noteData.offsetX || 0;
    startOffsetY = noteData.offsetY || 0;

    // Enhanced drag visual feedback
    noteElement.classList.add("dragging");
    updateNoteCursor(noteElement);
    noteElement.style.transform = "scale(1.05) rotateZ(2deg) translateZ(0)";
    noteElement.style.boxShadow = "0 8px 32px rgba(0, 0, 0, 0.24), 0 4px 8px rgba(0, 0, 0, 0.12)";
    noteElement.style.zIndex = "10001";
    noteElement.style.opacity = "0.9";
    noteElement.style.transition = "none"; // Disable transitions during drag

    // Add event listeners to document for smooth dragging
    // Note: { passive: false } is required on mousemove to allow preventDefault()
    // This prevents text selection and other default behaviors during drag
    // Performance impact: Disables scroll optimizations during drag operations
    document.addEventListener("mousemove", handleDragMove, { passive: false });
    document.addEventListener("mouseup", handleDragEnd, { once: true });
  }

  function handleDragMove(e) {
    if (!isDragging) return;

    e.preventDefault();
    e.stopPropagation();

    // Calculate new offset based on drag delta
    const deltaX = e.clientX - dragStartX;
    const deltaY = e.clientY - dragStartY;
    const newOffsetX = startOffsetX + deltaX;
    const newOffsetY = startOffsetY + deltaY;

    // Calculate and apply new position immediately (no restrictions)
    const newPosition = calculateNotePosition({ ...noteData, offsetX: newOffsetX, offsetY: newOffsetY }, targetElement);

    // Update visual position immediately
    noteElement.style.left = `${newPosition.x}px`;
    noteElement.style.top = `${newPosition.y}px`;

    // Update the working offset values for this session
    noteData.offsetX = newOffsetX;
    noteData.offsetY = newOffsetY;
  }

  function handleDragEnd(e) {
    if (!isDragging) return;

    e.preventDefault();
    e.stopPropagation();

    isDragging = false;

    // Restore normal styling with smooth transition
    noteElement.classList.remove("dragging");
    updateNoteCursor(noteElement);
    noteElement.style.transform = "scale(1) rotateZ(0deg) translateZ(0)";
    noteElement.style.boxShadow = "0 3px 12px rgba(0, 0, 0, 0.12), 0 1px 3px rgba(0, 0, 0, 0.08)";
    noteElement.style.zIndex = "10000";
    noteElement.style.opacity = "1";
    noteElement.style.transition = "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)"; // Re-enable transitions

    // Remove drag event listeners
    document.removeEventListener("mousemove", handleDragMove);

    // Save the final offset to storage
    updateNoteOffset(noteData.id, noteData.offsetX || 0, noteData.offsetY || 0);

    // Ensure note maintains minimum visibility after drag
    setTimeout(() => {
      ensureNoteVisibility(noteElement, noteData);
    }, TIMING.DOM_UPDATE_DELAY);

    const offset = `(${noteData.offsetX || 0}, ${noteData.offsetY || 0})`;
  }

  // Add mousedown event listener to start dragging
  noteElement.addEventListener("mousedown", handleDragStart);

  // Prevent text selection during potential drag (but allow it in edit mode)
  noteElement.addEventListener("selectstart", e => {
    if (!noteElement.classList.contains("editing")) {
      e.preventDefault();
    }
  });
}

/**
 * Add double-click editing capability to a note
 * @param {Element} noteElement - The note DOM element
 * @param {Object} noteData - The note data object
 */
function addEditingCapability(noteElement, noteData) {
  let clickTimeout = null;

  // Handle click events for double-click detection
  function handleNoteClick(event) {
    // Don't interfere with dragging
    if (noteElement.classList.contains("dragging")) {
      return;
    }

    event.stopPropagation();

    const now = Date.now();
    const timeDiff = now - EditingState.lastClickTime;

    if (EditingState.lastClickedNote === noteElement && timeDiff < TIMING.DOUBLE_CLICK_DELAY) {
      // Double-click detected - always use current data from element
      clearTimeout(clickTimeout);
      const currentNoteData = noteElement.noteData || noteData;
      enterEditMode(noteElement, currentNoteData);
    } else {
      // Single click - wait to see if there's a second click
      EditingState.lastClickTime = now;
      EditingState.lastClickedNote = noteElement;

      clickTimeout = setTimeout(() => {
        // Single click confirmed - do nothing for now
        EditingState.lastClickedNote = null;
      }, TIMING.DOUBLE_CLICK_DELAY);
    }
  }

  // Add click listener
  noteElement.addEventListener("click", handleNoteClick);

  // Prevent text selection during potential double-click
  noteElement.addEventListener("selectstart", e => {
    if (!noteElement.classList.contains("editing")) {
      e.preventDefault();
    }
  });
}

/**
 * Enter edit mode for a note
 * @param {Element} noteElement - The note DOM element
 * @param {Object} noteData - The note data object (may be stale, will use fresh data from element)
 */
function enterEditMode(noteElement, noteData) {
  // Exit any currently editing note
  if (EditingState.currentlyEditingNote && EditingState.currentlyEditingNote !== noteElement) {
    exitEditMode(EditingState.currentlyEditingNote, false);
  }

  EditingState.currentlyEditingNote = noteElement;
  noteElement.classList.add("editing");

  // CRITICAL FIX: Always use the most recent data from the DOM element
  // The noteData parameter may be stale from the original closure
  const currentNoteData = noteElement.noteData || noteData;
  const content = currentNoteData.content || "";

  // Create textarea for editing
  const textarea = document.createElement("textarea");
  textarea.className = "note-editor";
  textarea.value = content;

  // Style the textarea to match the note
  const noteStyles = window.getComputedStyle(noteElement);
  textarea.style.cssText = `
    width: ${noteStyles.width};
    height: 100%;
    border: none;
    background: transparent;
    font-family: ${noteStyles.fontFamily};
    font-size: ${noteStyles.fontSize};
    font-weight: ${noteStyles.fontWeight};
    line-height: ${noteStyles.lineHeight};
    letter-spacing: ${noteStyles.letterSpacing};
    color: ${noteStyles.color};
    padding: 0;
    margin: 0;
    resize: both;
    outline: none;
    max-width: calc(${noteStyles.maxWidth} - 20px);
    overflow: hidden;
  `;

  // Store original content for cancellation
  textarea.originalContent = content;

  // Create container for toolbar, textarea and delete button
  const editContainer = document.createElement("div");
  editContainer.style.cssText = `
    position: relative;
    width: 100%;
    height: 100%;
  `;

  // Create markdown toolbar
  const toolbar = createMarkdownToolbar(textarea);
  toolbar.className += " edit-toolbar";

  // Create delete button
  const deleteButton = document.createElement("button");
  deleteButton.className = "note-delete-button";
  deleteButton.innerHTML = "&times;";
  deleteButton.style.cssText = `
    position: absolute;
    top: -8px;
    right: -8px;
    width: 20px;
    height: 20px;
    background: #f44336;
    color: white;
    border: none;
    border-radius: 50%;
    font-size: 14px;
    font-weight: bold;
    cursor: pointer;
    z-index: 10002;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    transition: all 0.2s ease;
    line-height: 1;
    padding: 0;
  `;

  // Add hover effects to delete button
  deleteButton.addEventListener("mouseenter", () => {
    deleteButton.style.background = "#d32f2f";
    deleteButton.style.transform = "scale(1.1)";
    deleteButton.style.boxShadow = "0 3px 6px rgba(0, 0, 0, 0.3)";
  });

  deleteButton.addEventListener("mouseleave", () => {
    deleteButton.style.background = "#f44336";
    deleteButton.style.transform = "scale(1)";
    deleteButton.style.boxShadow = "0 2px 4px rgba(0, 0, 0, 0.2)";
  });

  // Add delete button click handler
  deleteButton.addEventListener("click", event => {
    event.preventDefault();
    event.stopPropagation();
    handleNoteDelete(noteElement, currentNoteData);
  });

  // Clear note content and add edit container
  noteElement.innerHTML = "";
  editContainer.appendChild(toolbar);
  editContainer.appendChild(textarea);
  editContainer.appendChild(deleteButton);
  noteElement.appendChild(editContainer);

  // Focus and select content
  textarea.focus();
  textarea.select();

  // Update cursor for edit mode
  updateNoteCursor(noteElement);

  // Add visual indicator for edit mode
  noteElement.style.borderColor = "#2196F3";
  noteElement.style.borderWidth = "2px";
  noteElement.style.borderStyle = "solid";

  // Auto-resize textarea
  function autoResize() {
    textarea.style.height = "auto";
    textarea.style.width = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
    textarea.style.width = textarea.scrollWidth + "px";
  }

  //textarea.addEventListener("input", autoResize);
  autoResize(); // Initial resize

  // Add keyboard shortcuts
  textarea.addEventListener("keydown", event => {
    handleEditKeydown(event, noteElement, currentNoteData, textarea);
  });

  // Auto-save functionality
  let saveTimeout;
  textarea.addEventListener("input", () => {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
      autoSaveNote(noteElement, currentNoteData, textarea.value);
    }, TIMING.AUTOSAVE_DELAY);
    EditingState.autosaveTimeouts.set(currentNoteData.id, saveTimeout);
  });

  // Click outside to save and exit
  function handleClickOutside(event) {
    if (!noteElement.contains(event.target)) {
      exitEditMode(noteElement, true);
      document.removeEventListener("click", handleClickOutside);
    }
  }

  // Add click outside listener after a brief delay to avoid immediate trigger
  setTimeout(() => {
    document.addEventListener("click", handleClickOutside);
  }, 100);
}

/**
 * Exit edit mode for a note
 * @param {Element} noteElement - The note DOM element
 * @param {boolean} save - Whether to save changes
 */
function exitEditMode(noteElement, save = true) {
  if (!noteElement.classList.contains("editing")) {
    return; // Not in edit mode
  }

  const textarea = noteElement.querySelector(".note-editor");
  if (!textarea) {
    return; // No textarea found
  }

  // Always use current data from element (may have been updated since edit mode started)
  const noteData = noteElement.noteData;
  if (!noteData) {
    return;
  }
  const newContent = save ? textarea.value : textarea.originalContent;

  // Clear any pending auto-save
  if (EditingState.autosaveTimeouts.has(noteData.id)) {
    clearTimeout(EditingState.autosaveTimeouts.get(noteData.id));
    EditingState.autosaveTimeouts.delete(noteData.id);
  }

  // Update note data and display
  if (save && newContent !== textarea.originalContent) {
    const updatedData = NoteDataUtils.createNoteData(noteData, newContent);
    // CRITICAL: Update the DOM element's data to ensure consistency
    noteElement.noteData = updatedData;

    // Save to storage
    updateNote(window.location.href, noteData.id, updatedData).then(success => {
      if (success) {
        console.log(`[YAWN] Note ${noteData.id} saved successfully`);
      } else {
        console.log(`[YAWN] Failed to save note ${noteData.id}`);
      }
    });
  }

  // Restore note display using the most current data
  const displayContent = NoteDataUtils.getDisplayContent(noteElement.noteData);
  noteElement.innerHTML = displayContent.html;

  // Restore styling
  noteElement.classList.remove("editing");
  updateNoteCursor(noteElement);
  noteElement.style.borderColor = "";
  noteElement.style.borderWidth = "";
  noteElement.style.borderStyle = "";

  // Clear editing state
  EditingState.currentlyEditingNote = null;
}

/**
 * Handle keyboard shortcuts during editing
 * @param {KeyboardEvent} event - The keyboard event
 * @param {Element} noteElement - The note DOM element
 * @param {Object} noteData - The note data object
 * @param {Element} textarea - The textarea element
 */
function handleEditKeydown(event, noteElement, noteData, textarea) {
  // Escape key - cancel and revert
  if (event.key === "Escape") {
    event.preventDefault();
    exitEditMode(noteElement, false);
    return;
  }

  // Ctrl+Enter or Cmd+Enter - save and exit
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    exitEditMode(noteElement, true);
    return;
  }

  // Tab for indentation (basic markdown support)
  if (event.key === "Tab") {
    event.preventDefault();
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;

    if (event.shiftKey) {
      // Shift+Tab - remove indentation
      const lineStart = value.lastIndexOf("\n", start - 1) + 1;
      const lineContent = value.substring(lineStart, start);
      if (lineContent.match(/^\s{1,2}/)) {
        textarea.value = value.substring(0, lineStart) + lineContent.replace(/^\s{1,2}/, "") + value.substring(start);
        // eslint-disable-next-line max-len
        textarea.setSelectionRange(
          start - Math.min(2, lineContent.match(/^\s*/)[0].length),
          end - Math.min(2, lineContent.match(/^\s*/)[0].length),
        );
      }
    } else {
      // Tab - add indentation
      textarea.value = value.substring(0, start) + "  " + value.substring(end);
      textarea.setSelectionRange(start + 2, end + 2);
    }

    // Trigger auto-resize
    textarea.dispatchEvent(new Event("input"));
  }

  // Ctrl+B for bold (basic markdown shortcut)
  if ((event.ctrlKey || event.metaKey) && event.key === "b") {
    event.preventDefault();
    insertMarkdownSyntax(textarea, "**", "**");
  }

  // Ctrl+I for italic (basic markdown shortcut)
  if ((event.ctrlKey || event.metaKey) && event.key === "i") {
    event.preventDefault();
    insertMarkdownSyntax(textarea, "*", "*");
  }
}

/**
 * Create a markdown toolbar for the editing interface
 * @param {Element} textarea - The textarea element to control
 * @returns {Element} The toolbar element
 */
function createMarkdownToolbar(textarea) {
  const toolbar = document.createElement("div");
  toolbar.className = "markdown-toolbar";
  toolbar.style.cssText = `
    display: flex;
    flex-wrap: nowrap;
    gap: 2px;
    padding: 4px;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-radius: 4px;
    border: 0.5px solid rgba(0, 0, 0, 0.08);
    margin-bottom: 4px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    width: max-content;
  `;

  // Define toolbar buttons with their configurations
  const toolbarButtons = [
    {
      title: "Bold",
      icon: "B",
      style: "font-weight: bold;",
      action: () => insertMarkdownSyntax(textarea, "**", "**"),
    },
    {
      title: "Italic",
      icon: "I",
      style: "font-style: italic;",
      action: () => insertMarkdownSyntax(textarea, "*", "*"),
    },
    {
      title: "Header 1",
      icon: "H1",
      style: "font-size: 12px; font-weight: bold;",
      action: () => insertLinePrefix(textarea, "# "),
    },
    {
      title: "Header 2",
      icon: "H2",
      style: "font-size: 11px; font-weight: bold;",
      action: () => insertLinePrefix(textarea, "## "),
    },
    {
      title: "Header 3",
      icon: "H3",
      style: "font-size: 10px; font-weight: bold;",
      action: () => insertLinePrefix(textarea, "### "),
    },
    {
      title: "Link",
      icon: "🔗",
      style: "",
      action: () => insertMarkdownLink(textarea),
    },
    {
      title: "Unordered List",
      icon: "•",
      style: "font-weight: bold;",
      action: () => insertLinePrefix(textarea, "- "),
    },
    {
      title: "Ordered List",
      icon: "1.",
      style: "font-size: 11px; font-weight: bold;",
      action: () => insertOrderedListItem(textarea),
    },
    {
      title: "Inline Code",
      icon: "<>",
      style: "font-family: monospace; font-size: 11px;",
      action: () => insertMarkdownSyntax(textarea, "`", "`"),
    },
    {
      title: "Quote",
      icon: '"',
      style: "font-weight: bold; font-size: 14px;",
      action: () => insertLinePrefix(textarea, "> "),
    },
    {
      title: "Strikethrough",
      icon: "S",
      style: "text-decoration: line-through;",
      action: () => insertMarkdownSyntax(textarea, "~~", "~~"),
    },
  ];

  // Add sharing button if SharingInterface is available
  // Auth check will happen when button is clicked
  if (typeof SharingInterface !== "undefined") {
    toolbarButtons.push({
      title: "Share this note",
      icon: "🔗",
      style: "font-size: 10px;",
      action: () => handleNoteSharing(textarea),
    });
  }

  // Create buttons
  toolbarButtons.forEach(buttonConfig => {
    const button = document.createElement("button");
    button.className = "toolbar-button";
    button.title = buttonConfig.title;
    button.innerHTML = buttonConfig.icon;

    button.style.cssText = `
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 14px;
      height: 14px;
      border: 0.5px solid rgba(0, 0, 0, 0.12);
      background: linear-gradient(135deg, #ffffff 0%, #f0f2f5 100%);
      color: #333;
      border-radius: 2px;
      cursor: pointer;
      font-size: 8px;
      padding: 0;
      transition: all 0.2s ease;
      user-select: none;
      ${buttonConfig.style}
    `;

    // Add hover and active effects
    button.addEventListener("mouseenter", () => {
      button.style.background = "linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)";
      button.style.borderColor = "#2196F3";
      button.style.transform = "translateY(-1px)";
      button.style.boxShadow = "0 2px 4px rgba(0, 0, 0, 0.15)";
    });

    button.addEventListener("mouseleave", () => {
      button.style.background = "linear-gradient(135deg, #ffffff 0%, #f0f2f5 100%)";
      button.style.borderColor = "rgba(0, 0, 0, 0.15)";
      button.style.transform = "translateY(0)";
      button.style.boxShadow = "none";
    });

    button.addEventListener("mousedown", () => {
      button.style.transform = "translateY(1px)";
    });

    button.addEventListener("mouseup", () => {
      button.style.transform = "translateY(-1px)";
    });

    // Add click handler
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      buttonConfig.action();

      // Maintain focus on textarea
      setTimeout(() => {
        textarea.focus();
      }, 0);
    });

    toolbar.appendChild(button);
  });

  // Add color dropdown if the function is available
  if (typeof createColorDropdown === "function") {
    try {
      const colorDropdown = createColorDropdown(textarea);
      toolbar.appendChild(colorDropdown);
    } catch (error) {
      console.log("[YAWN] Error adding color dropdown to toolbar:", error);
    }
  }

  return toolbar;
}

/**
 * Insert markdown syntax around selected text
 * @param {Element} textarea - The textarea element
 * @param {string} before - Text to insert before selection
 * @param {string} after - Text to insert after selection
 */
function insertMarkdownSyntax(textarea, before, after) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const selectedText = textarea.value.substring(start, end);
  const replacement = before + selectedText + after;

  textarea.value = textarea.value.substring(0, start) + replacement + textarea.value.substring(end);

  // Position cursor
  if (selectedText) {
    textarea.setSelectionRange(start, start + replacement.length);
  } else {
    textarea.setSelectionRange(start + before.length, start + before.length);
  }

  // Trigger auto-resize and change events
  textarea.dispatchEvent(new Event("input"));
  textarea.focus();
}

/**
 * Insert prefix at the beginning of the current line
 * @param {Element} textarea - The textarea element
 * @param {string} prefix - The prefix to insert
 */
function insertLinePrefix(textarea, prefix) {
  const start = textarea.selectionStart;
  const value = textarea.value;

  // Find the beginning of the current line
  const lineStart = value.lastIndexOf("\n", start - 1) + 1;
  const lineEnd = value.indexOf("\n", start);
  const actualLineEnd = lineEnd === -1 ? value.length : lineEnd;
  const currentLine = value.substring(lineStart, actualLineEnd);

  // Check if the line already has this prefix
  if (currentLine.startsWith(prefix)) {
    // Remove the prefix
    const newLine = currentLine.substring(prefix.length);
    textarea.value = value.substring(0, lineStart) + newLine + value.substring(actualLineEnd);
    textarea.setSelectionRange(start - prefix.length, start - prefix.length);
  } else {
    // Add the prefix
    const newLine = prefix + currentLine;
    textarea.value = value.substring(0, lineStart) + newLine + value.substring(actualLineEnd);
    textarea.setSelectionRange(start + prefix.length, start + prefix.length);
  }

  // Trigger auto-resize and change events
  textarea.dispatchEvent(new Event("input"));
  textarea.focus();
}

/**
 * Insert an ordered list item with proper numbering
 * @param {Element} textarea - The textarea element
 */
function insertOrderedListItem(textarea) {
  const start = textarea.selectionStart;
  const value = textarea.value;

  // Find the beginning of the current line
  const lineStart = value.lastIndexOf("\n", start - 1) + 1;
  const lineEnd = value.indexOf("\n", start);
  const actualLineEnd = lineEnd === -1 ? value.length : lineEnd;
  const currentLine = value.substring(lineStart, actualLineEnd);

  // Check if there's already a numbered list item
  const listItemMatch = currentLine.match(/^(\d+)\.\s/);
  if (listItemMatch) {
    // Remove the numbering
    const newLine = currentLine.substring(listItemMatch[0].length);
    textarea.value = value.substring(0, lineStart) + newLine + value.substring(actualLineEnd);
    textarea.setSelectionRange(start - listItemMatch[0].length, start - listItemMatch[0].length);
  } else {
    // Look for the previous line to determine the number
    let number = 1;
    const prevLineEnd = lineStart - 1;
    if (prevLineEnd > 0) {
      const prevLineStart = value.lastIndexOf("\n", prevLineEnd - 1) + 1;
      const prevLine = value.substring(prevLineStart, prevLineEnd);
      const prevMatch = prevLine.match(/^(\d+)\.\s/);
      if (prevMatch) {
        number = parseInt(prevMatch[1]) + 1;
      }
    }

    // Add the numbered prefix
    const prefix = `${number}. `;
    const newLine = prefix + currentLine;
    textarea.value = value.substring(0, lineStart) + newLine + value.substring(actualLineEnd);
    textarea.setSelectionRange(start + prefix.length, start + prefix.length);
  }

  // Trigger auto-resize and change events
  textarea.dispatchEvent(new Event("input"));
  textarea.focus();
}

/**
 * Insert a markdown link with placeholder text
 * @param {Element} textarea - The textarea element
 */
function insertMarkdownLink(textarea) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const selectedText = textarea.value.substring(start, end);

  let linkText, linkUrl, replacement;

  if (selectedText) {
    // If text is selected, use it as the link text
    linkText = selectedText;
    linkUrl = "url";
    replacement = `[${linkText}](${linkUrl})`;
  } else {
    // No selection, insert template
    linkText = "link text";
    linkUrl = "url";
    replacement = `[${linkText}](${linkUrl})`;
  }

  textarea.value = textarea.value.substring(0, start) + replacement + textarea.value.substring(end);

  // Select the URL part for easy editing
  const urlStart = start + linkText.length + 3; // [link text](
  const urlEnd = urlStart + linkUrl.length;
  textarea.setSelectionRange(urlStart, urlEnd);

  // Trigger auto-resize and change events
  textarea.dispatchEvent(new Event("input"));
  textarea.focus();
}
