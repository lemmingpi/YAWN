# YAWN User Guide
**Yet Another Web Notes App - Sticky Notes for Web Pages**

## Table of Contents
1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [Creating Notes](#creating-notes)
4. [Storage Options: Local vs Sync](#storage-options-local-vs-sync)
5. [Editing Notes](#editing-notes)
6. [Managing Notes](#managing-notes)

---

## Installation

### Installing the Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer Mode** (toggle in top-right corner)
3. Click **Load unpacked**
4. Select the `chrome-extension` folder from this project
5. (Optional) Pin the extension by clicking the puzzle icon and pinning "YAWN"

---

## Getting Started

### First Launch

After installing the extension, you'll see the YAWN icon (🗒️) in your Chrome toolbar. Click it to open the popup interface where you can:
- Configure storage options (Local, Chrome Sync, or Server Sync)
- Sign in with Google (for server sync)
- View storage statistics

**By default, notes are stored locally on your device** - no sign-in required!

---

## Creating Notes

### Method 1: Right-Click Context Menu

1. Navigate to any webpage
2. **Right-click** anywhere on the page
3. Select **"🗒️ Add Web Note"** from the context menu
4. A sticky note will appear at your cursor position
5. Start typing to add your note content

### Method 2: Creating Notes from Selected Text

1. **Select text** on any webpage
2. **Right-click** the selected text
3. Choose **"🗒️ Add Web Note"**
4. A note will be created with the selected text highlighted on the page

### Note Features

Each note includes:
- **Drag-and-drop repositioning** - Click and drag the note title bar
- **Color customization** - Click the color button to choose from multiple colors
- **Rich text editing** - Support for formatting and markdown
- **Delete button** - Remove notes you no longer need
- **Automatic persistence** - Notes are saved automatically as you type

---

## Storage Options: Local vs Sync

YAWN offers three storage modes. Choose the one that fits your workflow:

### 1. Local Storage (Default)
- **How it works**: Notes are stored only on your current device/browser
- **Best for**: Quick personal notes, privacy-focused usage
- **Setup**: No setup required - works out of the box!
- **Limitation**: Notes won't sync to other devices or browsers

### 2. Chrome Sync Storage
- **How it works**: Notes sync across all your Chrome browsers where you're signed in to Chrome
- **Best for**: Users who want sync without creating an account
- **Setup**:
  1. Click the YAWN extension icon
  2. Check "Sync notes using Chrome Sync (no server needed)"
- **Limitation**: Only works within Chrome ecosystem

### 3. Server Sync (Cloud Storage)
- **How it works**: Notes are stored on a cloud server and sync across any browser
- **Best for**: Multi-browser usage, sharing notes with others
- **Setup**:
  1. Click the YAWN extension icon
  2. Enter the server URL (if not already configured)
  3. Click **"Sign In with Google"**
  4. Grant necessary permissions
- **Benefits**:
  - Access notes from any browser
  - Share pages/sites with other users
  - Backup and recovery

### Switching Between Storage Modes

You can migrate notes between storage modes:
1. Open the YAWN popup (click extension icon)
2. Sign in if using server sync
3. Use the **Data Sync** section:
   - **"Copy Server Notes to Local"** - Download cloud notes to local storage
   - **"Copy Local Notes to Server"** - Upload local notes to cloud

**Note**: These are copy operations, not moves. The original notes remain in their source location.

---

## Editing Notes

### Text Editing

Notes support rich text editing with markdown syntax. Click inside any note to start editing.

**For full markdown syntax reference**, see: [Markdown Guide](https://www.markdownguide.org/basic-syntax/)

### Common Markdown Examples

```markdown
**bold text**
*italic text*
# Heading 1
## Heading 2
- Bullet point
1. Numbered list
[link text](https://example.com)
```

### Customizing Note Appearance

- **Change color**: Click the color picker button in the note toolbar
- **Resize**: Drag the note edges (if supported by your note type)
- **Move**: Click and drag the note's title bar to reposition

---

## Managing Notes

### Deleting Notes

Click the **delete button** (usually an X or trash icon) on the note you want to remove.

### Viewing Your Notes

Notes are:
- **Page-specific**: Notes appear on the specific page where you created them
- **Persistent**: Return to the same URL to see your notes again
- **Organized**: The popup shows storage statistics for all your notes

### Sharing (Server Sync Only)

If you're using server sync, you can share your notes:

1. Sign in to the server
2. Click the YAWN extension icon
3. Use the **Sharing** section:
   - **Share Page** - Share all notes on the current page
   - **Share Site** - Share all notes across the entire website
   - **Manage Shares** - View and manage who has access

---

## Tips & Tricks

- **Selected text notes**: Highlight text before creating a note to automatically capture and highlight that text
- **Keyboard shortcuts**: Edit notes like any text field (Ctrl+B for bold, etc.)
- **Quick access**: Pin the extension for one-click access to settings
- **Storage stats**: Check the popup to see how many notes you've created
- **Cross-device**: Use server sync to access notes from work, home, and mobile browsers

---

## Troubleshooting

### Notes not appearing?
- Ensure you're on the exact same URL where you created them
- Check your storage mode - local notes won't appear on other devices

### Sync not working?
- Verify you're signed in (check the popup)
- Ensure server URL is configured correctly
- Check your internet connection

### Extension not loading?
- Reload the extension from `chrome://extensions/`
- Check that all files are present in the extension folder
- Look for error messages in the Chrome console (F12)

---

## Privacy & Data

- **Local mode**: Your notes never leave your device
- **Chrome Sync**: Notes are encrypted and synced via Google's Chrome sync
- **Server sync**: Notes are stored on the configured server - review the server's privacy policy

---

## Support & Feedback

For issues, feature requests, or contributions:
- GitHub: [https://github.com/gpalumbo/notes](https://github.com/gpalumbo/notes)

---

**Happy note-taking!** 🗒️
