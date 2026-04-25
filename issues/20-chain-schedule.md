# Issue #20: chain-schedule

**Difficulty:** Tier 4 (Chain)
**File(s):** `app/executor.py`
**Type:** 404 on schedule due to missing record

## Description

`POST /workflows/{id}/schedule` returns 404 Not Found. Like the run and step endpoints, it cannot locate the workflow because the record was staged but never committed during creation.

## Reproduction

```bash
ID=$(curl -s -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "description": ""}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -X POST http://localhost:8000/workflows/$ID/schedule \
  -H "Content-Type: application/json" \
  -d '{"scheduled_at": "2026-05-01T09:00:00Z"}'
# {"detail": "Workflow not found"}
```

## Expected Behavior

A created workflow can be scheduled for future execution.

## Actual Behavior

404 — parent record not in DB, scheduling fails.

## Chain Note

This issue shares a root cause with issues #16–20. Fix the root once and all five resolve.
