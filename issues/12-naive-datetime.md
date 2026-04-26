# Issue #12: naive-datetime

**Difficulty:** Tier 3 (Vague)
**File(s):** `app/executor.py`
**Type:** Timezone-aware vs naive datetime mismatch

## Description

`execution.started_at` is set using `datetime.utcnow()`, which returns a naive datetime (no `tzinfo`). When this value is later compared to a timezone-aware datetime (e.g., from a scheduled trigger or the DB column default), Python raises a `TypeError: can't compare offset-naive and offset-aware datetimes`. This surfaces as an intermittent 500 error on execution status queries.

## Reproduction

```python
from datetime import datetime, timezone

naive = datetime.utcnow()          # no tzinfo
aware = datetime.now(timezone.utc) # has tzinfo

naive < aware  # TypeError: can't compare offset-naive and offset-aware datetimes
```

## Expected Behavior

All datetime values use timezone-aware UTC: `datetime.now(timezone.utc)`.

## Actual Behavior

`started_at` is naive; comparisons with aware datetimes raise `TypeError` at runtime.

## Steps to Fix

1. Read `app/executor.py` and understand the bug described above.
2. Apply the minimal fix — only edit files in `app/`.
3. Validate: `python -m pytest scoring/test_issues.py::test_12_naive_datetime -v`
4. Confirm the test passes before submitting.
