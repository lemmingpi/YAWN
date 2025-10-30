# Chrome Web Store Compliance Refactoring Plan

## Executive Summary

The YAWN Chrome extension currently faces **likely rejection** from the Chrome Web Store due to overly broad permissions. This document provides a complete refactoring guide to achieve compliance while maintaining all functionality.

### Critical Issues to Fix

1. **`<all_urls>` content script injection** - 16 JS files injected on every page
2. **Broad host permissions** - `https://*/*` gives access to all sites
3. **Missing privacy policy** - Required for extensions using identity/storage
4. **Development URLs in production** - `localhost:8000` in manifest
5. **Unprofessional naming** - "YAWN" acronym may be rejected

### Solution Overview

Replace automatic content script injection with Chrome's recommended `activeTab` permission pattern, using programmatic injection only when the user interacts with the extension.

**Impact on Functionality**: All features remain intact with minor UX changes:
- Notes still appear on pages that have them
- Right-click to add notes still works
- Sharing and AI features unchanged
- Better performance and privacy

---

## Pre-Implementation Checklist

Before starting, ensure you have:
- [ ] Backup of current working extension
- [ ] Test environment with multiple Chrome profiles
- [ ] Access to Chrome Extension Developer Dashboard
- [ ] Privacy policy hosting location ready

---

## Phase 1: Core Infrastructure Setup

### 1.1 Add Content Script Management Utilities

**File**: `chrome-extension/background.js`

Add these functions after line 20 (after `const ongoingInjections = new Set();`):

```javascript
// ===== CONTENT SCRIPT INJECTION MANAGEMENT =====

/**
 * Track which tabs have content scripts injected
 * Map of tabId -> injection status
 */
const injectedTabs = new Map();

/**
 * List of content scripts to inject in order
 */
const CONTENT_SCRIPTS = [
  "libs/marked.min.js",
  "libs/dompurify.min.js",
  "base-utils.js",
  "note-state.js",
  "color-utils.js",
  "color-dropdown.js",
  "markdown-utils.js",
  "shared-utils.js",
  "error-handling.js",
  "contentDialog.js",
  "contextGeneratorDialog.js",
  "sharing-interface.js",
  "sharing.js",
  "selector-utils.js",
  "ai-generation.js",
  "note-positioning.js",
  "note-interaction-editing.js",
  "content.js"  // MUST be last
];

/**
 * Check if content scripts are already injected in a tab
 * @param {number} tabId - The tab ID to check
 * @returns {Promise<boolean>} True if scripts are injected
 */
async function isContentScriptInjected(tabId) {
  // Check cache first
  if (injectedTabs.get(tabId) === true) {
    // Verify scripts are still active
    try {
      const response = await chrome.tabs.sendMessage(tabId, { action: "ping" });
      return response && response.success === true;
    } catch (error) {
      // Scripts not responding, clear cache
      injectedTabs.delete(tabId);
      return false;
    }
  }
  return false;
}

/**
 * Inject all content scripts into a tab
 * @param {number} tabId - The tab ID to inject into
 * @returns {Promise<boolean>} True if injection succeeded
 */
async function injectContentScripts(tabId) {
  try {
    // Check if already injected
    if (await isContentScriptInjected(tabId)) {
      console.log(`[Web Notes] Scripts already injected in tab ${tabId}`);
      return true;
    }

    // Check if injection is already in progress
    if (ongoingInjections.has(tabId)) {
      console.log(`[Web Notes] Injection already in progress for tab ${tabId}`);
      // Wait for ongoing injection
      await new Promise(resolve => setTimeout(resolve, 100));
      return isContentScriptInjected(tabId);
    }

    // Mark injection as in progress
    ongoingInjections.add(tabId);

    console.log(`[Web Notes] Injecting content scripts into tab ${tabId}`);

    // Inject all scripts in order
    await chrome.scripting.executeScript({
      target: { tabId: tabId },
      files: CONTENT_SCRIPTS,
      injectImmediately: false
    });

    // Mark as injected
    injectedTabs.set(tabId, true);
    console.log(`[Web Notes] Successfully injected scripts into tab ${tabId}`);

    return true;
  } catch (error) {
    console.error(`[Web Notes] Failed to inject scripts into tab ${tabId}:`, error);
    injectedTabs.delete(tabId);
    return false;
  } finally {
    ongoingInjections.delete(tabId);
  }
}

/**
 * Inject content scripts and retry a message
 * @param {number} tabId - The tab ID
 * @param {Object} message - The message to send after injection
 * @returns {Promise<any>} The response from the message
 */
async function injectContentScriptAndRetry(tabId, message) {
  try {
    // First try to inject scripts
    const injected = await injectContentScripts(tabId);
    if (!injected) {
      throw new Error("Failed to inject content scripts");
    }

    // Wait a bit for scripts to initialize
    await new Promise(resolve => setTimeout(resolve, 100));

    // Now send the message
    const response = await chrome.tabs.sendMessage(tabId, message);
    return response;
  } catch (error) {
    logError(`Failed to inject and retry message in tab ${tabId}`, error);
    throw error;
  }
}

/**
 * Handle tab removal - clean up injection tracking
 */
chrome.tabs.onRemoved.addListener((tabId) => {
  injectedTabs.delete(tabId);
  ongoingInjections.delete(tabId);
});

/**
 * Handle tab navigation - mark as needing re-injection
 */
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'loading') {
    // Page is navigating, clear injection status
    injectedTabs.delete(tabId);
  }
});
```

