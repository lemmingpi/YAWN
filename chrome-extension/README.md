# Web Notes Hello World Chrome Extension

This is a hello world Chrome extension for the Web Notes project. It demonstrates basic extension functionality before implementing the full notes features.

## Installation Instructions

1. **Open Chrome** and navigate to `chrome://extensions/`

2. **Enable Developer Mode** by toggling the switch in the top-right corner

3. **Load Unpacked Extension**:
   - Click "Load unpacked" button
   - Navigate to and select the `chrome-extension` folder in this project
   - The extension should now appear in your extensions list

4. **Pin the Extension** (optional but recommended):
   - Click the puzzle piece icon in Chrome toolbar
   - Find "Web Notes - Hello World" and click the pin icon

## Testing the Extension

### Context Menu Test (Primary Feature)
1. Navigate to any website (e.g., `https://google.com`)
2. **Right-click anywhere on the page**
3. Look for "🗒️ Show Web Notes Banner" in the context menu
4. Click it to show the banner
5. Click the banner message to see an alert
6. Click the "×" to close the banner
7. Try right-clicking again - if banner exists, it will pulse instead of creating a new one

### Popup Interface Test
1. Click the extension icon in the Chrome toolbar (🗒️)
2. A popup should appear with:
   - Web Notes branding
   - Version information
   - "Show Banner", "Hide Banner", and "Clear Stats" buttons
   - Local storage stats display
   - Feature preview list

3. Test the popup buttons:
   - **Show Banner**: Creates a banner that says "Web Notes - Popup Triggered!"
   - **Hide Banner**: Removes any visible banner with animation
   - **Clear Stats**: Resets all stored statistics

### Local Storage Functionality Test
**What's stored**: Install date, banner show count, context menu click count, popup open count, last seen timestamp

**How to test**:
1. Open popup - "Popup opens" count increases
2. Right-click → "Show Web Notes Banner" - "Context menu clicks" and "Banner shows" counts increase
3. Click "Show Banner" in popup - "Banner shows" count increases
4. Click "Clear Stats" - All counts reset to zero
5. Close and reopen popup - "Popup opens" count increases again
6. **Advanced**: Open Chrome DevTools → Application tab → Storage → Local Storage → chrome-extension://[extension-id] to see raw data

### Browser Console Test
1. Open Developer Tools (F12)
2. Go to the Console tab
3. Navigate to any website
4. You should see: `Web Notes Hello World - Content script loaded!`
5. Check for background script messages when using context menu

### Banner Close Button Test
1. Right-click → "Show Web Notes Banner" or click "Show Banner" in popup
2. Click the **message text** (not the ×) - shows alert dialog
3. Click the **× button** - banner slides out and disappears
4. Verify the × has hover effect (background circle appears)

## Extension Features

### Current Features
- ✅ Content script injection on all pages
- ✅ **Context menu integration** - Right-click to show banner
- ✅ Animated banner notifications with close functionality
- ✅ Extension popup interface with manual controls
- ✅ Local storage integration with usage tracking
- ✅ Click interactions and alerts
- ✅ Background service worker for context menu handling
- ✅ **Comprehensive error handling** and logging
- ✅ **Security hardening** with CSP and XSS prevention
- ✅ Tab validation and injection timeout protection
- ✅ User-friendly error messages in popup

### Architecture Preview
This hello world extension demonstrates the foundation for:
- DOM manipulation for note placement
- Chrome extension API usage
- Local storage for data persistence
- Content script and popup communication
- Visual feedback and user interactions

## Files Structure

```
chrome-extension/
├── manifest.json       # Extension configuration with context menu permissions
├── background.js      # Service worker for context menu handling
├── content.js         # Minimal content script (logs loading)
├── popup.html         # Extension popup interface
├── popup.js          # Popup functionality with stats tracking
├── icon16.svg        # 16px icon
├── icon48.svg        # 48px icon
├── icon128.svg       # 128px icon
└── README.md         # This file
```

## Next Steps

This hello world extension will be expanded to include:
1. Note creation and editing functionality
2. DOM element anchoring system
3. Cloud synchronization
4. Rich text editing
5. Note categories and organization

## Troubleshooting

**Extension not loading?**
- Check that Developer Mode is enabled
- Verify all files are in the correct directory
- Check the Chrome Extensions page for error messages
- Look for CSP violations in console if modifying code

**Context menu not appearing?**
- Ensure extension is properly loaded and enabled
- Try right-clicking on different page elements
- Check extension permissions in chrome://extensions
- Avoid restricted pages (chrome://, extension pages)

**Banner not appearing?**
- Make sure you're using the context menu (right-click)
- Check for error messages in popup (red background)
- Open DevTools console to see detailed error logs
- Verify you're not on a restricted page type

**Popup not working?**
- Verify the extension is pinned and visible
- Check for popup blocker interference
- Look for error messages with red background in popup
- Open DevTools to see console errors
- Reload the extension if needed

**Performance issues?**
- Check console for timeout errors
- Extension auto-handles script injection timeouts (5 seconds)
- Multiple banner creation attempts are safely handled
