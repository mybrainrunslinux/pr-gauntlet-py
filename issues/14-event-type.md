# Issue #14: event-type

**Difficulty:** Tier 3 (Vague)
**File(s):** `app/executor.py`
**Type:** Event name mismatch (emit vs subscribe)

## Description

When a step finishes, the executor emits `event_bus.emit("step_done", ...)` but all subscribers (including the DAG scheduler) listen for `"step_complete"`. The name mismatch means step-completion events are silently discarded: downstream steps are never triggered, and the workflow stalls after the first step.

## Reproduction

```python
# Run a 2-step sequential workflow
# Step 1 completes (status = "completed" in DB)
# Step 2 never starts — waits for "step_complete" event that never fires
# Workflow appears hung after step 1
```

## Expected Behavior

The executor emits `"step_complete"` so the DAG scheduler picks up the event and schedules the next eligible step.

## Actual Behavior

The executor emits `"step_done"`. No subscriber listens for this; the workflow halts after the first step.
