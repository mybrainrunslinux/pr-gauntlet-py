# Issue #19: chain-step

**Difficulty:** Tier 4 (Chain)
**File(s):** `app/executor.py`
**Type:** 404 on step creation due to missing parent record

## Description

`POST /workflows/{id}/steps` returns 404 Not Found when trying to add a step to a workflow. The workflow ID is valid (returned by the create endpoint) but the record doesn't exist in the database, so the foreign-key lookup for the parent workflow fails.

## Reproduction

```bash
ID=$(curl -s -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "description": ""}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -X POST http://localhost:8000/workflows/$ID/steps \
  -H "Content-Type: application/json" \
  -d '{"name": "step1", "command": "echo hello", "order": 1}'
# {"detail": "Workflow not found"}
```

## Expected Behavior

Steps can be added to any workflow that was successfully created.

## Actual Behavior

404 — the parent workflow record was never persisted.

## Chain Note

This issue shares a root cause with issues #16–20. Fix the root once and all five resolve.

## Steps to Fix

- In `app/executor.py`, change session.flush() to session.commit() in the final workflow status update block. Verify with: `python -m pytest scoring/test_issues.py::test_19_chain_step -v` (must fail before fix, pass after).
