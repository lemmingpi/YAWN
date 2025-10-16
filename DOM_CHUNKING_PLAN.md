# DOM Chunking Implementation Plan

## Executive Summary

### Problem
Currently, the auto-note generation system truncates page DOM content at 50KB to fit within LLM token limits. This results in incomplete analysis of large pages, missing potentially important content and generating fewer useful study notes.

### Solution
Implement smart semantic chunking that splits large DOM content into multiple batches, processes chunks **in parallel with rate limiting** (3 concurrent requests), and aggregates results on the frontend. This enables complete page coverage while respecting token limits and maximizing performance.

### Impact
- **Complete Coverage**: Process entire pages regardless of size
- **5x Faster**: Parallel processing (3 chunks at a time) vs sequential
- **Better Quality**: More comprehensive note generation across all content
- **Simpler Backend**: No session state, stateless chunk processing
- **User Control**: No manual truncation or content loss
- **Scalability**: Handle pages from small to very large

---

## Current State Analysis

### Existing Flow
```
User triggers context menu "Generate Auto Notes with DOM"
  ↓
content.js: extractPageDOMForTest() - cleans and extracts DOM (truncates at 50KB)
  ↓
content.js: handleGenerateDOMTestNotes() - sends to background
  ↓
background.js: API_generateDOMTestNotes handler - registers page
  ↓
server-api.js: generateAutoNotesWithDOM() - POST to /auto-notes/pages/{id}/generate
  ↓
auto_notes.py router: generate_auto_notes() - receives request
  ↓
auto_note_service.py: generate_auto_notes() - builds prompt with DOM
  ↓
gemini_provider.py: generate_content_large() - sends to LLM
  ↓
auto_note_service.py: parses JSON response, validates selectors, creates Notes
  ↓
Returns AutoNoteGenerationResponse with notes array
  ↓
Extension reloads page to display new notes
```

### Current Limitations
1. **Hard 50KB truncation** in `content.js:2567-2569`
2. **No chunking mechanism** - single request only
3. **Content loss** for large pages (e.g., long articles, documentation)
4. **Alert shown to user** when truncating, but no alternative

### Files Involved

#### Frontend (Chrome Extension)
- `chrome-extension/content.js:2529-2578` - `extractPageDOMForTest()` function
- `chrome-extension/content.js:2583-2634` - `handleGenerateDOMTestNotes()` function
- `chrome-extension/background.js:476-484` - Message handler for DOM generation
- `chrome-extension/server-api.js:544-571` - `generateAutoNotesWithDOM()` method

#### Backend
- `backend/app/routers/auto_notes.py:28-104` - `generate_auto_notes()` endpoint
- `backend/app/services/auto_note_service.py:203-314` - `generate_auto_notes()` service
- `backend/app/schemas.py:864-908` - Request/Response schemas
- `backend/prompts/auto_notes/study_guide_generation.jinja2` - Prompt template

---

## Architecture Design

### Core Principles

1. **Semantic Chunking**: Split by meaningful HTML boundaries (sections, articles, divs)
2. **Token-Aware**: Estimate tokens and target ~40KB per chunk (buffer for safety)
3. **Context Preservation**: Include parent hierarchy for accurate CSS selectors
4. **Batched Parallel Processing**: Process 3 chunks at a time (frontend rate limiting)
5. **Stateless Backend**: No session management, each chunk independent
6. **Frontend Aggregation**: Frontend collects and aggregates all results
7. **Progress Feedback**: Show user "Processing batch X of Y" with live updates

### Token Estimation
- **Heuristic**: 1 token ≈ 4 characters (conservative for HTML)
- **Target**: ~40KB per chunk (~10,000 tokens)
- **Buffer**: Leave headroom for prompt template, instructions, context

### Chunking Strategy

#### Semantic Boundaries (Priority Order)
1. `<section>` elements with meaningful IDs/classes
2. `<article>` elements
3. `<div>` elements with semantic classes (content, main, article-body)
4. `<div>` elements with IDs
5. Major heading boundaries (`<h1>`, `<h2>`)
6. Paragraph groups if sections still too large

#### Chunk Structure
```javascript
{
  chunk_index: 0,           // 0-based index
  total_chunks: 5,          // Total number of chunks
  chunk_dom: "<html>...</html>", // Cleaned DOM fragment
  parent_context: {         // For selector accuracy
    body_classes: ["article", "post"],
    main_id: "content",
    document_structure: "article > div.main > section"
  },
  batch_id: "auto_abc123", // Frontend-generated batch ID (shared across all chunks)
  position_offset: 40      // Position offset for this chunk (index * 20)
}
```

### Data Flow for Chunked Processing

```
User triggers "Generate Auto Notes with DOM"
  ↓
content.js: extractPageDOMInChunks() - returns array of chunks
  ↓
content.js: Generate batch_id (shared across all chunks)
  ↓
content.js: handleGenerateDOMTestNotes() - batched parallel processing
  ↓
  FOR EACH BATCH OF 3 CHUNKS (in parallel):
    background.js: API_generateDOMTestNotesChunk - sends chunk (×3)
    ↓
    server-api.js: generateAutoNotesWithDOMChunk() - POST with chunk metadata (×3)
    ↓
    auto_notes.py: generate_auto_notes_chunked() - stateless endpoint (×3)
    ↓
    auto_note_service.py: generate_auto_notes_chunked() - processes chunk (×3)
    ↓
    Saves notes to DB with batch_id, returns immediately (×3)
    ↓
    Returns ChunkedAutoNoteResponse with notes from this chunk (×3)
  ↓
  WAIT for batch to complete, then process next batch
  ↓
content.js: Aggregates all successful results
  ↓
  - Flatten all notes arrays
  - Sum costs and tokens
  - Calculate success rate
  ↓
Extension displays all notes (DB handles deduplication via batch_id)
```

---

## Implementation Phases

### Phase 1: Frontend Chunking (Chrome Extension)

#### Phase 1.1: Add Utility Functions to `content.js`

**Location**: `chrome-extension/content.js` (after `extractPageDOMForTest()`)

**New Functions**:

