# YAWN Setup Guide

Complete guide for setting up YAWN (Yet Another Web Notes App) for local development and deployment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Database Setup](#database-setup)
4. [Chrome Extension Setup](#chrome-extension-setup)
5. [Configuration](#configuration)
6. [Secrets Management](#secrets-management)
7. [Domain Registration & DNS](#domain-registration--dns-production-only)
8. [Deployment](#deployment)
9. [Post-Deployment & Maintenance](#post-deployment--maintenance)
10. [Troubleshooting](#troubleshooting)
11. [Development Workflow Commands](#development-workflow-commands)
12. [Next Steps](#next-steps)

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

### LLM Provider Setup (Optional but Recommended)

YAWN supports AI-powered features for note generation and enhancement. Set up at least one provider.

#### Option 1: Google Gemini API (Recommended for Free Tier)

**Free Tier**: 15 requests per minute, 1,500 requests per day

**Setup**:
1. Visit https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Select your GCP project
4. Copy the API key

**Test API Key**:
```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

**Configuration**:
```bash
GOOGLE_AI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash  # or gemini-1.5-pro
LLM_PROVIDER=gemini
```

#### Option 2: OpenAI ChatGPT API

**Free Tier**: $5 free credit for first 3 months (new accounts)

**Setup**:
1. Create account at https://platform.openai.com/signup
2. Navigate to https://platform.openai.com/api-keys
3. Click "Create new secret key" and name it "YAWN-Production"
4. Copy the key (shown only once!)

**Set Usage Limits** (Important!):
- Go to https://platform.openai.com/account/billing/limits
- Set monthly budget limit: $10
- Set email alerts at 50% and 90%

**Test API Key**:
```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50
  }'
```

**Configuration**:
```bash
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_MODEL=gpt-3.5-turbo  # or gpt-4-turbo
LLM_PROVIDER=openai
```

**Pricing** (as of 2025):
- GPT-3.5-turbo: $0.0005/1K tokens (input), $0.0015/1K tokens (output)
- GPT-4-turbo: $0.01/1K tokens (input), $0.03/1K tokens (output)

#### Option 3: Anthropic Claude API

**No Free Tier** - Pay-as-you-go from day 1

**Setup**:
1. Create account at https://console.anthropic.com/
2. Add payment method and set budget alerts ($20/month recommended)
3. Navigate to https://console.anthropic.com/settings/keys
4. Click "Create Key" and name it "YAWN-Production"
5. Copy the key

**Test API Key**:
```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: YOUR_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Configuration**:
```bash
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
ANTHROPIC_MODEL=claude-3-haiku-20240307  # cheapest
# Or: claude-3-5-sonnet-20241022  # best quality
LLM_PROVIDER=anthropic
```

**Pricing** (as of 2025):
- Claude 3 Haiku: $0.25/MTok (input), $1.25/MTok (output)
- Claude 3.5 Sonnet: $3/MTok (input), $15/MTok (output)

#### LLM Selection Strategy

**For Development**:
```bash
LLM_PROVIDER=gemini  # Use free tier
```

**For Production (Cost-Optimized)**:
```bash
LLM_PROVIDER=gemini       # Primary (free tier)
FALLBACK_PROVIDER=openai  # Fallback if rate limited
```

**For Production (Quality-Optimized)**:
```bash
LLM_PROVIDER=claude       # Best quality
FALLBACK_PROVIDER=openai  # Fallback for cost
```

Add these to `backend/env/env.dev` or configure via the web dashboard at `/app/llm-providers`.

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

## Domain Registration & DNS (Production Only)

For production deployment, you'll need a custom domain for your API and potentially for your web dashboard.

### Purchase Domain

**Recommended Registrars**:
- **Namecheap**: ~$12/year, easy DNS management
- **Google Domains**: Integrates with GCP
- **Cloudflare**: Competitive pricing with free DNS and CDN

**Example Domain**: `yawn-notes.com`

### Configure DNS

After deploying your backend to Cloud Run (see Deployment section below), configure DNS:

**1. Get Cloud Run URL**:
```bash
gcloud run services describe yawn-api --region=us-central1 --format='value(status.url)'
# Example output: https://yawn-api-xxxxx-uc.a.run.app
```

**2. Add DNS Records** (Namecheap example):
```
Type: CNAME Record
Host: api
Value: gloo.run.app
TTL: Automatic

Type: CNAME Record
Host: www
Value: gloo.run.app
TTL: Automatic
```

**3. Domain Mapping in GCP**:
```bash
# Enable required services
gcloud services enable run.googleapis.com
gcloud services enable compute.googleapis.com

# Map your domain to Cloud Run
gcloud run domain-mappings create \
  --service yawn-api \
  --domain api.yawn-notes.com \
  --region us-central1

# Verify mapping
gcloud run domain-mappings list --region us-central1
```

### SSL Certificate (Automatic)

Google Cloud Run automatically provisions SSL certificates via Let's Encrypt.

**Verification** (wait 15-60 minutes for DNS propagation):
```bash
# Check certificate status
gcloud run domain-mappings describe \
  --domain api.yawn-notes.com \
  --region us-central1

# Test HTTPS
curl -I https://api.yawn-notes.com/api/health
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

#### Create Artifact Registry Repository

```bash
# Create Docker repository
gcloud artifacts repositories create yawn-docker \
  --repository-format=docker \
  --location=us-central1 \
  --description="YAWN application images"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

#### Build and Push Docker Image

Create `backend/Dockerfile` (if not exists):

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc postgresql-client && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements/base.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Build and push**:

```bash
cd backend

# Build image
docker build -t us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:latest .

# Test locally (optional)
docker run -p 8080:8080 \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@host.docker.internal:5432/webnotes" \
  us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:latest

# Push to registry
docker push us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:latest
```

#### Deploy to Cloud Run

```bash
# Deploy with secrets and Cloud SQL
gcloud run deploy yawn-api \
  --image=us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=300 \
  --concurrency=80 \
  --port=8080 \
  --add-cloudsql-instances=yawn-notes-prod:us-central1:yawn-postgres \
  --set-secrets="DATABASE_URL=db-password:latest,JWT_SECRET_KEY=jwt-secret:latest,GOOGLE_AI_API_KEY=gemini-api-key:latest,OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  --set-env-vars="LLM_PROVIDER=gemini,ENVIRONMENT=production,LOG_LEVEL=INFO,GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com"

# Get service URL
gcloud run services describe yawn-api --region=us-central1 --format="value(status.url)"
```

#### Run Database Migrations

**Method 1: Via Cloud SQL Proxy (local)**:

```bash
# Start proxy
./cloud_sql_proxy -instances=yawn-notes-prod:us-central1:yawn-postgres=tcp:5432 &

# Run migrations
cd backend
export DATABASE_URL="postgresql+asyncpg://yawn_app:PASSWORD@localhost:5432/yawn_production"
alembic upgrade head
```

**Method 2: Via Cloud Run Job** (recommended):

```bash
# Create migration job
gcloud run jobs create yawn-migrate \
  --image=us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:latest \
  --region=us-central1 \
  --add-cloudsql-instances=yawn-notes-prod:us-central1:yawn-postgres \
  --set-secrets="DATABASE_URL=db-password:latest" \
  --command="alembic" \
  --args="upgrade,head"

# Execute migration
gcloud run jobs execute yawn-migrate --region=us-central1
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

The packaging process:
- ✅ Validates manifest.json syntax
- ✅ Converts SVG icons to PNG (required by Chrome Web Store)
- ✅ Excludes development/test files
- ✅ Creates optimized ZIP package

#### Create Store Listing Assets

**Screenshots** (required: minimum 1, recommended: 5):
- Size: 1280x800 or 640x400 pixels
- Format: PNG or JPEG
- Show extension in action on real websites

**Screenshot Ideas**:
1. Creating a note on a webpage
2. Editing markdown content with toolbar
3. Multiple notes with different colors
4. Extension popup showing settings
5. Context menu integration

**Promotional Images**:
- Small tile: 440x280 PNG (required, shown in search results)
- Marquee: 1400x560 PNG (optional, for featured placement)

#### Privacy Policy

Create and host a privacy policy (required). Example template:

```markdown
# Privacy Policy for YAWN Chrome Extension

**Data Collection**: YAWN does not collect, store, or transmit personal data without explicit consent.

**Local Storage**: Notes are stored locally in your browser by default using Chrome's storage API.

**Optional Sync**: If you enable server sync by signing in with Google, notes are stored on our secure servers.

**Permissions**:
- activeTab: To inject notes into web pages
- storage: To save notes locally
- scripting: To display notes on pages
- contextMenus: For right-click menu
- identity: Optional Google sign-in

**Third-Party Services**: No third-party analytics or tracking services are used.

**Contact**: [your-email@example.com]
```

Host this at a public URL (e.g., GitHub Pages, your domain).

#### Upload to Chrome Web Store

1. **Developer Account**:
   - Go to: https://chrome.google.com/webstore/devconsole
   - Pay $5 one-time registration fee
   - Enable 2-Step Verification on Google account

2. **Upload Extension**:
   - Click "New Item"
   - Upload `dist/web-notes-extension-vX.Y.Z.zip`
   - Wait for upload to complete

3. **Fill Out Store Listing**:

**Required Information**:
- **Name**: YAWN - Yet Another Web Notes
- **Summary**: Add persistent sticky notes to any webpage (max 132 characters)
- **Category**: Productivity
- **Language**: English

**Description**:
```
Transform any webpage into your personal notepad with YAWN.

FEATURES:
• Create notes anywhere on any webpage
• Rich markdown support with formatting toolbar
• Notes anchor to page elements (survive page updates)
• Highlight text and create notes from selection
• Drag-and-drop positioning
• Color-coded notes for organization
• Sync across devices (optional)
• Privacy-first: local storage by default

PERFECT FOR:
• Research and studying
• Web development documentation
• Collaborative learning
• Content curation
• Personal knowledge management

PRIVACY FOCUSED:
• Notes stored locally by default
• Optional server sync requires Google sign-in
• No tracking or analytics
• Your notes remain completely private

Get YAWN today and never lose track of important web content again!
```

**Requested Permissions Justification**:
- **activeTab**: Access current tab to inject notes
- **storage**: Store notes data locally in browser
- **scripting**: Execute content scripts to display notes
- **contextMenus**: Add right-click menu integration
- **identity**: Optional Google sign-in for sync

**Privacy Policy**: Link to your hosted privacy policy

**Screenshots**: Upload 1-5 screenshots you created

**Distribution Settings**:
- Visibility: Public
- Pricing: Free
- Regions: All regions

4. **Submit for Review**:
   - Review all information
   - Click "Submit for review"
   - Review period: 1-3 business days (typically 24-48 hours)
   - Monitor email for status updates

**Common Review Issues**:
- ❌ SVG icons not supported → Packaging script converts to PNG
- ❌ Unclear permission justifications → Add detailed explanations above
- ❌ Missing privacy policy → Create and link policy
- ❌ Misleading screenshots → Use actual extension UI
- ❌ Broken functionality → Test thoroughly before submission

#### Post-Approval

Once approved:
- Extension appears in Chrome Web Store
- Install link: `https://chrome.google.com/webstore/detail/YOUR_EXTENSION_ID`
- Add install link to your website/README
- Monitor reviews and ratings
- Respond to user feedback

#### Publishing Updates

1. Update `version` in `manifest.json` (e.g., 1.0.0 → 1.0.1)
2. Run `make package-extension`
3. Go to Developer Dashboard
4. Select your extension
5. Click "Package" tab
6. Upload new ZIP
7. Update store listing if needed
8. Submit for review

**Version Numbering** (semantic versioning):
- Patch (1.0.X): Bug fixes
- Minor (1.X.0): New features
- Major (X.0.0): Breaking changes

---

## Post-Deployment & Maintenance

### Monitoring & Alerts

**View Cloud Run Logs**:
```bash
# Recent logs
gcloud run services logs read yawn-api --region=us-central1 --limit=50

# Follow logs in real-time
gcloud run services logs tail yawn-api --region=us-central1
```

**Create Uptime Check**:
```bash
gcloud monitoring uptime create yawn-api-health \
  --resource-type=uptime-url \
  --host=api.yawn-notes.com \
  --path=/api/health \
  --check-interval=60s
```

**Set Budget Alert**:
```bash
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT \
  --display-name="YAWN Monthly Budget" \
  --budget-amount=10 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

### Database Backups

Cloud SQL automatic backups are enabled by default (configured during setup).

**Manual Backup**:
```bash
gcloud sql backups create \
  --instance=yawn-postgres \
  --description="Pre-migration backup $(date +%Y-%m-%d)"

# List backups
gcloud sql backups list --instance=yawn-postgres

# Restore from backup (if needed)
gcloud sql backups restore BACKUP_ID \
  --backup-instance=yawn-postgres
```

**Database Maintenance**:
```sql
-- Connect to database
psql "postgresql://yawn_app:PASSWORD@localhost:5432/yawn_production"

-- Check table sizes
SELECT tablename, pg_size_pretty(pg_total_relation_size('public.'||tablename))
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.'||tablename) DESC;

-- Vacuum and analyze
VACUUM ANALYZE;
```

### Backend Updates

**Update with Zero Downtime**:
```bash
# Build new version
cd backend
docker build -t us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:v1.1.0 .
docker push us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:v1.1.0

# Deploy without traffic first
gcloud run deploy yawn-api \
  --image=us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:v1.1.0 \
  --region=us-central1 \
  --no-traffic

# Test new revision
REVISION_URL=$(gcloud run services describe yawn-api --region=us-central1 --format='value(status.traffic[0].url)')
curl $REVISION_URL/api/health

# Route traffic to new revision
gcloud run services update-traffic yawn-api \
  --region=us-central1 \
  --to-latest

# Rollback if needed
gcloud run services update-traffic yawn-api \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100
```

### Cost Optimization

**Enable Cloud SQL Auto-Pause** (saves ~$10/month):
```bash
gcloud sql instances patch yawn-postgres \
  --database-flags=cloudsql.enable_auto_pause=on,cloudsql.auto_pause_delay=600
```

**Reduce Cloud Run Memory** (if usage is low):
```bash
gcloud run services update yawn-api \
  --region=us-central1 \
  --memory=256Mi  # Down from 512Mi
```

**Monitor Costs**:
```bash
# View current month costs
gcloud billing projects describe yawn-notes-prod

# Check Cloud Run usage
gcloud run services describe yawn-api --region=us-central1 --format='value(status.observedGeneration)'
```

**LLM Cost Controls**:
- Use Gemini free tier for development
- Set monthly budget limits in provider dashboards
- Monitor usage via web dashboard at `/app/llm-providers`
- Implement daily spending limits in code if needed

### Security Maintenance

**Rotate Secrets** (recommended: quarterly):
```bash
# Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# Update database password
gcloud sql users set-password yawn_app \
  --instance=yawn-postgres \
  --password=$NEW_PASSWORD

# Update secret
echo -n "$NEW_PASSWORD" | gcloud secrets versions add db-password --data-file=-

# Restart Cloud Run
gcloud run services update yawn-api --region=us-central1
```

**Check for Updates**:
- Python dependencies: `pip list --outdated`
- Extension dependencies: Check Chrome Web Store dashboard
- GCP services: Monitor GCP status dashboard

### Monitoring Checklist

Weekly:
- [ ] Check Cloud Run logs for errors
- [ ] Review Cloud SQL performance metrics
- [ ] Check LLM API usage and costs
- [ ] Monitor extension reviews/ratings

Monthly:
- [ ] Review GCP billing
- [ ] Check database backup status
- [ ] Update dependencies if needed
- [ ] Review security alerts

Quarterly:
- [ ] Rotate secrets
- [ ] Review and optimize costs
- [ ] Update documentation
- [ ] Plan feature releases

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
