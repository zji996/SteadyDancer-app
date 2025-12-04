from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from libs.py_core.celery_client import celery_client


router = APIRouter(prefix="/steadydancer", tags=["steadydancer"])


class SteadyDancerJobCreate(BaseModel):
    input_dir: str = Field(
        ...,
        description=(
            "Directory containing SteadyDancer preprocessed inputs, "
            "including ref_image.png, prompt.txt, positive/ and negative/."
        ),
    )
    prompt_override: str | None = Field(
        None,
        description="Optional prompt override; falls back to prompt.txt if omitted.",
    )
    size: str = Field(
        "1024*576",
        description="Output resolution, e.g. 1024*576. Must be supported by upstream.",
    )
    frame_num: int = Field(
        81,
        description="Number of frames (4n+1), default 81 as in upstream examples.",
    )
    sample_guide_scale: float = Field(5.0, description="CFG scale for sampling.")
    condition_guide_scale: float = Field(
        1.0,
        description="CFG scale specific to the condition.",
    )
    end_cond_cfg: float = Field(
        0.4,
        description="End config for negative condition guidance.",
    )
    base_seed: int = Field(
        -1,
        description="Base random seed; -1 means random seed as in upstream.",
    )
    cuda_visible_devices: str | None = Field(
        None,
        description="Optional CUDA_VISIBLE_DEVICES override for this job.",
    )


class SteadyDancerJobCreated(BaseModel):
    task_id: str


class SteadyDancerJobStatus(BaseModel):
    task_id: str
    state: str
    result: dict[str, Any] | None = None


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

    task_payload = {
        "input_dir": str(input_dir),
        "prompt_override": payload.prompt_override,
        "size": payload.size,
        "frame_num": payload.frame_num,
        "sample_guide_scale": payload.sample_guide_scale,
        "condition_guide_scale": payload.condition_guide_scale,
        "end_cond_cfg": payload.end_cond_cfg,
        "base_seed": payload.base_seed,
        "cuda_visible_devices": payload.cuda_visible_devices,
    }

    task = celery_client.send_task("steadydancer.generate.i2v", args=[task_payload])
    return SteadyDancerJobCreated(task_id=task.id)


@router.get("/jobs/{task_id}", response_model=SteadyDancerJobStatus)
async def get_job_status(task_id: str) -> SteadyDancerJobStatus:
    """
    Query the status of a SteadyDancer generation job.

    When finished, the result contains:
    - success: bool
    - video_path: str | null
    - stdout / stderr / return_code
    """
    async_result = celery_client.AsyncResult(task_id)
    state = async_result.state

    result: dict[str, Any] | None
    if async_result.failed():
        # Celery wraps exceptions; surface a simple message.
        raise HTTPException(
            status_code=500,
            detail={"task_id": task_id, "state": state, "error": str(async_result.info)},
        )

    if async_result.successful():
        data = async_result.result
        if isinstance(data, dict):
            result = data
        else:
            result = {"value": data}
    else:
        result = None

    return SteadyDancerJobStatus(task_id=task_id, state=state, result=result)

