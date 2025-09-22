# Web Notes Project - Code Index

This document provides a comprehensive index of all files, functions, procedures, and key concepts in the Web Notes Chrome extension project for easy lookup, modification, and refactoring.

## 📁 Project Structure

```
notes/
├── 📋 PROJECT_SPEC.md           # Project architecture and requirements
├── 📋 CLAUDE_CONTEXT.md         # Development session rules and context
├── 📋 README.md                 # Basic project information
├── 📋 INDEX.md                  # This file - comprehensive code index
├── 📂 docs/
│   └── 📋 PLAN.md              # Initial project planning document
├── 📂 chrome-extension/         # Chrome extension source code
│   ├── 📋 README.md            # Extension installation and testing guide
│   ├── ⚙️ manifest.json         # Extension configuration and permissions
│   ├── 🟨 background.js        # Service worker - context menu & stats
│   ├── 🟨 popup.js             # Popup interface logic
│   ├── 🟨 content.js           # Minimal content script
│   ├── 🌐 popup.html           # Popup interface HTML
│   ├── 🎨 icon16.svg           # 16px extension icon
│   ├── 🎨 icon48.svg           # 48px extension icon
│   └── 🎨 icon128.svg          # 128px extension icon
└── 📂 .claude/
    └── ⚙️ settings.local.json   # Claude Code configuration
```

## 🔧 Core Functionality Map

### Extension Entry Points
1. **Service Worker**: `background.js` - Handles context menu and initialization
2. **Popup Interface**: `popup.html` + `popup.js` - Manual banner controls
3. **Content Script**: `content.js` - Minimal page presence
4. **Manifest**: `manifest.json` - Permissions and configuration

### User Interactions
1. **Right-click → Context Menu** → `background.js:chrome.contextMenus.onClicked`
2. **Extension Icon Click** → `popup.html` → `popup.js` event handlers
3. **Banner Close Button** → Injected event handlers in page context

---

## 📄 File-by-File Index

### `chrome-extension/manifest.json`
**Purpose**: Extension configuration, permissions, and entry points

**Key Configurations**:
- `manifest_version: 3` - Modern Chrome extension format
- `permissions`: `["activeTab", "storage", "scripting", "contextMenus"]`
- `content_security_policy` - XSS protection
- `background.service_worker` - Points to background.js
- `action.default_popup` - Points to popup.html

**Dependencies**: All other extension files

---

### `chrome-extension/background.js`
**Purpose**: Service worker handling context menu, stats, and banner injection

#### Constants
- `EXTENSION_ID`: `'show-web-notes-banner'` - Context menu item ID
- `MENU_TITLE`: `'🗒️ Show Web Notes Banner'` - Context menu display text
- `STATS_KEY`: `'extensionStats'` - Local storage key
- `SCRIPT_INJECTION_TIMEOUT`: `5000` - Script injection timeout (ms)
- `DEFAULT_STATS`: Default statistics object structure

#### Core Functions

**Error Handling & Utilities**
- `logError(context, error)` - Centralized error logging with context
- `safeApiCall(apiCall, context)` - Wrapper for Chrome API calls with error handling

**Storage Management**
- `getStats()` → `Promise<Object>` - Retrieves extension stats from storage
- `setStats(stats)` → `Promise<boolean>` - Saves stats to storage with error handling

**Context Menu & Initialization**
- `createContextMenu()` - Creates right-click context menu item
- `initializeStats()` - Initializes stats on first extension install

**Tab & Script Management**
- `isTabValid(tab)` → `boolean` - Validates if tab allows script injection
- `injectBannerScript(tabId)` → `Promise<boolean>` - Injects banner with timeout

**Injected Functions** (Execute in page context)
- `showWebNotesBanner()` - Creates banner DOM elements safely in webpage

#### Event Listeners
- `chrome.runtime.onInstalled` - Extension install/update initialization
- `chrome.contextMenus.onClicked` - Context menu click handling
- `chrome.runtime.onStartup` - Extension startup logging