### 1.2 Add Ping Response to Content Script

**File**: `chrome-extension/content.js`

Add this message handler after line 153 (in the chrome.runtime.onMessage listener):

```javascript
// Add ping response for injection detection
if (request.action === "ping") {
  sendResponse({ success: true });
  return true;
}
```

---

## Phase 2: Update Manifest

### 2.1 Remove Content Scripts Block

**File**: `chrome-extension/manifest.json`

Remove lines 15-39 (the entire `content_scripts` block):

```json
// DELETE THIS ENTIRE BLOCK:
"content_scripts": [
  {
    "matches": ["<all_urls>"],
    "js": [
      // ... all the script files ...
    ]
  }
],
```

### 2.2 Update Permissions and Host Permissions

Replace lines 6-7 with:

```json
"permissions": ["activeTab", "storage", "scripting", "contextMenus", "identity"],
"host_permissions": ["https://yawn-api-1040678620671.us-central1.run.app/*"],
```

### 2.3 Add Privacy Policy URL

Add after line 4 (after description):

```json
"homepage_url": "https://your-domain.com/privacy-policy",
```

### 2.4 Update Extension Name and Description

Replace lines 3-5 with:

```json
"name": "Web Notes - Sticky Notes for Any Page",
"version": "1.0.1",
"description": "Add sticky notes to any webpage. Rich text editing, markdown support, cloud sync, and sharing. Your notes follow you everywhere.",
```

---

## Phase 3: Update Background Script Handlers

### 3.1 Update handleAddNote Function

**File**: `chrome-extension/background.js`

Replace the `handleAddNote` function (lines 287-310) with:

```javascript
async function handleAddNote(info, tab) {
  try {
    // Inject content scripts if needed
    const injected = await injectContentScripts(tab.id);
    if (!injected) {
      console.error("[Web Notes] Could not inject content scripts");
      return;
    }

    // Get next note number using enhanced URL matching
    const notes = await getNotes(tab.url);
    const urlNotes = getNotesForUrl(tab.url, notes);
    const noteNumber = urlNotes.length + 1;

    // Get click coordinates from content script and create note
    const success = await createNoteWithCoordinates(tab.id, noteNumber);

    if (success) {
      // Update stats only on successful injection
      const stats = await getStats();
      await setStats({
        ...stats,
        contextMenuClicks: stats.contextMenuClicks + 1,
        notesCreated: stats.notesCreated + 1,
        lastSeen: Date.now(),
      });
    }
  } catch (error) {
    logError("Error handling add note action", error);
  }
}
```

### 3.2 Update All Context Menu Handlers

For each of these handlers, add script injection before sending messages:

**handleSharePage** (lines 317-330):
```javascript
async function handleSharePage(info, tab) {
  try {
    // Inject content scripts if needed
    await injectContentScripts(tab.id);

    // Send message to content script to open sharing dialog
    chrome.tabs.sendMessage(tab.id, {
      type: "shareCurrentPage",
    }).catch(error => {
      console.error("[Web Notes] Failed to send share page message:", error);
    });
  } catch (error) {
    logError("Error handling share page action", error);
  }
}
```

