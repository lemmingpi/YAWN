# DOM Chunking Implementation Plan - Server-Side Architecture v3.0

## Critical Issue: CSS Selector Validation Problem

### The Core Problem
When processing chunk 2+ of a large page, the LLM generates document-relative CSS selectors like:
```css
body > main > article > section:nth-child(2) > p#p3
```

But the validation only has chunk 2's DOM:
```html
<section id="main">
  <p id="p3">Text</p>
</section>
```

**Result**: The selector fails validation because `body > main > article` doesn't exist in the chunk DOM. This breaks note positioning for all chunks except the first.

### The Solution
**Server-side chunking with backend parallelization**: Backend receives full DOM, chunks it internally, processes chunks in parallel with asyncio, and always validates against the full DOM.

---

## Executive Summary

### Current State
- **Partial Implementation**: Frontend chunking functions exist (content.js lines 2589-2909)
- **Backend endpoint exists**: `/generate/chunked` but validates against chunk DOM only
- **Problem**: CSS selectors fail validation for chunks 2+

### New Architecture
- **Single Request**: Frontend sends full DOM to backend in one request
- **Server Chunks**: Backend splits DOM using ported chunking algorithm
- **Parallel Processing**: Backend uses `asyncio.gather()` for 3 concurrent LLM calls
- **Full DOM Validation**: Every chunk validates selectors against complete DOM
- **Aggregated Response**: Backend returns all notes in single response

### Benefits
- ✅ **Correct Validation**: Selectors work for all chunks
- ✅ **Same Performance**: 90s for 15 chunks (parallel processing)
- ✅ **Simpler Frontend**: No chunking complexity
- ✅ **Better Error Handling**: Backend manages retries
- ✅ **Truly Stateless**: No session/cache management

---

## Test-First Implementation Strategy

### Phase 0: Write Critical Validation Tests (FIRST!)

Create `backend/tests/test_critical_selector_validation.py`:

```python
"""
Critical tests proving CSS selector validation issue with chunked DOM.
These tests MUST pass before the implementation is complete.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.app.services.auto_note_service import AutoNoteService
from backend.app.services.selector_validator import SelectorValidator


class TestCriticalSelectorValidation:
    """Prove that selector validation must use full DOM, not chunk DOM."""

    @pytest.fixture
    def full_dom(self):
        """Complete DOM as it exists on the page."""
        return """
        <html>
        <body class="article-page">
            <header id="site-header">
                <h1>Site Title</h1>
            </header>
            <main>
                <article class="content">
                    <section id="intro" class="section-1">
                        <h2>Introduction</h2>
                        <p id="p1">First paragraph in intro.</p>
                        <p id="p2">Second paragraph.</p>
                    </section>
                    <section id="main" class="section-2">
                        <h2>Main Content</h2>
                        <p id="p3">Target paragraph to annotate.</p>
                        <p id="p4">Another paragraph.</p>
                    </section>
                    <section id="conclusion" class="section-3">
                        <h2>Conclusion</h2>
                        <p id="p5">Final thoughts.</p>
                    </section>
                </article>
            </main>
        </body>
        </html>
        """

    @pytest.fixture
    def chunk_2_dom(self):
        """Chunk 2: Just the main section (missing all parent context)."""
        return """
        <section id="main" class="section-2">
            <h2>Main Content</h2>
            <p id="p3">Target paragraph to annotate.</p>
            <p id="p4">Another paragraph.</p>
        </section>
        """

    def test_problem_selectors_fail_with_chunk_dom(self, chunk_2_dom):
        """
        CURRENT STATE (FAILS): Selectors fail validation with chunk DOM only.
        This test documents the problem we're fixing.
        """
        selectors_from_llm = [
            "body > main > article > section:nth-child(2) > p#p3",
            "article.content > section#main > p:first-of-type",
            "main > article > section:nth-child(2) > p:nth-child(2)",
        ]

        validator = SelectorValidator()
        for selector in selectors_from_llm:
            is_valid = validator.validate_selector(chunk_2_dom, selector)[0]
            assert is_valid == False, f"Selector '{selector}' fails with chunk DOM"

    def test_solution_selectors_work_with_full_dom(self, full_dom):
        """
        DESIRED STATE (MUST PASS): Same selectors work with full DOM.
        This is what we're implementing.
        """
        selectors_from_llm = [
            "body > main > article > section:nth-child(2) > p#p3",
            "article.content > section#main > p:first-of-type",
            "main > article > section:nth-child(2) > p:nth-child(2)",
        ]

        validator = SelectorValidator()
        for selector in selectors_from_llm:
            is_valid, match_count, _ = validator.validate_selector(full_dom, selector)
            assert is_valid == True, f"Selector '{selector}' must work with full DOM"
            assert match_count > 0, f"Selector '{selector}' must find matches"

    @pytest.mark.asyncio
    async def test_service_validates_with_full_dom(self, full_dom, chunk_2_dom):
        """
        Integration test: Service method uses full DOM for validation.
        """
        mock_db = MagicMock()
        service = AutoNoteService(mock_db)

        # This is the NEW method we'll implement
        result = await service.process_chunk_with_full_dom(
            chunk_dom=chunk_2_dom,  # For LLM prompt
            full_dom=full_dom,       # For validation (KEY!)
            chunk_index=1,
            total_chunks=3,
            # ... other params
        )

        assert result['validation_success'] == True
        assert len(result['notes']) > 0
```

