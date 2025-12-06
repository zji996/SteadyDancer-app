from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ExperimentConfig(BaseModel):
    """
    SteadyDancer-specific configuration stored at the experiment level.

    These fields mirror a subset of SteadyDancerJobCreate without input_dir.
    """

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
    sample_steps: int | None = Field(
        None,
        description="Optional sampling steps; forwarded to upstream sampler when supported.",
    )
    sample_shift: float | None = Field(
        None,
        description="Optional sampling shift factor for flow-matching schedulers.",
    )
    sample_solver: str | None = Field(
        None,
        description="Optional sampling solver, e.g. 'unipc' or 'dpm++'.",
    )
    offload_model: bool | None = Field(
        None,
        description=(
            "Override model offload behavior for the backend. "
            "If unset, each backend uses its own default."
        ),
    )
    cuda_visible_devices: str | None = Field(
        None,
        description="Optional CUDA_VISIBLE_DEVICES override for this experiment.",
    )


class ExperimentCreate(BaseModel):
    name: str = Field(..., description="Human-friendly name of the experiment.")
    description: str | None = Field(
        None,
        description="Optional description of the experiment intent.",
    )
    reference_id: UUID | None = Field(
        None,
        description="Optional reference asset ID associated with this experiment.",
    )
    motion_id: UUID | None = Field(
        None,
        description="Optional motion asset ID associated with this experiment.",
    )
    source_input_dir: str = Field(
        ...,
        description=(
            "Path to a prepared SteadyDancer input directory (pair_dir). "
            "The directory will be copied into the experiment's input/ folder."
        ),
    )
    config: ExperimentConfig | None = Field(
        None,
        description="Optional default SteadyDancer configuration for this experiment.",
    )


class ExperimentOut(BaseModel):
    id: UUID
    project_id: UUID
    reference_id: UUID | None
    motion_id: UUID | None
    name: str
    description: str | None = None
    input_dir: str | None = None
    config: dict[str, Any] | None = None

    class Config:
        from_attributes = True
