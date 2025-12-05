from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import Project


async def create_project(
    session: AsyncSession,
    name: str,
    description: str | None,
) -> Project:
    """
    Create and persist a new project entity.
    """
    project = Project(name=name, description=description)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def get_project(session: AsyncSession, project_id: UUID) -> Project | None:
    """
    Retrieve a project by ID, or None if not found.
    """
    return await session.get(Project, project_id)


async def list_projects(session: AsyncSession) -> list[Project]:
    """
    List all projects ordered by creation time (newest first).
    """
    result = await session.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    return list(result.scalars().all())