### Phase 0.1: Chunking Algorithm Tests

Create `backend/tests/test_dom_chunking.py`:

```python
"""Test the DOM chunking algorithm ported from JavaScript."""

import pytest
from backend.app.services.dom_chunker import DOMChunker


class TestDOMChunking:

    def test_small_dom_single_chunk(self):
        """DOM < 40KB returns single chunk."""
        small_dom = "<body>" + "<p>Text</p>" * 100 + "</body>"  # ~2KB
        chunker = DOMChunker()
        chunks = chunker.chunk_html(small_dom)

        assert len(chunks) == 1
        assert chunks[0]['chunk_index'] == 0
        assert chunks[0]['total_chunks'] == 1

    def test_large_dom_multiple_chunks(self):
        """Large DOM splits into multiple chunks."""
        # Create 200KB DOM
        large_dom = "<body>"
        for i in range(50):
            large_dom += f'<section id="s{i}">' + "<p>Text</p>" * 100 + '</section>'
        large_dom += "</body>"

        chunker = DOMChunker()
        chunks = chunker.chunk_html(large_dom, max_chars=40000)

        assert len(chunks) > 1
        assert all(len(c['chunk_dom']) <= 40000 for c in chunks)

    def test_semantic_boundaries_respected(self):
        """Chunks split at semantic boundaries (sections/articles)."""
        dom_with_sections = """
        <body>
            <section id="intro">
                <p>Intro content</p>
            </section>
            <section id="main">
                <p>Main content</p>
            </section>
            <section id="conclusion">
                <p>Conclusion content</p>
            </section>
        </body>
        """

        chunker = DOMChunker()
        chunks = chunker.chunk_html(dom_with_sections, max_chars=500)

        # Each chunk should contain complete sections
        for chunk in chunks:
            assert '<section' in chunk['chunk_dom']
            assert '</section>' in chunk['chunk_dom']
```

### Phase 0.2: Parallel Processing Tests

Create `backend/tests/test_parallel_processing.py`:

```python
"""Test parallel chunk processing with asyncio."""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from backend.app.services.auto_note_service import AutoNoteService


class TestParallelProcessing:

    @pytest.mark.asyncio
    async def test_chunks_process_in_parallel(self):
        """Verify chunks process in parallel, not sequentially."""

        async def mock_llm_call(prompt):
            """Simulate LLM call with 1 second delay."""
            await asyncio.sleep(1)
            return {"content": '{"notes": []}', "tokens": 1000, "cost": 0.01}

        service = AutoNoteService(AsyncMock())

        with patch.object(service, '_call_llm', side_effect=mock_llm_call):
            start_time = time.time()

            # Process 6 chunks with max 3 concurrent
            results = await service.process_chunks_parallel(
                chunks=[{'chunk_dom': f'<div>{i}</div>'} for i in range(6)],
                full_dom="<body>...</body>",
                max_concurrent=3
            )

            elapsed = time.time() - start_time

            # Should take ~2 seconds (2 batches of 3), not 6 seconds
            assert 1.8 < elapsed < 2.5, f"Parallel processing took {elapsed}s"
            assert len(results) == 6

    @pytest.mark.asyncio
    async def test_rate_limiting_enforced(self):
        """Max 3 concurrent LLM calls at a time."""
        concurrent_count = 0
        max_concurrent_seen = 0

        async def mock_llm_with_tracking(prompt):
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.1)
            concurrent_count -= 1
            return {"content": '{"notes": []}', "tokens": 1000, "cost": 0.01}

        service = AutoNoteService(AsyncMock())

        with patch.object(service, '_call_llm', side_effect=mock_llm_with_tracking):
            await service.process_chunks_parallel(
                chunks=[{'chunk_dom': f'<div>{i}</div>'} for i in range(10)],
                full_dom="<body>...</body>",
                max_concurrent=3
            )

            assert max_concurrent_seen == 3, f"Max concurrent was {max_concurrent_seen}"

    @pytest.mark.asyncio
    async def test_chunk_failure_doesnt_stop_others(self):
        """One chunk failing doesn't prevent others from processing."""

        async def mock_llm_some_fail(prompt):
            if "chunk_2" in prompt:
                raise Exception("LLM error for chunk 2")
            return {"content": '{"notes": [{"content": "Note"}]}', "tokens": 1000, "cost": 0.01}

        service = AutoNoteService(AsyncMock())

        with patch.object(service, '_call_llm', side_effect=mock_llm_some_fail):
            results = await service.process_chunks_parallel(
                chunks=[
                    {'chunk_dom': '<div>chunk_1</div>'},
                    {'chunk_dom': '<div>chunk_2</div>'},  # This will fail
                    {'chunk_dom': '<div>chunk_3</div>'},
                ],
                full_dom="<body>...</body>",
                max_concurrent=3
            )

            # Should get results for chunks 1 and 3
            assert len(results) == 2
            assert any('chunk_1' in str(r) for r in results)
            assert any('chunk_3' in str(r) for r in results)
```

