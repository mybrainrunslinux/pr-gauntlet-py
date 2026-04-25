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
