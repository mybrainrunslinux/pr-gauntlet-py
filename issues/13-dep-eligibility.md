# Issue #13: dep-eligibility

**Difficulty:** Tier 3 (Vague)
**File(s):** `app/executor.py`
**Type:** Wrong set-membership predicate (any vs all)

## Description

Step eligibility for execution uses `any(d in completed for d in deps)` — a step becomes runnable as soon as ANY one of its dependencies completes. The correct predicate is `all()`: a step should only run when ALL of its declared dependencies have completed.

This bug causes steps to run prematurely, reading outputs from dependencies that haven't finished yet and producing incorrect results or crashes.

## Reproduction

```python
# DAG: A → C, B → C  (C depends on both A and B)
# With any(): C starts as soon as A finishes, even if B is still running
# With all(): C only starts once both A and B are done
```

## Expected Behavior

A step with dependencies `[A, B]` only starts after both A and B have completed.

## Actual Behavior

The step starts after either A or B completes — whichever finishes first.

## Steps to Fix

- In `app/executor.py`, change the DAG eligibility check from any(d in completed for d in deps) to all(d in completed for d in deps). Verify with: `python -m pytest scoring/test_issues.py::test_13_dep_eligibility -v` (must fail before fix, pass after).
