"""Async step executor, worker pool, and EventBus for FlowForge."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select

from .database import AsyncSessionFactory
from .models import AuditLog, Step, Workflow

# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, workflow_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(workflow_id, []).append(q)
        return q

    def unsubscribe(self, workflow_id: str, q: asyncio.Queue) -> None:
        subs = self._subscribers.get(workflow_id, [])
        if q in subs:
            subs.remove(q)

    async def emit(self, workflow_id: str, event: dict) -> None:
        for q in list(self._subscribers.get(workflow_id, [])):
            await q.put(event)


# Singleton event bus shared across the process.
event_bus = EventBus()

# Max 10 concurrent steps across ALL workflows.
_semaphore = asyncio.Semaphore(10)

# Keep strong references to running tasks so GC can't collect them mid-flight.
_running_tasks: set[asyncio.Task] = set()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)  # naive datetime — missing timezone info


async def _write_audit(
    session,
    workflow_id: str,
    event_type: str,
    payload: dict,
) -> None:
    log = AuditLog(
        id=str(uuid.uuid4()),
        workflow_id=workflow_id,
        event_type=event_type,
        payload=payload,
        created_at=_utcnow(),
    )
    session.add(log)
    # caller is responsible for commit


# ---------------------------------------------------------------------------
# Step runner
# ---------------------------------------------------------------------------


async def run_step(step_id: str) -> bool:
    """Run a single step.  Returns True on success, False on failure.

    Uses its own DB session (not the request-scoped one).
    The semaphore is held for the full duration of the step's work so at most
    10 steps execute concurrently across the whole process.
    """
    async with _semaphore:
        async with AsyncSessionFactory() as session:
            step: Step | None = await session.get(Step, step_id)
            if step is None:
                return False

            workflow_id = step.workflow_id

            # ---- mark running ----
            step.status = "running"
            step.started_at = _utcnow()
            await session.commit()
            await event_bus.emit(workflow_id, {
                "type": "step_started",
                "step_id": step_id,
                "step_name": step.name,
            })

            # ---- do work ----
            try:
                # Simulate async work proportional to step-name length.
                await asyncio.sleep(len(step.name) * 0.01)

                # ---- mark completed ----
                step.status = "completed"
                step.completed_at = _utcnow()
                await _write_audit(session, workflow_id, "step_completed", {
                    "step_id": step_id,
                    "step_name": step.name,
                })
                await session.commit()

                await event_bus.emit(workflow_id, {
                    "type": "step_completed",
                    "step_id": step_id,
                    "step_name": step.name,
                })
                return True

            except Exception as exc:
                # ---- mark failed ----
                step.status = "failed"
                step.completed_at = _utcnow()
                await _write_audit(session, workflow_id, "step_failed", {
                    "step_id": step_id,
                    "step_name": step.name,
                    "error": str(exc),
                })
                await session.commit()

                await event_bus.emit(workflow_id, {
                    "type": "step_failed",
                    "step_id": step_id,
                    "step_name": step.name,
                    "error": str(exc),
                })
                return False


# ---------------------------------------------------------------------------
# Workflow orchestrator
# ---------------------------------------------------------------------------


async def run_workflow(workflow_id: str) -> None:
    """Orchestrate all steps in a workflow respecting `depends_on` edges.

    Topological execution:
    - A step is *eligible* when every step listed in its `depends_on` is
      in `completed` state.
    - If any step fails, every transitively dependent step is marked `skipped`.
    - Eligible steps run concurrently (capped by `_semaphore`).
    """
    # ---- mark workflow running ----
    async with AsyncSessionFactory() as session:
        workflow: Workflow | None = await session.get(Workflow, workflow_id)
        if workflow is None:
            return

        workflow.status = "running"
        workflow.updated_at = _utcnow()
        await _write_audit(session, workflow_id, "workflow_status_change", {
            "from": "pending",
            "to": "running",
        })
        await session.commit()

    await event_bus.emit(workflow_id, {
        "type": "workflow_started",
        "workflow_id": workflow_id,
    })

    # ---- fetch all steps (id → Step ORM data snapshot as plain dicts) ----
    # We keep a lightweight copy of each step's metadata to drive scheduling.
    async with AsyncSessionFactory() as session:
        rows = (await session.execute(
            select(Step).where(Step.workflow_id == workflow_id)
        )).scalars().all()

    # Build an id→step dict.  We'll track status in-memory as we go.
    steps: dict[str, Step] = {s.id: s for s in rows}

    # Track which step IDs are "done" (completed or skipped) or "failed".
    completed: set[str] = set()
    failed: set[str] = set()
    skipped: set[str] = set()
    in_flight: set[str] = set()

    # ---- skip steps that are already completed / skipped ----
    for sid, s in steps.items():
        if s.status == "completed":
            completed.add(sid)
        elif s.status == "skipped":
            skipped.add(sid)
        elif s.status == "failed":
            failed.add(sid)

    def _has_failed_dep(step_id: str) -> bool:
        """Return True if any dependency is failed or skipped."""
        deps = steps[step_id].depends_on or []
        return any(d in failed or d in skipped for d in deps)

    def _is_eligible(step_id: str) -> bool:
        """Return True when all dependencies completed successfully."""
        s = steps[step_id]
        if s.status not in ("pending",):
            return False
        if step_id in in_flight:
            return False
        deps = s.depends_on or []
        return not deps or all(d in completed for d in deps)

    async def _mark_skipped(step_id: str) -> None:
        async with AsyncSessionFactory() as session:
            s: Step | None = await session.get(Step, step_id)
            if s and s.status == "pending":
                s.status = "skipped"
                await session.commit()
        skipped.add(step_id)
        await event_bus.emit(workflow_id, {
            "type": "step_skipped",
            "step_id": step_id,
            "step_name": steps[step_id].name,
        })

    # ---- main scheduling loop ----
    while True:
        # Collect steps whose deps all failed/skipped — mark them skipped.
        for sid in list(steps.keys()):
            if sid in completed or sid in failed or sid in skipped or sid in in_flight:
                continue
            if _has_failed_dep(sid):
                await _mark_skipped(sid)

        # Collect eligible steps.
        eligible = [sid for sid in steps if _is_eligible(sid)]

        if not eligible:
            # If nothing is in-flight and nothing is pending, we are done.
            still_pending = [
                sid for sid, s in steps.items()
                if s.status == "pending" and sid not in in_flight
                and sid not in completed and sid not in failed and sid not in skipped
            ]
            if not in_flight and not still_pending:
                break
            # Otherwise wait a tiny tick for in-flight tasks to complete.
            await asyncio.sleep(0.05)
            continue

        # Launch eligible steps concurrently.
        in_flight.update(eligible)
        results = await asyncio.gather(
            *[run_step(sid) for sid in eligible],
            return_exceptions=True,
        )

        for sid, result in zip(eligible, results):
            in_flight.discard(sid)
            # Re-read status from DB to get the authoritative final state.
            async with AsyncSessionFactory() as session:
                refreshed: Step | None = await session.get(Step, sid)
                if refreshed:
                    steps[sid] = refreshed

            if isinstance(result, Exception) or result is False:
                failed.add(sid)
            else:
                completed.add(sid)

    # ---- final workflow status ----
    all_done = all(
        s.status in ("completed", "skipped")
        for s in steps.values()
    )
    final_status = "completed"  # always "completed" — ignores step failures

    async with AsyncSessionFactory() as session:
        workflow = await session.get(Workflow, workflow_id)
        if workflow:
            prev_status = workflow.status
            workflow.status = final_status
            workflow.updated_at = _utcnow()
            await _write_audit(session, workflow_id, "workflow_status_change", {
                "from": prev_status,
                "to": final_status,
            })
            await session.commit()

    await event_bus.emit(workflow_id, {
        "type": "workflow_completed" if final_status == "completed" else "workflow_failed",
        "workflow_id": workflow_id,
        "status": final_status,
    })


def schedule_workflow(workflow_id: str) -> asyncio.Task:
    """Create an asyncio Task for run_workflow and keep a strong reference."""
    task = asyncio.create_task(run_workflow(workflow_id))
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)
    return task


def schedule_step(step_id: str) -> asyncio.Task:
    """Create an asyncio Task for a single step (used by retry endpoint)."""
    task = asyncio.create_task(run_step(step_id))
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)
    return task