---

## Implementation Plan

### Phase 1: Backend - Port Chunking Algorithm

#### Step 1.1: Create DOM Chunker Service

**File**: `backend/app/services/dom_chunker.py` (NEW)

```python
"""
DOM chunking service ported from JavaScript.
Splits large HTML into semantic chunks for LLM processing.
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re


class DOMChunker:
    """Handles semantic chunking of HTML content."""

    # Semantic boundaries in priority order
    BOUNDARY_SELECTORS = [
        'section[id], section[class]',
        'article',
        'div.content, div.main, div.article',
        'div[id]',
        'h1, h2',
    ]

    def __init__(self, max_chars: int = 40000, min_chars: int = 10000):
        """
        Initialize chunker with size constraints.

        Args:
            max_chars: Maximum characters per chunk (~10k tokens)
            min_chars: Minimum characters to avoid tiny chunks
        """
        self.max_chars = max_chars
        self.min_chars = min_chars

    def chunk_html(self, html_content: str) -> List[Dict]:
        """
        Split HTML into semantic chunks.

        Args:
            html_content: Full HTML content to chunk

        Returns:
            List of chunk dictionaries with metadata
        """
        # Small enough for single chunk?
        if len(html_content) <= self.max_chars:
            return [{
                'chunk_index': 0,
                'total_chunks': 1,
                'chunk_dom': html_content,
                'parent_context': self._extract_parent_context(html_content),
            }]

        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        body = soup.body if soup.body else soup

        # Extract parent context once
        parent_context = self._extract_parent_context(html_content)

        # Find semantic boundaries
        boundaries = self._find_semantic_boundaries(body)

        # Group into chunks
        raw_chunks = self._group_boundaries_into_chunks(boundaries)

        # Merge small chunks
        merged_chunks = self._merge_small_chunks(raw_chunks)

        # Build final chunk objects
        return self._build_chunk_objects(merged_chunks, parent_context)

    def _extract_parent_context(self, html: str) -> Dict:
        """Extract document metadata for selector accuracy."""
        soup = BeautifulSoup(html, 'html.parser')
        body = soup.body if soup.body else soup

        return {
            'body_classes': body.get('class', []) if hasattr(body, 'get') else [],
            'body_id': body.get('id', '') if hasattr(body, 'get') else '',
            'main_container': bool(soup.select_one('main, [role="main"]')),
            'document_title': soup.title.string if soup.title else ''
        }

    def _find_semantic_boundaries(self, element) -> List:
        """Find elements to use as chunk boundaries."""
        for selector in self.BOUNDARY_SELECTORS:
            # BeautifulSoup uses select() for CSS selectors
            boundaries = element.select(selector)
            if len(boundaries) > 1:
                return boundaries

        # Fallback to paragraphs
        return element.select('p, div')

    def _group_boundaries_into_chunks(self, boundaries: List) -> List[List]:
        """Group boundary elements into size-appropriate chunks."""
        chunks = []
        current_chunk = []
        current_size = 0

        for element in boundaries:
            element_html = str(element)
            element_size = len(element_html)

            # Start new chunk if adding would exceed limit
            if current_size + element_size > self.max_chars and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [element]
                current_size = element_size
            else:
                current_chunk.append(element)
                current_size += element_size

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _merge_small_chunks(self, chunks: List[List]) -> List[List]:
        """Merge chunks smaller than minimum size."""
        merged = []
        current_merged = []
        current_size = 0

        for chunk in chunks:
            chunk_size = sum(len(str(el)) for el in chunk)

            if not current_merged:
                current_merged = chunk
                current_size = chunk_size
            elif current_size < self.min_chars and current_size + chunk_size <= self.max_chars:
                current_merged.extend(chunk)
                current_size += chunk_size
            else:
                merged.append(current_merged)
                current_merged = chunk
                current_size = chunk_size

        if current_merged:
            merged.append(current_merged)

        return merged

    def _build_chunk_objects(self, chunks: List[List], parent_context: Dict) -> List[Dict]:
        """Convert chunk elements to final chunk dictionaries."""
        total_chunks = len(chunks)
        return [
            {
                'chunk_index': i,
                'total_chunks': total_chunks,
                'chunk_dom': '\n'.join(str(el) for el in elements),
                'parent_context': parent_context,
            }
            for i, elements in enumerate(chunks)
        ]
```

