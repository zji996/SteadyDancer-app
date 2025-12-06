from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


def _bool_env(name: str, default: bool) -> bool:
    """
    Parse a boolean-ish environment variable.

    Accepts: 1/true/yes/y/on (case-insensitive) as True, 0/false/no/n/off as False.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _make_async_url(raw_url: str | None) -> str:
    """
    Normalize DATABASE_URL into an async SQLAlchemy URL.

    - If not set, default to local Postgres.
    - If using 'postgresql://' without an async driver, upgrade to 'postgresql+asyncpg://'.
    """
    if not raw_url:
        raw_url = "postgresql://postgres:postgres@localhost:5432/steadydancer"

    if raw_url.startswith("postgresql://") and "+asyncpg" not in raw_url:
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return raw_url


class Base(DeclarativeBase):
    pass


DATABASE_URL = _make_async_url(os.getenv("DATABASE_URL"))

engine = create_async_engine(DATABASE_URL, future=True, echo=False)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Project(Base):
    __tablename__ = "projects"

    __table_args__ = (
        Index("ix_projects_created_at", "created_at"),
        Index("ix_projects_updated_at", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    references: Mapped[list["ReferenceAsset"]] = relationship(
        "ReferenceAsset",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    motions: Mapped[list["MotionAsset"]] = relationship(
        "MotionAsset",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    experiments: Mapped[list["Experiment"]] = relationship(
        "Experiment",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ReferenceAsset(Base):
    __tablename__ = "reference_assets"

    __table_args__ = (
        Index(
            "ix_reference_assets_project_created_at",
            "project_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    project: Mapped[Project] = relationship(
        "Project",
        back_populates="references",
    )


class MotionAsset(Base):
    __tablename__ = "motion_assets"

    __table_args__ = (
        Index(
            "ix_motion_assets_project_created_at",
            "project_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    video_path: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    project: Mapped[Project] = relationship(
        "Project",
        back_populates="motions",
    )


class Experiment(Base):
    __tablename__ = "experiments"

    __table_args__ = (
        Index(
            "ix_experiments_project_created_at",
            "project_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reference_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    motion_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("motion_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    project: Mapped[Project] = relationship(
        "Project",
        back_populates="experiments",
    )
    reference: Mapped[ReferenceAsset | None] = relationship("ReferenceAsset")
    motion: Mapped[MotionAsset | None] = relationship("MotionAsset")
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="experiment",
    )


class Job(Base):
    __tablename__ = "generation_jobs"

    __table_args__ = (
        Index(
            "ix_generation_jobs_project_created_at",
            "project_id",
            "created_at",
        ),
        Index(
            "ix_generation_jobs_project_experiment_created_at",
            "project_id",
            "experiment_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    experiment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "PENDING",
            "RECEIVED",
            "STARTED",
            "RETRY",
            "REVOKED",
            "SUCCESS",
            "FAILURE",
            "EXPIRED",
            "UNKNOWN",
            name="job_status_enum",
        ),
        nullable=False,
        default="PENDING",
    )
    input_dir: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    result_video_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancel_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    project: Mapped[Project] = relationship(
        "Project",
        back_populates="jobs",
    )
    experiment: Mapped[Experiment | None] = relationship(
        "Experiment",
        back_populates="jobs",
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency that yields an AsyncSession.
    """
    async with AsyncSessionFactory() as session:
        yield session


async def init_db() -> None:
    """
    Initialize database schema for local/dev environments.

    Production deployments are expected to manage migrations explicitly,
    but create_all() is convenient in development.

    Controlled by STEADYDANCER_DB_AUTO_CREATE:
    - If unset or truthy (1/true/yes/...), tables will be created if missing;
    - If set to a falsy value, init_db() becomes a no-op.
    """
    if not _bool_env("STEADYDANCER_DB_AUTO_CREATE", default=True):
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