#### Dependencies
- Chrome APIs: `runtime`, `contextMenus`, `scripting`, `storage`
- Injects into: Web page DOM

---

### `chrome-extension/popup.js`
**Purpose**: Popup interface logic for manual banner control and stats display

#### Constants
- `STATS_KEY`: `'extensionStats'` - Local storage key (shared with background)
- `SCRIPT_INJECTION_TIMEOUT`: `5000` - Script injection timeout
- `DEFAULT_STATS`: Default statistics object (shared structure)

#### Core Functions

**Storage Management** (Duplicated from background for popup context)
- `getStats()` → `Promise<Object>` - Get stats with error fallback
- `setStats(stats)` → `Promise<boolean>` - Save stats with error handling

**UI Management**
- `updateStatsDisplay()` - Updates popup stats display using safe DOM methods
- `incrementPopupCount()` - Increments popup open counter
- `showUserError(message)` - Shows red error message in popup

**Tab & Script Management**
- `isTabValid(tab)` → `boolean` - Same validation as background script
- `getCurrentTab()` → `Promise<Object|null>` - Gets active tab with error handling
- `executeScriptInTab(tabId, func)` → `Promise<boolean>` - Executes script with timeout

**Injected Functions** (Execute in page context)
- `showHelloWorldBanner()` - Creates banner (popup variant message)
- `hideHelloWorldBanner()` - Removes banner with animation

#### Event Handlers
- `DOMContentLoaded` - Popup initialization
- `show-banner` button click - Manual banner show
- `hide-banner` button click - Manual banner hide
- `clear-stats` button click - Reset statistics

#### DOM Elements Referenced
- `#show-banner` - Show banner button
- `#hide-banner` - Hide banner button
- `#clear-stats` - Clear stats button
- `#stats-content` - Stats display container
- `.status` - Status message container

#### Dependencies
- Chrome APIs: `tabs`, `scripting`, `storage`
- DOM: popup.html elements
- Injects into: Web page DOM

---

### `chrome-extension/content.js`
**Purpose**: Minimal content script for page presence

**Functionality**:
- Console logging: `'Web Notes Hello World - Content script loaded!'`
- No DOM manipulation (banner creation moved to injected scripts)

**Dependencies**: None (standalone)

---

### `chrome-extension/popup.html`
**Purpose**: Extension popup interface HTML structure

#### Key Elements
- `.header` - Extension branding and title
- `#show-banner` - Manual banner show button
- `#hide-banner` - Manual banner hide button
- `#clear-stats` - Clear statistics button
- `.status` - Extension status display
- `#storage-stats` container
  - `#stats-content` - Dynamic stats display area
- `.feature-list` - Coming soon features

#### Styling
- Inline CSS with gradient background matching banner theme
- Responsive button design with hover effects
- Monospace font compatibility

#### Dependencies
- `popup.js` - JavaScript functionality
- Extension icons (referenced in manifest)

---

### `chrome-extension/README.md`
**Purpose**: Installation, testing, and troubleshooting guide

**Key Sections**:
- Installation instructions for Chrome developer mode
- Context menu testing procedures
- Local storage functionality verification
- Security feature documentation
- Troubleshooting guide with error scenarios

---

## 🔄 Function Dependencies & Call Flow

### Extension Startup Flow
```
1. Chrome loads manifest.json
2. background.js service worker starts
3. chrome.runtime.onInstalled fires
4. createContextMenu() called
5. initializeStats() called if first install
```

### Context Menu Flow
```
1. User right-clicks on webpage
2. Context menu shows "🗒️ Show Web Notes Banner"
3. chrome.contextMenus.onClicked fires
4. isTabValid() validates target tab
5. injectBannerScript() with timeout protection
6. showWebNotesBanner() executes in page context
7. Stats updated via getStats() + setStats()
```