```javascript
// Configuration constant for rate limiting
const MAX_CONCURRENT_CHUNKS = 3;  // Process 3 chunks at a time

/**
 * Estimate token count from text
 * @param {string} text - Text to estimate
 * @returns {number} Estimated token count
 */
function estimateTokenCount(text) {
  // Conservative estimate: 1 token ≈ 4 characters for HTML
  return Math.ceil(text.length / 4);
}

/**
 * Find semantic boundaries in HTML for chunking
 * @param {HTMLElement} element - Root element to analyze
 * @returns {Array<HTMLElement>} Array of boundary elements
 */
function findSemanticBoundaries(element) {
  // Priority order for splitting
  const selectors = [
    'section[id], section[class]',
    'article',
    'div[class*="content"], div[class*="main"], div[class*="article"]',
    'div[id]',
    'h1, h2'
  ];

  for (const selector of selectors) {
    const boundaries = Array.from(element.querySelectorAll(selector));
    if (boundaries.length > 1) {
      return boundaries;
    }
  }

  // Fallback: split by paragraphs
  return Array.from(element.querySelectorAll('p, div'));
}

/**
 * Extract parent context for selector accuracy
 * @param {HTMLElement} element - Element to extract context from
 * @returns {Object} Context metadata
 */
function extractParentContext(element) {
  const body = element.querySelector('body') || element;
  return {
    body_classes: Array.from(body.classList || []),
    body_id: body.id || null,
    main_container: body.querySelector('main, [role="main"]')?.tagName.toLowerCase(),
    document_title: element.querySelector('title')?.textContent || ''
  };
}

/**
 * Chunk DOM content into semantic pieces
 * @param {string} htmlContent - Full HTML content
 * @param {number} maxTokensPerChunk - Maximum tokens per chunk
 * @returns {Array<Object>} Array of chunk objects
 */
function chunkDOMContent(htmlContent, maxTokensPerChunk = 10000) {
  const maxCharsPerChunk = maxTokensPerChunk * 4; // ~4 chars per token
  const minCharsPerChunk = 10000; // Minimum ~2500 tokens to avoid tiny chunks

  // If small enough, return as single chunk
  if (htmlContent.length <= maxCharsPerChunk) {
    return [{
      chunk_index: 0,
      total_chunks: 1,
      chunk_dom: htmlContent,
      parent_context: null,
      is_final_chunk: true
    }];
  }

  // Parse HTML into DOM
  const parser = new DOMParser();
  const doc = parser.parseFromString(htmlContent, 'text/html');
  const body = doc.body;

  // Extract parent context once
  const parentContext = extractParentContext(doc.documentElement);

  // Find semantic boundaries
  const boundaries = findSemanticBoundaries(body);

  // Group boundaries into chunks
  const chunks = [];
  let currentChunk = [];
  let currentSize = 0;

  for (const element of boundaries) {
    const elementHTML = element.outerHTML;
    const elementSize = elementHTML.length;

    // If adding this would exceed limit and we have content, start new chunk
    if (currentSize + elementSize > maxCharsPerChunk && currentChunk.length > 0) {
      chunks.push(currentChunk);
      currentChunk = [element];
      currentSize = elementSize;
    } else {
      currentChunk.push(element);
      currentSize += elementSize;
    }
  }

  // Add final chunk
  if (currentChunk.length > 0) {
    chunks.push(currentChunk);
  }

  // Merge small chunks to meet minimum size requirement
  const mergedChunks = [];
  let currentMerged = [];
  let currentMergedSize = 0;

  for (const chunk of chunks) {
    const chunkSize = chunk.reduce((sum, el) => sum + el.outerHTML.length, 0);

    // If current merged chunk is empty, start with this chunk
    if (currentMerged.length === 0) {
      currentMerged = chunk;
      currentMergedSize = chunkSize;
    }
    // If current merged is too small and adding this won't exceed max, merge
    else if (currentMergedSize < minCharsPerChunk &&
             currentMergedSize + chunkSize <= maxCharsPerChunk) {
      currentMerged = currentMerged.concat(chunk);
      currentMergedSize += chunkSize;
    }
    // Otherwise, finalize current merged chunk and start new one
    else {
      mergedChunks.push(currentMerged);
      currentMerged = chunk;
      currentMergedSize = chunkSize;
    }
  }

  // Add final merged chunk
  if (currentMerged.length > 0) {
    mergedChunks.push(currentMerged);
  }

  // Build chunk objects
  const totalChunks = mergedChunks.length;
  return mergedChunks.map((elements, index) => {
    const chunkDOM = elements.map(el => el.outerHTML).join('\n');
    return {
      chunk_index: index,
      total_chunks: totalChunks,
      chunk_dom: chunkDOM,
      parent_context: parentContext,
      is_final_chunk: index === totalChunks - 1
    };
  });
}

/**
 * Extract page DOM in chunks for large pages
 * @returns {Array<Object>} Array of chunk objects with metadata
 */
function extractPageDOMInChunks() {
  try {
    console.log("[Web Notes] Extracting page DOM in chunks for auto-note generation");

    // Clone and clean document (same as extractPageDOMForTest)
    const clonedDoc = document.documentElement.cloneNode(true);

    const removeSelectors = ["script", "style", "noscript", "iframe", "object", "embed", "svg", ".web-note"];
    removeSelectors.forEach(selector => {
      clonedDoc.querySelectorAll(selector).forEach(el => el.remove());
    });

    const preserveAttrs = ["id", "class", "data-section", "data-paragraph", "role", "aria-label"];
    clonedDoc.querySelectorAll("*").forEach(el => {
      const attrs = Array.from(el.attributes);
      attrs.forEach(attr => {
        if (!preserveAttrs.includes(attr.name)) {
          el.removeAttribute(attr.name);
        }
      });
    });

    const bodyElement = clonedDoc.querySelector("body");
    if (!bodyElement) {
      console.warn("[Web Notes] No body element found");
      return [{
        chunk_index: 0,
        total_chunks: 1,
        chunk_dom: document.body.innerHTML.substring(0, 50000),
        parent_context: null,
        is_final_chunk: true
      }];
    }

    let contentHTML = bodyElement.innerHTML;
    contentHTML = contentHTML.replace(/\s+/g, " ").trim();

    // Chunk the content
    const chunks = chunkDOMContent(contentHTML);

    const totalSize = contentHTML.length;
    console.log(`[Web Notes] Split ${Math.round(totalSize / 1000)}KB into ${chunks.length} chunks`);

    return chunks;
  } catch (error) {
    console.error("[Web Notes] Error extracting page DOM in chunks:", error);
    throw error;
  }
}
```

