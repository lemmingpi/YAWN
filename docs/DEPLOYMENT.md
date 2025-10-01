# YAWN - Yet Another Web Notes App - Complete Deployment Guide

Complete deployment guide for Chrome Web Store and Google Cloud Platform with PostgreSQL.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [LLM API Setup](#llm-api-setup)
3. [Domain Registration & DNS](#domain-registration--dns)
4. [GCP Infrastructure Setup](#gcp-infrastructure-setup)
5. [Backend Deployment](#backend-deployment)
6. [Chrome Extension Publishing](#chrome-extension-publishing)
7. [Post-Deployment](#post-deployment)
8. [Security & Maintenance](#security--maintenance)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Accounts
- **Google Cloud Platform** account with billing enabled
- **Domain registrar** account (Namecheap, Google Domains, Cloudflare, etc.)
- **Chrome Web Store Developer** account ($5 one-time fee)
- **GitHub** account (for version control and CI/CD)
- **Google Account** with 2-Step Verification enabled (for Chrome Web Store)

### Development Tools
```bash
# Install Google Cloud SDK
# Windows: Download from https://cloud.google.com/sdk/docs/install
# Mac: brew install google-cloud-sdk
# Linux: curl https://sdk.cloud.google.com | bash

# Install required CLI tools
gcloud components install cloud-sql-proxy
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Install Docker
# Download from https://www.docker.com/products/docker-desktop

# Install Node.js (for extension development)
# Download from https://nodejs.org/
```

### Estimated Costs
- **GCP**: $2-4/month (Cloud Run + Cloud SQL with auto-pause)
- **Domain**: $10-15/year
- **Chrome Developer**: $5 one-time
- **LLM APIs**:
  - Gemini: Free tier (15 requests/min)
  - OpenAI: $5 free credit, then pay-as-you-go
  - Anthropic Claude: Pay-as-you-go (no free tier)

### Extension Requirements
- ✅ Manifest V3 compliant (current extension is compliant)
- ✅ No code obfuscation (we use clear, readable code)
- ✅ All functionality discernible from submitted code
- ✅ Required icons: 16px, 48px, 128px (converted to PNG during packaging)

---

## LLM API Setup

Your application supports three LLM providers. Set up at least one.

### Option 1: Google Gemini API (Recommended for Free Tier)

**Free Tier**: 15 requests per minute, 1,500 requests per day

1. **Create API Key**: ✅ 
   ```bash
   # Visit Google AI Studio
   # https://makersuite.google.com/app/apikey

   # Or use gcloud CLI
   gcloud services enable generativelanguage.googleapis.com
   ```

2. **Get API Key**: ✅ 
   - Navigate to https://makersuite.google.com/app/apikey
   - Click "Create API Key"
   - Select your GCP project
   - Copy the API key

3. **Test API Key**: ✅ 
   ```bash
   curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY" \
     -H 'Content-Type: application/json' \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
   ```

4. **Environment Variable**:  ✅
   ```bash
   GOOGLE_AI_API_KEY=your_GOOGLE_AI_API_KEY_here
   GEMINI_MODEL=gemini-1.5-flash  # or gemini-1.5-pro
   ```

### Option 2: OpenAI ChatGPT API

**Free Tier**: $5 free credit for first 3 months (new accounts)

1. **Create Account**:
   - Visit https://platform.openai.com/signup
   - Verify email and phone number

2. **Get API Key**:
   - Navigate to https://platform.openai.com/api-keys
   - Click "Create new secret key"
   - Name it "YAWN-Production"
   - Copy the key (shown only once!)

3. **Set Usage Limits** (Important!):
   - Go to https://platform.openai.com/account/billing/limits
   - Set monthly budget limit: $10
   - Set email alerts at 50% and 90%

4. **Test API Key**:
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

5. **Environment Variables**:
   ```bash
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
   OPENAI_MODEL=gpt-3.5-turbo  # or gpt-4-turbo for better quality
   ```

6. **Pricing** (as of 2025):
   - GPT-3.5-turbo: $0.0005/1K tokens (input), $0.0015/1K tokens (output)
   - GPT-4-turbo: $0.01/1K tokens (input), $0.03/1K tokens (output)

### Option 3: Anthropic Claude API

**No Free Tier** - Pay-as-you-go from day 1

1. **Create Account**:
   - Visit https://console.anthropic.com/
   - Sign up with email

2. **Add Payment Method**:
   - Navigate to https://console.anthropic.com/settings/billing
   - Add credit card
   - Set budget alerts (recommended: $20/month)

3. **Get API Key**:
   - Navigate to https://console.anthropic.com/settings/keys
   - Click "Create Key"
   - Name it "YAWN-Production"
   - Copy the key

4. **Test API Key**:
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

5. **Environment Variables**:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
   ANTHROPIC_MODEL=claude-3-haiku-20240307  # cheapest
   # Or: claude-3-5-sonnet-20241022  # best quality
   ```

6. **Pricing** (as of 2025):
   - Claude 3 Haiku: $0.25/MTok (input), $1.25/MTok (output)
   - Claude 3.5 Sonnet: $3/MTok (input), $15/MTok (output)

### LLM Selection Strategy

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
LLM_PROVIDER=claude       # Best quality for note generation
FALLBACK_PROVIDER=openai  # Fallback for cost
```

### LLM Usage Monitoring

Add to your backend monitoring:

```python
# backend/app/services/llm_monitor.py
import logging
from datetime import datetime
from typing import Dict

class LLMUsageMonitor:
    """Track LLM API usage and costs"""

    def __init__(self):
        self.usage_log = []

    def log_request(self, provider: str, model: str,
                   input_tokens: int, output_tokens: int,
                   cost: float):
        entry = {
            "timestamp": datetime.utcnow(),
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost
        }
        self.usage_log.append(entry)
        logging.info(f"LLM usage: {entry}")

    def get_daily_cost(self) -> float:
        """Calculate today's LLM costs"""
        today = datetime.utcnow().date()
        return sum(
            entry["cost"]
            for entry in self.usage_log
            if entry["timestamp"].date() == today
        )
```

---

## Domain Registration & DNS

### Step 1: Purchase Domain

**Recommended Registrars**:
- **Namecheap**: Cheapest, easy DNS management
- **Google Domains**: Integrates with GCP
- **Cloudflare**: Free DNS with CDN

**Example: Namecheap**:
```
1. Visit namecheap.com
2. Search for domain: "yawn-notes.com"
3. Add to cart (~$12/year)
4. Complete purchase
```

### Step 2: Configure DNS

You'll need to point your domain to Google Cloud Run.

**A. Get Cloud Run URL** (do this after backend deployment):
```bash
gcloud run services describe yawn-api --region=us-central1 --format='value(status.url)'
# Output: https://yawn-api-xxxxx-uc.a.run.app
```

**B. Add DNS Records**:

For **Namecheap**:
```
1. Login → Domain List → Manage → Advanced DNS
2. Add Records:

Type: CNAME Record
Host: api
Value: gloo.run.app
TTL: Automatic

Type: CNAME Record
Host: @
Value: gloo.run.app
TTL: Automatic

Type: CNAME Record
Host: www
Value: gloo.run.app
TTL: Automatic
```

For **Google Domains**:
```
1. Login → My Domains → DNS
2. Custom resource records:

Name: api
Type: CNAME
TTL: 1H
Data: gloo.run.app

Name: @
Type: A
TTL: 1H
Data: [Google Cloud Run IP - provided after domain mapping]
```

### Step 3: Domain Mapping in GCP

```bash
# Enable required services
gcloud services enable run.googleapis.com
gcloud services enable compute.googleapis.com

# Map domain to Cloud Run
gcloud run domain-mappings create \
  --service yawn-api \
  --domain api.yawn-notes.com \
  --region us-central1

# For root domain (optional)
gcloud run domain-mappings create \
  --service yawn-api \
  --domain yawn-notes.com \
  --region us-central1

# Verify mapping
gcloud run domain-mappings list --region us-central1
```

### Step 4: SSL Certificate (Automatic)

Google Cloud Run automatically provisions SSL certificates via Let's Encrypt.

**Verification**:
```bash
# Wait 15-60 minutes for DNS propagation
# Check certificate status
gcloud run domain-mappings describe \
  --domain api.yawn-notes.com \
  --region us-central1

# Test HTTPS
curl -I https://api.yawn-notes.com/health
```

---

## GCP Infrastructure Setup

### Step 1: Create GCP Project

```bash
# Create project
gcloud projects create yawn-notes-prod --name="YAWN Production"

# Set as active project
gcloud config set project yawn-notes-prod

# Enable billing (required)
# Visit: https://console.cloud.google.com/billing
# Link billing account to project

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

### Step 2: Set Up Cloud SQL PostgreSQL

**Create Database Instance**:
```bash
# Create db-f1-micro instance (auto-pause enabled)
gcloud sql instances create yawn-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-type=HDD \
  --storage-size=10GB \
  --storage-auto-increase \
  --backup-start-time=03:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=04 \
  --database-flags=max_connections=50 \
  --activation-policy=ALWAYS \
  --enable-bin-log=false

# Note: Auto-pause after 10 minutes idle (saves cost)
# Add flag: --database-flags=cloudsql.enable_auto_pause=on
```

**Create Database and User**:
```bash
# Set root password
gcloud sql users set-password postgres \
  --instance=yawn-postgres \
  --password=YOUR_SECURE_ROOT_PASSWORD

# Create application database
gcloud sql databases create yawn_production \
  --instance=yawn-postgres

# Create application user
gcloud sql users create yawn_app \
  --instance=yawn-postgres \
  --password=YOUR_SECURE_APP_PASSWORD
```

**Get Connection String**:
```bash
# Get connection name
gcloud sql instances describe yawn-postgres \
  --format='value(connectionName)'

# Output: yawn-notes-prod:us-central1:yawn-postgres
```

**Connection String Format**:
```bash
# For Cloud Run (using Unix socket)
DATABASE_URL=postgresql://yawn_app:PASSWORD@/yawn_production?host=/cloudsql/yawn-notes-prod:us-central1:yawn-postgres

# For local development (using Cloud SQL Proxy)
DATABASE_URL=postgresql://yawn_app:PASSWORD@localhost:5432/yawn_production
```

### Step 3: Set Up Secret Manager

Store sensitive configuration securely.

```bash
# Create secrets
echo -n "YOUR_DATABASE_PASSWORD" | gcloud secrets create db-password --data-file=-
echo -n "YOUR_GOOGLE_AI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
echo -n "YOUR_OPENAI_API_KEY" | gcloud secrets create openai-api-key --data-file=-
echo -n "YOUR_ANTHROPIC_API_KEY" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "YOUR_JWT_SECRET" | gcloud secrets create jwt-secret --data-file=-

# Grant Cloud Run access to secrets
PROJECT_NUMBER=$(gcloud projects describe yawn-notes-prod --format='value(projectNumber)')

gcloud secrets add-iam-policy-binding db-password \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding anthropic-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding jwt-secret \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# List secrets
gcloud secrets list
```

### Step 4: Create Artifact Registry Repository

Store Docker images for Cloud Run.

```bash
# Create Docker repository
gcloud artifacts repositories create yawn-docker \
  --repository-format=docker \
  --location=us-central1 \
  --description="YAWN application images"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### Step 5: Set Up Cloud SQL Proxy (Local Development)

```bash
# Download Cloud SQL Proxy
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy
chmod +x cloud_sql_proxy

# Run proxy (in separate terminal)
./cloud_sql_proxy -instances=yawn-notes-prod:us-central1:yawn-postgres=tcp:5432

# Now you can connect locally
psql "postgresql://yawn_app:PASSWORD@localhost:5432/yawn_production"
```

---

## Backend Deployment

### Step 1: Create Dockerfile

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run with gunicorn
CMD ["gunicorn", "app.main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8080", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

### Step 2: Create .dockerignore

Create `backend/.dockerignore`:

```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info
dist
build
.venv
venv
.env
.env.local
test.db
*.sqlite
.pytest_cache
.coverage
htmlcov
.git
.gitignore
README.md
DEPLOYMENT.md
```

### Step 3: Create Environment Configuration

Create `backend/.env.production.template`:

```bash
# Database
DATABASE_URL=postgresql://yawn_app:PASSWORD@/yawn_production?host=/cloudsql/PROJECT:REGION:INSTANCE

# LLM APIs
GOOGLE_AI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
LLM_PROVIDER=gemini

# JWT
JWT_SECRET_KEY=your_jwt_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret

# CORS
ALLOWED_ORIGINS=https://yawn-notes.com,https://api.yawn-notes.com

# App Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Step 4: Build and Push Docker Image

```bash
# Navigate to backend directory
cd backend

# Build image
docker build -t us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:latest .

# Test locally
docker run -p 8080:8080 \
  -e DATABASE_URL="postgresql://yawn_app:PASSWORD@host.docker.internal:5432/yawn_production" \
  -e GOOGLE_AI_API_KEY="your_key" \
  us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:latest

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:latest
```

### Step 5: Deploy to Cloud Run

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
  --set-secrets="DATABASE_URL=db-password:latest,GOOGLE_AI_API_KEY=gemini-api-key:latest,OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,JWT_SECRET_KEY=jwt-secret:latest" \
  --set-env-vars="LLM_PROVIDER=gemini,ENVIRONMENT=production,LOG_LEVEL=INFO"

# Get service URL
gcloud run services describe yawn-api --region=us-central1 --format='value(status.url)'
```

### Step 6: Run Database Migrations

```bash
# Connect to Cloud SQL via proxy
./cloud_sql_proxy -instances=yawn-notes-prod:us-central1:yawn-postgres=tcp:5432 &

# Run Alembic migrations
cd backend
export DATABASE_URL="postgresql://yawn_app:PASSWORD@localhost:5432/yawn_production"
alembic upgrade head

# Or run migration via Cloud Run job
gcloud run jobs create yawn-migrate \
  --image=us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:latest \
  --region=us-central1 \
  --add-cloudsql-instances=yawn-notes-prod:us-central1:yawn-postgres \
  --set-secrets="DATABASE_URL=db-password:latest" \
  --command="alembic" \
  --args="upgrade,head"

gcloud run jobs execute yawn-migrate --region=us-central1
```

### Step 7: Set Up CI/CD with GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main
    paths:
      - 'backend/**'

env:
  PROJECT_ID: yawn-notes-prod
  REGION: us-central1
  SERVICE_NAME: yawn-api
  REPOSITORY: yawn-docker

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker
        run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev

      - name: Build Docker image
        working-directory: backend
        run: |
          docker build -t ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:${{ github.sha }} .
          docker tag ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:${{ github.sha }} \
            ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:latest

      - name: Push Docker image
        run: |
          docker push ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:${{ github.sha }}
          docker push ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:latest

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ${{ env.SERVICE_NAME }} \
            --image=${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:${{ github.sha }} \
            --region=${{ env.REGION }} \
            --platform=managed

      - name: Run migrations
        run: |
          gcloud run jobs execute yawn-migrate --region=${{ env.REGION }} --wait
```

---

## Chrome Extension Publishing

### Step 1: Create Chrome Web Store Developer Account

```
1. Visit: https://chrome.google.com/webstore/devconsole
2. Sign in with Google account (2-Step Verification required)
3. Pay $5 one-time developer fee
4. Fill out developer profile
```

### Step 2: Pre-Package Validation

Run these commands to ensure your extension is ready:

```bash
# Validate extension structure and files
make validate-extension

# Run code quality checks
make lint-js

# Check package information
make package-info
```

### Step 3: Prepare Extension Assets

**Create Icons** (required sizes):
```
chrome-extension/
  icons/
    icon-16.png    (16x16)
    icon-48.png    (48x48)
    icon-128.png   (128x128)
```

Use a tool like [Figma](https://www.figma.com/) or [GIMP](https://www.gimp.org/) to create icons.

**Update manifest.json**:
```json
{
  "manifest_version": 3,
  "name": "YAWN - Yet Another Web Notes",
  "version": "1.0.0",
  "description": "Add sticky notes to any webpage. Notes persist across visits and sync across devices.",
  "icons": {
    "16": "icons/icon-16.png",
    "48": "icons/icon-48.png",
    "128": "icons/icon-128.png"
  },
  "host_permissions": ["https://api.yawn-notes.com/*"],
  "oauth2": {
    "client_id": "YOUR_ACTUAL_CLIENT_ID.apps.googleusercontent.com",
    "scopes": ["openid", "email", "profile"]
  },
  ...
}
```

### Step 4: Package Extension

Create the Chrome Web Store package:

```bash
# This will create dist/web-notes-extension-v1.0.0.zip
make package-extension

# Or manually:
cd chrome-extension
zip -r yawn-extension-v1.0.0.zip . -x "*.git*" "node_modules/*" ".DS_Store" "test-*.html" "*.test.js" "*.spec.js"

# Verify ZIP contents
unzip -l yawn-extension-v1.0.0.zip
```

**What the packaging process does**:
- ✅ Validates manifest.json syntax
- ✅ Checks for all required files
- ✅ Converts SVG icons to PNG format (required by Chrome Web Store)
- ✅ Excludes development/test files
- ✅ Creates optimized ZIP package
- ✅ Validates package structure

**Package Contents**:
- `manifest.json` (with PNG icon references)
- All JavaScript files (`background.js`, `content.js`, etc.)
- `popup.html`
- PNG icons (`16.png`, `48.png`, `128.png`)
- `libs/` directory with dependencies

**Excluded from package**:
- `test-*.html` files
- `README.md`
- `INLINE_STYLES_DEMO.md`
- Any `.test.js` or `.spec.js` files
- Development configuration files

### Step 5: Create Store Listing Assets

**Screenshots** (minimum 1, recommended 5):
- Size: 1280x800 or 640x400 pixels
- Format: PNG or JPEG
- Show the extension in action on real websites

**Example Screenshots to Take**:
1. Adding a note to a webpage
2. Editing markdown content
3. Note with rich text formatting
4. Multiple notes on a page
5. Settings/sync interface
6. Color selection dropdown
7. Context menu integration

**Promotional Images**:
- Small tile: 440x280 PNG (required, shown in search results)
- Marquee: 1400x560 PNG (optional, featured placement)
- Small icon: 128x128 PNG (search results)

### Step 6: Submit to Chrome Web Store

**Upload Extension**:
1. Go to [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/developer/dashboard)
2. Click "**Add new item**"
3. Upload your ZIP file (`dist/web-notes-extension-v1.0.0.zip`)
4. Wait for upload to complete and initial processing

**Fill Out Store Listing**:

**Required Information**:
- **Name**: YAWN - Yet Another Web Notes
- **Summary**: Add persistent sticky notes to any webpage (max 132 characters)
- **Category**: Productivity
- **Language**: English (or your primary language)

**Description** (detailed):
```
Transform any webpage into your personal notepad with YAWN - the ultimate productivity extension for Chrome.

FEATURES:
• Create notes anywhere on any webpage
• Rich markdown support with formatting toolbar
• Notes anchor to page elements (survive page updates)
• Highlight text and create notes from selection
• Drag-and-drop positioning
• Color-coded notes for organization
• Sync across devices (optional)
• Privacy-first: local storage by default
• Beautiful color themes for note backgrounds
• Clean, intuitive interface that doesn't interfere with webpage content

PERFECT FOR:
• Research and studying
• Web development documentation
• Collaborative learning
• Content curation
• Personal knowledge management
• Students taking research notes
• Professionals annotating web content
• Writers collecting inspiration
• Anyone who needs to remember important details from websites

PRIVACY FOCUSED:
• Notes are stored locally in your browser by default
• Optional server sync requires Google sign-in
• No data transmitted to external servers without consent
• No tracking or analytics
• Your notes remain completely private

HOW TO USE:
1. Right-click on any webpage and select "Show Web Notes Banner"
2. Click anywhere to create a new note
3. Double-click any note to edit with rich text formatting
4. Use the color picker to organize notes by theme
5. Drag notes around to position them perfectly

Get YAWN today and never lose track of important web content again!
```

**Privacy Policy**:
```
Privacy Policy for YAWN Chrome Extension

Data Collection: YAWN does not collect, store, or transmit any personal data or user information to external servers without explicit user consent.

Local Storage: All notes and user data are stored locally in your browser using Chrome's storage API by default. This data remains on your device and is never shared.

Optional Sync: If you choose to enable sync by signing in with Google, your notes will be stored on our secure servers. This is entirely optional.

Permissions: The extension requests the following permissions:
- activeTab: To inject notes into web pages
- storage: To save your notes locally
- scripting: To display notes on web pages
- contextMenus: To add the right-click menu option
- identity: For optional Google sign-in

Third-Party Services: YAWN does not use any third-party analytics, tracking, or data collection services.

Updates: This privacy policy may be updated when new features are added. Users will be notified of any material changes.

Contact: [Your email address for privacy concerns]
```

**Requested Permissions Justification**:
- **activeTab**: Access the current tab to inject notes
- **storage**: Store notes data locally in browser
- **scripting**: Execute content scripts to display notes
- **contextMenus**: Add right-click menu integration
- **identity**: Optional Google sign-in for sync

**Distribution Settings**:
- **Visibility**: Public
- **Pricing**: Free
- **Regions**: All regions (or select specific countries)

### Step 7: Submit for Review

1. Review all information in the Developer Console
2. Click "**Submit for review**"
3. Review period: 1-3 business days (typically 24-48 hours)
4. Monitor email for review status
5. Address any issues raised by reviewers

**Common Review Issues**:
- Icons: SVG icons not supported (packaging script fixes this)
- Unclear permission justifications → Add detailed explanations
- Missing privacy policy → Create and link policy page
- Misleading screenshots → Use actual extension UI
- Broken functionality → Test thoroughly before submission
- Permissions: Requesting unnecessary permissions
- Policy violations: Using restricted APIs or behaviors

### Step 8: Post-Approval

Once approved:
```
1. Extension appears in Chrome Web Store
2. Install link: https://chrome.google.com/webstore/detail/YOUR_EXTENSION_ID
3. Add install link to your website
4. Monitor reviews and ratings
5. Respond to user feedback
```

---

## Post-Deployment

### Monitoring & Alerts

**Cloud Run Monitoring**:
```bash
# View logs
gcloud run services logs read yawn-api --region=us-central1 --limit=50

# Create uptime check
gcloud monitoring uptime create yawn-api-health \
  --resource-type=uptime-url \
  --host=api.yawn-notes.com \
  --path=/health \
  --check-interval=60s

# Create alert policy for errors
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="YAWN API Errors" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s
```

**Cost Monitoring**:
```bash
# Set budget alert
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT \
  --display-name="YAWN Monthly Budget" \
  --budget-amount=10 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

**LLM Usage Dashboard**:

Create simple monitoring in your backend:

```python
# backend/app/routers/admin.py
from fastapi import APIRouter, Depends
from app.services.llm_monitor import LLMUsageMonitor

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/llm-usage")
async def get_llm_usage(monitor: LLMUsageMonitor = Depends()):
    """Get LLM API usage statistics"""
    return {
        "daily_cost": monitor.get_daily_cost(),
        "total_requests": len(monitor.usage_log),
        "by_provider": monitor.get_usage_by_provider()
    }
```

**Chrome Extension Monitoring**:
- **User ratings and reviews**: Respond to feedback
- **Usage statistics**: Available in Developer Console
- **Crash reports**: Monitor for technical issues

### Database Maintenance

**Backups**:
```bash
# Cloud SQL automatic backups are enabled by default
# Manual backup:
gcloud sql backups create \
  --instance=yawn-postgres \
  --description="Pre-migration backup"

# List backups
gcloud sql backups list --instance=yawn-postgres

# Restore from backup
gcloud sql backups restore BACKUP_ID \
  --backup-instance=yawn-postgres \
  --backup-id=BACKUP_ID
```

**Database Optimization**:
```sql
-- Connect to database
psql "postgresql://yawn_app:PASSWORD@localhost:5432/yawn_production"

-- Check table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Vacuum and analyze
VACUUM ANALYZE;

-- Check for missing indexes
SELECT
  schemaname,
  tablename,
  attname,
  n_distinct,
  correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY n_distinct DESC;
```

### Updates & Versioning

**Backend Updates**:
```bash
# Update code
git pull origin main

# Build new image
cd backend
docker build -t us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:v1.1.0 .
docker push us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:v1.1.0

# Deploy with zero downtime
gcloud run deploy yawn-api \
  --image=us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:v1.1.0 \
  --region=us-central1 \
  --no-traffic  # Deploy without traffic first

# Test new revision
REVISION_URL=$(gcloud run services describe yawn-api --region=us-central1 --format='value(status.traffic[0].url)')
curl $REVISION_URL/health

# Route traffic to new revision
gcloud run services update-traffic yawn-api \
  --region=us-central1 \
  --to-latest

# Rollback if needed
gcloud run services update-traffic yawn-api \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100
```

**Chrome Extension Updates**:
```bash
# Update version in manifest.json
{
  "version": "1.1.0"
}

# Package new version
make package-extension
# Or manually:
cd chrome-extension
zip -r yawn-extension-v1.1.0.zip .

# Upload to Chrome Web Store
1. Go to Developer Dashboard
2. Select your extension
3. Click "Package" tab
4. Upload new ZIP
5. Update store listing if needed
6. Click "Submit for Review"
```

**Version Numbering**:
Follow semantic versioning (e.g., 1.0.1, 1.1.0, 2.0.0):
- **Patch** (1.0.X): Bug fixes
- **Minor** (1.X.0): New features
- **Major** (X.0.0): Breaking changes

### Cost Optimization

**Auto-Pause Cloud SQL**:
```bash
# Enable auto-pause (saves ~$10/month)
gcloud sql instances patch yawn-postgres \
  --database-flags=cloudsql.enable_auto_pause=on,cloudsql.auto_pause_delay=600
```

**Reduce Cloud Run Memory**:
```bash
# If usage is low, reduce from 512Mi to 256Mi
gcloud run services update yawn-api \
  --region=us-central1 \
  --memory=256Mi
```

**LLM Cost Controls**:
```python
# backend/app/services/llm_client.py
class LLMClient:
    MAX_DAILY_COST = 5.00  # $5/day limit

    async def generate(self, prompt: str):
        # Check daily cost before request
        if self.monitor.get_daily_cost() > self.MAX_DAILY_COST:
            raise Exception("Daily LLM budget exceeded")

        # Use rate limiting
        await self.rate_limiter.acquire()

        # Make request...
```

---

## Security & Maintenance

### Security Best Practices

**Secret Rotation**:
```bash
# Rotate database password quarterly
NEW_PASSWORD=$(openssl rand -base64 32)

gcloud sql users set-password yawn_app \
  --instance=yawn-postgres \
  --password=$NEW_PASSWORD

# Update secret
echo -n "$NEW_PASSWORD" | gcloud secrets versions add db-password --data-file=-

# Rotate LLM API keys
# 1. Generate new key from provider console
# 2. Update secret
echo -n "NEW_KEY" | gcloud secrets versions add gemini-api-key --data-file=-

# 3. Restart Cloud Run to pick up new secret
gcloud run services update yawn-api --region=us-central1
```

**HTTPS Enforcement**:
```python
# backend/app/middleware.py
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

app.add_middleware(HTTPSRedirectMiddleware)
```

**CORS Configuration**:
```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yawn-notes.com",
        "https://api.yawn-notes.com",
        "chrome-extension://YOUR_EXTENSION_ID"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

**Rate Limiting**:
```python
# backend/app/middleware.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/notes")
@limiter.limit("100/minute")
async def get_notes():
    ...
```

### Disaster Recovery

**Backup Strategy**:
```bash
# Daily automated backups (configured in Cloud SQL)
# Retention: 7 days

# Weekly manual backups
gcloud sql backups create \
  --instance=yawn-postgres \
  --description="Weekly backup $(date +%Y-%m-%d)"

# Export to Cloud Storage (monthly)
gcloud sql export sql yawn-postgres \
  gs://yawn-backups/monthly/backup-$(date +%Y-%m-%d).sql \
  --database=yawn_production
```

**Recovery Procedure**:
```bash
# 1. Create new instance from backup
gcloud sql instances clone yawn-postgres yawn-postgres-restored \
  --backup-id=BACKUP_ID

# 2. Test restored instance
./cloud_sql_proxy -instances=yawn-notes-prod:us-central1:yawn-postgres-restored=tcp:5433 &
psql "postgresql://yawn_app:PASSWORD@localhost:5433/yawn_production"

# 3. Switch Cloud Run to restored instance (if needed)
gcloud run services update yawn-api \
  --region=us-central1 \
  --clear-cloudsql-instances \
  --add-cloudsql-instances=yawn-notes-prod:us-central1:yawn-postgres-restored
```

### Compliance & Privacy

**Privacy Policy** (required for Chrome Web Store):

Create `docs/privacy.md`:
```markdown
# Privacy Policy for YAWN

Last updated: [DATE]

## Data Collection
- Notes content is stored locally in your browser by default
- Optional server sync stores encrypted notes on our servers
- Google sign-in collects email and profile information

## Data Usage
- Notes are used solely for the extension's core functionality
- No data is sold or shared with third parties
- LLM providers (Gemini/OpenAI/Claude) may process note content for AI features

## Data Retention
- Local notes: Stored until you uninstall the extension
- Server-synced notes: Stored until you delete your account
- Backups: Retained for 30 days

## User Rights
- Export all your data: Contact support@yawn-notes.com
- Delete your account: Visit account settings
- Opt-out of analytics: Disable in extension settings

## Contact
support@yawn-notes.com
```

**Terms of Service**:

Create `docs/terms.md` with standard terms covering:
- Service description
- User responsibilities
- Liability limitations
- Acceptable use policy

---

## Troubleshooting

### Common Issues

**1. Cloud Run Won't Start**:
```bash
# Check logs
gcloud run services logs read yawn-api --region=us-central1 --limit=100

# Common causes:
# - Database connection failure → Check Cloud SQL instance is running
# - Missing secrets → Verify secrets exist and permissions are set
# - Port mismatch → Ensure app listens on PORT env var (default 8080)
```

**2. Database Connection Errors**:
```bash
# Test connection manually
./cloud_sql_proxy -instances=yawn-notes-prod:us-central1:yawn-postgres=tcp:5432 &
psql "postgresql://yawn_app:PASSWORD@localhost:5432/yawn_production"

# Check Cloud SQL status
gcloud sql instances describe yawn-postgres --format='value(state)'
```

**3. SSL Certificate Not Provisioning**:
```bash
# Check DNS propagation
dig api.yawn-notes.com

# Check domain mapping status
gcloud run domain-mappings describe \
  --domain api.yawn-notes.com \
  --region us-central1

# Wait 15-60 minutes for Let's Encrypt provisioning
```

**4. Extension Not Loading**:
```
- Check manifest.json syntax
- Verify OAuth client ID is correct
- Check console errors: Chrome DevTools > Console
- Test in Incognito mode
```

**5. Chrome Web Store Rejection**:
```
- Icons: SVG icons not supported → Use PNG
- Permissions: Too broad → Be specific
- Privacy: Unclear policy → Update description
- Functionality: Doesn't work → Test thoroughly
```

**6. LLM API Rate Limits**:
```python
# Implement exponential backoff
import time

def retry_with_backoff(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except RateLimitError:
            wait_time = (2 ** i) + random.random()
            time.sleep(wait_time)
    raise Exception("Max retries exceeded")
```

---

## Quick Reference

### Essential Commands

```bash
# Deploy backend
gcloud run deploy yawn-api \
  --image=us-central1-docker.pkg.dev/yawn-notes-prod/yawn-docker/yawn-api:latest \
  --region=us-central1

# View logs
gcloud run services logs read yawn-api --region=us-central1 --limit=50

# Check costs
gcloud billing projects describe yawn-notes-prod

# Backup database
gcloud sql backups create --instance=yawn-postgres

# Update secret
echo -n "NEW_VALUE" | gcloud secrets versions add SECRET_NAME --data-file=-

# Package extension
make package-extension
# Or manually:
cd chrome-extension && zip -r ../yawn-extension.zip .
```

### Important URLs

- **GCP Console**: https://console.cloud.google.com
- **Cloud Run**: https://console.cloud.google.com/run
- **Cloud SQL**: https://console.cloud.google.com/sql
- **Secret Manager**: https://console.cloud.google.com/security/secret-manager
- **Chrome Web Store Dashboard**: https://chrome.google.com/webstore/devconsole
- **Chrome Extensions Documentation**: https://developer.chrome.com/docs/extensions
- **Gemini API**: https://makersuite.google.com/app/apikey
- **OpenAI API**: https://platform.openai.com/api-keys
- **Anthropic Console**: https://console.anthropic.com

### Support Contacts

- **GCP Support**: https://cloud.google.com/support
- **Chrome Web Store Support**: https://support.google.com/chrome_webstore
- **Stack Overflow**: Tag questions with `chrome-extension`
- **Project Issues**: https://github.com/gpalumbo/notes/issues

### Pre-Submission Checklist

Before submitting, ensure:

#### Technical Requirements
- [ ] Package created with `make package-extension`
- [ ] All linting checks pass (`make lint-js`)
- [ ] Extension validated (`make validate-extension`)
- [ ] Package size under 10MB (should be ~1MB)
- [ ] Icons converted to PNG format
- [ ] Manifest V3 compliant

#### Store Listing Requirements
- [ ] Compelling description written
- [ ] 1-5 screenshots created showing key features
- [ ] Category selected (Productivity)
- [ ] Privacy policy written
- [ ] All required fields completed

#### Testing Requirements
- [ ] Extension tested on multiple websites
- [ ] All features working correctly
- [ ] No console errors
- [ ] Notes persist across browser restarts
- [ ] Color selection works properly
- [ ] Rich text editing functions correctly

### Success Tips

1. **Clear value proposition**: Make it obvious why users need your extension
2. **Quality screenshots**: Show the extension in action on real websites
3. **Responsive support**: Reply to user reviews and feedback
4. **Regular updates**: Keep the extension maintained and secure
5. **User-focused**: Listen to feedback and implement requested features
6. **Store optimization**: Update keywords and description based on performance
7. **Marketing & Growth**: Use reviews to guide future development

---

**Congratulations!** Your YAWN application is now deployed and ready for users. 🎉

**Ready to publish?** Run `make package-extension` and follow this guide step by step. Your Web Notes extension will be live on the Chrome Web Store soon! 🚀
