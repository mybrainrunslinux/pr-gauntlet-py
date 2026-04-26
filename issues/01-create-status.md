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

- In `app/main.py`, change the status_code on the POST /workflows response from 200 to 201. Verify with: `python -m pytest scoring/test_issues.py::test_01_create_status -v` (must fail before fix, pass after).