**Implementation Details**:
- Add functions after line 2578 in `content.js`
- Use existing DOM cleaning logic from `extractPageDOMForTest()`
- Generate unique session IDs for chunk tracking
- Log chunk statistics for debugging

**Testing Requirements**:
- Test with small pages (< 40KB) → single chunk
- Test with medium pages (40-200KB) → 2-5 chunks
- Test with large pages (> 200KB) → 5+ chunks
- Verify semantic boundaries are respected
- Check parent context extraction

---

#### Phase 1.2: Update `handleGenerateDOMTestNotes()` Function

**Location**: `chrome-extension/content.js:2583-2634`

**Modifications**:

```javascript
/**
 * Handle DOM test auto-notes generation with batched parallel processing
 */
async function handleGenerateDOMTestNotes() {
  try {
    console.log("[Web Notes] Starting DOM test auto-note generation with chunking");

    // Check authentication
    const isAuth = await isServerAuthenticated();
    if (!isAuth) {
      alert("Please sign in to generate auto notes");
      return;
    }

    // Extract page DOM in chunks
    const chunks = extractPageDOMInChunks();
    const totalChunks = chunks.length;

    console.log(`[Web Notes] Processing ${totalChunks} chunk(s) in batches of ${MAX_CONCURRENT_CHUNKS}`);

    // Generate batch ID upfront (shared across all chunks)
    const batchId = `auto_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Add batch_id and position_offset to all chunks
    chunks.forEach((chunk, index) => {
      chunk.batch_id = batchId;
      chunk.position_offset = index * 20;  // Stagger positions
    });

    // Show initial progress
    const numBatches = Math.ceil(totalChunks / MAX_CONCURRENT_CHUNKS);
    if (totalChunks > 1) {
      alert(
        `Large page detected! Processing ${totalChunks} chunks in ${numBatches} batches.\n\n` +
        `This will take approximately ${Math.ceil(numBatches * 30 / 60)} minute(s). You'll be notified when complete.`
      );
    }

    // Get page info and register page ONCE
    const pageUrl = window.location.href;
    const pageTitle = document.title || "Untitled";

    // Register page first (before any chunks)
    const pageData = await chrome.runtime.sendMessage({
      action: "API_registerPage",
      url: pageUrl,
      title: pageTitle
    });

    if (!pageData || !pageData.id) {
      alert("Failed to register page. Please try again.");
      return;
    }

    console.log(`[Web Notes] Page registered with ID: ${pageData.id}`);

    // Process chunks in batches (parallel within batch)
    const allResults = [];

    for (let i = 0; i < chunks.length; i += MAX_CONCURRENT_CHUNKS) {
      const batch = chunks.slice(i, i + MAX_CONCURRENT_CHUNKS);
      const batchNum = Math.floor(i / MAX_CONCURRENT_CHUNKS) + 1;

      console.log(`[Web Notes] Processing batch ${batchNum}/${numBatches} (chunks ${i + 1}-${Math.min(i + MAX_CONCURRENT_CHUNKS, totalChunks)})`);

      // Process batch in parallel
      const batchPromises = batch.map(chunk =>
        chrome.runtime.sendMessage({
          action: "API_generateDOMTestNotesChunk",
          pageId: pageData.id,  // Use the already-registered page ID
          chunkData: chunk,
        }).catch(error => ({
          success: false,
          error: error.message,
          chunk_index: chunk.chunk_index
        }))
      );

      // Wait for all chunks in this batch to complete
      const batchResults = await Promise.all(batchPromises);
      allResults.push(...batchResults);

      console.log(`[Web Notes] Batch ${batchNum}/${numBatches} complete`);
    }

    // Aggregate successful results
    const successful = allResults.filter(r => r.success && r.data);
    const failed = allResults.filter(r => !r.success || !r.data);

    const allNotes = successful.flatMap(r => r.data.notes || []);
    const totalCost = successful.reduce((sum, r) => sum + (r.data.cost_usd || 0), 0);
    const totalTokens = successful.reduce((sum, r) => sum + (r.data.tokens_used || 0), 0);

    // Show final results
    if (allNotes.length > 0) {
      let message = `Successfully generated ${allNotes.length} study notes from ${successful.length}/${totalChunks} chunks!\n\n` +
        `Batch ID: ${batchId}\n` +
        `Total Cost: $${totalCost.toFixed(4)}\n` +
        `Total Tokens: ${totalTokens.toLocaleString()}`;

      if (failed.length > 0) {
        message += `\n\nWarning: ${failed.length} chunk(s) failed to process.`;
      }

      alert(message);

      // Refresh the page to load the new notes
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } else {
      alert(
        `No notes were generated from ${totalChunks} chunk(s).\n` +
        `Successful: ${successful.length}, Failed: ${failed.length}\n\n` +
        `The content might not have sufficient information or all chunks failed.`
      );
    }
  } catch (error) {
    console.error("[Web Notes] Error generating DOM test notes:", error);
    alert(`Failed to generate auto notes: ${error.message}`);
  }
}
```

**Implementation Details**:
- Replace existing function at lines 2583-2634
- Add `MAX_CONCURRENT_CHUNKS` constant at top of file
- Use batched parallel processing with `Promise.all()`
- Frontend generates `batch_id` (no backend session needed)
- Accumulate results from all chunks with error handling
- Show batch progress alerts

**Testing Requirements**:
- Verify batched parallel processing (3 at a time)
- Check error handling for failed chunks (continue with others)
- Validate result accumulation across batches
- Test progress messages for multiple batches
- Verify batch_id is used consistently

---

#### Phase 1.3: Update `background.js` Message Handler

**Location**: `chrome-extension/background.js:476-484`

**Modifications**:

```javascript
// In the chrome.runtime.onMessage.addListener handler
// Add new case after line 484:

case "API_registerPage":
  // Register the page (called once before chunks)
  result = await ServerAPI.registerPage(message.url, message.title);
  break;

case "API_generateDOMTestNotesChunk":
  // Generate notes with DOM chunk (page already registered)
  result = await ServerAPI.generateAutoNotesWithDOMChunk(message.pageId, message.chunkData);
  break;
