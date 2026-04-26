# Issue #01: create-status

**Difficulty:** Tier 1 (Clear)
**File(s):** `app/main.py`
**Type:** Wrong HTTP status code

## Description

Creating a new workflow via `POST /workflows` returns HTTP 200 instead of the correct 201 Created. REST convention requires 201 for successful resource creation so clients know a new resource was allocated.

## Reproduction

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"name": "my-flow", "description": ""}'
# Returns: 200 (should be 201)
```

## Expected Behavior

`POST /workflows` returns **201 Created** with the new workflow object.

## Actual Behavior

Returns **200 OK** — clients that check the status code to detect creation vs. update will malfunction.

## Steps to Fix

1. Read `app/main.py` and understand the bug described above.
2. Apply the minimal fix — only edit files in `app/`.
3. Validate: `python -m pytest scoring/test_issues.py::test_01_create_status -v`
4. Confirm the test passes before submitting.
