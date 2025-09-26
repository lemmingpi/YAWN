# Web Notes Server Integration

This document explains how the Chrome extension integrates with the Web Notes server API for syncing notes across devices.

## Overview

The extension now supports both local-only storage and server synchronization. When server sync is enabled, notes are:
- Saved locally first (for instant response)
- Synced to the server in the background
- Fetched from the server when loading pages
- Gracefully degraded to local-only if server is unavailable

## Configuration

### Server URL Configuration
1. Open the Web Notes popup
2. Enter your server URL in the "Sync Server URL" field (e.g., `https://your-server.com/api`)
3. The extension will automatically start syncing with the server

### Local vs Server Storage
- **Local Storage**: Notes are stored in Chrome's local storage
- **Chrome Sync**: Notes are stored in Chrome's sync storage (syncs across Chrome instances)
- **Server Sync**: Notes are additionally synced to the configured server

## Architecture

### Files Added
- **`server-api.js`**: Main server communication module
- **`error-handling.js`**: Error handling and user feedback utilities
- **`SERVER_INTEGRATION.md`**: This documentation

### Files Modified
- **`manifest.json`**: Added host permissions and new script files
- **`shared-utils.js`**: Updated storage functions to sync with server
- **`popup.js`**: Enhanced to show server sync status
- **`popup.html`**: Added server configuration UI

## API Integration

### Server Endpoints Used
- `GET /api/sites/` - Get or search sites by domain
- `POST /api/sites/` - Create new site
- `GET /api/pages/` - Get or search pages by URL
- `POST /api/pages/` - Create new page
- `GET /api/notes/` - Fetch notes for a page
- `POST /api/notes/` - Create single note
- `POST /api/notes/bulk` - Create/update multiple notes
- `PUT /api/notes/{id}` - Update single note
- `DELETE /api/notes/{id}` - Delete single note

### Data Flow
1. **Page Load**: Extension fetches notes from server for current URL
2. **Note Creation**: Note is created locally, then synced to server
3. **Note Update**: Note is updated locally, then synced to server
4. **Note Deletion**: Note is deleted locally, then removed from server

### Data Mapping
The extension converts between its internal format and the server format:

#### Extension Format
```javascript
{
  id: "web-note-123",
  content: "Note content",
  url: "https://example.com",
  elementSelector: "#main > p:nth-child(2)",
  elementXPath: "/html/body/div/p[2]",
  fallbackPosition: { x: 100, y: 200 },
  offsetX: 10,
  offsetY: 20,
  backgroundColor: "light-yellow",
  isMarkdown: false,
  selectionData: {...},
  isVisible: true
}
```

#### Server Format
```javascript
{
  id: 123,
  content: "Note content",
  position_x: 100,
  position_y: 200,
  anchor_data: {
    elementSelector: "#main > p:nth-child(2)",
    elementXPath: "/html/body/div/p[2]",
    offsetX: 10,
    offsetY: 20,
    backgroundColor: "light-yellow",
    isMarkdown: false,
    selectionData: {...}
  },
  is_active: true,
  server_link_id: "web-note-123",
  page_id: 456
}
```

## Error Handling

### Network Failures
- Operations gracefully fall back to local storage
- User is notified with temporary messages
- Automatic retry with exponential backoff

### Server Unavailable
- Extension continues working with local storage
- No data loss occurs
- Sync resumes automatically when server is available

### Configuration Errors
- Invalid server URLs are handled gracefully
- User feedback is provided for configuration issues

## Permissions

### Host Permissions Added
- `http://localhost:8000/*` - For local development server
- `https://*/*` - For production servers

### Security Considerations
- All requests use HTTPS in production
- Input validation on all server communications
- Timeout protection for all network requests
- No sensitive data stored in URLs or logs

## Testing

### Manual Testing Steps
1. **Configure Server**: Enter server URL in popup
2. **Create Notes**: Verify notes appear and sync to server
3. **Edit Notes**: Verify updates sync to server
4. **Delete Notes**: Verify deletions sync to server
5. **Reload Page**: Verify notes load from server
6. **Offline Mode**: Disable network, verify local operation
7. **Server Down**: Stop server, verify graceful degradation

### Network Conditions to Test
- Normal network connectivity
- Slow network connections
- Intermittent connectivity
- Server downtime
- Invalid server configuration

## Debugging

### Console Logs
- Server requests are logged with method and URL
- Sync operations show success/failure status
- Error messages include operation context

### Error Types
- `network`: Connection issues
- `server`: Server errors (5xx responses)
- `local_storage`: Chrome storage issues
- `unknown`: Unexpected errors

### Common Issues
- **CORS Errors**: Ensure server allows extension origin
- **Timeout Errors**: Check network connectivity and server performance
- **Permission Denied**: Verify host permissions in manifest

## Performance

### Caching Strategy
- Page ID resolution is cached in memory
- Server configuration is cached for 5 minutes
- Local storage is used as primary cache

### Optimization Features
- Bulk operations for multiple notes
- Background sync doesn't block UI
- Retry logic prevents excessive requests
- Request timeouts prevent hanging

## Future Enhancements

### Planned Features
- Conflict resolution for simultaneous edits
- Offline queue for pending sync operations
- Server health monitoring in popup
- Batch sync for multiple pages

### Configuration Options
- Sync frequency settings
- Conflict resolution preferences
- Server timeout configuration
- Debug logging levels