**Testing with Serena**:
```bash
# Use Serena to verify the chunking logic matches JavaScript version
mcp__serena__find_symbol "chunkDOMContent" "chrome-extension/content.js"
# Compare the JavaScript implementation with Python port
```

### Phase 2: Backend - Implement Parallel Processing

#### Step 2.1: Update Auto Note Service

**File**: `backend/app/services/auto_note_service.py`

Add these methods to the existing service:

```python
# Add imports at top
import asyncio
from typing import List, Dict, Any, Optional
from .dom_chunker import DOMChunker

class AutoNoteService:
    # ... existing code ...

    async def generate_auto_notes_with_full_dom(
        self,
        page_id: int,
        user_id: int,
        full_dom: str,
        llm_provider_id: int = 1,
        template_type: str = "study_guide",
        max_concurrent: int = 3,
    ) -> Dict:
        """
        Generate notes from large DOM using server-side chunking and parallel processing.

        This is the main entry point that:
        1. Chunks the DOM server-side
        2. Processes chunks in parallel (max 3 concurrent)
        3. Validates all selectors against full DOM
        4. Returns aggregated results

        Args:
            page_id: ID of page to generate notes for
            user_id: ID of user creating notes
            full_dom: Complete DOM content from frontend
            llm_provider_id: LLM provider to use
            template_type: Template type for generation
            max_concurrent: Max parallel LLM calls (rate limit)

        Returns:
            Dictionary with all notes and metadata
        """
        start_time = time.time()

        # Generate batch ID for all notes
        batch_id = f"auto_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        logger.info(f"Starting server-side chunking for page_id={page_id}, batch_id={batch_id}")

        # 1. Chunk the DOM server-side
        chunker = DOMChunker(max_chars=40000)
        chunks = chunker.chunk_html(full_dom)
        total_chunks = len(chunks)

        logger.info(f"Split {len(full_dom)/1000:.1f}KB into {total_chunks} chunks")

        # 2. Process chunks in parallel batches
        all_notes = []
        all_costs = []
        all_tokens = []
        failed_chunks = []

        # Process in batches to respect rate limit
        for batch_start in range(0, total_chunks, max_concurrent):
            batch_end = min(batch_start + max_concurrent, total_chunks)
            batch = chunks[batch_start:batch_end]
            batch_num = (batch_start // max_concurrent) + 1
            total_batches = (total_chunks + max_concurrent - 1) // max_concurrent

            logger.info(f"Processing batch {batch_num}/{total_batches} (chunks {batch_start}-{batch_end-1})")

            # Create tasks for parallel processing
            tasks = []
            for chunk in batch:
                task = self._process_single_chunk_with_full_dom(
                    chunk_dom=chunk['chunk_dom'],
                    full_dom=full_dom,  # KEY: Pass full DOM for validation!
                    chunk_index=chunk['chunk_index'],
                    total_chunks=chunk['total_chunks'],
                    parent_context=chunk['parent_context'],
                    page_id=page_id,
                    user_id=user_id,
                    batch_id=batch_id,
                    llm_provider_id=llm_provider_id,
                    template_type=template_type,
                    position_offset=chunk['chunk_index'] * 20,  # Stagger note positions
                )
                tasks.append(task)

            # Execute batch in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for idx, result in enumerate(batch_results):
                chunk_idx = batch_start + idx
                if isinstance(result, Exception):
                    logger.error(f"Chunk {chunk_idx} failed: {result}")
                    failed_chunks.append(chunk_idx)
                    continue

                if result and 'notes' in result:
                    all_notes.extend(result['notes'])
                    all_costs.append(result.get('cost_usd', 0))
                    all_tokens.append(result.get('tokens_used', 0))

        # 3. Calculate totals
        total_time = int((time.time() - start_time) * 1000)

        # 4. Return aggregated results
        return {
            "notes": all_notes,
            "batch_id": batch_id,
            "total_chunks": total_chunks,
            "successful_chunks": total_chunks - len(failed_chunks),
            "failed_chunks": failed_chunks,
            "tokens_used": sum(all_tokens),
            "cost_usd": sum(all_costs),
            "generation_time_ms": total_time,
        }

    async def _process_single_chunk_with_full_dom(
        self,
        chunk_dom: str,
        full_dom: str,  # Critical: Full DOM for validation
        chunk_index: int,
        total_chunks: int,
        parent_context: Dict,
        page_id: int,
        user_id: int,
        batch_id: str,
        llm_provider_id: int,
        template_type: str,
        position_offset: int,
    ) -> Dict:
        """
        Process a single chunk with full DOM for validation.

        This is where the fix happens: We generate from chunk_dom but
        validate against full_dom.
        """
        try:
            # Fetch page info
            result = await self.db.execute(
                select(Page).options(selectinload(Page.site)).where(Page.id == page_id)
            )
            page = result.scalar_one_or_none()

            if not page:
                raise ValueError(f"Page {page_id} not found")

            # Build prompt with chunk DOM
            chunk_instructions = (
                f"This is chunk {chunk_index + 1} of {total_chunks} from a large page. "
                f"Generate notes only for content in this chunk. "
                f"Use CSS selectors relative to the full document structure."
            )

            prompt = await self._build_prompt(
                page,
                template_type,
                chunk_instructions,
                page_source=None,
                page_dom=chunk_dom,  # Use chunk for generation
            )

            # Call LLM
            provider = await create_gemini_provider()
            generation_result = await provider.generate_content_large(prompt=prompt)

            # Parse response
            generated_content = generation_result["content"]
            generated_content = self._clean_json_response(generated_content)

            try:
                parsed_data = json.loads(generated_content)
                notes_data = parsed_data.get("notes", [])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON for chunk {chunk_index}: {e}")
                raise

            # Create notes with FULL DOM validation
            created_notes = []
            for idx, note_data in enumerate(notes_data):
                css_selector = note_data.get("css_selector")
                highlighted_text = note_data.get("highlighted_text", "")

                # CRITICAL FIX: Validate against full DOM, not chunk!
                if css_selector and full_dom:
                    is_valid, match_count, _ = self._validator.validate_selector(
                        full_dom,  # NOT chunk_dom!
                        css_selector
                    )

                    if not is_valid:
                        # Try to repair using full DOM
                        repair_result = self._validator.repair_selector(
                            full_dom,  # NOT chunk_dom!
                            highlighted_text,
                            css_selector,
                            note_data.get("xpath")
                        )

                        if repair_result["success"]:
                            css_selector = repair_result["css_selector"]
                            logger.info(f"Repaired selector for chunk {chunk_index}, note {idx}")

                # Create note with validated selector
                note = Note(
                    content=note_data.get("commentary", ""),
                    highlighted_text=highlighted_text,
                    position_x=100 + position_offset + (idx * 20),
                    position_y=100 + position_offset + (idx * 20),
                    anchor_data={
                        "auto_generated": True,
                        "chunk_index": chunk_index,
                        "elementSelector": css_selector,
                        "batch_id": batch_id,
                    },
                    page_id=page_id,
                    user_id=user_id,
                    generation_batch_id=batch_id,
                    server_link_id=f"{batch_id}_{chunk_index}_{idx}",
                    is_active=True,
                )

                self.db.add(note)
                created_notes.append(note)

            await self.db.commit()

            # Refresh to get IDs
            for note in created_notes:
                await self.db.refresh(note)

            logger.info(f"Chunk {chunk_index + 1}/{total_chunks}: Created {len(created_notes)} notes")

            return {
                "notes": created_notes,
                "tokens_used": generation_result["input_tokens"] + generation_result["output_tokens"],
                "cost_usd": generation_result["cost"],
                "chunk_index": chunk_index,
            }

        except Exception as e:
            logger.error(f"Error processing chunk {chunk_index}: {e}")
            raise

    def _clean_json_response(self, content: str) -> str:
        """Clean LLM response for JSON parsing."""
        if content.startswith("```json"):
            content = content.replace("```json", "", 1)
        if content.startswith("```"):
            content = content.replace("```", "", 1)
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        return content.strip()
```

### Phase 3: Backend - Create New Endpoint

#### Step 3.1: Add Schema

**File**: `backend/app/schemas.py`

Add after existing schemas (around line 950):

```python
class FullDOMAutoNoteRequest(BaseModel):
    """Request schema for server-side chunking with full DOM."""

    llm_provider_id: int = Field(1, description="LLM provider ID")
    template_type: str = Field("study_guide", description="Template type")
    full_dom: str = Field(..., min_length=1, description="Complete page DOM")
    custom_instructions: Optional[str] = Field(None, description="Custom instructions")


