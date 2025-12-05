from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import MotionAsset, Project, ReferenceAsset
from apps.api.schemas.assets import MotionAssetCreate, ReferenceAssetCreate
from libs.py_core.projects import ensure_motion_dirs, ensure_reference_dirs


class ProjectNotFoundError(Exception):
    """
    Raised when a project cannot be found for a given ID.
    """


class SourceFileNotFoundError(Exception):
    """
    Raised when the provided source file path does not exist.
    """


def _resolve_source_path(src: str) -> Path:
    path = Path(src)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


async def create_reference_asset(
    session: AsyncSession,
    project_id: UUID,
    payload: ReferenceAssetCreate,
) -> ReferenceAsset:
    project = await session.get(Project, project_id)
    if project is None:
        raise ProjectNotFoundError(f"Project not found: {project_id}")

    ref_id = uuid4()
    paths = ensure_reference_dirs(project_id=project_id, ref_id=ref_id)

    source = _resolve_source_path(payload.source_image_path)
    if not source.is_file():
        raise SourceFileNotFoundError(
            f"source_image_path not found or not a file: {source}"
        )

    dest = paths.source_dir / source.name
    try:
        shutil.copy2(source, dest)
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Failed to copy reference image: {exc}") from exc

    asset = ReferenceAsset(
        id=ref_id,
        project_id=project_id,
        name=payload.name,
        image_path=str(dest),
        meta=payload.meta,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return asset


async def create_motion_asset(
    session: AsyncSession,
    project_id: UUID,
    payload: MotionAssetCreate,
) -> MotionAsset:
    project = await session.get(Project, project_id)
    if project is None:
        raise ProjectNotFoundError(f"Project not found: {project_id}")

    motion_id = uuid4()
    paths = ensure_motion_dirs(project_id=project_id, motion_id=motion_id)

    source = _resolve_source_path(payload.source_video_path)
    if not source.is_file():
        raise SourceFileNotFoundError(
            f"source_video_path not found or not a file: {source}"
        )

    dest = paths.source_dir / source.name
    try:
        shutil.copy2(source, dest)
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Failed to copy motion video: {exc}") from exc

    asset = MotionAsset(
        id=motion_id,
        project_id=project_id,
        name=payload.name,
        video_path=str(dest),
        meta=payload.meta,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return asset


async def get_reference_asset(
    session: AsyncSession,
    project_id: UUID,
    asset_id: UUID,
) -> ReferenceAsset | None:
    asset = await session.get(ReferenceAsset, asset_id)
    if asset is None or asset.project_id != project_id:
        return None
    return asset


async def get_motion_asset(
    session: AsyncSession,
    project_id: UUID,
    asset_id: UUID,
) -> MotionAsset | None:
    asset = await session.get(MotionAsset, asset_id)
    if asset is None or asset.project_id != project_id:
        return None
    return asset


async def list_reference_assets(
    session: AsyncSession,
    project_id: UUID,
) -> list[ReferenceAsset]:
    """
    List all reference assets under a project.
    """
    result = await session.execute(
        select(ReferenceAsset)
        .where(ReferenceAsset.project_id == project_id)
        .order_by(ReferenceAsset.created_at.desc())
    )
    return list(result.scalars().all())


async def list_motion_assets(
    session: AsyncSession,
    project_id: UUID,
) -> list[MotionAsset]:
    """
    List all motion assets under a project.
    """
    result = await session.execute(
        select(MotionAsset)
        .where(MotionAsset.project_id == project_id)
        .order_by(MotionAsset.created_at.desc())
    )
    return list(result.scalars().all())
