# Issue #07: ws-close

**Difficulty:** Tier 2 (Moderate)
**File(s):** `app/main.py`
**Type:** Missing return after close

## Description

After calling `await websocket.close()` in the message loop's error handler, there is no `return` statement. Execution falls through and attempts to continue reading from the already-closed WebSocket, causing a spurious exception on the next iteration.

## Reproduction

```python
# Send an invalid message type over WebSocket
# Observe: WebSocket closes but server logs an additional exception
# ("Cannot call receive() after WebSocket is closed" or similar)
```

## Expected Behavior

After `websocket.close()`, the handler returns immediately with no further processing.

## Actual Behavior

The handler continues to the next loop iteration and raises an error attempting to read from the closed socket.

## Steps to Fix

1. Read `app/main.py` and understand the bug described above.
2. Apply the minimal fix — only edit files in `app/`.
3. Validate: `python -m pytest scoring/test_issues.py::test_07_ws_close -v`
4. Confirm the test passes before submitting.
