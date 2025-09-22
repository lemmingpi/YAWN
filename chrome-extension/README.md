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

### Automatic Content Script Test
1. Navigate to any website (e.g., `https://google.com`)
2. You should see a purple "Web Notes Hello World!" banner appear in the top-right corner
3. Click the banner to see an alert message
4. Click the "×" to close the banner

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
**What's stored**: Install date, banner show count, popup open count, last seen timestamp

**How to test**:
1. Open popup - "Popup opens" count increases
2. Click "Show Banner" - "Banner shows" count increases
3. Click "Clear Stats" - All counts reset to zero
4. Close and reopen popup - "Popup opens" count increases again
5. **Advanced**: Open Chrome DevTools → Application tab → Storage → Local Storage → chrome-extension://[extension-id] to see raw data

### Browser Console Test
1. Open Developer Tools (F12)
2. Go to the Console tab
3. Navigate to any website
4. You should see: `Web Notes Hello World - Content script loaded!`

### Banner Close Button Test
1. Wait for auto-banner or click "Show Banner" in popup
2. Click the **message text** (not the ×) - shows alert dialog
3. Click the **× button** - banner slides out and disappears
4. Verify the × has hover effect (background circle appears)

## Extension Features

### Current Features
- ✅ Content script injection on all pages
- ✅ Animated banner notifications
- ✅ Extension popup interface
- ✅ Local storage integration
- ✅ Click interactions and alerts

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
├── manifest.json       # Extension configuration
├── content.js         # Runs on all web pages
├── popup.html         # Extension popup interface
├── popup.js          # Popup functionality
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

**Banner not appearing?**
- Check browser console for JavaScript errors
- Try refreshing the page
- Ensure content script permissions are granted

**Popup not working?**
- Verify the extension is pinned and visible
- Check for popup blocker interference
- Reload the extension if needed