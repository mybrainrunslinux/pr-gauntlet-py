# Issue #04: delete-status

**Difficulty:** Tier 1 (Clear)
**File(s):** `app/main.py`
**Type:** Wrong HTTP status code

## Description

`DELETE /workflows/{id}` returns HTTP 200 with a JSON body instead of the correct 204 No Content. Successful deletions should return 204 with an empty body per REST convention.

## Reproduction

```bash
# Create then delete a workflow
ID=$(curl -s -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"name": "tmp", "description": ""}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -s -o /dev/null -w "%{http_code}" -X DELETE http://localhost:8000/workflows/$ID
# Returns: 200 (should be 204)
```

## Expected Behavior

`DELETE /workflows/{id}` returns **204 No Content** with an empty response body.

## Actual Behavior

Returns **200 OK** with a JSON message body.
