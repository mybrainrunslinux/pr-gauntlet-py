# PR-Gauntlet · Python Edition

A benchmark for coding agents, bots, and autonomous development stacks — **v2: Python/FastAPI**.

**20 crafted GitHub Issues** on a real Python/FastAPI application, ranging from crystal-clear one-liners to deeply interdependent bugs that require tracing a root cause across multiple files.

Part of the PR-Gauntlet series:
- [PR-Gauntlet v1](https://github.com/mybrainrunslinux/pr-gauntlet) — TypeScript/React (20 issues)
- **[PR-Gauntlet v2](https://github.com/mybrainrunslinux/pr-gauntlet-py) — Python/FastAPI (this repo)**
- [PR-Gauntlet v3](https://github.com/mybrainrunslinux/pr-gauntlet-gl) — Three.js/WebGL (20 issues)

## How It Works

```
┌─────────────┐    ┌────────────────┐    ┌─────────────────┐
│  v0-clean   │───▶│  v1-bugged     │───▶│  your-bot-branch│
│  (passes    │    │  (20 bugs      │    │  (agent fixes   │
│   all tests)│    │   introduced)  │    │   the issues)   │
└─────────────┘    └────────────────┘    └─────────────────┘
                         diff ▲                diff ▲
                    shows what was         shows what agent
                    broken                    changed
```

Fork the repo, point your agent at `v1-bugged`, and let it work through the issues. Run the scorer to see how many it fixed — and diff against `v0-clean` to see *how* it fixed them.

## Scoring

```bash
cd /path/to/pr-gauntlet-py
pip install -r app/requirements.txt pytest httpx pytest-asyncio pytest-json-report

# All 20 issues
pytest scoring/test_issues.py -v

# Single issue
pytest scoring/test_issues.py::test_01_create_status -v

# Machine-readable JSON report
pytest scoring/test_issues.py --json-report --json-report-file=results.json -q
```

## Issue Tiers

| Tier | Issues | Difficulty |
|------|--------|------------|
| 1 — Clear | 1–5 | Obvious bug, obvious fix |
| 2 — Moderate | 6–10 | Requires understanding async/concurrency patterns |
| 3 — Vague | 11–15 | Symptoms are real; root cause requires investigation |
| 4 — Chain | 16–20 | Issues share a root cause — fix the source, side-effects resolve |

### Issue Index

| # | Name | Description |
|---|------|-------------|
| 01 | create-status | POST /workflows returns 200 instead of 201 |
| 02 | page-offset | Pagination skips records with off-by-one offset |
| 03 | search-case | Case-sensitive search drops valid matches |
| 04 | delete-status | DELETE /workflows returns 200 instead of 204 |
| 05 | websocket-unsubscribe | WS unsubscribe leaves dangling task reference |
| 06 | retry-check | Step executor ignores max_retries configuration |
| 07 | ws-close | Bad WS message crashes connection unrecoverably |
| 08 | schedule-order | scheduled_at field not persisted on workflow |
| 09 | audit-typo | Audit log records "workflw_delete" typo instead of "workflow_delete" |
| 10 | min-length | Step name="" accepted; should return 422 |
| 11 | semaphore-leak | Semaphore acquired but never released on step failure |
| 12 | naive-datetime | Naive datetime comparison crashes on timezone-aware input |
| 13 | dep-eligibility | DAG dependency check runs steps before prerequisites complete |
| 14 | event-type | Wrong event type emitted for sequential step completion |
| 15 | step-status | Steps not queryable by status field |
| 16 | chain-flush | All 5 chain issues share a root cause in `executor.py` |
| 17 | chain-list | ↑ DB session flushes but never commits — records vanish on re-query |
| 18 | chain-run | ↑ Fix `session.flush()` → `session.commit()` to resolve all five |
| 19 | chain-step | ↑ |
| 20 | chain-schedule | ↑ |

### The Chain (Issues 16–20)

Issues 16–20 are not independent. They share a single root cause in `app/executor.py`. An agent that patches each symptom in isolation will not fully resolve any of them. An agent that finds the `session.flush()` / missing `session.commit()` bug will resolve all five as a side effect.

This is the benchmark's hardest test: does the agent understand *why* or just *what*?

## Setup

```bash
git clone https://github.com/mybrainrunslinux/pr-gauntlet-py
cd pr-gauntlet-py
git checkout v1-bugged

# Install app dependencies
pip install -r app/requirements.txt

# Start the app
uvicorn app.main:app --host 127.0.0.1 --port 9201

# In another terminal — run tests against the live app
pytest scoring/test_issues.py -v
```

Python 3.11+ required. SQLite only — no external services, no API keys, no Docker required.

## The App: FlowForge

A workflow orchestration API — Python 3.11, FastAPI, SQLAlchemy async, SQLite, WebSocket notifications. DAG-based step execution with dependency tracking, scheduling, and audit logging. Enough surface area to hide real concurrency and ORM bugs; clean enough to reason about end-to-end.

See [issues/](./issues/) for all 20 issue descriptions.

## Multi-Language Series

| Repo | Language | App | Status |
|------|----------|-----|--------|
| [pr-gauntlet](https://github.com/mybrainrunslinux/pr-gauntlet) | TypeScript / React | TaskFlow (kanban) | ✅ live |
| [pr-gauntlet-py](https://github.com/mybrainrunslinux/pr-gauntlet-py) | Python / FastAPI | FlowForge (workflows) | ✅ live |
| [pr-gauntlet-gl](https://github.com/mybrainrunslinux/pr-gauntlet-gl) | Three.js / WebGL | MindBend (3D cards) | ✅ live |

The chain primitive is language-specific (React stale closures → SQLAlchemy flush/commit → WebGL projection matrix) but the scoring methodology is identical across all three.

## Continuous Competition

- Fork → branch named `your-agent/attempt-N`
- Submit a PR against `v1-bugged`
- CI runs the scorer and posts results as a PR comment
- Diff vs `v0-clean` is visible in the PR for human review

## License

MIT. Benchmark dataset (issue descriptions + test files) is CC-BY-4.0.
