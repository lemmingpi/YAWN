# YAWN Setup Guide

Complete guide for setting up YAWN (Yet Another Web Notes App) for local development and deployment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Database Setup](#database-setup)
4. [Chrome Extension Setup](#chrome-extension-setup)
5. [Configuration](#configuration)
6. [Secrets Management](#secrets-management)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

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

## Secrets Management

YAWN requires several secrets for authentication, database access, and LLM integration. This section covers how to generate, store, and use these secrets securely.

### Required Secrets

#### 1. Database Password

**Purpose**: Secure database authentication

**Generate**:
```bash
# Generate strong random password
openssl rand -base64 32
```

**Usage**:
- Local: Set in `DATABASE_URL` in `backend/env/env.dev`
- Production: Store in GCP Secret Manager as `db-password`

#### 2. JWT Secret Key

**Purpose**: Sign and verify authentication tokens

**Generate**:
```bash
# Generate cryptographically secure secret
openssl rand -hex 64
```

**Usage**:
- Local: Set `JWT_SECRET_KEY` in `backend/env/env.dev`
- Production: Store in GCP Secret Manager as `jwt-secret`

**Configuration**:
```bash
JWT_SECRET_KEY=your_generated_secret_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours
```

#### 3. Google OAuth Credentials

**Purpose**: User authentication via Google Sign-In

**Obtain** (see [Google OAuth Setup](#google-oauth-setup) above):
- `GOOGLE_CLIENT_ID` - From GCP Console
- `GOOGLE_CLIENT_SECRET` - From GCP Console

**Usage**:
- Local: Set in `backend/env/env.dev`
- Production: Can be public (Client ID) or in Secret Manager (Client Secret)

#### 4. LLM API Keys

**Purpose**: Access to AI providers for note generation and enhancements

**Providers** (choose one or more):

**Google Gemini API**:
```bash
# Get key from: https://makersuite.google.com/app/apikey
GOOGLE_AI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-1.5-flash  # or gemini-1.5-pro
```

**OpenAI API**:
```bash
# Get key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_MODEL=gpt-3.5-turbo  # or gpt-4-turbo
```

**Anthropic Claude API**:
```bash
# Get key from: https://console.anthropic.com/settings/keys
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
ANTHROPIC_MODEL=claude-3-haiku-20240307  # or claude-3-5-sonnet-20241022
```

**Usage**:
- Local: Set in `backend/env/env.dev`
- Production: Store in GCP Secret Manager

**Cost Considerations**:
- **Gemini**: Free tier (15 requests/min, 1,500/day) - recommended for development
- **OpenAI**: $5 free credit for 3 months (new accounts)
- **Anthropic**: Pay-as-you-go, no free tier

### Local Development Setup

**Method 1: Environment Files** (Recommended)

Edit `backend/env/env.dev`:

```bash
# Database
DATABASE_URL="postgresql+asyncpg://webnotes_user:your_db_password@localhost:5432/webnotes"

# JWT
JWT_SECRET_KEY=your_jwt_secret_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# LLM Provider (choose one)
GOOGLE_AI_API_KEY=your_gemini_key
LLM_PROVIDER=gemini

# Optional: Additional providers
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Server Config
HOST=localhost
PORT=8080
DEBUG=True
ENVIRONMENT=development
LOG_LEVEL=INFO

# CORS
ALLOWED_ORIGINS='["http://localhost:3000", "http://localhost:8080", "chrome-extension://*"]'
```

**Method 2: Shell Environment**

```bash
# Export secrets as environment variables
export DATABASE_URL="postgresql+asyncpg://webnotes_user:password@localhost:5432/webnotes"
export JWT_SECRET_KEY="your_jwt_secret"
export GOOGLE_AI_API_KEY="your_gemini_key"
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"

# Run backend
cd backend
python -m app.main
```

**Security Notes**:
- ⚠️ **Never commit `.env` or `env.dev` files with real secrets to git**
- ✅ Use `.env.example` or `.env.template` for documentation
- ✅ Add `env.dev` and `env.prod` to `.gitignore`

### Production Setup (GCP Secret Manager)

#### Enable Secret Manager API

```bash
gcloud services enable secretmanager.googleapis.com
```

#### Create Secrets

```bash
# Database password
echo -n "YOUR_DATABASE_PASSWORD" | gcloud secrets create db-password --data-file=-

# JWT secret
echo -n "YOUR_JWT_SECRET" | gcloud secrets create jwt-secret --data-file=-

# Google OAuth (optional, can be env var)
echo -n "YOUR_GOOGLE_CLIENT_SECRET" | gcloud secrets create google-client-secret --data-file=-

# LLM API keys
echo -n "YOUR_GEMINI_KEY" | gcloud secrets create gemini-api-key --data-file=-
echo -n "YOUR_OPENAI_KEY" | gcloud secrets create openai-api-key --data-file=-
echo -n "YOUR_ANTHROPIC_KEY" | gcloud secrets create anthropic-api-key --data-file=-
```

#### Grant Access to Cloud Run

```bash
# Get project number
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')

# Grant access to each secret
for SECRET in db-password jwt-secret gemini-api-key openai-api-key anthropic-api-key google-client-secret; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

#### Configure Cloud Run with Secrets

When deploying to Cloud Run:

```bash
gcloud run deploy yawn-api \
  --image=YOUR_IMAGE \
  --region=us-central1 \
  --set-secrets="DATABASE_URL=db-password:latest,JWT_SECRET_KEY=jwt-secret:latest,GOOGLE_AI_API_KEY=gemini-api-key:latest,OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest" \
  --set-env-vars="GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com,LLM_PROVIDER=gemini,ENVIRONMENT=production,LOG_LEVEL=INFO"
```

**Note**: Non-secret config (like `GOOGLE_CLIENT_ID`, `LLM_PROVIDER`) can be set as environment variables.

#### View and Manage Secrets

```bash
# List all secrets
gcloud secrets list

# View secret versions
gcloud secrets versions list SECRET_NAME

# Access secret value (for debugging)
gcloud secrets versions access latest --secret=SECRET_NAME

# Update secret (creates new version)
echo -n "NEW_VALUE" | gcloud secrets versions add SECRET_NAME --data-file=-

# Delete old versions (keep latest 3)
gcloud secrets versions list SECRET_NAME --format="value(name)" | tail -n +4 | while read version; do
  gcloud secrets versions destroy $version --secret=SECRET_NAME --quiet
done
```

### Secret Rotation

For security, rotate secrets periodically (recommended: quarterly).

**Rotation Procedure**:

1. **Generate new secret**:
   ```bash
   NEW_PASSWORD=$(openssl rand -base64 32)
   ```

2. **Update in GCP Secret Manager**:
   ```bash
   echo -n "$NEW_PASSWORD" | gcloud secrets versions add db-password --data-file=-
   ```

3. **Update dependent services**:
   ```bash
   # For database password, update Cloud SQL user
   gcloud sql users set-password webnotes_user \
     --instance=yawn-postgres \
     --password=$NEW_PASSWORD
   ```

4. **Restart Cloud Run** (picks up latest secret version):
   ```bash
   gcloud run services update yawn-api --region=us-central1
   ```

5. **Verify** application still works

6. **Delete old secret version**:
   ```bash
   gcloud secrets versions destroy VERSION_NUMBER --secret=db-password
   ```

### Secrets Checklist

Before deploying to production:

- [ ] All secrets generated with cryptographically secure methods
- [ ] Database password is strong (32+ characters)
- [ ] JWT secret is at least 64 characters
- [ ] LLM API keys obtained and tested
- [ ] Google OAuth credentials configured
- [ ] Secrets stored in GCP Secret Manager (not in code)
- [ ] Cloud Run service account has `secretAccessor` role
- [ ] Local `.env` files excluded from git (`.gitignore`)
- [ ] Secret rotation schedule established
- [ ] Backup of secrets stored securely (password manager)

### Troubleshooting

**Issue**: Cloud Run can't access secrets

**Solution**: Verify IAM permissions:
```bash
gcloud secrets get-iam-policy SECRET_NAME
```

**Issue**: "Secret not found" error

**Solution**: Check secret exists in correct project:
```bash
gcloud secrets list --project=YOUR_PROJECT_ID
```

**Issue**: Database connection fails with wrong password

**Solution**: Verify secret matches database user password:
```bash
# View secret (locally)
gcloud secrets versions access latest --secret=db-password

# Reset database password to match
gcloud sql users set-password webnotes_user \
  --instance=yawn-postgres \
  --password=SECRET_VALUE
```

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