**handleShareSite** (lines 337-350):
```javascript
async function handleShareSite(info, tab) {
  try {
    // Inject content scripts if needed
    await injectContentScripts(tab.id);

    // Send message to content script to open sharing dialog
    chrome.tabs.sendMessage(tab.id, {
      type: "shareCurrentSite",
    }).catch(error => {
      console.error("[Web Notes] Failed to send share site message:", error);
    });
  } catch (error) {
    logError("Error handling share site action", error);
  }
}
```

**handleGenerateAIContext** (lines 388-402):
```javascript
async function handleGenerateAIContext(tab) {
  try {
    // Inject content scripts if needed
    await injectContentScripts(tab.id);

    // Send message to content script to show AI context dialog
    chrome.tabs.sendMessage(tab.id, {
      type: "showAIContextDialog",
    }).then(response => {})
    .catch(err => {
      console.warn("[Web Notes] Could not send message to tab:", err);
    });
  } catch (error) {
    logError("Error handling generate AI context action", error);
  }
}
```

**handleGenerateDOMTestNotes** (lines 408-430):
```javascript
async function handleGenerateDOMTestNotes(tab) {
  try {
    // Inject content scripts if needed
    const injected = await injectContentScripts(tab.id);
    if (!injected) {
      console.error("[Web Notes] Could not inject content scripts");
      return;
    }

    // Send message to content script to extract DOM and generate notes
    chrome.tabs.sendMessage(tab.id, {
      type: "generateDOMTestNotes",
    }).then(response => {
      if (response && response.success) {
        console.log("[Web Notes] DOM test notes generation initiated");
      }
    }).catch(err => {
      console.warn("[Web Notes] Could not send message to tab:", err);
    });
  } catch (error) {
    logError("Error handling DOM notes generation", error);
  }
}
```

### 3.3 Fix handleRegisterPage

The function already exists but needs script injection for error display:

**File**: `chrome-extension/background.js` (lines 356-382)

Update the error handling section:

```javascript
} catch (error) {
  console.error("[Web Notes] Failed to register page:", error);

  // Try to inject scripts first to show error
  await injectContentScripts(tab.id);

  // Send error message to content script to show alert
  chrome.tabs.sendMessage(tab.id, {
    type: "showRegistrationError",
    error: error.message || "Unknown error",
  }).catch(err => {
    console.warn("[Web Notes] Could not send error message to tab:", err);
  });

  logError("Error handling register page action", error);
}
```

---

## Phase 4: Handle Existing Notes on Pages

### 4.1 Add Tab Activation Handler

**File**: `chrome-extension/background.js`

Add this after the tab event listeners (around line 130, after injection utilities):

```javascript
/**
 * Check for existing notes when tab becomes active
 */
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);

    // Skip chrome:// and other restricted URLs
    if (!isTabValid(tab)) {
      return;
    }

    // Check if this page has notes
    const notes = await getNotes(tab.url);
    const urlNotes = getNotesForUrl(tab.url, notes);

    if (urlNotes && urlNotes.length > 0) {
      // Page has notes, inject content scripts to display them
      console.log(`[Web Notes] Found ${urlNotes.length} notes for ${tab.url}, injecting scripts`);
      await injectContentScripts(tab.id);

      // Update badge to show note count
      chrome.action.setBadgeText({
        tabId: tab.id,
        text: urlNotes.length.toString()
      });
      chrome.action.setBadgeBackgroundColor({
        color: '#4CAF50'
      });
    } else {
      // Clear badge if no notes
      chrome.action.setBadgeText({
        tabId: tab.id,
        text: ''
      });
    }
  } catch (error) {
    console.debug("[Web Notes] Error checking for notes on tab activation:", error);
  }
});

/**
 * Check for existing notes when page completes loading
 */
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete') {
    // Skip chrome:// and other restricted URLs
    if (!isTabValid(tab)) {
      return;
    }

    // Check if this page has notes
    const notes = await getNotes(tab.url);
    const urlNotes = getNotesForUrl(tab.url, notes);

    if (urlNotes && urlNotes.length > 0) {
      // Page has notes, inject content scripts to display them
      console.log(`[Web Notes] Found ${urlNotes.length} notes for loaded page ${tab.url}`);
      await injectContentScripts(tabId);

      // Update badge to show note count
      chrome.action.setBadgeText({
        tabId: tabId,
        text: urlNotes.length.toString()
      });
      chrome.action.setBadgeBackgroundColor({
        color: '#4CAF50'
      });
    } else {
      // Clear badge if no notes
      chrome.action.setBadgeText({
        tabId: tabId,
        text: ''
      });
    }
  }
});
```

