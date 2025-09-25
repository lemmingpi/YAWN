/**
 * Color dropdown functionality for Web Notes Chrome Extension
 * Creates and manages the color selection dropdown in the edit toolbar
 */

/* global NoteColorUtils, updateNote */

/**
 * Create a color dropdown button for the toolbar
 * @param {Element} textarea - The textarea element (for focusing after color selection)
 * @returns {Element} The color dropdown container element
 */
function createColorDropdown(textarea) {
  try {
    // Create the main dropdown container
    const dropdownContainer = document.createElement("div");
    dropdownContainer.className = "color-dropdown-container";
    dropdownContainer.style.cssText = `
      position: relative;
      display: inline-block;
    `;

    // Create the dropdown button (matches existing toolbar button styling)
    const dropdownButton = document.createElement("button");
    dropdownButton.className = "toolbar-button color-dropdown-button";
    dropdownButton.title = "Background Color";
    dropdownButton.textContent = "🎨";

    dropdownButton.style.cssText = `
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
    `;

    // Create the dropdown menu (initially hidden)
    const dropdownMenu = document.createElement("div");
    dropdownMenu.className = "color-dropdown-menu";
    dropdownMenu.style.cssText = `
      position: absolute;
      top: 100%;
      left: 0;
      background: white;
      border: 1px solid #ddd;
      border-radius: 4px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      padding: 4px;
      display: none;
      z-index: 10003;
      min-width: 120px;
      grid-template-columns: repeat(2, 1fr);
      gap: 2px;
    `;

    // Get available colors from NoteColorUtils
    const colorOptions = NoteColorUtils.getColorOptions();

    // Create color option buttons
    colorOptions.forEach(colorOption => {
      const colorButton = document.createElement("button");
      colorButton.className = "color-option";
      colorButton.title = colorOption.displayName;
      colorButton.setAttribute("data-color-name", colorOption.name);

      colorButton.style.cssText = `
        width: 20px;
        height: 20px;
        border: 1px solid #ccc;
        border-radius: 3px;
        cursor: pointer;
        background: ${colorOption.value};
        margin: 1px;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
      `;

      // Add hover effects
      colorButton.addEventListener("mouseenter", () => {
        colorButton.style.transform = "scale(1.1)";
        colorButton.style.borderColor = "#666";
        colorButton.style.boxShadow = "0 2px 4px rgba(0, 0, 0, 0.2)";
      });

      colorButton.addEventListener("mouseleave", () => {
        colorButton.style.transform = "scale(1)";
        colorButton.style.borderColor = "#ccc";
        colorButton.style.boxShadow = "none";
      });

      // Add click handler for color selection
      colorButton.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        handleColorSelection(colorOption.name, textarea);
        hideColorDropdown(dropdownMenu);
      });

      dropdownMenu.appendChild(colorButton);
    });

    // Set grid display after adding all color buttons
    dropdownMenu.style.display = "none";
    setTimeout(() => {
      dropdownMenu.style.display = "grid";
      dropdownMenu.style.display = "none"; // Hide initially
    }, 0);

    // Add button hover effects (matching existing toolbar buttons)
    dropdownButton.addEventListener("mouseenter", () => {
      dropdownButton.style.background = "linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)";
      dropdownButton.style.borderColor = "#2196F3";
      dropdownButton.style.transform = "translateY(-1px)";
      dropdownButton.style.boxShadow = "0 2px 4px rgba(0, 0, 0, 0.15)";
    });

    dropdownButton.addEventListener("mouseleave", () => {
      dropdownButton.style.background = "linear-gradient(135deg, #ffffff 0%, #f0f2f5 100%)";
      dropdownButton.style.borderColor = "rgba(0, 0, 0, 0.15)";
      dropdownButton.style.transform = "translateY(0)";
      dropdownButton.style.boxShadow = "none";
    });

    dropdownButton.addEventListener("mousedown", () => {
      dropdownButton.style.transform = "translateY(1px)";
    });

    dropdownButton.addEventListener("mouseup", () => {
      dropdownButton.style.transform = "translateY(-1px)";
    });

    // Toggle dropdown on button click
    dropdownButton.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleColorDropdown(dropdownMenu);

      // Maintain focus on textarea after interaction
      setTimeout(() => {
        textarea.focus();
      }, 0);
    });

    // Assemble the dropdown
    dropdownContainer.appendChild(dropdownButton);
    dropdownContainer.appendChild(dropdownMenu);

    // Store reference to menu for outside click handling
    dropdownContainer.dropdownMenu = dropdownMenu;

    return dropdownContainer;
  } catch (error) {
    console.error("[Web Notes] Error creating color dropdown:", error);
    return document.createElement("div"); // Return empty div as fallback
  }
}

