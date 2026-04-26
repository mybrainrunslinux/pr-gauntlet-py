# Issue #17: chain-list

**Difficulty:** Tier 4 (Chain)
**File(s):** `app/executor.py`
**Type:** Empty listing due to unpersisted records

## Description

`GET /workflows` consistently returns an empty list even after workflows have been successfully created via `POST /workflows`. No error is returned; the response is simply `{"workflows": [], "total": 0}`.

## Reproduction

```bash
# Create several workflows
for i in 1 2 3; do
  curl -s -X POST http://localhost:8000/workflows \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"flow-$i\", \"description\": \"\"}"
done

# List them — returns empty
curl "http://localhost:8000/workflows"
# {"workflows": [], "total": 0}
```

## Expected Behavior

`GET /workflows` returns all previously created workflows.

## Actual Behavior

Returns empty results — the created records were never committed to the database.

## Chain Note

This issue shares a root cause with issues #16–20. Fix the root once and all five resolve.

## Steps to Fix

- In `app/executor.py`, change session.flush() to session.commit() in the final workflow status update block. Verify with: `python -m pytest scoring/test_issues.py::test_17_chain_list -v` (must fail before fix, pass after).
