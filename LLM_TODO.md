# LLM Artifact Generation Implementation Plan

## Strategy: 3-Tier Hybrid Approach
- **Tier 1 (Default):** Gemini 2.0 Flash via app-supplied key (zero friction)
- **Tier 2 (Fallback):** Copy/paste prompt for any LLM (user controls cost)
- **Tier 3 (Power):** User API keys / Browser LLM (advanced users)

## Implementation Progress

### ✅ Phase 1.1: Database Schema (COMPLETE)
- Models: Note, NoteArtifact, UsageCost, OtherArtifactRequest
- Migrations: 7d6eb6277e6d, 90896c04e8d6
- Cost tracking fields added

### 🔄 Phase 1.2: Cost Tracking Service (NEXT)
- Create backend/app/services/cost_tracker.py
- Implement calculate_cost() with model pricing
- Models: Gemini 2.0 Flash, Claude 3.5, GPT-4

### 📋 Phase 1.3: Gemini Provider
- backend/app/services/gemini_provider.py
- Use google-generativeai package
- Implement rate limiting and error handling

### 📋 Phase 2.1: Context Assembly Service
- backend/app/services/context_builder.py
- Build prompts from note + page_section_html + highlighted_text
- Template system for different artifact types

### 📋 Phase 2.2: Enhanced Context
- Add related notes from same page
- Include site/page metadata
- Smart truncation for token limits

### 📋 Phase 3.1: Generate Endpoint
- POST /api/artifacts/generate/note/{note_id}
- Parameters: artifact_type, user_description, generation_mode
- Return: artifact content + cost estimate

### 📋 Phase 3.2: Preview Endpoint
- POST /api/artifacts/preview/note/{note_id}
- Show prompt without generating
- Return token count and cost estimate

### 📋 Phase 3.3: Paste Endpoint
- POST /api/artifacts/paste
- Accept pasted LLM responses
- Parse and store with proper attribution

### 📋 Phase 3.4: Usage Endpoint
- GET /api/artifacts/usage
- Daily/monthly cost aggregation
- Per-user and per-type breakdown

### 📋 Phase 3.5: Analytics Endpoint
- GET /api/artifacts/analytics
- Generation success rates
- Popular artifact types
- Cost trends

### 📋 Phase 4.1: Frontend Form UI
- Update note_detail.html template
- Artifact type dropdown
- User description textarea
- Generation mode selector

### 📋 Phase 4.2: Generate Flow UI
- Loading states during generation
- Cost preview before confirming
- Success/error messaging

### 📋 Phase 4.3: Copy/Paste Modal
- Instructions for manual LLM use
- Copy button for prompt
- Paste field for response

### 📋 Phase 4.4: Display UI
- Render artifacts in note detail
- Support markdown/code/images
- Edit/regenerate options

### 📋 Phase 4.5: Cost Dashboard
- Usage statistics page
- Cost breakdown charts
- Export usage data

### 📋 Phase 5.1: Image Generation
- Integrate DALL-E or Stable Diffusion
- POST /api/artifacts/generate-image
- Store image URLs in artifacts

### 📋 Phase 5.2: Image Display
- Render images in artifact display
- Thumbnail generation
- Full-size modal view

### 📋 Phase 5.3: Image Management
- Download generated images
- Regenerate with new prompts
- Gallery view for multiple images

## Optional Future Phases

### Phase 6: Browser-Native LLM
- Chrome built-in AI when available
- WebLLM integration for local models
- Zero-cost generation option

### Phase 7: User API Keys
- Secure key storage
- Per-user provider selection
- Usage tracking per key

### Phase 8: Advanced Features
- Batch generation for multiple notes
- Custom prompt templates
- Webhook integrations