---

## Phase 5: Update Popup Script

### 5.1 Add Content Script Injection Before Actions

**File**: `chrome-extension/popup.js`

Update the `showBanner` function (around lines 240-260) to inject scripts first:

```javascript
async function showBanner() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) return;

    // First inject content scripts if needed
    const response = await chrome.runtime.sendMessage({
      action: "injectContentScripts",
      tabId: tab.id
    });

    if (!response || !response.success) {
      console.error("Failed to inject content scripts");
      return;
    }

    // Now execute the show banner function
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        if (typeof window.showWebNotesBanner === 'function') {
          window.showWebNotesBanner("Web Notes - Popup Triggered!");
        }
      }
    });
  } catch (error) {
    console.error("Error showing banner:", error);
  }
}
```

Add corresponding message handler in background.js (in the message listener section):

```javascript
case "injectContentScripts":
  const injected = await injectContentScripts(message.tabId);
  sendResponse({ success: injected });
  break;
```

---

## Phase 6: Create Privacy Policy

### 6.1 Privacy Policy Template

Create a file `privacy-policy.html` or host on your website:

```html
<!DOCTYPE html>
<html>
<head>
  <title>Web Notes - Privacy Policy</title>
</head>
<body>
  <h1>Privacy Policy for Web Notes Chrome Extension</h1>
  <p><strong>Last Updated: [Current Date]</strong></p>

  <h2>Data Collection</h2>
  <p>Web Notes respects your privacy. The extension:</p>
  <ul>
    <li>Does NOT collect browsing history</li>
    <li>Does NOT track your web activity</li>
    <li>Does NOT sell or share your data</li>
  </ul>

  <h2>Data Storage</h2>
  <ul>
    <li><strong>Local Storage</strong>: Notes are stored locally in your browser using Chrome's storage API</li>
    <li><strong>Optional Cloud Sync</strong>: If you sign in with Google, notes can be synced to our secure servers</li>
    <li><strong>Authentication</strong>: Google OAuth2 is used only for identity verification</li>
  </ul>

  <h2>Permissions Used</h2>
  <ul>
    <li><strong>activeTab</strong>: To display notes on the current webpage when you interact with the extension</li>
    <li><strong>storage</strong>: To save your notes locally in the browser</li>
    <li><strong>scripting</strong>: To inject note display functionality into webpages</li>
    <li><strong>contextMenus</strong>: To add right-click menu options</li>
    <li><strong>identity</strong>: For optional Google sign-in for cloud sync</li>
  </ul>

  <h2>Third-Party Services</h2>
  <p>When using cloud sync (optional):</p>
  <ul>
    <li>Notes are stored on secure Google Cloud Platform servers</li>
    <li>Communication is encrypted using HTTPS</li>
    <li>We use Google OAuth2 for authentication</li>
  </ul>

  <h2>Data Deletion</h2>
  <p>You can delete your data at any time:</p>
  <ul>
    <li>Local notes: Clear extension data in Chrome settings</li>
    <li>Cloud notes: Use the "Delete All Server Data" option in the extension</li>
  </ul>

  <h2>Changes to This Policy</h2>
  <p>We may update this privacy policy. Significant changes will be notified through the extension.</p>

  <h2>Contact</h2>
  <p>For privacy concerns, contact: [your-email@domain.com]</p>
</body>
</html>
```

---

## Testing Checklist

### Pre-Deployment Testing

Test each scenario in order:

#### 1. Basic Functionality
- [ ] Install modified extension locally
- [ ] Verify NO console errors on regular browsing
- [ ] Check that pages load normally without extension active

