# Issue #03: search-case

**Difficulty:** Tier 1 (Clear)
**File(s):** `app/main.py`
**Type:** Case-sensitive search

## Description

Workflow search is case-sensitive: searching for `"deploy"` will not match a workflow named `"Deploy Pipeline"`. The `func.lower()` normalization was removed from the LIKE comparison, so only exact-case matches are returned.

## Reproduction

```bash
# Create a workflow with uppercase name
curl -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"name": "Deploy Pipeline", "description": ""}'

# Search with lowercase — should match, doesn't
curl "http://localhost:8000/workflows?search=deploy"
# Returns: {"workflows": [], "total": 0}
```

## Expected Behavior

Search is case-insensitive: `"deploy"` matches `"Deploy Pipeline"`, `"DEPLOY"`, etc.

## Actual Behavior

Only exact-case matches are returned. `"deploy"` does not match `"Deploy Pipeline"`.

## Steps to Fix

1. Read `app/main.py` and understand the bug described above.
2. Apply the minimal fix — only edit files in `app/`.
3. Validate: `python -m pytest scoring/test_issues.py::test_03_search_case -v`
4. Confirm the test passes before submitting.
