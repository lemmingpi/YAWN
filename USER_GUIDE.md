# YAWN User Guide
**Yet Another Web Notes App - Sticky Notes for Web Pages**

## Table of Contents
1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [Creating Notes](#creating-notes)
4. [Storage Options: Local vs Sync](#storage-options-local-vs-sync)
5. [Editing Notes](#editing-notes)
6. [Managing Notes](#managing-notes)
7. [Server Web Dashboard](#server-web-dashboard)
8. [Tips & Tricks](#tips--tricks)
9. [Troubleshooting](#troubleshooting)

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

### Extension Features When Authenticated

When you sign in with Google and connect to the server, additional features become available in the extension:

#### Enhanced Popup Menu

The extension popup (click the 🗒️ icon) shows additional sections when authenticated:

**User Status Section:**
- Your name and email address
- Sign Out button
- Server sync status indicator

**Sharing Section:**
- **Share Page** - Share all notes on the current page with other users
- **Share Site** - Share all notes across the entire website
- **Manage Shares** - View and manage who has access to your shared content
- **Sharing Status** - See if the current page or site is already shared

**Data Sync Section:**
- **Copy Server Notes to Local** - Download all your cloud notes to local storage
- **Copy Local Notes to Server** - Upload all your local notes to the cloud
- **Delete All Server Data** - Permanently remove all your data from the server (requires confirmation)

#### Enhanced Context Menu (Right-Click)

When authenticated, additional options appear in your right-click context menu:

**🔗 Share Submenu:**
- **Share Current Page** - Share all notes on this page with collaborators
- **Share Current Site** - Share all notes across this entire website

**📋 Register Page (without notes):**
- Register a page in the server database without creating any notes
- Useful for tracking pages you want to annotate later

**🤖 Generate AI Context:**
- Analyze the current page and generate contextual information using AI
- Creates structured context for better note organization

**🤖 Generate Auto Notes with DOM:**
- Automatically generate notes based on page content
- Uses DOM extraction and AI to create relevant annotations

**⚠️ Important Note about AI Features:**
The "Generate AI Context" and "Generate Auto Notes with DOM" features scrape content from the current webpage to provide AI-powered analysis. **It is your responsibility to ensure that your use of these features complies with the terms of service of any website you visit.** Some websites prohibit automated scraping or data extraction. Always review and respect the terms of service and robots.txt policies of websites before using these features.

These authenticated features enable collaboration, advanced organization, and AI-powered enhancements to your note-taking workflow.

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

## Server Web Dashboard

The YAWN server provides a comprehensive web dashboard for managing your notes, sites, and pages from any browser. This is separate from the Chrome extension and offers a centralized view of all your data.

### Accessing the Dashboard

1. Navigate to your YAWN server URL (e.g., `https://your-server.com`)
2. You'll be redirected to the dashboard at `/app/dashboard`
3. Sign in with Google if not already authenticated
4. The dashboard will load with your statistics and recent activity

### Dashboard Overview

The main dashboard displays:

- **Statistics Cards**:
  - Total Sites - Number of domains you're tracking
  - Total Pages - Number of individual pages with notes
  - Total Notes - Count of all your notes
  - Total Artifacts - AI-generated content associated with your notes

- **Recent Activity**:
  - Recent Pages - Your most recently updated pages
  - Recent Notes - Latest notes you've created or modified

- **Quick Actions**: Direct links to create new sites, notes, artifacts, or configure LLM settings

### Managing Sites

**Sites** represent domains where you've created notes (e.g., `github.com`, `stackoverflow.com`).

**To view sites:**
1. Click **"Sites"** in the navigation menu
2. Browse the list of all sites you're tracking
3. Use search, filters, and sorting options to find specific sites

**To add a new site:**
1. Click **"Add Site"** button
2. Enter the domain name (e.g., `example.com`)
3. Optionally add user context (personal notes about this site)
4. Set status (Active/Inactive)
5. Click **"Save"**

**To view site details:**
1. Click on any site domain
2. View all pages and notes associated with that site
3. See sharing status and manage permissions

### Managing Pages

**Pages** are individual URLs within sites where you've created notes.

**To view pages:**
1. Click **"Pages"** in the navigation menu
2. Browse all pages across all your sites
3. Filter by site or search by page title/URL

**To view page details:**
1. Click on any page title
2. View all notes on that specific page
3. See page metadata (URL, title, creation date)
4. Manage sharing for the page

### Managing Notes

**Notes** are the sticky notes you create on web pages.

**To view all notes:**
1. Click **"Notes"** in the navigation menu
2. Browse your complete collection of notes
3. Filter by site, page, or search by content

**To view note details:**
1. Click on any note
2. View full note content with markdown rendering
3. See associated artifacts (AI-generated enhancements)
4. View metadata (creation date, last modified, position on page)

**To edit or delete notes:**
- Most note editing is done via the Chrome extension directly on web pages
- The dashboard provides viewing and organizational capabilities

### LLM Features

YAWN includes AI-powered features for enhancing your notes.

#### Artifacts

**Artifacts** are AI-generated content derived from your notes, such as:
- Summaries of page content
- Extracted insights
- Generated documentation
- Enhanced note formatting

**To view artifacts:**
1. View any note detail page
2. Artifacts associated with that note will be displayed
3. Click on an artifact to see its full content

#### LLM Provider Configuration

**To configure AI providers:**
1. Click **"LLM Settings"** or navigate to `/app/llm-providers`
2. Add provider credentials (OpenAI, Anthropic, Google, etc.)
3. Set default providers for different operations
4. Test provider connections

**Supported providers:**
- OpenAI (GPT models)
- Anthropic (Claude models)
- Google (Gemini models)
- Other compatible providers

### Sharing Features

Share your notes with other users when using the server.

**To share a page:**
1. Navigate to the page detail view
2. Click **"Share"** button
3. Enter the email of the user to share with
4. Set permission level (View/Edit)
5. User will receive access to all notes on that page

**To share an entire site:**
1. Navigate to the site detail view
2. Click **"Share Site"** button
3. All pages and notes on that site will be shared

**To manage existing shares:**
1. View any site or page detail
2. See the list of current shares
3. Revoke access or modify permissions as needed

### Navigation

The dashboard includes:
- **Top Navigation Bar**: Links to Dashboard, Sites, Pages, Notes
- **User Menu**: Profile, settings, and sign out
- **Breadcrumbs**: Track your location in the hierarchy (Sites → Pages → Notes)
- **Quick Search**: Find content across all your data

### Data Synchronization

The web dashboard always displays your server data in real-time:
- Changes made in the Chrome extension sync automatically
- Refresh the dashboard to see the latest updates
- Use the refresh button on the dashboard for manual updates

---

## Tips & Tricks

- **Selected text notes**: Highlight text before creating a note to automatically capture and highlight that text
- **Keyboard shortcuts**: Edit notes like any text field (Ctrl+B for bold, etc.)
- **Quick access**: Pin the extension for one-click access to settings
- **Storage stats**: Check the popup to see how many notes you've created
- **Cross-device**: Use server sync to access notes from work, home, and mobile browsers

---

## Troubleshooting

### Extension Issues

#### Notes not appearing?
- Ensure you're on the exact same URL where you created them
- Check your storage mode - local notes won't appear on other devices

#### Sync not working?
- Verify you're signed in (check the popup)
- Ensure server URL is configured correctly
- Check your internet connection

#### Extension not loading?
- Reload the extension from `chrome://extensions/`
- Check that all files are present in the extension folder
- Look for error messages in the Chrome console (F12)

### Server Dashboard Issues

#### Can't access the dashboard?
- Verify the server URL is correct
- Check that the server is running (contact your administrator)
- Try clearing browser cache and cookies

#### Dashboard shows "Not authenticated"?
- Click the sign-in button and authenticate with Google
- Check that you're using the correct Google account
- Ensure cookies are enabled in your browser

#### Dashboard data not loading?
- Check your internet connection
- Click the refresh button on the dashboard
- Verify your authentication token hasn't expired (sign out and sign back in)
- Check browser console (F12) for API errors

#### Sharing not working?
- Ensure both users are authenticated on the same server
- Verify the email address is correct
- Check that the recipient has created an account on the server

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