#### 2. Note Creation
- [ ] Navigate to any webpage
- [ ] Right-click and select "Add Web Note"
- [ ] Verify note appears at click location
- [ ] Edit note text
- [ ] Change note color
- [ ] Delete note

#### 3. Text Selection Notes
- [ ] Select text on a page
- [ ] Right-click on selection
- [ ] Choose "Add Web Note"
- [ ] Verify note contains selected text
- [ ] Verify text is highlighted

#### 4. Existing Notes
- [ ] Create notes on a test page
- [ ] Navigate away and return
- [ ] Verify notes appear automatically
- [ ] Check badge shows note count

#### 5. Multiple Tabs
- [ ] Open 3+ tabs
- [ ] Add notes to each
- [ ] Switch between tabs
- [ ] Verify notes appear correctly

#### 6. Context Menu Actions
- [ ] Test "Share Current Page" (if authenticated)
- [ ] Test "Share Current Site" (if authenticated)
- [ ] Test "Generate AI Context" (if authenticated)
- [ ] Test "Register Page" (if authenticated)

#### 7. Authentication Flow
- [ ] Sign in with Google
- [ ] Verify context menu items appear
- [ ] Test server sync
- [ ] Sign out and verify items hidden

#### 8. Performance
- [ ] Open 10+ tabs without using extension
- [ ] Verify no performance impact
- [ ] Use extension on one tab
- [ ] Verify other tabs unaffected

#### 9. Error Recovery
- [ ] Try to use extension on chrome:// page
- [ ] Try to use on chrome.google.com/webstore
- [ ] Verify graceful failure

#### 10. SPA Navigation
- [ ] Test on GitHub (SPA)
- [ ] Navigate between pages
- [ ] Verify notes update correctly

---

## Chrome Web Store Submission Checklist

### Before Submission

#### Code Preparation
- [ ] Remove all console.log statements (or wrap in debug flag)
- [ ] Remove localhost from manifest.json
- [ ] Update version number in manifest.json
- [ ] Verify no API keys or secrets in code
- [ ] Run linter on all JavaScript files

#### Assets
- [ ] Create 5 screenshots (1280x800 or 640x400)
- [ ] Prepare promotional images (440x280, 1400x560)
- [ ] Ensure icons are PNG format (16, 48, 128)
- [ ] Write compelling store description
- [ ] Host privacy policy publicly

#### Testing
- [ ] Test on Windows, Mac, Linux (if possible)
- [ ] Test with different Chrome versions
- [ ] Test with/without authentication
- [ ] Verify no memory leaks
- [ ] Check all features work

### Submission Package

Run these commands:

```bash
# 1. Clean up development files
rm -rf chrome-extension/test-*.html
rm -rf chrome-extension/*.md

# 2. Create distribution folder
mkdir -p dist
cp -r chrome-extension dist/

# 3. Update manifest for production
# Edit dist/chrome-extension/manifest.json:
# - Remove localhost from host_permissions
# - Ensure privacy policy URL is added
# - Verify version number

# 4. Create ZIP file
cd dist
zip -r web-notes-v1.0.1.zip chrome-extension/
cd ..

# 5. Verify ZIP size (should be < 10MB)
ls -lh dist/web-notes-v1.0.1.zip
```

### Store Listing Information

#### Basic Information
- **Name**: Web Notes - Sticky Notes for Any Page
- **Summary**: Add sticky notes to any webpage with rich text editing and cloud sync
- **Category**: Productivity
- **Language**: English

