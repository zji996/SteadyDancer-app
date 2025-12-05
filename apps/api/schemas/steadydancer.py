from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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