/**
 * Toggle the visibility of the color dropdown menu
 * @param {Element} dropdownMenu - The dropdown menu element
 */
function toggleColorDropdown(dropdownMenu) {
  try {
    const isVisible = dropdownMenu.style.display === "grid";

    if (isVisible) {
      hideColorDropdown(dropdownMenu);
    } else {
      showColorDropdown(dropdownMenu);
    }
  } catch (error) {
    console.error("[Web Notes] Error toggling color dropdown:", error);
  }
}

/**
 * Show the color dropdown menu
 * @param {Element} dropdownMenu - The dropdown menu element
 */
function showColorDropdown(dropdownMenu) {
  try {
    // Hide any other open dropdowns first
    document.querySelectorAll(".color-dropdown-menu").forEach(menu => {
      if (menu !== dropdownMenu) {
        hideColorDropdown(menu);
      }
    });

    dropdownMenu.style.display = "grid";

    // Add click outside handler
    setTimeout(() => {
      document.addEventListener("click", handleClickOutsideColorDropdown);
    }, 0);
  } catch (error) {
    console.error("[Web Notes] Error showing color dropdown:", error);
  }
}

/**
 * Hide the color dropdown menu
 * @param {Element} dropdownMenu - The dropdown menu element
 */
function hideColorDropdown(dropdownMenu) {
  try {
    dropdownMenu.style.display = "none";
    document.removeEventListener("click", handleClickOutsideColorDropdown);
  } catch (error) {
    console.error("[Web Notes] Error hiding color dropdown:", error);
  }
}

/**
 * Handle clicks outside the color dropdown to close it
 * @param {Event} event - The click event
 */
function handleClickOutsideColorDropdown(event) {
  try {
    const isClickInsideDropdown = event.target.closest(".color-dropdown-container");

    if (!isClickInsideDropdown) {
      // Close all open color dropdowns
      document.querySelectorAll(".color-dropdown-menu").forEach(menu => {
        hideColorDropdown(menu);
      });
    }
  } catch (error) {
    console.error("[Web Notes] Error handling outside click:", error);
  }
}

/**
 * Handle color selection from the dropdown
 * @param {string} colorName - The selected color name
 * @param {Element} textarea - The textarea element to focus
 */
function handleColorSelection(colorName, textarea) {
  try {
    console.log(`[Web Notes] Color selected: ${colorName}`);

    // Get the current note element from the textarea's context
    const noteElement = textarea.closest(".web-note");
    if (!noteElement || !noteElement.noteData) {
      console.error("[Web Notes] Could not find note element or note data for color change");
      return;
    }

    const noteData = noteElement.noteData;

    // Update the note's background color in data
    const updatedNoteData = {
      ...noteData,
      backgroundColor: colorName,
    };

    // Update the DOM element's data
    noteElement.noteData = updatedNoteData;

    // Apply the color immediately to the note element (without animation for immediate feedback)
    const colorValue = NoteColorUtils.getColorValue(colorName);
    noteElement.style.background = colorValue;

    console.log(`[Web Notes] Applied background color ${colorName} (${colorValue}) to note ${noteData.id}`);

    // Save to storage
    updateNote(window.location.href, noteData.id, updatedNoteData).then(success => {
      if (success) {
        console.log(`[Web Notes] Note ${noteData.id} color saved successfully`);
      } else {
        console.error(`[Web Notes] Failed to save note ${noteData.id} color`);
      }
    });

    // Maintain focus on textarea
    setTimeout(() => {
      textarea.focus();
    }, 0);

  } catch (error) {
    console.error("[Web Notes] Error handling color selection:", error);
  }
}

// Export for use in content.js (if needed)
if (typeof window !== "undefined") {
  window.createColorDropdown = createColorDropdown;
}