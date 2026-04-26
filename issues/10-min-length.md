# Issue #10: min-length

**Difficulty:** Tier 2 (Moderate)
**File(s):** `app/schemas.py`
**Type:** Missing validation constraint

## Description

The `StepCreate` schema's `name` field is missing `min_length=1`. This allows steps to be created with an empty string as their name, which breaks display, logging, and any name-based lookup.

## Reproduction

```bash
# Create a workflow first, get its ID, then:
curl -X POST http://localhost:8000/workflows/$WF_ID/steps \
  -H "Content-Type: application/json" \
  -d '{"name": "", "command": "echo hi", "order": 1}'
# Returns 200/201 — should return 422 Unprocessable Entity
```

## Expected Behavior

`StepCreate` with `name=""` is rejected with HTTP 422 and a validation error.

## Actual Behavior

Empty step names are accepted and persisted.

## Steps to Fix

- In `app/schemas.py`, add min_length=1 constraint to the step name field in the Pydantic schema. Verify with: `python -m pytest scoring/test_issues.py::test_10_min_length -v` (must fail before fix, pass after).
