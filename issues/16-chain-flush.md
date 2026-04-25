# Issue #16: chain-flush

**Difficulty:** Tier 4 (Chain — root cause)
**File(s):** `app/executor.py`
**Type:** Flush without commit — data not persisted

## Description

`create_workflow` calls `await session.flush()` instead of `await session.commit()`. `flush()` stages the INSERT in the current transaction but does not persist it to disk. When the session context manager exits, the transaction is rolled back and the workflow record is lost. The response object is returned with an ID that no longer exists in the database.

## Reproduction

```bash
ID=$(curl -s -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "description": ""}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Workflow appears created, but:
curl http://localhost:8000/workflows/$ID
# Returns 404 — record was rolled back
```

## Expected Behavior

`session.commit()` persists the new workflow; subsequent GETs return the record.

## Actual Behavior

`session.flush()` stages but does not commit; the record is rolled back and the returned ID is a ghost.

## Chain Note

This issue shares a root cause with issues #16–20. Fix the root once and all five resolve.
