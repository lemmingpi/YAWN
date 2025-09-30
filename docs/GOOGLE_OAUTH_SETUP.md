# Google OAuth2 Setup for Web Notes Extension

## Overview

The Chrome extension requires Google OAuth2 configuration to enable user authentication. This document provides step-by-step instructions to set up the required credentials.

## Prerequisites

- Google Cloud Platform account
- Access to Google Cloud Console
- Domain ownership (for production deployment)

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: `web-notes-extension`
4. Click "Create"

## Step 2: Enable Required APIs

1. In the Google Cloud Console, go to "APIs & Services" → "Library"
2. Search for and enable:
   - **Google+ API** (for basic profile access)
   - **People API** (recommended for profile information)

## Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Choose "External" user type (unless using Google Workspace)
3. Fill out required fields:
   - **App name**: Web Notes
   - **User support email**: Your email
   - **Developer contact information**: Your email
4. Add scopes:
   - `openid`
   - `email`
   - `profile`
5. Save and continue

## Step 4: Create OAuth2 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. Choose "Chrome extension" as application type
4. Enter extension ID (get this after loading unpacked extension in Chrome)
5. Click "Create"
6. Copy the generated **Client ID**

## Step 5: Update Extension Configuration

### Update manifest.json

Replace the placeholder in `chrome-extension/manifest.json`:

```json
{
  "oauth2": {
    "client_id": "YOUR_ACTUAL_CLIENT_ID.apps.googleusercontent.com",
    "scopes": [
      "openid",
      "email",
      "profile"
    ]
  }
}
```

### Update Backend Environment

Create or update `.env` file in the backend directory:

```bash
GOOGLE_CLIENT_ID=YOUR_ACTUAL_CLIENT_ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET
```

## Step 6: Get Extension ID

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `chrome-extension` folder
4. Copy the generated extension ID (long string of letters)
5. Go back to Google Cloud Console credentials and update the OAuth2 client with this ID

## Step 7: Test Authentication

1. Reload the extension in Chrome
2. Click the extension icon to open popup
3. Click "Sign In with Google"
4. Verify the OAuth flow works without errors

## Troubleshooting

### Common Issues

1. **"OAuth2 client not found"**
   - Verify the Client ID is correctly set in manifest.json
   - Ensure the extension ID matches in Google Cloud Console

2. **"Invalid scope"**
   - Verify scopes match between manifest.json and Google Cloud Console
   - Ensure required APIs are enabled

3. **"Unauthorized domain"**
   - For production: Add your domain to authorized domains in OAuth consent screen
   - For development: Use localhost or load unpacked extension

### Debug Steps

1. Check Chrome extension console for detailed error messages
2. Verify the extension ID in `chrome://extensions/`
3. Confirm OAuth2 client configuration in Google Cloud Console
4. Test with a clean Chrome profile to avoid cached auth states

## Security Notes

- Keep Client Secret secure (backend only)
- Use environment variables for sensitive configuration
- Regularly rotate credentials for production use
- Review and limit OAuth scopes to minimum required

## Production Deployment

For production deployment:

1. Publish extension to Chrome Web Store
2. Update OAuth2 client with published extension ID
3. Set up proper domain verification
4. Configure production environment variables
5. Test with real users before full release
