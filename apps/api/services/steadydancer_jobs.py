from __future__ import annotations

import shutil
import json
from pathlib import Path
from typing import Any, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import Experiment, Job, Project, utcnow
from apps.api.schemas.steadydancer import SteadyDancerJobCreate
from libs.py_core.celery_client import celery_client
from libs.py_core.projects import (
    ensure_job_dirs,
    from_data_relative,
    resolve_repo_relative,
    to_data_relative,
)


class ProjectNotFoundError(Exception):
    """
    Raised when a project cannot be found for a given ID.
    """


class InputDirNotFoundError(Exception):
    """
    Raised when the provided input_dir does not exist or is not a directory.
    """


class JobPreparationError(Exception):
    """
    Raised when preparing the job input directory fails.
    """


def build_task_payload(payload: SteadyDancerJobCreate, input_dir: Path) -> dict[str, Any]:
    """
    Build the Celery task payload from an API-level request and resolved input_dir.
    """
    data: dict[str, Any] = {
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
    # Optional advanced parameters are only included when explicitly set.
    if payload.sample_steps is not None:
        data["sample_steps"] = payload.sample_steps
    if payload.sample_shift is not None:
        data["sample_shift"] = payload.sample_shift
    if payload.sample_solver is not None:
        data["sample_solver"] = payload.sample_solver
    if payload.offload_model is not None:
        data["offload_model"] = payload.offload_model
    return data


def enqueue_steadydancer_task(task_payload: dict[str, Any]) -> str:
    """
    Enqueue a SteadyDancer Celery task and return its task_id.
    """
    task = celery_client.send_task("steadydancer.generate.i2v", args=[task_payload])
    return task.id


def query_celery_task(task_id: str) -> Tuple[str, dict[str, Any] | None, Exception | None]:
    """
    Query Celery for a given task_id and return (state, result, error).
    """
    async_result = celery_client.AsyncResult(task_id)
    state = async_result.state

    if async_result.failed():
        return state, None, async_result.info  # type: ignore[return-value]

    result: dict[str, Any] | None
    if async_result.successful():
        data = async_result.result
        if isinstance(data, dict):
            result = data
        else:
            result = {"value": data}
    else:
        result = None

    return state, result, None


async def create_project_steadydancer_job(
    session: AsyncSession,
    project_id: UUID,
    payload: SteadyDancerJobCreate,
    experiment: Experiment | None = None,
) -> Job:
    """
    Create a SteadyDancer I2V job under a project.

    This function:
    - Validates the project exists;
    - Prepares the per-job directory structure and copies inputs;
    - Enqueues the Celery task;
    - Persists a Job row in the database.
    """
    project = await session.get(Project, project_id)
    if project is None:
        raise ProjectNotFoundError(f"Project not found: {project_id}")

    job_id = uuid4()
    job_paths = ensure_job_dirs(project_id=project_id, job_id=job_id)

    # If an experiment is provided and has a canonical input_dir, prefer it.
    if experiment is not None and experiment.input_dir:
        source_input_dir = from_data_relative(experiment.input_dir)
    else:
        source_input_dir = resolve_repo_relative(payload.input_dir)

    if not source_input_dir.is_dir():
        raise InputDirNotFoundError(
            f"input_dir not found or not a directory: {source_input_dir}"
        )

    try:
        shutil.copytree(
            source_input_dir,
            job_paths.input_dir,
            dirs_exist_ok=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise JobPreparationError(
            f"Failed to prepare job input directory: {exc}"
        ) from exc

    task_payload = build_task_payload(payload=payload, input_dir=job_paths.input_dir)
    # Enrich payload with identifiers so the worker can log under the per-job directory.
    task_payload["project_id"] = str(project_id)
    task_payload["job_id"] = str(job_id)

    # Persist the task payload to disk for offline debugging.
    try:
        config_path = job_paths.job_root / "config.json"
        config_path.write_text(
            json.dumps(task_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        # Best-effort; failures here must not prevent job creation.
        pass
    task_id = enqueue_steadydancer_task(task_payload=task_payload)

    job = Job(
        id=job_id,
        project_id=project_id,
        experiment_id=experiment.id if experiment is not None else None,
        task_id=task_id,
        job_type="steadydancer_i2v",
        status="PENDING",
        input_dir=to_data_relative(job_paths.input_dir),
        params=task_payload,
        success=None,
        result_video_path=None,
        error_message=None,
    )
    session.add(job)
    await session.commit()

    return job


async def refresh_project_job_status(
    session: AsyncSession,
    job: Job,
) -> Tuple[str, dict[str, Any] | None, str | None]:
    """
    Refresh a project's job status from Celery and persist the changes.

    Returns (state, result, error_message).
    """
    state, result, error_exc = query_celery_task(task_id=job.task_id)

    if error_exc is not None:
        error_msg = str(error_exc)
        job.status = state
        job.success = False
        job.error_message = error_msg
        if job.finished_at is None:
            job.finished_at = utcnow()
        await session.commit()
        return state, None, error_msg

        # Job finished or in-progress without fatal error.
    if result is not None:
        job.status = state

        # Persist success flag if present.
        if "success" in result:
            job.success = bool(result.get("success"))

        # Normalize the result video path and store it as a data-root-relative path.
        video_path_value = result.get("video_path")
        if video_path_value:
            if job.result_video_path:
                # We already normalized once; just mirror the stored path back into the result.
                result["video_path"] = str(from_data_relative(job.result_video_path))
            else:
                from pathlib import Path

                src = Path(str(video_path_value)).expanduser().resolve()
                if src.is_file():
                    job.result_video_path = to_data_relative(src)
                    # For API responses, keep the absolute normalized path.
                    result["video_path"] = str(src)
                else:
                    # File not found; still store the original path for debugging.
                    job.result_video_path = to_data_relative(str(src))
        if job.started_at is None and state == "STARTED":
            job.started_at = utcnow()
        if job.finished_at is None and state in {"SUCCESS", "FAILURE", "REVOKED"}:
            job.finished_at = utcnow()
    else:
        # Task is pending / started / retrying.
        # If Celery backend has expired the result for a previously finished job,
        # keep a stable terminal state in our DB.
        if (
            job.finished_at is not None
            and state == "PENDING"
            and job.status in {"SUCCESS", "FAILURE", "REVOKED"}
        ):
            job.status = "EXPIRED"
        else:
            job.status = state

    await session.commit()

    return state, result, None


async def list_project_jobs(
    session: AsyncSession,
    project_id: UUID,
) -> list[Job]:
    """
    List all jobs under a project ordered by creation time (newest first).
    """
    result = await session.execute(
        select(Job)
        .where(Job.project_id == project_id)
        .order_by(Job.created_at.desc())
    )
    return list(result.scalars().all())


async def list_experiment_jobs(
    session: AsyncSession,
    project_id: UUID,
    experiment_id: UUID,
) -> list[Job]:
    """
    List all jobs under a specific experiment.
    """
    result = await session.execute(
        select(Job)
        .where(
            Job.project_id == project_id,
            Job.experiment_id == experiment_id,
        )
        .order_by(Job.created_at.desc())
    )
    return list(result.scalars().all())


async def cancel_project_job(
    session: AsyncSession,
    job: Job,
    reason: str | None = None,
) -> Job:
    """
    Cancel a running or pending job via Celery and persist cancellation metadata.
    """
    try:
        # Best-effort revoke; Celery will mark the task as revoked if possible.
        celery_client.control.revoke(job.task_id, terminate=True)
    except Exception:
        # Even if Celery control fails (e.g., broker issues), record the intent locally.
        pass

    job.status = "REVOKED"
    job.canceled_at = utcnow()
    if reason:
        job.cancel_reason = reason

    await session.commit()
    await session.refresh(job)
    return job