#### Detailed Description
```
Transform any webpage into your personal workspace with Web Notes - the smart sticky notes extension for Chrome.

✨ KEY FEATURES
• Create colorful sticky notes on any website with a simple right-click
• Rich text editing with full markdown support
• Beautiful color themes to organize your thoughts
• Drag and drop notes anywhere on the page
• Notes automatically save and persist across sessions
• Optional cloud sync with Google account
• Share notes and collaborate with others

🎯 PERFECT FOR
• Students researching and taking notes
• Professionals annotating web content
• Writers collecting inspiration
• Researchers organizing information
• Anyone who needs to remember important web content

🚀 SMART & EFFICIENT
• Uses activeTab permission - only activates when you need it
• Lightweight - doesn't slow down your browsing
• Notes appear automatically on pages where you've added them
• Badge indicator shows note count per page

🔒 PRIVACY FOCUSED
• Works completely offline - no internet required for basic features
• Local notes never leave your computer
• Optional cloud sync requires explicit sign-in
• No tracking, no analytics, no data collection
• Full control over your data

💡 HOW TO USE
1. Right-click anywhere on a webpage
2. Select "Add Web Note" from the menu
3. Type your note and customize with colors
4. Double-click to edit, drag to reposition
5. Your notes are automatically saved

🔄 OPTIONAL CLOUD FEATURES
Sign in with Google to unlock:
• Sync notes across devices
• Share pages with other users
• Generate AI-powered page summaries
• Advanced collaboration features

Web Notes respects your privacy and browsing experience. The extension only activates on pages where you interact with it, ensuring optimal performance and security.

Version 1.0.1 - Now with improved performance and Chrome Web Store compliance!
```

#### Screenshots Needed
1. **Hero Shot**: Multiple colorful notes on a popular website
2. **Right-Click Menu**: Showing the context menu in action
3. **Rich Text Editing**: Toolbar and formatted text
4. **Color Selection**: Color dropdown in use
5. **Sharing Dialog**: (Optional) Collaboration features

---

## Rollback Plan

If issues arise after deployment:

### Quick Rollback

1. Keep the original version ZIP file as backup
2. In Chrome Web Store Developer Dashboard:
   - Upload the previous version
   - Submit for review as urgent fix

### Local Rollback for Testing

```bash
# Restore from backup
cp backup/manifest.json chrome-extension/manifest.json
# Reload extension in Chrome
```

### Partial Rollback

If only specific features break, you can:

1. Keep activeTab permission
2. Re-add minimal content script for critical features:

```json
"content_scripts": [{
  "matches": ["<all_urls>"],
  "js": ["emergency-listener.js"],
  "run_at": "document_idle"
}]
```

Where `emergency-listener.js` only captures coordinates:

```javascript
// Minimal listener for emergency rollback
document.addEventListener('contextmenu', (e) => {
  chrome.storage.local.set({
    lastClick: {
      x: e.clientX,
      y: e.clientY,
      selection: window.getSelection().toString()
    }
  });
});
```

---

## Post-Deployment Monitoring

### Week 1
- Monitor Chrome Web Store reviews
- Check for crash reports in Developer Dashboard
- Track installation/uninstallation rates
- Respond to user feedback quickly

### Metrics to Track
- Daily active users
- Crash rate (should be < 1%)
- Uninstall rate (should be < 5%)
- User reviews and ratings
- Support emails

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| "Notes don't appear" | User needs to click extension or right-click menu first |
| "Lost all my notes" | Check if notes are in local storage, provide recovery guide |
| "Extension is slow" | Verify script injection is working correctly |
| "Can't authenticate" | Check OAuth2 configuration and scopes |

---

## Support Documentation

Create these help documents:

### FAQ for Users

**Q: Why don't my notes appear automatically?**
A: For privacy and performance, the extension now only activates when you interact with it. Your notes are still saved - just click the extension icon or right-click menu to see them.

**Q: Is my data safe?**
A: Yes! Local notes never leave your computer. Cloud sync is optional and uses Google's secure servers.

**Q: Can I use this offline?**
A: Yes! All core features work offline. Only cloud sync requires internet.

---

## Contact and Resources

- Chrome Extension Documentation: https://developer.chrome.com/docs/extensions/
- Chrome Web Store Dashboard: https://chrome.google.com/webstore/devconsole
- Support Email: [your-email@domain.com]

---

## Final Notes

This refactoring maintains all functionality while achieving Chrome Web Store compliance. The key change is moving from automatic content script injection to user-initiated activation, which aligns with Chrome's privacy-first approach.

The activeTab permission pattern is not just recommended - it's the future-proof way to build Chrome extensions. This refactoring positions the extension for long-term success and user trust.

**Estimated Implementation Time**: 4-6 hours for an experienced developer
**Testing Time**: 2-3 hours
**Total Time**: 6-9 hours

Good luck with your Chrome Web Store submission!