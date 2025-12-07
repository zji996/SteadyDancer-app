from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import Experiment, MotionAsset, Project, ReferenceAsset
from apps.api.schemas.experiments import (
    ExperimentConfig,
    ExperimentCreate,
    ExperimentPreprocessCreate,
)
from libs.py_core.celery_client import celery_client
from libs.py_core.projects import (
    ensure_experiment_dirs,
    from_data_relative,
    resolve_repo_relative,
    to_data_relative,
)


class ProjectNotFoundError(Exception):
    """
    Raised when a project cannot be found for a given ID.
    """


class AssetNotFoundError(Exception):
    """
    Raised when a referenced asset cannot be found.
    """


class SourceInputDirNotFoundError(Exception):
    """
    Raised when the provided source_input_dir does not exist or is not a directory.
    """


def _resolve_source_dir(src: str) -> Path:
    return resolve_repo_relative(src)


async def create_experiment(
    session: AsyncSession,
    project_id: UUID,
    payload: ExperimentCreate,
) -> Experiment:
    """
    Create an experiment under a project.

    The experiment links optional reference / motion assets, and stores a canonical
    SteadyDancer input directory by copying source_input_dir into
    <data_root>/projects/{project_id}/experiments/{experiment_id}/input/.
    """
    project = await session.get(Project, project_id)
    if project is None:
        raise ProjectNotFoundError(f"Project not found: {project_id}")

    reference_id: UUID | None = payload.reference_id
    motion_id: UUID | None = payload.motion_id

    if reference_id is not None:
        ref = await session.get(ReferenceAsset, reference_id)
        if ref is None or ref.project_id != project_id:
            raise AssetNotFoundError(f"Reference asset not found: {reference_id}")

    if motion_id is not None:
        motion = await session.get(MotionAsset, motion_id)
        if motion is None or motion.project_id != project_id:
            raise AssetNotFoundError(f"Motion asset not found: {motion_id}")

    experiment_id = uuid4()
    paths = ensure_experiment_dirs(project_id=project_id, experiment_id=experiment_id)

    source_input_dir = _resolve_source_dir(payload.source_input_dir)
    if not source_input_dir.is_dir():
        raise SourceInputDirNotFoundError(
            f"source_input_dir not found or not a directory: {source_input_dir}"
        )

    try:
        shutil.copytree(
            source_input_dir,
            paths.input_dir,
            dirs_exist_ok=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            f"Failed to prepare experiment input directory: {exc}"
        ) from exc

    config_dict: dict[str, Any] | None = None
    if payload.config is not None:
        # Store as plain dict for easier querying.
        config_dict = payload.config.model_dump()

    experiment = Experiment(
        id=experiment_id,
        project_id=project_id,
        reference_id=reference_id,
        motion_id=motion_id,
        name=payload.name,
        description=payload.description,
        input_dir=to_data_relative(paths.input_dir),
        config=config_dict,
    )
    session.add(experiment)
    await session.commit()
    await session.refresh(experiment)

    # Optionally persist the config json to disk for debugging / offline use.
    if config_dict is not None:
        try:
            paths.config_path.write_text(
                json.dumps(config_dict, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            # Best-effort; failure here does not affect DB state.
            pass

    return experiment


async def get_experiment(
    session: AsyncSession,
    project_id: UUID,
    experiment_id: UUID,
) -> Experiment | None:
    exp = await session.get(Experiment, experiment_id)
    if exp is None or exp.project_id != project_id:
        return None
    return exp


async def list_experiments(
    session: AsyncSession,
    project_id: UUID,
) -> list[Experiment]:
    """
    List all experiments under a project.
    """
    result = await session.execute(
        select(Experiment)
        .where(Experiment.project_id == project_id)
        .order_by(Experiment.created_at.desc())
    )
    return list(result.scalars().all())


async def create_experiment_with_preprocess(
    session: AsyncSession,
    project_id: UUID,
    payload: ExperimentPreprocessCreate,
) -> tuple[Experiment, str]:
    """
    Create an experiment from existing ReferenceAsset + MotionAsset and
    enqueue a Celery preprocess task that prepares the canonical input_dir.
    """
    project = await session.get(Project, project_id)
    if project is None:
        raise ProjectNotFoundError(f"Project not found: {project_id}")

    reference_id: UUID = payload.reference_id
    motion_id: UUID = payload.motion_id

    ref = await session.get(ReferenceAsset, reference_id)
    if ref is None or ref.project_id != project_id:
        raise AssetNotFoundError(f"Reference asset not found: {reference_id}")

    motion = await session.get(MotionAsset, motion_id)
    if motion is None or motion.project_id != project_id:
        raise AssetNotFoundError(f"Motion asset not found: {motion_id}")

    experiment_id = uuid4()
    paths = ensure_experiment_dirs(project_id=project_id, experiment_id=experiment_id)

    config_dict: dict[str, Any] | None = None
    prompt_text: str | None = None
    if payload.config is not None:
        config_dict = payload.config.model_dump()
        prompt_text = payload.config.prompt_override

    preprocess_payload: dict[str, Any] = {
        "project_id": str(project_id),
        "experiment_id": str(experiment_id),
        "reference_image_path": str(from_data_relative(ref.image_path)),
        "motion_video_path": str(from_data_relative(motion.video_path)),
        "prompt": prompt_text,
    }
    task = celery_client.send_task(
        "steadydancer.preprocess.experiment",
        args=[preprocess_payload],
    )

    experiment = Experiment(
        id=experiment_id,
        project_id=project_id,
        reference_id=reference_id,
        motion_id=motion_id,
        name=payload.name,
        description=payload.description,
        input_dir=to_data_relative(paths.input_dir),
        config=config_dict,
        preprocess_task_id=task.id,
    )
    session.add(experiment)
    await session.commit()
    await session.refresh(experiment)

    # Optionally persist the config json to disk for debugging / offline use.
    if config_dict is not None:
        try:
            paths.config_path.write_text(
                json.dumps(config_dict, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            # Best-effort; failure here does not affect DB state.
            pass

    return experiment, task.id
