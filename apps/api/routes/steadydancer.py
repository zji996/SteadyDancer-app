from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from apps.api.schemas.steadydancer import (
    SteadyDancerJobCreate,
    SteadyDancerJobCreated,
    SteadyDancerJobStatus,
)
from apps.api.services import steadydancer_jobs as job_service


router = APIRouter(prefix="/steadydancer", tags=["steadydancer"])


@router.post("/jobs", response_model=SteadyDancerJobCreated)
async def create_job(payload: SteadyDancerJobCreate) -> SteadyDancerJobCreated:
    """
    Enqueue a SteadyDancer I2V generation job.

    This only schedules the Celery task and returns its ID.
    """
    input_dir = Path(payload.input_dir)
    if not input_dir.is_absolute():
        # Interpret repo-root-relative paths; Celery worker runs in the same repo.
        input_dir = Path.cwd() / input_dir

    task_payload = job_service.build_task_payload(payload=payload, input_dir=input_dir)
    task_id = job_service.enqueue_steadydancer_task(task_payload=task_payload)
    return SteadyDancerJobCreated(task_id=task_id)


@router.get("/jobs/{task_id}", response_model=SteadyDancerJobStatus)
async def get_job_status(task_id: str) -> SteadyDancerJobStatus:
    """
    Query the status of a SteadyDancer generation job.

    When finished, the result contains:
    - success: bool
    - video_path: str | null
    - stdout / stderr / return_code
    """
    state, result, error = job_service.query_celery_task(task_id=task_id)

    if error is not None:
        # Celery wraps exceptions; surface a simple message.
        raise HTTPException(
            status_code=500,
            detail={"task_id": task_id, "state": state, "error": str(error)},
        )

    return SteadyDancerJobStatus(task_id=task_id, state=state, result=result)
