# Issue #18: chain-run

**Difficulty:** Tier 4 (Chain)
**File(s):** `app/executor.py`
**Type:** 404 on run due to missing record

## Description

`POST /workflows/{id}/run` returns 404 Not Found for any workflow ID, even one just returned by a successful `POST /workflows`. The workflow appears to be created (the creation endpoint returns a valid ID) but cannot be found when attempting to run it.

## Reproduction

```bash
ID=$(curl -s -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "description": ""}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -X POST http://localhost:8000/workflows/$ID/run
# {"detail": "Workflow not found"}
```

## Expected Behavior

A workflow created via `POST /workflows` can immediately be run via `POST /workflows/{id}/run`.

## Actual Behavior

404 — the workflow record was not committed and does not exist.

## Chain Note

This issue shares a root cause with issues #16–20. Fix the root once and all five resolve.

## Steps to Fix

- In `app/executor.py`, change session.flush() to session.commit() in the final workflow status update block. Verify with: `python -m pytest scoring/test_issues.py::test_18_chain_run -v` (must fail before fix, pass after).
