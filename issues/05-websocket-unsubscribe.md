# Issue #05: websocket-unsubscribe

**Difficulty:** Tier 1 (Clear)
**File(s):** `app/main.py`
**Type:** Resource leak

## Description

The WebSocket disconnect handler's `finally` block does nothing (`pass`) instead of calling `event_bus.unsubscribe(workflow_id, queue)`. Every WebSocket client that disconnects leaves its queue subscribed indefinitely, causing memory growth and phantom deliveries to dead connections.

## Reproduction

```python
import asyncio, websockets

async def test():
    async with websockets.connect("ws://localhost:8000/ws/workflows/some-id") as ws:
        pass  # connect then immediately disconnect
    # Queue for this workflow is still subscribed in event_bus — never cleaned up

asyncio.run(test())
```

## Expected Behavior

When a WebSocket client disconnects, its queue is removed from `event_bus` subscriptions.

## Actual Behavior

The subscription is never removed. Repeated connects/disconnects accumulate stale queue entries.

## Steps to Fix

1. Read `app/main.py` and understand the bug described above.
2. Apply the minimal fix — only edit files in `app/`.
3. Validate: `python -m pytest scoring/test_issues.py::test_05_websocket_unsubscribe -v`
4. Confirm the test passes before submitting.