```

**Implementation Details**:
- Add two cases after existing `API_generateDOMTestNotes` handler
- `API_registerPage`: Handles page registration (called once)
- `API_generateDOMTestNotesChunk`: Processes chunks (uses pageId directly)
- No duplicate registration in chunk handler

**Testing Requirements**:
- Verify page registration happens exactly once
- Check pageId is passed correctly to chunks
- Verify chunk metadata is passed correctly

---

#### Phase 1.4: Update `server-api.js` with Chunk Support

**Location**: `chrome-extension/server-api.js` (after line 571)

**New Method**:

```javascript
/**
 * Generate auto notes with DOM chunk
 * @param {number} pageId - Page ID
 * @param {Object} chunkData - Chunk metadata and content
 * @returns {Promise<Object>} Generation response
 */
async generateAutoNotesWithDOMChunk(pageId, chunkData) {
  try {
    if (!this.isAuthenticated()) {
      throw new Error("User not authenticated - cannot generate auto notes");
    }

    const requestData = {
      llm_provider_id: 1, // Default to Gemini
      template_type: "study_guide",
      chunk_index: chunkData.chunk_index,
      total_chunks: chunkData.total_chunks,
      chunk_dom: chunkData.chunk_dom,
      parent_context: chunkData.parent_context,
      batch_id: chunkData.batch_id,  // Frontend-generated batch ID
      position_offset: chunkData.position_offset,  // Position offset for this chunk
      custom_instructions:
        "Use the provided DOM content chunk to generate precise study notes. " +
        `This is chunk ${chunkData.chunk_index + 1} of ${chunkData.total_chunks}.`,
    };

    const response = await this.makeRequest(`/auto-notes/pages/${pageId}/generate/chunked`, {
      method: "POST",
      body: JSON.stringify(requestData),
    });

    const result = await response.json();
    console.log(
      `[Web Notes] Generated ${result.notes?.length || 0} notes from chunk ${chunkData.chunk_index + 1}/${chunkData.total_chunks}`
    );
    return result;
  } catch (error) {
    console.error("[Web Notes] Failed to generate auto notes with DOM chunk:", error);
    throw error;
  }
}
```

**Implementation Details**:
- Add method after `generateAutoNotesWithDOM()` at line 571
- Send chunk metadata including `batch_id` and `position_offset`
- Use new `/generate/chunked` endpoint
- No session management needed

**Testing Requirements**:
- Verify chunk metadata is sent correctly (especially batch_id)
- Check authentication handling
- Test error propagation
- Verify parallel requests work correctly

---

### Phase 2: Backend Schema & Endpoints

#### Phase 2.1: Add Chunked Request/Response Schemas

**Location**: `backend/app/schemas.py` (after line 946)

**New Schemas**:

```python
class ChunkedAutoNoteRequest(BaseModel):
    """Schema for chunked auto note generation requests (stateless)."""

    llm_provider_id: int = Field(1, description="LLM provider ID to use")
    template_type: str = Field(
        "study_guide",
        description="Type of template: 'study_guide' or 'content_review'",
    )
    chunk_index: int = Field(..., ge=0, description="Index of current chunk (0-based)")
    total_chunks: int = Field(..., gt=0, description="Total number of chunks")
    chunk_dom: str = Field(..., min_length=1, description="DOM content for this chunk")
    parent_context: Optional[Dict[str, Any]] = Field(
        None, description="Parent document context for selector accuracy"
    )
    batch_id: str = Field(..., description="Frontend-generated batch ID (shared across all chunks)")
    position_offset: int = Field(0, description="Position offset for notes in this chunk")
    custom_instructions: Optional[str] = Field(
        None, description="Optional custom instructions for generation"
    )


class ChunkedAutoNoteResponse(BaseModel):
    """Schema for single chunk response (stateless, no aggregation)."""

    notes: List[GeneratedNoteData] = Field(
        ..., description="Notes generated from this chunk"
    )
    chunk_index: int = Field(..., description="Index of processed chunk")
    total_chunks: int = Field(..., description="Total chunks in request")
    batch_id: str = Field(..., description="Batch ID for this set of notes")
    tokens_used: int = Field(..., description="Tokens consumed for this chunk")
    cost_usd: float = Field(..., description="Cost for this chunk in USD")
    input_tokens: int = Field(..., description="Input tokens for this chunk")
    output_tokens: int = Field(..., description="Output tokens for this chunk")
    generation_time_ms: int = Field(..., description="Generation time for this chunk in milliseconds")
