# Web Notes App - Incremental Development Plan

## Phase 1: Foundation (Week 1)

### 1.1 Development Environment Setup
**Tasks:**
- Initialize GitHub repository with structure
- Create PROJECT_SPEC.md and CLAUDE_CONTEXT.md
- Set up Python virtual environment
- Initialize FastAPI project with basic structure
- Create requirements.txt with core dependencies

**Manual Testing:**
- [ ] `uvicorn main:app --reload` starts successfully
- [ ] `/docs` endpoint shows SwaggerUI
- [ ] Basic health check endpoint returns 200

### 1.2 Local Database Setup
**Tasks:**
- Install PostgreSQL locally
- Create database schema (users, notes, categories tables only)
- Implement nearform/temporal_tables
- Create Alembic migration structure
- Add SQLAlchemy models for core tables

**Manual Testing:**
- [ ] `alembic upgrade head` runs without errors
- [ ] Can connect to local PostgreSQL
- [ ] Temporal tables triggers fire on INSERT/UPDATE/DELETE
- [ ] Verify history table populates correctly

### 1.3 Chrome Extension Skeleton
**Tasks:**
- Create manifest.json v3 with required permissions
- Implement basic content script that logs page URL
- Add extension popup with "Add Note" button
- Set up chrome.storage.local structure
- Create background service worker

**Manual Testing:**
- [ ] Extension loads in Chrome developer mode
- [ ] Content script runs on all pages
- [ ] Popup opens when clicking extension icon
- [ ] chrome.storage.local saves/retrieves test data
- [ ] Background worker stays alive during page navigation

## Phase 2: Core Functionality (Week 2)

### 2.1 Note Creation (Local Only)
**Tasks:**
- Implement note creation UI (floating div)
- Add DOM element detection on click
- Store note with anchor data in chrome.storage.local
- Create note positioning algorithm
- Add visual indicator for existing notes

**Manual Testing:**
- [ ] Click "Add Note" creates note at mouse position
- [ ] Note saves to local storage with correct URL
- [ ] Note includes DOM path and XPath
- [ ] Closing and reopening tab shows saved note
- [ ] Note appears in correct position after page reload

### 2.2 Note Display and Positioning
**Tasks:**
- Implement anchor resolution strategy (DOM → XPath → coordinates)
- Create note rendering with Shadow DOM
- Add minimize/expand functionality
- Handle page resize events
- Implement fallback positioning

**Manual Testing:**
- [ ] Notes appear on correct DOM elements
- [ ] Notes survive minor page layout changes
- [ ] Fallback to coordinates when DOM changes
- [ ] Notes reposition on window resize
- [ ] Shadow DOM prevents style conflicts

### 2.3 Note Editing
**Tasks:**
- Add contentEditable to note body
- Implement auto-save on blur
- Add character limit indicator
- Create delete button with confirmation
- Update local storage on changes

**Manual Testing:**
- [ ] Click note to edit text
- [ ] Changes save automatically on click outside
- [ ] Delete button removes note from page and storage
- [ ] Undo works within contentEditable
- [ ] Special characters save correctly

## Phase 3: Backend Integration (Week 3)

### 3.1 FastAPI CRUD Endpoints
**Tasks:**
- Implement user creation/auth endpoints
- Create note CRUD endpoints
- Add request/response validation with Pydantic
- Implement database connection pooling
- Add error handling middleware

**Manual Testing:**
- [ ] POST /api/notes creates note in database
- [ ] GET /api/notes?url=example.com returns notes
- [ ] PUT /api/notes/{id} updates note
- [ ] DELETE /api/notes/{id} removes note
- [ ] Invalid requests return appropriate errors

### 3.2 Chrome Identity Integration
**Tasks:**
- Add identity permission to manifest
- Implement getAuthToken in service worker
- Create auth state management
- Add token validation endpoint
- Handle token refresh logic

**Manual Testing:**
- [ ] Extension requests Chrome identity permission
- [ ] Successfully retrieves Google auth token
- [ ] Token validates against backend
- [ ] Expired tokens refresh automatically
- [ ] Sign out clears local and server state

### 3.3 Basic Sync Implementation
**Tasks:**
- Create sync queue in local storage
- Implement POST /api/sync endpoint
- Add last_sync timestamp tracking
- Create conflict detection
- Implement simple last-write-wins resolution

**Manual Testing:**
- [ ] Local changes queue when offline
- [ ] Sync uploads local changes to server
- [ ] Server changes download to local storage
- [ ] Conflicting changes resolved by timestamp
- [ ] Sync indicator shows status

## Phase 4: MVP Completion (Week 4)

### 4.1 Categories Implementation
**Tasks:**
- Add category selection to note UI
- Create default categories on user creation
- Implement category colors in notes
- Add category filter in extension popup
- Include categories in sync

