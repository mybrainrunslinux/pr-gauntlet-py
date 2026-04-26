# Issue #02: page-offset

**Difficulty:** Tier 1 (Clear)
**File(s):** `app/main.py`
**Type:** Off-by-one pagination

## Description

The pagination offset calculation uses `page * limit` instead of `(page - 1) * limit`. Page 1 therefore skips the first `limit` results, page 2 skips `2 * limit`, and so on. The first page of results is unreachable.

## Reproduction

```python
import httpx
# Seed 5 workflows first, then:
r = httpx.get("http://localhost:8000/workflows?page=1&limit=5")
print(len(r.json()["workflows"]))  # Returns 0, should return up to 5
```

## Expected Behavior

Page 1 returns the first `limit` items (offset 0). Page 2 returns the next batch (offset = `limit`).

## Actual Behavior

Page 1 returns items starting at offset `limit` (skipping the entire first page). Page 1 is always empty when the total item count equals `limit`.

## Steps to Fix

1. Read `app/main.py` and understand the bug described above.
2. Apply the minimal fix — only edit files in `app/`.
3. Validate: `python -m pytest scoring/test_issues.py::test_02_page_offset -v`
4. Confirm the test passes before submitting.
