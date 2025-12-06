from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., description="Project name for grouping related jobs.")
    description: str | None = Field(
        None,
        description="Optional human-readable description for this project.",
    )


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


class ProjectJobCreated(BaseModel):
    project_id: UUID
    job_id: UUID
    task_id: str


class ProjectJobStatus(BaseModel):
    project_id: UUID
    job_id: UUID
    task_id: str
    state: str
    result: dict[str, Any] | None = None


class ProjectJobCancel(BaseModel):
    reason: str | None = Field(
        None,
        description="Optional human-readable reason for cancelling the job.",
    )


class ProjectJobSummary(BaseModel):
    id: UUID
    project_id: UUID
    experiment_id: UUID | None
    task_id: str
    job_type: str
    status: str
    result_video_path: str | None = None

    class Config:
        from_attributes = True
