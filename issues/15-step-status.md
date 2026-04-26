# Issue #15: step-status

**Difficulty:** Tier 3 (Vague)
**File(s):** `app/executor.py`
**Type:** Raw string instead of enum value

## Description

After a step executes successfully, `step.status` is set to the raw string `"completed"` instead of `StepStatus.COMPLETED`. SQLAlchemy stores the string correctly, but queries that filter by `step.status == StepStatus.COMPLETED` return no rows because Python's enum comparison fails between `"completed"` (str) and `StepStatus.COMPLETED` (enum member).

## Reproduction

```python
# Run a workflow, then query:
from app.models import StepStatus
steps = session.query(Step).filter(Step.status == StepStatus.COMPLETED).all()
print(steps)  # [] — returns empty even though steps finished

# vs. raw string query:
steps2 = session.query(Step).filter(Step.status == "completed").all()
print(steps2)  # Returns results — inconsistent depending on query style
```

## Expected Behavior

`step.status = StepStatus.COMPLETED` — enum member used consistently, allowing enum-based filtering to work correctly.

## Actual Behavior

`step.status = "completed"` — raw string breaks enum-based queries.

## Steps to Fix

- In `app/main.py`, add an optional status query parameter to the list_steps endpoint. Verify with: `python -m pytest scoring/test_issues.py::test_15_step_status -v` (must fail before fix, pass after).
