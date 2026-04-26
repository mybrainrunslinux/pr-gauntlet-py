# Issue #11: semaphore-leak

**Difficulty:** Tier 3 (Vague)
**File(s):** `app/executor.py`
**Type:** Semaphore never released

## Description

`_execute_step` calls `await _semaphore.acquire()` to limit concurrency but never calls `_semaphore.release()`. Every step execution consumes one semaphore slot permanently. After the semaphore is exhausted (typically after `max_concurrent_steps` executions), all new steps block forever — the executor appears to hang with no error message.

## Reproduction

```python
# Set MAX_CONCURRENT_STEPS=2 and run a workflow with 3+ steps
# First 2 steps execute; the 3rd blocks indefinitely
# No timeout, no error — executor silently stalls
```

## Expected Behavior

Each step releases the semaphore on completion (success or failure), allowing the next queued step to run.

## Actual Behavior

After `MAX_CONCURRENT_STEPS` total executions across all workflows, all further steps block indefinitely. The system requires a restart to recover.

## Steps to Fix

- In `app/executor.py`, replace the bare _semaphore.acquire() call with async with _semaphore: to ensure it is always released. Verify with: `python -m pytest scoring/test_issues.py::test_11_semaphore_leak -v` (must fail before fix, pass after).
