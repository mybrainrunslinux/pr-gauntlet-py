"""FlowForge — workflow orchestration API.

Endpoints
---------
POST   /token                               - obtain a JWT (dev convenience)
POST   /workflows                           - create workflow  [auth]
GET    /workflows                           - list (paginated, searchable)
GET    /workflows/{id}                      - workflow + steps
DELETE /workflows/{id}                      - delete  [auth]

POST   /workflows/{id}/run                  - start workflow  [auth]
POST   /workflows/{id}/steps/{step_id}/retry - retry step  [auth]

GET    /workflows/{id}/steps                - list steps
GET    /workflows/{id}/steps/{step_id}      - single step

WS     /workflows/{id}/events               - real-time events
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import create_access_token, require_auth
from .database import AsyncSessionFactory, get_db, init_db
from .executor import event_bus, schedule_step, schedule_workflow
from .models import AuditLog, Step, Workflow
from .schemas import (
    StepRead,
    TokenRequest,
    TokenResponse,
    WorkflowCreate,
    WorkflowDetail,
    WorkflowList,
    WorkflowRead,
)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="FlowForge", version="1.0.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _get_workflow_or_404(workflow_id: str, db: AsyncSession) -> Workflow:
    wf = await db.get(Workflow, workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


async def _get_step_or_404(
    workflow_id: str, step_id: str, db: AsyncSession
) -> Step:
    step = await db.get(Step, step_id)
    if step is None or step.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Step not found")
    return step


async def _write_audit(
    db: AsyncSession,
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
    db.add(log)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@app.post("/token", response_model=TokenResponse, tags=["auth"])
async def get_token(body: TokenRequest) -> TokenResponse:
    """Development convenience — returns a valid token for any username."""
    token = create_access_token(subject=body.username)
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# Workflows — CRUD
# ---------------------------------------------------------------------------


@app.post(
    "/workflows",
    response_model=WorkflowDetail,
    status_code=status.HTTP_201_CREATED,
    tags=["workflows"],
)
async def create_workflow(
    body: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> WorkflowDetail:
    """Create a workflow with its steps.

    `StepCreate.depends_on` contains **step names** from the same request.
    They are resolved to UUIDs before persisting so the JSON column stores IDs.
    """
    workflow_id = str(uuid.uuid4())
    now = _utcnow()

    workflow = Workflow(
        id=workflow_id,
        name=body.name,
        description=body.description,
        status="pending",
        created_at=now,
        updated_at=now,
        scheduled_at=body.scheduled_at,
    )
    db.add(workflow)

    # Assign UUIDs to steps first so we can resolve depends_on names → IDs.
    name_to_id: dict[str, str] = {}
    step_objects: list[Step] = []

    for sc in body.steps:
        sid = str(uuid.uuid4())
        name_to_id[sc.name] = sid
        step_objects.append(
            Step(
                id=sid,
                workflow_id=workflow_id,
                name=sc.name,
                depends_on=[],  # filled in below
                status="pending",
                retry_count=0,
                max_retries=sc.max_retries,
            )
        )

    # Resolve depends_on names → IDs.
    for sc, step in zip(body.steps, step_objects):
        resolved: list[str] = []
        for dep_name in sc.depends_on:
            dep_id = name_to_id.get(dep_name)
            if dep_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Step '{sc.name}' depends_on unknown step name '{dep_name}'",
                )
            resolved.append(dep_id)
        step.depends_on = resolved
        db.add(step)

    # Audit: workflow created.
    await _write_audit(db, workflow_id, "workflow_create", {
        "name": body.name,
        "step_count": len(step_objects),
    })

    # get_db commits on success.
    await db.flush()

    # Build response manually (relationships aren't auto-loaded in async).
    return WorkflowDetail(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        status=workflow.status,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        scheduled_at=workflow.scheduled_at,
        steps=[StepRead.model_validate(s) for s in step_objects],
    )


@app.get("/workflows", response_model=WorkflowList, tags=["workflows"])
async def list_workflows(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> WorkflowList:
    """List workflows with optional case-insensitive name search."""
    offset = (page - 1) * limit

    base_filter = []
    if search:
        base_filter.append(
            Workflow.name.ilike(f"%{search}%")
        )

    # Total count with same filter.
    count_result = await db.execute(
        select(func.count(Workflow.id)).where(*base_filter)
    )
    total: int = count_result.scalar_one()

    # Paginated rows.
    rows_result = await db.execute(
        select(Workflow)
        .where(*base_filter)
        .order_by(Workflow.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    workflows = rows_result.scalars().all()

    return WorkflowList(
        items=[WorkflowRead.model_validate(w) for w in workflows],
        total=total,
        page=page,
        limit=limit,
    )


@app.get("/workflows/{workflow_id}", response_model=WorkflowDetail, tags=["workflows"])
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
) -> WorkflowDetail:
    """Get workflow with all its steps."""
    workflow = await _get_workflow_or_404(workflow_id, db)

    steps_result = await db.execute(
        select(Step).where(Step.workflow_id == workflow_id)
    )
    steps = steps_result.scalars().all()

    return WorkflowDetail(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        status=workflow.status,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        scheduled_at=workflow.scheduled_at,
        steps=[StepRead.model_validate(s) for s in steps],
    )


@app.delete(
    "/workflows/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["workflows"],
)
async def delete_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> Response:
    """Delete a workflow and all its steps (CASCADE)."""
    workflow = await _get_workflow_or_404(workflow_id, db)
    await db.delete(workflow)
    await _write_audit(db, workflow_id, "workflow_delete", {})
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Workflow execution
# ---------------------------------------------------------------------------


@app.post(
    "/workflows/{workflow_id}/run",
    response_model=WorkflowRead,
    tags=["workflows"],
)
async def run_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> WorkflowRead:
    """Start running a workflow in the background."""
    workflow = await _get_workflow_or_404(workflow_id, db)

    if workflow.status in ("running",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workflow is already running",
        )
    if workflow.status in ("completed",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workflow already completed — delete and recreate to re-run",
        )

    # Schedule background execution (strong reference held by executor module).
    schedule_workflow(workflow_id)

    return WorkflowRead.model_validate(workflow)


# ---------------------------------------------------------------------------
# Step endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/workflows/{workflow_id}/steps",
    response_model=list[StepRead],
    tags=["steps"],
)
async def list_steps(
    workflow_id: str,
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[StepRead]:
    """List all steps for a workflow."""
    await _get_workflow_or_404(workflow_id, db)

    query = select(Step).where(Step.workflow_id == workflow_id)
    if status:
        query = query.where(Step.status == status)
    
    result = await db.execute(query)
    steps = result.scalars().all()
    return [StepRead.model_validate(s) for s in steps]


@app.get(
    "/workflows/{workflow_id}/steps/{step_id}",
    response_model=StepRead,
    tags=["steps"],
)
async def get_step(
    workflow_id: str,
    step_id: str,
    db: AsyncSession = Depends(get_db),
) -> StepRead:
    """Get a single step."""
    step = await _get_step_or_404(workflow_id, step_id, db)
    return StepRead.model_validate(step)


@app.post(
    "/workflows/{workflow_id}/steps/{step_id}/retry",
    response_model=StepRead,
    tags=["steps"],
)
async def retry_step(
    workflow_id: str,
    step_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> StepRead:
    """Retry a failed step.

    Rejects with 400 if the step has already reached max_retries.
    Rejects with 409 if the step is not in `failed` state.
    """
    step = await _get_step_or_404(workflow_id, step_id, db)

    if step.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step is in '{step.status}' state — only failed steps can be retried",
        )
    if step.retry_count >= step.max_retries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Step has reached max_retries ({step.max_retries}); "
                "increase max_retries to retry further"
            ),
        )

    # Reset step to pending state.
    step.status = "pending"
    step.retry_count += 1
    step.started_at = None
    step.completed_at = None
    step.result = None
    # Schedule the individual step BEFORE committing (background task may see stale state).
    schedule_step(step_id)

    await db.commit()

    return StepRead.model_validate(step)


# ---------------------------------------------------------------------------
# WebSocket — real-time events
# ---------------------------------------------------------------------------


@app.websocket("/workflows/{workflow_id}/events")
async def workflow_events(workflow_id: str, websocket: WebSocket) -> None:
    """Subscribe to real-time events for a workflow."""
    await websocket.accept()

    # Verify workflow exists (quick read, no auth required per spec).
    async with AsyncSessionFactory() as session:
        wf = await session.get(Workflow, workflow_id)
        if wf is None:
            await websocket.send_json({"error": "Workflow not found"})
            await websocket.close(code=1008)

    queue = event_bus.subscribe(workflow_id)
    try:
        while True:
            # Wait for an event OR a client disconnect (whichever comes first).
            # We poll get() with a short timeout and also try to receive from
            # the client so WebSocketDisconnect is raised promptly.
            try:
                event = queue.get_nowait()
                await websocket.send_json(event)
            except asyncio.QueueEmpty:
                # Short wait to yield the event loop; also allows disconnect
                # detection via the receive below.
                try:
                    # Non-blocking peek for client messages / disconnects.
                    await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                except asyncio.TimeoutError:
                    pass  # normal: no message yet
                except Exception:
                    # Handle any unexpected errors in receive_text()
                    break
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe(workflow_id, queue)
