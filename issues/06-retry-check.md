# Issue #06: retry-check

**Difficulty:** Tier 2 (Moderate)
**File(s):** `app/main.py`
**Type:** Off-by-one retry boundary

## Description

The retry eligibility check uses `step.retry_count > step.max_retries` (strict greater-than) instead of `>=`. A step configured with `max_retries=2` will be retried 3 times (counts 0, 1, 2) instead of the intended 2.

## Reproduction

```python
# Create a step with max_retries=1
# Trigger failure — observe it retries twice instead of once
# retry_count reaches 1, check is 1 > 1 = False → retries again
# retry_count reaches 2, check is 2 > 1 = True → finally marked failed
```

## Expected Behavior

A step with `max_retries=N` is retried at most N times total, then marked as permanently failed.

## Actual Behavior

The step is retried N+1 times before being marked failed.

## Steps to Fix

- In `app/main.py`, change the retry boundary check from retry_count > max_retries to retry_count >= max_retries. Verify with: `python -m pytest scoring/test_issues.py::test_06_retry_check -v` (must fail before fix, pass after).
