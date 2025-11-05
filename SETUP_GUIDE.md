# YAWN Setup Guide

Complete guide for setting up YAWN (Yet Another Web Notes App) for local development and deployment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Database Setup](#database-setup)
4. [Chrome Extension Setup](#chrome-extension-setup)
5. [Configuration](#configuration)
6. [Deployment](#deployment)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

**Python**:
- Python 3.13 or higher
- `pip` package manager
- `venv` module (usually included with Python)

**Database**:
- PostgreSQL 14 or higher
- PostgreSQL client tools (`psql`)

**Node.js** (for extension development tools):
- Node.js 18.0 or higher
- npm (comes with Node.js)

**Chrome Browser**:
- Google Chrome (latest stable version)
- Chrome Developer Mode enabled

### Platform-Specific Notes

**Windows**:
- Git Bash recommended (comes with Git for Windows)
- Alternatively, use PowerShell or WSL2

**Mac**:
- Install Homebrew: https://brew.sh
- Use Homebrew to install PostgreSQL and Python

**Linux**:
- Use package manager (apt, yum, pacman, etc.)
- May need `python3-venv` package separately

### Checking Prerequisites

```bash
# Check Python version (should be 3.13+)
python --version

# Check pip
pip --version

# Check PostgreSQL
psql --version

# Check Node.js (should be 18+)
node --version

# Check npm
npm --version
```

---

## Local Development Setup

### Quick Start (Recommended)

From the project root directory:

```bash
# Complete setup for Python and Node.js environments
make all

# Start the development server
make dev
```

The API will be available at:
- **Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8000/app/dashboard
- **Health Check**: http://localhost:8000/api/health

### Manual Setup

If you prefer to set up manually or need to troubleshoot:

#### 1. Clone the Repository

```bash
git clone https://github.com/your-username/yawn.git
cd yawn
```

#### 2. Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (Git Bash):
source .venv/Scripts/activate

# On Mac/Linux:
source .venv/bin/activate
```

#### 3. Install Python Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Install development dependencies
pip install -r requirements/dev.txt
```

#### 4. Install Pre-commit Hooks

```bash
# Install git hooks for code quality
pre-commit install
```

#### 5. Install Node.js Dependencies (Optional)

For extension linting and formatting tools:

```bash
npm install
```

#### 6. Verify Installation

```bash
# Check environment
make check-env

# Check npm (if installed)
make check-npm
```

---

## Database Setup

### PostgreSQL Installation

**Mac** (using Homebrew):
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows**:
- Download installer from: https://www.postgresql.org/download/windows/
- Run installer and follow setup wizard
- Note the password you set for the `postgres` user

### Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE webnotes;
CREATE USER webnotes_user WITH PASSWORD 'your_password_here';
GRANT ALL PRIVILEGES ON DATABASE webnotes TO webnotes_user;

# Exit psql
\q
```

### Run Database Migrations

```bash
# From project root
source .venv/Scripts/activate  # Windows
source .venv/bin/activate      # Mac/Linux

# Run migrations
cd backend
alembic upgrade head
```

### Verify Database

```bash
# Connect to database
psql -U webnotes_user -d webnotes

# List tables (should see users, sites, pages, notes, etc.)
\dt

# Exit
\q
```

---

## Chrome Extension Setup

### Load Extension in Chrome

1. **Open Chrome Extensions Page**:
   - Navigate to: `chrome://extensions/`
   - Or: Menu → More Tools → Extensions

2. **Enable Developer Mode**:
   - Toggle the "Developer mode" switch in the top-right corner

3. **Load Unpacked Extension**:
   - Click "Load unpacked" button
   - Navigate to the `chrome-extension/` folder in the project
   - Select the folder (not individual files)

4. **Verify Installation**:
   - Extension should appear with 🗒️ icon
   - Check for any errors in the extension list

5. **Pin Extension** (recommended):
   - Click puzzle piece icon in Chrome toolbar
   - Find "YAWN" and click pin icon

### Test Extension

1. Navigate to any website
2. Right-click on the page
3. Look for "🗒️ Add Web Note" in context menu
4. Click to create a test note

### Reload Extension After Changes

When you modify extension code:

1. Go to `chrome://extensions/`
2. Find YAWN extension
3. Click the reload icon (🔄)
4. Refresh any open web pages

---

## Configuration

### Environment Variables

Configuration files are in `backend/env/`:

- `env.dev` - Local development configuration
- `env.prod` - Production configuration

**Key Variables**:

```bash
# Database
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/webnotes"

# JWT Authentication
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours

# Server
HOST=localhost
PORT=8080
DEBUG=True

# CORS (allow extension to connect)
ALLOWED_ORIGINS='["http://localhost:3000", "http://localhost:8080", "chrome-extension://*"]'

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=True
LOG_FILE=../logs/app.log
```

### Google OAuth Setup

For authentication features:

1. **Create Google Cloud Project**:
   - Go to: https://console.cloud.google.com
   - Create new project or select existing

2. **Enable Google Identity API**:
   - Navigate to APIs & Services → Library
   - Search for "Google Identity"
   - Click "Enable"

3. **Create OAuth 2.0 Credentials**:
   - Go to APIs & Services → Credentials
   - Click "Create Credentials" → "OAuth 2.0 Client ID"
   - Application type: "Web application"
   - Authorized redirect URIs: `http://localhost:8080/api/auth/callback`
   - Note the Client ID and Client Secret

4. **Update Environment Variables**:
   ```bash
   # Add to backend/env/env.dev
   GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
   GOOGLE_CLIENT_SECRET="your-client-secret"
   ```

5. **Configure Extension**:
   - Update `chrome-extension/manifest.json` with your Client ID:
   ```json
   "oauth2": {
     "client_id": "your-client-id.apps.googleusercontent.com",
     "scopes": ["openid", "email", "profile"]
   }
   ```

### LLM Provider Setup (Optional)

For AI-powered features, configure LLM providers:

**OpenAI**:
```bash
OPENAI_API_KEY="sk-..."
```

**Anthropic**:
```bash
ANTHROPIC_API_KEY="sk-ant-..."
```

**Google Gemini**:
```bash
GOOGLE_GEMINI_API_KEY="..."
```

Add these to your environment file or configure via the web dashboard at `/app/llm-providers`.

---

## Deployment

### Google Cloud Platform (GCP) Deployment

YAWN is designed to run on GCP with minimal cost ($2-4/month for ~12 users).

#### Architecture

```
┌─────────────────┐
│   Cloud Run     │  Serverless backend (scales to zero)
│  (FastAPI app)  │
└────────┬────────┘
         │
┌────────▼────────┐
│   Cloud SQL     │  Managed PostgreSQL (db-f1-micro)
│  (PostgreSQL)   │
└─────────────────┘
```

#### Prerequisites

1. **GCP Account**: https://cloud.google.com
2. **gcloud CLI**: Install from https://cloud.google.com/sdk
3. **Project Setup**:
   ```bash
   gcloud auth login
   gcloud projects create yawn-notes
   gcloud config set project yawn-notes
   ```

#### Deploy Cloud SQL

```bash
# Create PostgreSQL instance
gcloud sql instances create yawn-db \
  --tier=db-f1-micro \
  --region=us-central1 \
  --database-version=POSTGRES_14 \
  --storage-auto-increase

# Create database
gcloud sql databases create webnotes --instance=yawn-db

# Create user
gcloud sql users create webnotes_user \
  --instance=yawn-db \
  --password=SECURE_PASSWORD_HERE

# Get connection name
gcloud sql instances describe yawn-db --format="value(connectionName)"
```

#### Deploy Cloud Run

```bash
# Build and deploy
gcloud run deploy yawn-api \
  --source=backend \
  --region=us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://webnotes_user:PASSWORD@/webnotes?host=/cloudsql/CONNECTION_NAME" \
  --add-cloudsql-instances=CONNECTION_NAME

# Get service URL
gcloud run services describe yawn-api --region=us-central1 --format="value(status.url)"
```

#### Update Extension for Production

1. **Update Server URL** in `chrome-extension/popup.js`:
   ```javascript
   const API_BASE_URL = 'https://your-cloud-run-url.run.app';
   ```

2. **Rebuild Extension**:
   ```bash
   make package-extension
   ```

3. **Upload to Chrome Web Store** (see below)

### Chrome Web Store Publishing

#### Prepare Extension Package

```bash
# Validate extension structure
make validate-extension

# Create distribution package
make package-extension
```

This creates: `dist/web-notes-extension-vX.Y.Z.zip`

#### Upload to Chrome Web Store

1. **Developer Account**:
   - Go to: https://chrome.google.com/webstore/devconsole
   - Pay $5 one-time registration fee
   - Enable 2-Step Verification on Google account

2. **Create New Item**:
   - Click "New Item"
   - Upload the ZIP file
   - Fill out store listing:
     - Name: "YAWN - Web Notes"
     - Description: [Copy from USER_GUIDE.md intro]
     - Screenshots: Take 4-5 screenshots of extension in use
     - Category: Productivity
     - Privacy policy URL

3. **Submit for Review**:
   - Review can take 1-3 business days
   - Check email for approval or feedback

#### Publishing Updates

1. Update version in `manifest.json`
2. Run `make package-extension`
3. Upload new ZIP to existing item in dashboard
4. Submit for review

---

## Troubleshooting

### Python Environment Issues

**Problem**: `command not found: python`
- **Solution**: Try `python3` instead, or install Python 3.13

**Problem**: `No module named 'venv'`
- **Linux**: `sudo apt install python3-venv`
- **Mac**: Reinstall Python from Homebrew

**Problem**: Virtual environment activation fails
- **Windows**: Use Git Bash, not CMD
- **Mac/Linux**: Ensure you use `source`, not just `./`

### Database Issues

**Problem**: `psql: connection refused`
- **Solution**: Check if PostgreSQL is running:
  ```bash
  # Mac
  brew services list

  # Linux
  sudo systemctl status postgresql

  # Windows
  # Check services.msc for PostgreSQL service
  ```

**Problem**: `password authentication failed`
- **Solution**: Reset PostgreSQL password:
  ```bash
  sudo -u postgres psql
  ALTER USER postgres PASSWORD 'new_password';
  ```

**Problem**: `database "webnotes" does not exist`
- **Solution**: Create database:
  ```bash
  psql -U postgres
  CREATE DATABASE webnotes;
  ```

**Problem**: Alembic migration fails
- **Solution**: Check database connection in `env.dev`
- **Solution**: Drop and recreate database if in development:
  ```bash
  psql -U postgres
  DROP DATABASE webnotes;
  CREATE DATABASE webnotes;
  \q
  alembic upgrade head
  ```

### Extension Issues

**Problem**: Extension won't load
- **Solution**: Check manifest.json syntax with: `make validate-extension`
- **Solution**: Look for errors in `chrome://extensions/`

**Problem**: "Manifest version not supported"
- **Solution**: Update Chrome to latest version (requires v88+)

**Problem**: Extension loads but doesn't work
- **Solution**: Check browser console (F12) for JavaScript errors
- **Solution**: Verify backend is running at correct URL

**Problem**: Notes don't sync to server
- **Solution**: Check backend logs for errors
- **Solution**: Verify CORS settings in `env.dev`
- **Solution**: Check network tab (F12) for failed requests

### Backend Issues

**Problem**: `make dev` fails
- **Solution**: Ensure virtual environment is created: `make setup`
- **Solution**: Check for port conflicts (port 8000 in use)

**Problem**: "Module not found" errors
- **Solution**: Reinstall dependencies: `pip install -r requirements/dev.txt`

**Problem**: Tests fail unexpectedly
- **Solution**: Ensure test database is set up
- **Solution**: Check if test fixtures are creating conflicts

**Problem**: Pre-commit hooks fail
- **Solution**: Run `make format` to auto-fix formatting
- **Solution**: Manually fix issues shown by linters

### Deployment Issues

**Problem**: Cloud Run deployment fails
- **Solution**: Check service account permissions
- **Solution**: Verify Dockerfile exists in `backend/`
- **Solution**: Check Cloud Run logs in GCP Console

**Problem**: Database connection fails in production
- **Solution**: Verify Cloud SQL connection name is correct
- **Solution**: Check that Cloud Run has Cloud SQL permission
- **Solution**: Test connection with Cloud SQL Proxy locally

**Problem**: Extension can't connect to production API
- **Solution**: Verify CORS settings include Chrome extension origin
- **Solution**: Check SSL certificate is valid
- **Solution**: Update `API_BASE_URL` in extension code

---

## Development Workflow Commands

### Common Commands

```bash
# Setup
make setup              # Initial setup
make all               # Full setup (Python + Node.js)
make check-env         # Verify Python environment
make check-npm         # Verify Node.js environment

# Development
make dev               # Start backend server
make test              # Run tests with coverage
make test-fast         # Run tests without coverage

# Code Quality
make lint              # Check code quality
make format            # Auto-format code
make lint-all          # Lint Python and JavaScript
make format-all        # Format Python and JavaScript
make pre-commit        # Run pre-commit hooks

# Database
alembic upgrade head   # Apply migrations
alembic downgrade -1   # Rollback one migration
alembic revision --autogenerate -m "message"  # Create migration

# Extension
make validate-extension     # Validate extension structure
make package-extension      # Create Chrome Web Store package

# Cleanup
make clean             # Clean Python environment
make clean-npm         # Clean Node.js environment
```

### Aliases

```bash
make run       # Same as make dev
make server    # Same as make dev
make install   # Same as make install-dev
```

---

## Next Steps

After setup is complete:

1. **Read the Developer Guide**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
2. **Review Architecture**: [PROJECT_SPEC.md](PROJECT_SPEC.md)
3. **Check User Documentation**: [USER_GUIDE.md](USER_GUIDE.md)
4. **See Project Tasks**: [TODO.md](TODO.md)

---

**Need Help?** Open an issue on the GitHub repository or check existing documentation.