### Popup Interaction Flow
```
1. User clicks extension icon
2. popup.html loads with popup.js
3. incrementPopupCount() updates usage stats
4. updateStatsDisplay() shows current stats
5. Button clicks trigger tab validation + script injection
6. User feedback via showUserError() on failures
```

### Banner Creation Flow (In Page Context)
```
1. Check if banner already exists (pulse if found)
2. createElement('div') with safe styling
3. Build content with createElement/textContent
4. Append styles if not already present
5. Add event listeners for interaction
6. Auto-fade after timeout
```

---

## 🎯 Key Constants & Configuration

### Storage Keys
- `'extensionStats'` - Main stats object key
- Stats object structure:
  ```javascript
  {
    installDate: Date.now(),
    bannerShows: 0,
    popupOpens: 0,
    contextMenuClicks: 0,
    lastSeen: Date.now()
  }
  ```

### DOM IDs & Classes
- `'web-notes-hello-banner'` - Banner element ID
- `'web-notes-banner-styles'` - Injected style element ID
- `'.banner-message'` - Clickable banner text
- `'.banner-close'` - Close button element

### Timeouts & Timing
- `5000ms` - Script injection timeout
- `300ms` - Banner slide animation duration
- `500ms` - Pulse animation duration
- `5000ms` - Auto-fade delay
- `3000ms` - Error message display duration

### Chrome Extension Permissions
- `activeTab` - Access to current tab
- `storage` - Local storage access
- `scripting` - Script injection capability
- `contextMenus` - Right-click menu creation

---

## 🔒 Security Features & Patterns

### XSS Prevention
- **No innerHTML usage** - All content created via createElement/textContent
- **Content Security Policy** in manifest.json
- **Input validation** on all user-controlled content

### Error Handling Patterns
- **chrome.runtime.lastError** checking on all Chrome API calls
- **Try-catch blocks** around all async operations
- **Timeout protection** on script injection
- **Graceful fallbacks** with default values

### Tab Validation
- **Restricted URL detection**: `chrome:`, `chrome-extension:`, `edge:`, `moz-extension:`
- **Tab existence validation** before script injection
- **Permission checking** before DOM manipulation

---

## 🔄 Refactoring Opportunities

### Code Duplication
1. **Storage functions** - `getStats()`/`setStats()` duplicated in background.js and popup.js
2. **isTabValid()** - Identical function in both files
3. **Banner creation** - Similar logic in both injection contexts
4. **Constants** - STATS_KEY, DEFAULT_STATS, timeouts duplicated

### Suggested Improvements
1. **Create shared utilities module** for common functions
2. **Centralize constants** in single configuration file
3. **Abstract banner creation** into reusable components
4. **Add TypeScript** for better type safety and documentation

### Performance Optimizations
1. **Debounce rapid user interactions** to prevent multiple script injections
2. **Cache DOM queries** in popup.js
3. **Lazy load stats** only when popup opens
4. **Optimize storage operations** with batching

---

## 🧪 Testing Entry Points

### Manual Testing Procedures
- **Context Menu**: Right-click → "Show Web Notes Banner"
- **Popup Interface**: Extension icon → buttons
- **Error Scenarios**: Try on chrome:// pages
- **Stats Tracking**: Monitor storage changes
- **Security**: Test XSS attempts (should fail)

### Automated Testing Opportunities
- **Unit tests** for utility functions
- **Integration tests** for Chrome API interactions
- **E2E tests** for full user workflows
- **Security tests** for XSS prevention

---

## 📚 Related Documentation

- `PROJECT_SPEC.md` - Overall architecture and requirements
- `CLAUDE_CONTEXT.md` - Development standards and rules
- `chrome-extension/README.md` - User-facing installation guide
- `docs/PLAN.md` - Initial project planning

---

*Last Updated: [Auto-generated from source code analysis]*
*For questions about specific implementations, refer to the JSDoc comments in the source files.*