```

**Implementation Details**:
- Add after `BatchDeleteResponse` at line 946
- Reuse existing `GeneratedNoteData` schema
- Single response type (no partial/final distinction)
- Backend is stateless - no session management needed

**Testing Requirements**:
- Validate schema with Pydantic
- Test serialization/deserialization
- Check field constraints
- Verify batch_id field works correctly

---

#### Phase 2.2: Create Chunked Endpoint

**Location**: `backend/app/routers/auto_notes.py` (after line 104)

**New Endpoint**:

```python
@router.post(
    "/pages/{page_id}/generate/chunked",
    response_model=ChunkedAutoNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_auto_notes_chunked(
    page_id: int,
    request: ChunkedAutoNoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ChunkedAutoNoteResponse:
    """
    Generate AI-powered study notes from a DOM chunk (stateless).

    Each chunk is processed independently with no backend session management.
    Frontend aggregates results from all chunks.

    Args:
        page_id: ID of page to generate notes for
        request: Chunked generation configuration
        db: Database session
        current_user: Authenticated user

    Returns:
        Single chunk response with notes and metadata

    Raises:
        HTTPException: If page not found or generation fails
    """
    logger.info(
        f"Chunked auto note generation requested for page_id={page_id}, "
        f"chunk {request.chunk_index + 1}/{request.total_chunks}, "
        f"batch_id={request.batch_id}, user_id={current_user.id}"
    )

    service = AutoNoteService(db)

    try:
        result = await service.generate_auto_notes_chunked(
            page_id=page_id,
            user_id=current_user.id,
            llm_provider_id=request.llm_provider_id,
            template_type=request.template_type,
            chunk_index=request.chunk_index,
            total_chunks=request.total_chunks,
            chunk_dom=request.chunk_dom,
            parent_context=request.parent_context,
            batch_id=request.batch_id,
            position_offset=request.position_offset,
            custom_instructions=request.custom_instructions,
        )

        # Return single chunk response
        notes_data = [
            GeneratedNoteData(
                id=note.id,
                content=note.content,
                highlighted_text=note.highlighted_text,
                position_x=note.position_x,
                position_y=note.position_y,
            )
            for note in result["notes"]
        ]

        return ChunkedAutoNoteResponse(
            notes=notes_data,
            chunk_index=request.chunk_index,
            total_chunks=request.total_chunks,
            batch_id=request.batch_id,
            tokens_used=result["tokens_used"],
            cost_usd=result["cost_usd"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            generation_time_ms=result["generation_time_ms"],
        )

    except ValueError as e:
        logger.error(f"Value error during chunked auto note generation: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during chunked auto note generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auto notes from chunk: {str(e)}",
        )
```

**Implementation Details**:
- Add after existing `generate_auto_notes()` endpoint
- No need for `Union` import - single response type
- Stateless endpoint - no session management
- Log chunk and batch_id for debugging

**Testing Requirements**:
- Test with single chunk
- Test with multiple parallel chunks
- Verify batch_id is stored correctly in DB
- Verify error handling
- Test concurrent requests (3 at a time)

---

### Phase 3: Service Layer

#### Phase 3.1: Add `generate_auto_notes_chunked()` Method (Stateless)

**Location**: `backend/app/services/auto_note_service.py` (after line 314)

**New Method**:

```python
async def generate_auto_notes_chunked(
    self,
    page_id: int,
    user_id: int,
    llm_provider_id: int,
    chunk_index: int,
    total_chunks: int,
    chunk_dom: str,
    batch_id: str,
    position_offset: int = 0,
    template_type: str = "study_guide",
    parent_context: Optional[Dict[str, Any]] = None,
    custom_instructions: Optional[str] = None,
) -> Dict:
    """
    Generate AI-powered study notes from a DOM chunk (stateless).

    Each chunk is processed independently. Frontend-generated batch_id links
    all notes together. No backend session management.

    Args:
        page_id: ID of page to generate notes for
        user_id: ID of user creating the notes
        llm_provider_id: LLM provider to use
        chunk_index: Index of current chunk (0-based)
        total_chunks: Total number of chunks
        chunk_dom: DOM content for this chunk
        batch_id: Frontend-generated batch ID (shared across all chunks)
        position_offset: Position offset for notes in this chunk
        template_type: Type of template ('study_guide' or 'content_review')
        parent_context: Parent document context for selectors
        custom_instructions: Optional user instructions

    Returns:
        Dictionary with notes and metadata for this chunk only

    Raises:
        ValueError: If page not found
    """
    start_time = time.time()

    logger.info(
        f"Processing chunk {chunk_index + 1}/{total_chunks}, "
        f"batch_id={batch_id}, page_id={page_id}"
    )

    # Fetch page
    result = await self.db.execute(
        select(Page).options(selectinload(Page.site)).where(Page.id == page_id)
    )
    page = result.scalar_one_or_none()

    if not page:
        raise ValueError(f"Page with ID {page_id} not found")

    # Build prompt with chunk context
    chunk_instructions = (
        f"Processing chunk {chunk_index + 1} of {total_chunks}. "
        f"Generate notes only for content in this chunk. "
    )
    if custom_instructions:
        chunk_instructions += custom_instructions

    prompt = await self._build_prompt(
        page,
        template_type,
        chunk_instructions,
        page_source=None,
        page_dom=chunk_dom,
    )

    logger.info(f"Chunk {chunk_index + 1}/{total_chunks}: Prompt built, {len(prompt)} chars")

    # Generate using Gemini
    provider = await create_gemini_provider()
    generation_result = await provider.generate_content_large(prompt=prompt)

    logger.info(
        f"Chunk {chunk_index + 1}/{total_chunks}: Generation complete, "
        f"{generation_result['input_tokens']} in, {generation_result['output_tokens']} out"
    )

    # Parse JSON response
    generated_content = generation_result["content"]

    # Remove markdown code blocks if present
    if generated_content.startswith("```json"):
        generated_content = generated_content.replace("```json", "", 1)
    if generated_content.startswith("```"):
        generated_content = generated_content.replace("```", "", 1)
    if generated_content.endswith("```"):
        generated_content = generated_content.rsplit("```", 1)[0]

    generated_content = generated_content.strip()

    try:
        parsed_data = json.loads(generated_content)
        notes_data = parsed_data.get("notes", [])
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response for chunk {chunk_index + 1}: {e}")
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    # Create Note records for this chunk
    created_notes = []
    if notes_data:
        for idx, note_data in enumerate(notes_data):
            # Extract selectors
            css_selector = note_data.get("css_selector")
            xpath = note_data.get("xpath")

            # Fallback to old format
            if not css_selector and not xpath:
                position = note_data.get("position") or note_data.get("position_hint")
                if position:
                    css_selector, xpath = detect_selector_type(position)

            # Validate and repair selectors if chunk_dom available
            validation_metadata = None
            if chunk_dom and css_selector:
                highlighted_text = note_data.get("highlighted_text", "")

                is_valid, match_count, _ = self._validator.validate_selector(
                    chunk_dom, css_selector
                )

                if not is_valid:
                    repair_result = self._validator.repair_selector(
                        chunk_dom, highlighted_text, css_selector, xpath
                    )

                    if repair_result["success"]:
                        css_selector = repair_result["css_selector"]
                        xpath = repair_result["xpath"]
                        validation_metadata = {
                            "original_selector": note_data.get("css_selector"),
                            "was_repaired": True,
                            "match_count": repair_result["match_count"],
                            "text_similarity": repair_result["text_similarity"],
                        }

            # Build anchor_data
            anchor_data: Dict[str, Any] = {
                "auto_generated": True,
                "chunk_index": chunk_index,
            }

            if validation_metadata:
                anchor_data["validation"] = validation_metadata

            if css_selector:
                anchor_data["elementSelector"] = css_selector
            if xpath:
                anchor_data["elementXPath"] = xpath

            # Build selectionData
            highlighted_text = note_data.get("highlighted_text", "")
            if highlighted_text and (css_selector or xpath):
                selector = css_selector or xpath
                anchor_data["selectionData"] = {
                    "selectedText": highlighted_text,
                    "startSelector": selector,
                    "endSelector": selector,
                    "startOffset": 0,
                    "endOffset": len(highlighted_text),
                    "startContainerType": 3,
                    "endContainerType": 3,
                    "commonAncestorSelector": selector,
                }

            # Create unique server_link_id
            server_link_id = f"{batch_id}_{chunk_index}_{idx}"

            note = Note(
                content=note_data.get("commentary", ""),
                highlighted_text=highlighted_text,
                page_section_html=None,
                position_x=100 + position_offset + (idx * 20),
                position_y=100 + position_offset + (idx * 20),
                anchor_data=anchor_data,
                page_id=page_id,
                user_id=user_id,
                generation_batch_id=batch_id,  # Use frontend-provided batch_id
                server_link_id=server_link_id,
                is_active=True,
            )
            self.db.add(note)
            created_notes.append(note)

        await self.db.commit()

        # Refresh to get IDs
        for note in created_notes:
            await self.db.refresh(note)

        logger.info(
            f"Chunk {chunk_index + 1}/{total_chunks}: Created {len(created_notes)} notes"
        )

    # Calculate generation time for this chunk
    generation_time_ms = int((time.time() - start_time) * 1000)

    # Return results for this chunk only (stateless)
    return {
        "notes": created_notes,
        "tokens_used": generation_result["input_tokens"] + generation_result["output_tokens"],
        "cost_usd": generation_result["cost"],
        "input_tokens": generation_result["input_tokens"],
        "output_tokens": generation_result["output_tokens"],
        "generation_time_ms": generation_time_ms,
    }
```

**Implementation Details**:
- Add after existing `generate_auto_notes()` method
- **No session state management** - completely stateless
- Use frontend-provided `batch_id` for linking notes
- Use `position_offset` for staggered note positioning
- Reuse existing validation and selector repair logic
- Return results immediately (no waiting for other chunks)

**Testing Requirements**:
- Test single chunk processing
- Test parallel chunk processing (simulate 3 concurrent)
- Verify batch_id is stored correctly in DB
- Verify position_offset works correctly
- Test error handling
- Verify no race conditions with concurrent requests

---

#### Phase 3.2: Update Prompt Template for Chunking

**Location**: `backend/prompts/auto_notes/study_guide_generation.jinja2`

**Modifications**:

Add context about chunking at the beginning of the template:

```jinja2
{% if chunk_index is defined %}
**CHUNKING CONTEXT**:
This is chunk {{ chunk_index + 1 }} of {{ total_chunks }} from a large page.
- Generate notes ONLY for content visible in this chunk
- Use CSS selectors relative to the full document structure (not just this chunk)
- The page may have been split at semantic boundaries (sections, articles, divs)
- Previous/next chunks may contain related content, but focus on this chunk

{% endif %}
```

**Implementation Details**:
- Add variables: `chunk_index`, `total_chunks`
- Pass from `_build_prompt()` when chunking
- Instruct LLM about partial content

**Testing Requirements**:
- Verify template renders with chunk context
- Test without chunk variables (backward compatible)
- Validate selector generation accuracy

---

### Phase 4: Testing & Refinement

#### Phase 4.1: Functional Testing

**Test Cases**:

1. **Small Page (< 40KB)**
   - Should use single chunk
   - No chunking overhead
   - Identical behavior to non-chunked

2. **Medium Page (40-150KB)**
   - Should split into 2-4 chunks
   - All chunks processed successfully
   - Notes distributed across chunks

3. **Large Page (> 200KB)**
   - Should split into 5+ chunks
   - Sequential processing
   - Progress feedback shown
   - All notes aggregated

4. **Error Scenarios**
   - Network failure mid-chunk → retry logic
   - LLM error on one chunk → continue with others
   - Invalid session ID → error message
   - Browser refresh during processing → session timeout

**Testing Files**:
- Create test HTML pages of various sizes
- Mock DOM structures with semantic boundaries
- Test with real Wikipedia articles, documentation pages

---

#### Phase 4.2: Error Handling & Retry

**Enhancements**:

1. **Retry Failed Chunks**
   ```javascript
   // In content.js
   async function processChunkWithRetry(chunk, maxRetries = 3) {
     for (let attempt = 1; attempt <= maxRetries; attempt++) {
       try {
         return await sendChunkToBackend(chunk);
       } catch (error) {
         if (attempt === maxRetries) throw error;
         await sleep(1000 * attempt); // Exponential backoff
       }
     }
   }
   ```

2. **Session Timeout**
   ```python
   # In auto_note_service.py
   SESSION_TIMEOUT = 600  # 10 minutes

   def cleanup_old_sessions():
     now = time.time()
     for session_id, session in list(_chunk_sessions.items()):
       if now - session["start_time"] > SESSION_TIMEOUT:
         del _chunk_sessions[session_id]
   ```

3. **Partial Success Handling**
   - Track which chunks succeeded
   - Allow user to retry failed chunks only
   - Display partial results even if some chunks fail

---

#### Phase 4.3: Performance Optimization

**Optimizations**:

1. **Parallel Validation**
   - Validate selectors in parallel after generation
   - Use asyncio.gather() for multiple validators

2. **Smarter Chunking**
   - Learn optimal chunk sizes based on page structure
   - Adjust boundaries to avoid splitting mid-paragraph

3. **Caching**
   - Cache cleaned DOM for retry scenarios
   - Cache page registration to avoid duplicate lookups

4. **Streaming Responses**
   - Show notes as each chunk completes (don't wait for all)
   - Progressive rendering in extension

---

#### Phase 4.4: User Experience Improvements

**Enhancements**:

1. **Progress Bar**
   - Replace alerts with persistent progress indicator
   - Show current chunk, total chunks, notes generated so far

2. **Cancel Operation**
   - Allow user to cancel mid-processing
   - Clean up session and partial notes

3. **Preview Before Processing**
   - Show estimated chunks and cost before starting
   - Give user option to proceed or cancel

4. **Chunk Size Configuration**
   - Let advanced users adjust chunk size
   - Store preference in extension settings

---

## Edge Cases & Error Handling

### Edge Case Matrix

| Scenario | Behavior | Mitigation |
|----------|----------|------------|
| Page < 40KB | Single chunk, no overhead | Auto-detect, use non-chunked endpoint |
| Very large section (> 40KB) | Section exceeds chunk size | Split by paragraphs or headings |
| Network interruption | Chunk request fails | Retry with exponential backoff (3x) |
| LLM timeout on chunk | Chunk processing stalls | Timeout after 60s, mark as failed |
| Session expires | State lost | 10-minute timeout, prompt to restart |
| Concurrent sessions | State collision | Unique session IDs, isolated state |
| Selector invalid after repair | Note positioning fails | Use fallback x/y coordinates |
| No semantic boundaries | Can't chunk intelligently | Fall back to character-based splits |
| Browser refresh mid-process | Session lost | Warn user, offer to restart |

### Error Messages

**User-Facing**:
- "Processing large page in 5 chunks. This may take 2-3 minutes..."
- "Chunk 3 of 5 failed. Retrying... (attempt 2 of 3)"
- "Successfully processed 4 of 5 chunks. 47 notes generated."
- "Processing cancelled. Partial notes have been saved."

**Developer Logs**:
- `[CHUNK] Session abc123: Processing chunk 2/5 (40KB)`
- `[CHUNK] Session abc123: Chunk 2 complete, 8 notes, $0.0012`
- `[CHUNK] Session abc123: Chunk 3 failed, retrying...`
- `[CHUNK] Session abc123: All chunks complete, 42 total notes`

---

## Rollout Strategy

### Phase A: Feature Flag Implementation

**Add Configuration**:
```javascript
// chrome-extension/content.js
const CHUNKING_CONFIG = {
  enabled: true,              // Master switch
  threshold: 40000,           // KB to trigger chunking
  chunkSize: 40000,           // Target chunk size
  maxChunks: 20,              // Safety limit
  retryAttempts: 3,           // Retry failed chunks
};
```

**Gradual Rollout**:
1. **Week 1**: Internal testing only (flag disabled in prod)
2. **Week 2**: Enable for pages > 200KB
3. **Week 3**: Enable for pages > 100KB
4. **Week 4**: Enable for all pages > 40KB
5. **Week 5+**: Monitor metrics, adjust thresholds

### Phase B: Backward Compatibility

**Maintain Old Endpoint**:
- Keep `/pages/{page_id}/generate` endpoint
- Users on old extension versions continue to work
- Deprecate after 2 months with warning

**Version Detection**:
```javascript
// Extension manifest.json
"version": "1.5.0"  // Chunking support

// Server checks version header
if (extensionVersion < "1.5.0") {
  // Use old single-request flow
} else {
  // Use new chunked flow
}
```

### Phase C: Monitoring & Metrics

**Track**:
- Average chunks per page
- Chunk processing time distribution
- Chunk failure rate
- Selector repair rate per chunk
- User satisfaction (notes kept vs. deleted)

**Dashboards**:
- Real-time chunk processing monitor
- Daily chunk statistics
- Error rate by chunk index (first chunks fail more?)
- Cost per chunk vs. cost per page

---

## Success Metrics

### Quantitative Metrics

1. **Page Coverage**
   - **Target**: 100% of page content processed
   - **Measure**: Average % of DOM included across all generations
   - **Current**: ~60% (due to 50KB truncation)

2. **Note Quality**
   - **Target**: > 90% selector accuracy after repair
   - **Measure**: % of notes that position correctly
   - **Current**: ~75%

3. **Performance**
   - **Target**: < 2 minutes for 15-chunk page (batches of 3)
   - **Measure**: Average time from start to completion
   - **Acceptable**: ~30s per batch of 3 chunks
   - **Improvement**: 5x faster than sequential (90s vs 450s for 15 chunks)

4. **Reliability**
   - **Target**: > 95% chunk success rate
   - **Measure**: % of chunks that complete without error
   - **Threshold**: Retry up to 3x before marking failed

### Qualitative Metrics

1. **User Satisfaction**
   - Survey users: "Did chunking improve note quality?"
   - Track batch deletion rate (lower = better)
   - Monitor feature usage (adoption rate)

2. **Note Usefulness**
   - Track notes edited vs. kept unchanged
   - Monitor time spent on pages with auto-notes
   - Collect user feedback on chunk quality

---

## Development Checklist

### Phase 1: Frontend (Chrome Extension)
- [ ] Add MAX_CONCURRENT_CHUNKS constant (set to 3)
- [ ] Add token estimation function
- [ ] Add semantic boundary detection
- [ ] Add DOM chunking function
- [ ] Add extractPageDOMInChunks() function (no session_id needed)
- [ ] Update handleGenerateDOMTestNotes() for batched parallel processing
- [ ] Generate batch_id on frontend (shared across all chunks)
- [ ] Use Promise.all() for parallel chunk processing
- [ ] Add chunk retry logic (optional)
- [ ] Update background.js message handler
- [ ] Add generateAutoNotesWithDOMChunk() to server-api.js
- [ ] Test with various page sizes
- [ ] Test error handling (continue on chunk failure)
- [ ] Add batch progress feedback UI

### Phase 2: Backend Schemas
- [ ] Add ChunkedAutoNoteRequest schema (with batch_id and position_offset)
- [ ] Add ChunkedAutoNoteResponse schema (single response type)
- [ ] Test schema validation
- [ ] Add to API documentation

### Phase 2.2: Backend Endpoint
- [ ] Create /pages/{page_id}/generate/chunked endpoint (stateless)
- [ ] Add request validation
- [ ] Single response type (no Union needed)
- [ ] Add error handling
- [ ] Add logging with batch_id
- [ ] Test with parallel API requests

### Phase 3: Backend Service (Stateless)
- [ ] Add generate_auto_notes_chunked() method (stateless)
- [ ] Use frontend-provided batch_id
- [ ] Use position_offset for note positioning
- [ ] No session management needed
- [ ] Test parallel chunk processing
- [ ] Test batch_id consistency in DB

### Phase 5: Testing
- [ ] Unit tests for chunking functions
- [ ] Integration tests for full flow
- [ ] Test small pages (single chunk)
- [ ] Test medium pages (2-5 chunks)
- [ ] Test large pages (5+ chunks)
- [ ] Test error scenarios
- [ ] Test concurrent sessions
- [ ] Performance testing
- [ ] Load testing

### Phase 6: Documentation
- [ ] Update API documentation
- [ ] Add user guide for chunking
- [ ] Add developer notes
- [ ] Update CHANGELOG
- [ ] Create migration guide

### Phase 7: Deployment
- [ ] Feature flag implementation
- [ ] Gradual rollout plan
- [ ] Monitoring setup
- [ ] Alert configuration
- [ ] Rollback plan
- [ ] User communication

---

## File Reference

### Files to Create
- None (all modifications to existing files)

### Files to Modify

#### Frontend (Chrome Extension)
1. **chrome-extension/content.js**
   - Lines 2529-2578: Keep extractPageDOMForTest() (fallback)
   - After 2578: Add new chunking functions
   - Lines 2583-2634: Replace handleGenerateDOMTestNotes()

2. **chrome-extension/background.js**
   - After line 484: Add chunk message handler

3. **chrome-extension/server-api.js**
   - After line 571: Add generateAutoNotesWithDOMChunk()

#### Backend
4. **backend/app/schemas.py**
   - After line 946: Add chunked schemas

5. **backend/app/routers/auto_notes.py**
   - After line 104: Add chunked endpoint
   - Add Union import

6. **backend/app/services/auto_note_service.py**
   - After line 314: Add generate_auto_notes_chunked() (stateless)

7. **backend/prompts/auto_notes/study_guide_generation.jinja2**
   - Beginning: Add chunk context section

---

## Timeline Estimate

### Parallel Development Tracks

**Track 1: Frontend (3-4 days)**
- Day 1: Chunking utility functions
- Day 2: Update handlers and API client
- Day 3: Testing and refinement
- Day 4: Error handling and UX

**Track 2: Backend (3-4 days)**
- Day 1: Schemas and endpoint
- Day 2: Service layer implementation
- Day 3: Session management and caching
- Day 4: Testing and optimization

**Track 3: Integration & Testing (2-3 days)**
- Day 1: End-to-end testing
- Day 2: Performance testing
- Day 3: Bug fixes and polish

**Total: 8-11 days** (with parallel work)
**Total: 15-20 days** (sequential work)

---

## Appendix

### Glossary

- **Chunk**: A semantic portion of a page's DOM, sized to fit within LLM token limits
- **Session**: A collection of related chunks being processed together
- **Semantic Boundary**: Natural split points in HTML (sections, articles, divs)
- **Parent Context**: Metadata about the full document structure for selector accuracy
- **Batch ID**: Unique identifier for all notes generated in a session
- **Selector Repair**: Process of fixing invalid CSS selectors using fuzzy matching

### Related Documents

- `CLAUDE.md` - Project session rules
- `PROJECT_SPEC.md` - Architecture specification
- `LLM_TODO.md` - LLM integration plan (Phases 1-5)
- `dom_auto_notes_context` memory - Current DOM auto-notes implementation

### API Examples

**Chunk Request (all chunks use same format)**:
```json
POST /auto-notes/pages/123/generate/chunked
{
  "llm_provider_id": 1,
  "template_type": "study_guide",
  "chunk_index": 1,
  "total_chunks": 5,
  "chunk_dom": "<div class='section-2'>...</div>",
  "parent_context": {
    "body_classes": ["article", "post"],
    "body_id": "main-content"
  },
  "batch_id": "auto_1234567890_abc",  // Frontend-generated, shared across all chunks
  "position_offset": 20  // 20 pixels per chunk for staggering
}
```

**Chunk Response (same for all chunks)**:
```json
{
  "notes": [
    {"id": 101, "content": "...", "highlighted_text": "..."},
    {"id": 102, "content": "...", "highlighted_text": "..."}
  ],
  "chunk_index": 1,
  "total_chunks": 5,
  "batch_id": "auto_1234567890_abc",
  "tokens_used": 8500,
  "cost_usd": 0.0023,
  "input_tokens": 7000,
  "output_tokens": 1500,
  "generation_time_ms": 28000
}
```

**Frontend Aggregation (example)**:
```javascript
// Frontend aggregates all responses
const allNotes = responses.flatMap(r => r.notes);  // [notes1, notes2, ...]
const totalCost = responses.reduce((sum, r) => sum + r.cost_usd, 0);  // 0.0115
const totalTokens = responses.reduce((sum, r) => sum + r.tokens_used, 0);  // 42000
```

---

## Notes for Future Sessions

### Context Loading
When starting a new session to implement chunking:

1. **Read this document** (`DOM_CHUNKING_PLAN.md`)
2. **Read memory**: `dom_auto_notes_context`
3. **Check current files**: Verify line numbers haven't changed
4. **Choose a phase**: Pick from Phase 1-4 based on priority
5. **Update checklist**: Mark completed items as you go

### Recommended Session Split

**Session 1: Frontend Chunking**
- Implement Phase 1.1 (utility functions)
- Implement Phase 1.2 (handler updates)
- Test locally with console logs

**Session 2: Frontend Integration**
- Implement Phase 1.3 (background.js)
- Implement Phase 1.4 (server-api.js)
- Test with mock backend responses

**Session 3: Backend Schemas & Endpoint**
- Implement Phase 2.1 (schemas)
- Implement Phase 2.2 (endpoint)
- Test with Swagger/Postman

**Session 4: Backend Service**
- Implement Phase 3.1 (stateless chunked generation)
- No session management needed
- Test with parallel chunks

**Session 5: Integration & Testing**
- End-to-end testing
- Error handling
- Performance optimization

**Session 6: Polish & Deploy**
- UX improvements
- Documentation
- Deployment

### Quick Start Commands

```bash
# Backend
cd backend
source .venv/Scripts/activate  # Windows
python -m pytest tests/  # Run tests
uvicorn app.main:app --reload  # Start server

# Frontend
cd chrome-extension
# Load unpacked extension in Chrome
# Open DevTools console to see logs

# Testing
# Visit large pages:
# - Wikipedia long articles
# - MDN documentation
# - News articles
```

---

**Document Version**: 2.0 (Parallel + Rate Limited)
**Last Updated**: 2025-01-16
**Author**: Claude (Sonnet 4.5)
**Status**: Ready for Implementation

**Key Changes in v2.0**:
- ✅ Batched parallel processing (3 chunks at a time) instead of sequential
- ✅ Frontend rate limiting via MAX_CONCURRENT_CHUNKS constant
- ✅ Stateless backend (no session management)
- ✅ Frontend-generated batch_id for linking notes
- ✅ Single response type (no partial/final distinction)
- ✅ 5x faster performance (90s vs 450s for 15 chunks)
- ✅ Simpler architecture and easier to maintain