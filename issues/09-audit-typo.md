# Issue #09: audit-typo

**Difficulty:** Tier 2 (Moderate)
**File(s):** `app/main.py`
**Type:** Typo in event name

## Description

The audit log event type for workflow deletion is emitted as `"workflw_delete"` (missing the letter `'o'`). Any downstream consumer filtering on `"workflow_delete"` will silently miss all deletion events.

## Reproduction

```python
import httpx, json

# Delete a workflow and inspect the audit log
r = httpx.delete("http://localhost:8000/workflows/some-id")
# Search audit records for event_type == "workflow_delete" — returns nothing
# Records exist but with event_type == "workflw_delete"
```

## Expected Behavior

Audit log records for workflow deletion have `event_type == "workflow_delete"`.

## Actual Behavior

Records are stored with `event_type == "workflw_delete"` (typo), breaking all consumers that filter by the correct event name.

## Steps to Fix

1. Read `app/main.py` and understand the bug described above.
2. Apply the minimal fix — only edit files in `app/`.
3. Validate: `python -m pytest scoring/test_issues.py::test_09_audit_typo -v`
4. Confirm the test passes before submitting.
