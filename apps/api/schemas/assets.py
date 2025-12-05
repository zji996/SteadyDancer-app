from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ReferenceAssetCreate(BaseModel):
    name: str = Field(..., description="Human-friendly name of the reference asset.")
    source_image_path: str = Field(
        ...,
        description=(
            "Path to the source reference image (absolute or repo-root-relative). "
            "The file will be copied into the project's refs directory."
        ),
    )
    meta: dict[str, Any] | None = Field(
        None,
        description="Optional metadata, such as prompt, character name, tags, etc.",
    )


class ReferenceAssetOut(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    image_path: str
    meta: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class MotionAssetCreate(BaseModel):
    name: str = Field(..., description="Human-friendly name of the motion asset.")
    source_video_path: str = Field(
        ...,
        description=(
            "Path to the source driving video (absolute or repo-root-relative). "
            "The file will be copied into the project's motions directory."
        ),
    )
    meta: dict[str, Any] | None = Field(
        None,
        description="Optional metadata, such as style tags, duration, etc.",
    )


class MotionAssetOut(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    video_path: str
    meta: dict[str, Any] | None = None

    class Config:
        from_attributes = True

