# Web Notes App - Architecture Spec

## Overview
Chrome extension for persistent sticky notes on webpages with DOM anchoring and cloud sync. Optimized for ~12 users, sporadic usage (4 hours/day).

## Tech Stack
- **Cloud**: GCP (Cloud Run + Cloud SQL PostgreSQL)
- **Backend**: Python FastAPI
- **Database**: PostgreSQL with temporal versioning (nearform/temporal_tables)
- **Deployment**: Cloud Run (scales to zero), db-f1-micro (auto-pause)
- **Auth**: Chrome Identity API + Google OAuth2 + JWT
- **Storage**: Cloud Storage for attachments
- **Cost Target**: $2-4/month

## Data Flow
1. Chrome extension uses `chrome.storage.local` for instant display
2. All CRUD operations happen locally first (optimistic updates)
3. Background sync every 5 minutes when active
4. Server stores authoritative data, handles conflicts
5. Last-write-wins conflict resolution

## Database Schema
```sql
-- Core tables (all with user_id FK for multi-tenancy)
users (id, chrome_user_id, email, display_name, is_admin)
sites (id, user_id, domain, title)
pages (id, site_id, user_id, url, title)
notes (id, page_id, user_id, content, anchor_data, position, highlighted_text, page_section_html)
note_artifacts (id, note_id, artifact_type, content, cost_usd, tokens_in/out, generation_source)

-- Sharing tables
user_site_shares (user_id, site_id, permission_level)
user_page_shares (user_id, page_id, permission_level)

-- Cost tracking
usage_costs (user_id, date, total_cost_usd, artifact_count)
other_artifact_requests (note_id, user_type_description, request_details)

-- All tables include: created_at, updated_at
-- Temporal versioning via triggers
```

## Chrome Extension Architecture
```javascript
// Storage structure
{
  notes: { 'url_hash': [notes_array] },
  categories: [...],
  sync_queue: [pending_operations],
  metadata: { last_sync, schema_version },
  auth: { token, refresh_token, user_info }
}
```

**Anchoring Strategy** (priority):
1. Text fragment + DOM path
2. XPath to element
3. CSS selector
4. Absolute coordinates (fallback)

## API Structure
- `/api/*` - REST endpoints for extension
- `/app/*` - Web UI pages (dashboard, management)
- `/api/sync` - Batch sync with delta updates
- `/api/artifacts/generate` - LLM generation (18-phase plan in LLM_TODO.md)
- `/api/sharing/*` - 13 endpoints for permissions

## Development Phases
1. ✅ Foundation - Extension architecture, security
2. ✅ MVP - Local storage, basic notes, manual sync
3. ✅ Enhanced - Rich text, categories, auto-sync
4. 🔄 Advanced - LLM integration (Phase 1.1 complete), sharing

## Design Constraints
- Stateless backend (horizontal scaling)
- Chrome-only initially
- Simple last-write-wins conflicts
- No real-time collaboration (batch sync)
- Local-first architecture

## Security
- XSS prevention via DOMPurify
- CSP in manifest.json
- JWT with refresh tokens
- Input validation everywhere
- Chrome Identity API for auth