**Manual Testing:**
- [ ] New users get 5 default categories
- [ ] Can assign category when creating note
- [ ] Category color displays on note
- [ ] Filter notes by category works
- [ ] Categories sync across devices

### 4.2 User Web Dashboard
**Tasks:**
- Create /app/dashboard route in FastAPI
- Implement Jinja2 templates or React SPA
- Add notes list view by site/page
- Create note search functionality
- Add bulk operations (delete multiple)

**Manual Testing:**
- [ ] Dashboard loads at app.domain.com/dashboard
- [ ] Shows all user's notes grouped by domain
- [ ] Search filters notes in real-time
- [ ] Can edit note from dashboard
- [ ] Changes in dashboard appear in extension

### 4.3 GCP Deployment
**Tasks:**
- Create Dockerfile for FastAPI app
- Set up Cloud SQL instance with auto-pause
- Configure Cloud Run service
- Set up Cloud Storage bucket
- Add production environment variables

**Manual Testing:**
- [ ] Cloud Run URL responds to health check
- [ ] Can create user account in production
- [ ] Extension connects to production API
- [ ] Notes persist in Cloud SQL
- [ ] Auto-pause activates after inactivity

### 4.4 Polish and Error Handling
**Tasks:**
- Add loading states for all async operations
- Implement retry logic for failed syncs
- Create user-friendly error messages
- Add sync status indicator
- Implement offline detection

**Manual Testing:**
- [ ] Loading spinner during sync
- [ ] Failed API calls retry 3 times
- [ ] Network errors show clear message
- [ ] Offline mode indication works
- [ ] Can work fully offline and sync later

## MVP Testing Checklist
**End-to-End Scenarios:**
- [ ] Install extension → Create account → Add note → See note on refresh
- [ ] Add note offline → Go online → Verify sync → Check dashboard
- [ ] Create note on site A → Navigate to site B → Return to A → Note persists
- [ ] Add 10 notes → Categorize them → Filter by category → Bulk delete
- [ ] Use on two browsers → Create notes on both → Verify bi-directional sync

---

## Phase 5: Enhanced Features (Months 2-3)

### 5.1 Rich Text Editing
- Integrate minimal rich text editor (Quill/TipTap)
- Add link support with click handling
- Implement basic formatting toolbar
- Store HTML in content_html field

### 5.2 Advanced Anchoring
- Add text highlighting support
- Implement highlight → note association
- Create visual connection between highlight and note
- Add pattern-based anchoring for dynamic content

### 5.3 URL Migration Tools
- Create pattern matching UI in dashboard
- Implement bulk note URL updates
- Add migration preview before applying
- Create undo functionality for migrations

### 5.4 Performance Optimization
- Implement virtual scrolling for many notes
- Add IndexedDB for better local storage
- Create smart sync (only sync visible pages)
- Optimize DOM mutation observers

## Phase 6: Advanced Features (Months 3-4)

### 6.1 Extended Note Data
- Add image attachment support
- Implement Cloud Storage uploads
- Create expanded view modal
- Add markdown support for long-form notes

### 6.2 Sharing System
- Generate invite codes
- Create share permissions (view/edit)
- Add shared notes indicator
- Implement real-time sync for shared notes

### 6.3 LLM Integration
- Add "Summarize Page" with context
- Implement "Generate Note from Selection"
- Create prompt templates
- Add Gemini/Claude API configuration

### 6.4 Advanced Organization
- Implement tags alongside categories
- Create smart collections (auto-categorize)
- Add full-text search with filters
- Build note templates system

## Phase 7: Scaling & Polish (Month 5+)

### 7.1 Multi-Browser Support
- Abstract Chrome-specific APIs
- Add Firefox extension variant
- Create Edge compatibility
- Implement Safari extension (if possible)

### 7.2 Collaboration Features
- Add commenting on shared notes
- Implement activity feed
- Create team workspaces
- Add @mentions and notifications

### 7.3 Analytics & Insights
- Track note creation patterns
- Generate usage reports
- Add personal knowledge graph
- Implement note connections/links

### 7.4 Enterprise Features (Optional)
- SSO authentication
- Audit logs
- Data export tools
- API for third-party integrations

## Development Principles

### For Each Feature:
1. **Write failing test first** (when adding automated tests)
2. **Implement minimum viable version**
3. **Manual test all scenarios**
4. **Update CLAUDE_CONTEXT.md**
5. **Commit with descriptive message**
6. **Update documentation**

### Definition of Done (MVP):
- [ ] Feature works offline
- [ ] Syncs properly when online
- [ ] Handles errors gracefully
- [ ] Updates UI optimistically
- [ ] Tested on 3+ websites
- [ ] Works with Chrome 100+

### Post-MVP Definition of Done:
- All MVP criteria plus:
- [ ] Automated tests exist
- [ ] Performance benchmarked
- [ ] Accessibility checked
- [ ] Documentation updated