class FullDOMAutoNoteResponse(BaseModel):
    """Response schema for server-side chunking."""

    notes: List[GeneratedNoteData] = Field(..., description="All generated notes")
    batch_id: str = Field(..., description="Batch ID for this generation")
    total_chunks: int = Field(..., description="Number of chunks processed")
    successful_chunks: int = Field(..., description="Successfully processed chunks")
    failed_chunks: List[int] = Field(default_factory=list, description="Failed chunk indices")
    tokens_used: int = Field(..., description="Total tokens consumed")
    cost_usd: float = Field(..., description="Total cost in USD")
    generation_time_ms: int = Field(..., description="Total generation time")
```

#### Step 3.2: Add Endpoint

**File**: `backend/app/routers/auto_notes.py`

Add new endpoint after existing ones:

```python
@router.post(
    "/pages/{page_id}/generate/full-dom",
    response_model=FullDOMAutoNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_auto_notes_full_dom(
    page_id: int,
    request: FullDOMAutoNoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FullDOMAutoNoteResponse:
    """
    Generate auto notes with server-side chunking and parallel processing.

    This endpoint:
    1. Receives full DOM from frontend
    2. Chunks it server-side
    3. Processes chunks in parallel
    4. Validates all selectors against full DOM
    5. Returns all notes in single response

    This solves the CSS selector validation problem where selectors
    generated for chunk 2+ fail because they reference parent elements
    not present in the chunk.
    """
    logger.info(
        f"Server-side chunking requested for page_id={page_id}, "
        f"DOM size={len(request.full_dom)/1000:.1f}KB, user_id={current_user.id}"
    )

    service = AutoNoteService(db)

    try:
        result = await service.generate_auto_notes_with_full_dom(
            page_id=page_id,
            user_id=current_user.id,
            full_dom=request.full_dom,
            llm_provider_id=request.llm_provider_id,
            template_type=request.template_type,
        )

        # Convert notes to response format
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

        return FullDOMAutoNoteResponse(
            notes=notes_data,
            batch_id=result["batch_id"],
            total_chunks=result["total_chunks"],
            successful_chunks=result["successful_chunks"],
            failed_chunks=result.get("failed_chunks", []),
            tokens_used=result["tokens_used"],
            cost_usd=result["cost_usd"],
            generation_time_ms=result["generation_time_ms"],
        )

    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auto notes: {str(e)}",
        )
```

### Phase 4: Frontend - Simplify to Single Request

#### Step 4.1: Update Content.js

**File**: `chrome-extension/content.js`

Replace the complex `handleGenerateDOMTestNotes()` function (lines 2850-2950) with simplified version:

```javascript
/**
 * Handle DOM auto-notes generation with server-side chunking
 * Simplified: Send full DOM, let backend handle chunking and parallelization
 */
async function handleGenerateDOMTestNotes() {
  try {
    console.log("[Web Notes] Starting auto-note generation with server-side chunking");

    // Check authentication
    const isAuth = await isServerAuthenticated();
    if (!isAuth) {
      alert("Please sign in to generate auto notes");
      return;
    }

    // Extract full DOM (reuse existing function)
    const fullDOM = extractPageDOMForTest();

    if (!fullDOM) {
      alert("Failed to extract page content");
      return;
    }

    const domSize = Math.round(fullDOM.length / 1000);
    console.log(`[Web Notes] Sending ${domSize}KB DOM to server for chunking`);

    // Show loading message
    const estimatedTime = domSize > 100 ? Math.ceil(domSize / 50) : 1;
    alert(
      `Processing page content (${domSize}KB).\n\n` +
      `This may take ${estimatedTime} minute(s). ` +
      `The server will chunk and process the content in parallel.\n\n` +
      `You'll be notified when complete.`
    );

    // Register page
    const pageUrl = window.location.href;
    const pageTitle = document.title || "Untitled";

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

    // Single request with full DOM
    const response = await chrome.runtime.sendMessage({
      action: "API_generateAutoNotesFullDOM",
      pageId: pageData.id,
      fullDOM: fullDOM,
    });

    // Handle response
    if (response.success && response.data) {
      const { notes, total_chunks, successful_chunks, cost_usd, tokens_used, batch_id } = response.data;

      let message = `Successfully generated ${notes.length} study notes!\n\n` +
        `Processed ${successful_chunks}/${total_chunks} chunks\n` +
        `Batch ID: ${batch_id}\n` +
        `Total Cost: $${cost_usd.toFixed(4)}\n` +
        `Total Tokens: ${tokens_used.toLocaleString()}`;

      if (successful_chunks < total_chunks) {
        message += `\n\nWarning: ${total_chunks - successful_chunks} chunk(s) failed to process.`;
      }

      alert(message);

      // Refresh to show notes
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } else {
      alert(`Failed to generate auto notes: ${response.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error("[Web Notes] Error generating auto notes:", error);
    alert(`Failed to generate auto notes: ${error.message}`);
  }
}

// Keep the chunking functions for reference but mark as deprecated
// They contain valuable logic that was ported to Python
/** @deprecated Now handled server-side */
function chunkDOMContent(htmlContent, maxTokensPerChunk = 10000) {
  // ... existing code ...
}

/** @deprecated Now handled server-side */
function extractPageDOMInChunks() {
  // ... existing code ...
}
```

#### Step 4.2: Update Background.js

**File**: `chrome-extension/background.js`

Add handler for new message:

```javascript
// In chrome.runtime.onMessage.addListener, add:

case "API_generateAutoNotesFullDOM":
  // New endpoint: server-side chunking
  result = await ServerAPI.generateAutoNotesWithFullDOM(message.pageId, message.fullDOM);
  break;

// Keep old handlers for backward compatibility but mark deprecated
```

#### Step 4.3: Update Server API

**File**: `chrome-extension/server-api.js`

Add new method:

```javascript
/**
 * Generate auto notes with server-side chunking
 * Server handles all chunking and parallel processing
 * @param {number} pageId - Page ID
 * @param {string} fullDOM - Complete DOM content
 * @returns {Promise<Object>} Generation response with all notes
 */
async generateAutoNotesWithFullDOM(pageId, fullDOM) {
  try {
    if (!this.isAuthenticated()) {
      throw new Error("User not authenticated");
    }

    const requestData = {
      llm_provider_id: 1,  // Default to Gemini
      template_type: "study_guide",
      full_dom: fullDOM,
      custom_instructions: "Generate comprehensive study notes from this page content.",
    };

    // New endpoint that handles everything server-side
    const response = await this.makeRequest(`/auto-notes/pages/${pageId}/generate/full-dom`, {
      method: "POST",
      body: JSON.stringify(requestData),
      // Increase timeout for large pages
      signal: AbortSignal.timeout(180000),  // 3 minutes
    });

    const result = await response.json();
    console.log(
      `[Web Notes] Generated ${result.notes?.length || 0} notes from ${result.total_chunks} chunks`
    );
    return result;
  } catch (error) {
    console.error("[Web Notes] Failed to generate auto notes:", error);
    throw error;
  }
}

// Mark old chunking methods as deprecated
/** @deprecated Use generateAutoNotesWithFullDOM instead */
async generateAutoNotesWithDOMChunk(pageId, chunkData) {
  // ... existing code ...
}
```

---

## Rollback Strategy

### What to Keep
1. **Chunking Algorithm Logic** - Port from JavaScript to Python (valuable)
2. **Existing Backend Models** - Note, Page, etc. (unchanged)
3. **Authentication Flow** - Works fine (unchanged)

### What to Remove/Replace
1. **Frontend Chunking** in content.js - Simplify to single request
2. **Parallel Frontend Calls** - Move to backend
3. **Chunk Endpoints** - Keep for compatibility, mark deprecated
4. **Batch Processing in Frontend** - No longer needed

### Migration Path
1. Deploy new endpoint alongside old ones
2. Update extension to use new endpoint
3. Keep old endpoints for 2 months (backward compatibility)
4. Monitor usage, deprecate old endpoints

---

## Testing Strategy

### Run Tests in Order:
1. **Critical Validation Tests** - Must pass to prove fix works
2. **Chunking Algorithm Tests** - Verify Python port matches JS
3. **Parallel Processing Tests** - Ensure performance maintained
4. **Integration Tests** - Full flow with real pages

### Test Commands:
```bash
# Backend tests
cd backend
source .venv/Scripts/activate

# Run critical tests first
pytest tests/test_critical_selector_validation.py -v

# Then chunking tests
pytest tests/test_dom_chunking.py -v

# Then parallel processing
pytest tests/test_parallel_processing.py -v

# Full suite
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

### Manual Testing:
1. Small page (< 40KB) - Should work unchanged
2. Medium page (Wikipedia article) - 2-5 chunks
3. Large page (MDN docs) - 5+ chunks
4. Check all selectors position correctly

---

## Session Management Guide

### For Next Session

When picking up this implementation:

1. **Check Current State**:
   ```bash
   # Use Serena to check what's implemented
   mcp__serena__find_symbol "generate_auto_notes_with_full_dom" "backend"
   mcp__serena__find_symbol "handleGenerateDOMTestNotes" "chrome-extension/content.js"
   ```

2. **Run Critical Tests**:
   ```bash
   pytest backend/tests/test_critical_selector_validation.py -v
   ```
   - If tests FAIL: Problem not fixed yet
   - If tests PASS: Solution implemented correctly

3. **Check Implementation Progress**:
   - [ ] DOM Chunker service created
   - [ ] Parallel processing implemented
   - [ ] Full DOM validation in place
   - [ ] New endpoint created
   - [ ] Frontend simplified
   - [ ] Old code marked deprecated

4. **Next Steps Based on State**:
   - Tests failing? → Implement Phase 2 (parallel processing)
   - Backend done? → Simplify frontend (Phase 4)
   - All code done? → Integration testing
   - Tests passing? → Documentation and cleanup

### Key Files to Check:

**Backend**:
- `backend/app/services/dom_chunker.py` - NEW file
- `backend/app/services/auto_note_service.py` - Check for new methods
- `backend/app/routers/auto_notes.py` - Check for `/full-dom` endpoint
- `backend/app/schemas.py` - Check for FullDOM schemas

**Frontend**:
- `chrome-extension/content.js` - Should be simplified
- `chrome-extension/server-api.js` - Check for new method
- `chrome-extension/background.js` - Check for new handler

### Common Issues:

**If selectors still fail**:
- Check that `full_dom` is passed to validator, not `chunk_dom`
- Verify repair also uses `full_dom`
- Check test `test_solution_selectors_work_with_full_dom`

**If performance is slow**:
- Check `asyncio.gather()` is used
- Verify `max_concurrent=3` is set
- Check batching logic

**If chunks are too large**:
- Adjust `max_chars` in DOMChunker
- Check semantic boundary detection
- Verify merging logic

---

## Success Criteria

The implementation is complete when:

1. ✅ **All critical validation tests pass**
   - `test_problem_selectors_fail_with_chunk_dom` - Documents issue
   - `test_solution_selectors_work_with_full_dom` - Proves fix
   - `test_service_validates_with_full_dom` - Integration works

2. ✅ **Performance maintained**
   - 15-chunk page processes in ~90 seconds
   - Parallel processing verified in tests

3. ✅ **Frontend simplified**
   - Single request to backend
   - No chunking complexity
   - Clean code

4. ✅ **Backward compatibility**
   - Old endpoints still work
   - Graceful migration path

---

## Appendix: Key Code Snippets

### The Fix in One Line:
```python
# OLD (BROKEN):
is_valid = self._validator.validate_selector(chunk_dom, css_selector)

# NEW (FIXED):
is_valid = self._validator.validate_selector(full_dom, css_selector)
```

### Parallel Processing Pattern:
```python
# Process chunks in batches of 3
tasks = [process_chunk(c) for c in batch[:3]]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Serena Commands for Analysis:
```bash
# Find all validation calls
mcp__serena__search_for_pattern "validate_selector.*chunk_dom" "backend"

# Check if fix is applied
mcp__serena__search_for_pattern "validate_selector.*full_dom" "backend"

# Find chunking implementations
mcp__serena__find_symbol "chunk" "backend"
```

---

**Document Version**: 3.0 - Server-Side Architecture
**Last Updated**: 2025-01-16
**Focus**: Fix CSS selector validation with server-side chunking
**Status**: Ready for Test-First Implementation

**Critical Change**: All validation must use full DOM, not chunk DOM