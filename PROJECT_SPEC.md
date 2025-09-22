# Web Notes App - Project Specification

## Overview
Chrome extension that allows users to add persistent sticky notes to any webpage. Notes anchor to DOM elements, sync across devices, and support rich text editing. Optimized for personal use with ~12 users max, sporadic usage (4 hours/day, not daily).

## Core Architecture Decisions

### Tech Stack
- **Cloud**: Google Cloud Platform (GCP)
- **Backend**: Python FastAPI
- **Database**: Cloud SQL PostgreSQL (db-f1-micro with auto-pause)
- **Deployment**: Cloud Run (scales to zero)
- **Storage**: Cloud Storage for attachments
- **Auth**: Chrome Identity API + Google OAuth validation
- **Cache**: None (PostgreSQL only, local-first architecture)
- **Monthly Cost**: ~$2-4

### Data Flow
**Local-First with Batch Sync**
1. Chrome extension uses `chrome.storage.local` for instant note display
2. All CRUD operations happen locally first (optimistic updates)
3. Background sync every 5 minutes when active
4. Server stores authoritative data, handles conflict resolution
5. Last-write-wins for conflicts at this scale

### Database Schema Highlights
- **Temporal Versioning**: nearform/temporal_tables (PL/pgSQL implementation)
- **Note Anchoring**: JSONB field stores DOM path, XPath, text fragments, fallback coordinates
- **Key Tables**: users, notes, categories, highlights, note_extensions, sync_queue
- **All tables**: Include created_at, updated_at timestamps

### Chrome Extension Architecture
```javascript
// Storage Structure
{
  notes: { 'url_hash': [notes_array] },
  categories: [...],
  sync_queue: [pending_operations],
  metadata: { last_sync, schema_version }
}
```

**Anchoring Strategy** (priority order):
1. Text fragment + DOM path
2. XPath to element  
3. CSS selector
4. Absolute coordinates (fallback)

### API Structure
Single FastAPI app serves both:
- `/api/*` - REST endpoints for Chrome extension
- `/app/*` - User-facing web pages (note management, settings)

**Key Endpoints**:
- `POST /api/sync` - Batch sync with delta updates
- `GET /api/notes?url=` - Fallback fetch for URL
- `CRUD /api/notes/{id}` - Individual note operations
- `GET /app/dashboard` - User web interface

### Deployment Configuration
```dockerfile
# Cloud Run with FastAPI
FROM python:3.11-slim
# Install: fastapi, uvicorn, sqlalchemy, alembic, google-auth
# Run: gunicorn -k uvicorn.workers.UvicornWorker
```

**Cloud SQL Config**:
- db-f1-micro (0.6GB RAM, shared CPU)
- Auto-pause after 10 minutes idle
- nearform/temporal_tables for versioning

### Development Phases
1. **Foundation** ✅: Chrome extension architecture, security hardening, context menu integration
2. **MVP**: Local storage, basic notes, manual sync
3. **Enhanced**: Rich text, categories, auto-sync
4. **Advanced**: Highlights, LLM integration, sharing

### Key Design Constraints
- Stateless backend (for horizontal scaling)
- Chrome-only initially (no cross-browser)
- Simple last-write-wins conflict resolution
- No real-time collaboration (batch sync only)

### Future Considerations
- Share tokens via invite codes
- LLM integration (Gemini/Claude API)
- Text highlighting with note association
- URL pattern migration tools

## Quick Start Context
This is a personal productivity tool, not enterprise software. Optimize for:
- Developer velocity over perfection
- Cost minimization (target <$10/month)
- Local performance over server features
- Simple solutions at this scale (dozens of notes, not millions)

## TO DO
- LLM integration - local or server side pro/cons
- Workflows - game master, school notes, 
