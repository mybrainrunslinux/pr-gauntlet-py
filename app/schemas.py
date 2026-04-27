"""Pydantic v2 request/response schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Step schemas
# ---------------------------------------------------------------------------

class StepCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    depends_on: list[str] = Field(default_factory=list)
    max_retries: int = Field(default=3, ge=0)


class StepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    name: str
    depends_on: Optional[list[str]] = None
    status: str
    retry_count: int
    max_retries: int
    result: Optional[Any] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Workflow schemas
# ---------------------------------------------------------------------------

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    scheduled_at: Optional[datetime] = Field(default=None)
    steps: list[StepCreate] = Field(default_factory=list)


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    scheduled_at: Optional[datetime] = None


class WorkflowDetail(WorkflowRead):
    steps: list[StepRead] = Field(default_factory=list)


class WorkflowList(BaseModel):
    items: list[WorkflowRead]
    total: int
    page: int
    limit: int


# ---------------------------------------------------------------------------
# AuditLog schemas
# ---------------------------------------------------------------------------

class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    event_type: str
    payload: Optional[Any] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
