# Issue #08: schedule-order

**Difficulty:** Tier 2 (Moderate)
**File(s):** `app/main.py`
**Type:** Race condition / wrong operation order

## Description

In the schedule endpoint, `workflow.scheduled_at` is set to `scheduled_time` before the database session is committed. If the scheduler fires between the assignment and the commit, it reads a workflow record that has `scheduled_at` set but whose transaction hasn't been persisted — it may operate on stale or rolled-back state.

## Reproduction

```bash
# Schedule a workflow with a very short lead time
# Under load, the job can fire before session.commit() completes
# Result: scheduler sees inconsistent workflow state
```

## Expected Behavior

`session.commit()` persists the schedule change first; only then is the job enqueued.

## Actual Behavior

The job is enqueued before the commit, creating a window where the scheduler fires against uncommitted data.

## Steps to Fix

1. Read `app/main.py` and understand the bug described above.
2. Apply the minimal fix — only edit files in `app/`.
3. Validate: `python -m pytest scoring/test_issues.py::test_08_schedule_order -v`
4. Confirm the test passes before submitting.
