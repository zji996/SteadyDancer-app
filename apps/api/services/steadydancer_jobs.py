from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import Experiment, Job, Project, utcnow
from apps.api.schemas.steadydancer import SteadyDancerJobCreate
from libs.py_core.celery_client import celery_client
from libs.py_core.projects import ensure_job_dirs


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
    return {
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
        source_input_dir = Path(experiment.input_dir)
    else:
        source_input_dir = Path(payload.input_dir)
        if not source_input_dir.is_absolute():
            source_input_dir = Path.cwd() / source_input_dir

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
    task_id = enqueue_steadydancer_task(task_payload=task_payload)

    job = Job(
        id=job_id,
        project_id=project_id,
        experiment_id=experiment.id if experiment is not None else None,
        task_id=task_id,
        job_type="steadydancer_i2v",
        status="PENDING",
        input_dir=str(job_paths.input_dir),
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

        # Normalize / move result video into the job's output/ directory.
        video_path_value = result.get("video_path")
        if video_path_value:
            if job.result_video_path:
                # We already normalized once; just mirror the stored path back into the result.
                result["video_path"] = job.result_video_path
            else:
                try:
                    from pathlib import Path
                    import shutil

                    src = Path(str(video_path_value)).expanduser().resolve()
                    if src.is_file():
                        from libs.py_core.projects import ensure_job_dirs

                        job_paths = ensure_job_dirs(
                            project_id=job.project_id,
                            job_id=job.id,
                        )
                        dest = job_paths.output_dir / src.name
                        if src != dest:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(src), str(dest))
                        # Use the destination path if move succeeded, otherwise fall back.
                        final_path = str(dest if dest.is_file() else src)
                        job.result_video_path = final_path
                        result["video_path"] = final_path
                    else:
                        # File not found; still store the original path for debugging.
                        job.result_video_path = str(src)
                except Exception:
                    # Best-effort normalization; on failure we keep Celery's raw path.
                    job.result_video_path = str(video_path_value)
        if job.finished_at is None and state in {"SUCCESS", "FAILURE"}:
            job.finished_at = utcnow()
    else:
        # Task is pending / started / retrying.
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
