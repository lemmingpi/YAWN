# Plan: Two-Pass CSS Selector Improvement for Auto-Generated Notes

## Problem Summary
LLM generates notes with CSS selectors that often fail due to:
- Over-reliance on `nth-child` despite prompts discouraging it
- Over-specification of enclosing nodes
- Selectors that don't match actual DOM elements
- Browser differences in how selectors are processed

## Approach 1: Procedural/Algorithmic Validation & Repair

### Phase 1: Research & Design (1-2 hours)
1. **Analyze current failures**:
   - Collect 10-15 examples of generated selectors that fail
   - Categorize failure modes (nth-child issues, wrong nodes, non-unique, etc.)
   - Document patterns in what works vs what doesn't

2. **Design text-matching strategy**:
   - Decide: exact match vs fuzzy match (using `difflib` or similar)
   - Handle multi-element text spans (text crossing tags)
   - Strategy for multiple matches (use surrounding context, position in document)

3. **Design selector generation logic**:
   - Port extension's `generateOptimalSelector()` to Python
   - Use `lxml` for parsing, `cssselect` for validation
   - Alternative: Use Selenium/Playwright to leverage browser's selector engine

### Phase 2: Implementation (3-4 hours)
1. **Create `SelectorValidator` class** in `backend/app/services/selector_validator.py`:
   - `validate_selector(dom, selector)` - test if selector works and is unique
   - `find_text_in_dom(dom, text)` - locate highlighted text in DOM
   - `generate_robust_selector(element)` - create CSS + XPath for element
   - `repair_selector(dom, highlighted_text, old_selector)` - find text, generate new selector

2. **Integrate into `AutoNoteService`**:
   - After LLM generates notes, before saving to DB
   - Validate each selector against the provided `page_dom`
   - For failed selectors: find text, generate new selector
   - Log statistics (% repaired, % unfixable)

3. **Add fallback handling**:
   - If text not found: keep original selector + log warning
   - If multiple matches: use heuristics (first match, nearest to expected position)
   - Store validation metadata in note for debugging

### Phase 3: Testing & Refinement (2-3 hours)
1. Test on 5-10 real web pages
2. Measure success rate (before/after repair)
3. Add unit tests for common failure cases
4. Tune text-matching sensitivity

**Estimated Total: 6-9 hours**

---

## Approach 2: LLM-Based Second Pass

### Phase 1: Research & Prompt Engineering (2-3 hours)
1. **Design validator prompt**:
   - Provide: original notes, page DOM, list of failed selectors
   - Ask LLM to test each selector mentally and propose fixes
   - Use very specific output format (JSON with repairs)
   - Include examples of good selector repairs

2. **Test temperature settings**:
   - Try 0.0, 0.1, 0.2, 0.5
   - Measure consistency across runs
   - Find optimal balance of accuracy vs creativity

3. **Cost analysis**:
   - Calculate token costs (DOM + notes + prompt overhead)
   - Estimate cost per generation (likely $0.01-0.05 per page)
   - Compare to first-pass costs

### Phase 2: Implementation (3-4 hours)
1. **Create validation prompt template** in `backend/prompts/auto_notes/selector_validation.jinja2`:
   - Input: page_dom, notes with selectors
   - Instructions: validate each selector, propose repairs for failures
   - Output: JSON with selector status and fixes

2. **Create `SelectorRefiner` class** in `backend/app/services/selector_refiner.py`:
   - `validate_selectors_with_llm(page_dom, notes)` - second LLM pass
   - Uses low temperature (0.1)
   - Parses validation results
   - Updates note selectors

3. **Integrate into `AutoNoteService.generate_auto_notes()`**:
   - After initial LLM generation
   - Before saving to database
   - Optional toggle (can enable/disable via config)
   - Track costs separately

### Phase 3: Testing & Optimization (2-3 hours)
1. **A/B testing**:
   - Compare procedural vs LLM approach
   - Test on same 10-15 pages
   - Measure success rate, cost, speed

2. **Prompt refinement**:
   - Iterate on prompt based on failures
   - Add few-shot examples of corrections
   - Fine-tune instructions

