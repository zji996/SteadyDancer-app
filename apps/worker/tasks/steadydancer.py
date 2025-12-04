from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.worker.celery_app import celery_app
from libs.py_core.models.steadydancer_cli import (
    SteadyDancerI2VRequest,
    run_i2v_generation,
)


@celery_app.task(name="steadydancer.generate.i2v")
def generate_i2v_task(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Celery task wrapper for SteadyDancer I2V generation.

    Expected payload structure (all paths absolute or repo-root-relative):
    - input_dir: str  # directory containing ref_image.png, positive/, negative/, etc.
    - prompt_override: Optional[str]
    - size: str
    - frame_num: int
    - sample_guide_scale: float
    - condition_guide_scale: float
    - end_cond_cfg: float
    - base_seed: int
    - cuda_visible_devices: Optional[str]
    """
    input_dir = Path(payload["input_dir"])

    req = SteadyDancerI2VRequest(
        input_dir=input_dir,
        prompt_override=payload.get("prompt_override"),
        size=payload.get("size", "1024*576"),
        frame_num=int(payload.get("frame_num", 81)),
        sample_guide_scale=float(payload.get("sample_guide_scale", 5.0)),
        condition_guide_scale=float(payload.get("condition_guide_scale", 1.0)),
        end_cond_cfg=float(payload.get("end_cond_cfg", 0.4)),
        base_seed=int(payload.get("base_seed", -1)),
        cuda_visible_devices=payload.get("cuda_visible_devices"),
    )

    result = run_i2v_generation(req)
    return result.to_dict()

