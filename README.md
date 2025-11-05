# YAWN - Yet Another Web Notes App

> Persistent sticky notes for web pages with DOM anchoring, cloud sync, and AI-powered features

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is YAWN?

YAWN is a Chrome extension that lets you add sticky notes to any webpage. Notes stay attached to page content even when the layout changes, sync across devices, and can be enhanced with AI-generated insights. Perfect for research, collaboration, and organizing your thoughts across the web.

## Key Features

- **Smart Note Anchoring**: Notes stay attached to page content using DOM anchoring (CSS selectors, XPath, text fragments)
- **Multi-User Collaboration**: Share notes on specific pages or entire sites with other users
- **Cloud Sync**: Access your notes across any browser and device with server sync
- **AI-Powered**: Generate contextual insights, summaries, and auto-notes with LLM integration (OpenAI, Anthropic, Google)
- **Rich Text Editing**: Markdown support, drag-and-drop repositioning, color customization
- **Local-First Architecture**: Works offline with instant display, syncs in background when connected
- **Flexible Storage**: Choose between local-only, Chrome Sync, or server sync storage
- **Web Dashboard**: Manage notes, sites, pages, and sharing from any browser

## Quick Start

### For End Users

Install the Chrome extension and start taking notes on any webpage:

📖 **[Complete User Guide →](USER_GUIDE.md)**

Quick setup:
1. Load the extension from `chrome-extension/` folder
2. Right-click on any webpage → "Add Web Note"
3. Optional: Sign in with Google for cloud sync and sharing

### For Developers

Set up your local development environment:

📖 **[Setup Guide →](SETUP_GUIDE.md)** | **[Developer Guide →](DEVELOPER_GUIDE.md)**

Quick start:
```bash
# Complete setup
make setup

# Start development server
make dev
```

The API will be available at:
- **Server**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8000/app/dashboard

## Project Status

### Completed ✅

- **Chrome Extension**: Production-ready with rich editing, text selection, drag-drop, markdown, toolbar, color customization
- **Multi-User System**: Google OAuth2 authentication, JWT tokens, Chrome Identity API integration
- **Database Schema**: PostgreSQL with multi-user support, temporal versioning ready, cost tracking
- **Backend API**: FastAPI with 13 sharing endpoints, CRUD operations for sites/pages/notes
- **Sharing System**: Granular permissions (VIEW, EDIT, ADMIN) at page and site levels
- **Web Dashboard**: Full UI for managing notes, sites, pages, LLM settings, and shares
- **LLM Integration Phase 1.1**: Database structure, artifact generation, cost tracking models

### In Progress 🔄

- **LLM Integration Phase 1.2+**: Enhanced prompts, multiple provider support, advanced features
- **DOM Anchoring Improvements**: Enhanced selector generation and fallback strategies

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete guide for end users (installation, features, troubleshooting)
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Local environment setup, database configuration, deployment
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Architecture, code structure, data model, development workflows
- **[TODO.md](TODO.md)** - General project tasks and technical debt
- **[CLAUDE.md](CLAUDE.md)** - AI assistant guidelines and project state

## Contributing

We welcome contributions! To get started:

1. Fork the repository and create a feature branch
2. Set up your development environment: see [SETUP_GUIDE.md](SETUP_GUIDE.md)
3. Make your changes and ensure tests pass: `make test && make lint`
4. Submit a pull request with a clear description

For detailed development workflows, code quality standards, and architecture information, see the **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)**.

## Deployment

### Local Development

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for complete instructions.

### Production (GCP)

YAWN is designed for Google Cloud Platform:

1. **Cloud SQL**: PostgreSQL database (db-f1-micro, auto-pause)
2. **Cloud Run**: Serverless FastAPI backend (scales to zero)
3. **Chrome Web Store**: Published extension package

Deployment scripts and detailed instructions in [SETUP_GUIDE.md](SETUP_GUIDE.md#deployment).

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support & Feedback

- **Issues**: [GitHub Issues](https://github.com/your-username/yawn/issues)
- **Documentation**: See guides linked above
- **Questions**: Open a discussion or issue

---

**Happy note-taking!** 🗒️