3. **Hybrid approach exploration**:
   - Use procedural for simple cases (exact text match)
   - Use LLM only when procedural fails
   - Best of both worlds?

**Estimated Total: 7-10 hours**

---

## Recommended Experimentation Order

### Week 1: Build & Test Procedural Approach
- Implement Approach 1 fully
- Measure baseline improvement
- Understand limitations

### Week 2: Build & Test LLM Approach
- Implement Approach 2 fully
- Compare to Approach 1 results
- Analyze cost/benefit

### Week 3: Optimize & Choose
- If Approach 1 is good enough (>90% success): ship it
- If Approach 2 significantly better: ship it (if cost acceptable)
- If neither perfect: implement hybrid

---

## Files to Create/Modify

### Approach 1 (Procedural):
- **New**: `backend/app/services/selector_validator.py`
- **New**: `backend/tests/test_selector_validator.py`
- **Modify**: `backend/app/services/auto_note_service.py` (add validation step at line ~400)
- **Modify**: `backend/app/schemas.py` (add validation metadata fields)

### Approach 2 (LLM):
- **New**: `backend/prompts/auto_notes/selector_validation.jinja2`
- **New**: `backend/app/services/selector_refiner.py`
- **New**: `backend/tests/test_selector_refiner.py`
- **Modify**: `backend/app/services/auto_note_service.py` (add LLM refinement step at line ~400)

---

## Success Metrics

For both approaches, measure:
1. **Selector success rate**: % of selectors that correctly locate elements
2. **Uniqueness rate**: % of selectors that match exactly one element
3. **Processing time**: Time to validate/repair all selectors
4. **Cost** (Approach 2 only): Additional LLM API costs
5. **User satisfaction**: Reduction in misplaced notes

**Target: >90% success rate for selectors**

---

## Key Technical Details

### Current System Context
- DOM extraction: `chrome-extension/content.js:2530` (`extractPageDOMForTest()`)
- First LLM pass: `backend/app/services/auto_note_service.py:201` (`generate_auto_notes()`)
- Prompt template: `backend/prompts/auto_notes/study_guide_generation.jinja2`
- Extension selector finding: `chrome-extension/content.js:2000` (`findTargetElement()`)
- Extension selector generation: `chrome-extension/content.js:2081` (`generateOptimalSelector()`)

### Integration Point
Both approaches integrate at the same location in `auto_note_service.py`:
```python
# Line ~400, after JSON parsing, before creating Note records
for idx, note_data in enumerate(notes_data):
    # CURRENT: Extract selectors from LLM response
    css_selector = note_data.get("css_selector")
    xpath = note_data.get("xpath")

    # NEW: Add validation/refinement here
    # Approach 1: validator.repair_selector(page_dom, note_data)
    # Approach 2: refiner.validate_and_fix(page_dom, note_data)
```

### Research Questions to Answer

**Approach 1 (Procedural)**:
1. What Python library best handles CSS selector validation? (`lxml.cssselect`, `parsel`, `bs4`, `playwright`)
2. How to handle text that spans multiple elements?
3. What tolerance for fuzzy text matching? (exact, 90% similar, word-boundary flexible?)
4. How to generate robust selectors from element? (copy extension JS logic or use library?)

**Approach 2 (LLM)**:
1. What's the optimal prompt structure for selector validation?
2. Which temperature gives best consistency? (test 0.0, 0.1, 0.2)
3. Should we send all selectors at once or validate individually?
4. How to handle LLM hallucinations (invalid selector suggestions)?
5. Is cost worth the improvement over procedural?

---

## Next Steps

1. **Decision Point**: Choose which approach to prototype first
   - Recommend: Start with Approach 1 (faster, cheaper, deterministic)
   - Then build Approach 2 to compare

2. **Collect Test Data**:
   - Run current system on 10-15 diverse pages
   - Save: page DOM, generated notes, which selectors failed
   - Use as test suite for both approaches

3. **Create Feature Branch**:
   ```bash
   git checkout -b feature/selector-validation-v2
   ```

4. **Begin Implementation** (based on chosen approach)
