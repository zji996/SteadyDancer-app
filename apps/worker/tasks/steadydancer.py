from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.worker.celery_app import celery_app
from libs.py_core.models.steadydancer_cli import (
    SteadyDancerI2VRequest,
    run_i2v_generation,
)
from libs.py_core.models.steadydancer_preprocess import (
    SteadyDancerPreprocessRequest,
    run_preprocess_pipeline,
)
from libs.py_core.projects import ensure_experiment_dirs, ensure_job_dirs
import json


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
    - sample_steps?: Optional[int]
    - sample_shift?: Optional[float]
    - sample_solver?: Optional[str]
    - offload_model?: Optional[bool]
    - cuda_visible_devices: Optional[str]
    - project_id?: str
    - job_id?: str
    """
    input_dir = Path(payload["input_dir"])

    project_id = payload.get("project_id")
    job_id = payload.get("job_id")
    job_paths = None
    output_dir: Path | None = None
    if project_id is not None and job_id is not None:
        try:
            job_paths = ensure_job_dirs(project_id=project_id, job_id=job_id)
            output_dir = job_paths.output_dir
        except Exception:
            # Best-effort; failures here must not break inference.
            job_paths = None
            output_dir = None

    req = SteadyDancerI2VRequest(
        input_dir=input_dir,
        output_dir=output_dir,
        prompt_override=payload.get("prompt_override"),
        size=payload.get("size", "1024*576"),
        frame_num=int(payload.get("frame_num", 81)),
        sample_guide_scale=float(payload.get("sample_guide_scale", 5.0)),
        condition_guide_scale=float(payload.get("condition_guide_scale", 1.0)),
        end_cond_cfg=float(payload.get("end_cond_cfg", 0.4)),
        base_seed=int(payload.get("base_seed", -1)),
        sample_steps=(
            int(payload["sample_steps"]) if "sample_steps" in payload and payload["sample_steps"] is not None else None
        ),
        sample_shift=(
            float(payload["sample_shift"])
            if "sample_shift" in payload and payload["sample_shift"] is not None
            else None
        ),
        sample_solver=payload.get("sample_solver"),
        offload_model=payload.get("offload_model"),
        cuda_visible_devices=payload.get("cuda_visible_devices"),
    )

    result = run_i2v_generation(req)

    # Persist result and payload snapshot under the job's logs directory, if available.
    if job_paths is not None:
        try:
            logs_dir = job_paths.logs_dir
            logs_dir.mkdir(parents=True, exist_ok=True)

            log_path = logs_dir / "i2v_result.json"
            payload_snapshot = dict(payload)
            # Avoid accidentally persisting very large values in the payload snapshot.
            payload_snapshot.pop("input_dir", None)

            log_content = {
                "payload": payload_snapshot,
                "result": result.to_dict(),
            }
            log_path.write_text(
                json.dumps(log_content, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            # Logging is best-effort and must never break task execution.
            pass

    return result.to_dict()


@celery_app.task(name="steadydancer.preprocess.experiment")
def preprocess_experiment_task(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Celery task wrapper for SteadyDancer preprocess pipeline.

    Expected payload:
    - project_id: str (UUID)
    - experiment_id: str (UUID)
    - reference_image_path: str
    - motion_video_path: str
    - prompt: Optional[str]
    """
    project_id = payload["project_id"]
    experiment_id = payload["experiment_id"]

    ref_image_path = Path(payload["reference_image_path"])
    motion_video_path = Path(payload["motion_video_path"])
    prompt = payload.get("prompt")

    # Ensure experiment dirs exist and compute the canonical input_dir.
    exp_paths = ensure_experiment_dirs(
        project_id=project_id,
        experiment_id=experiment_id,
    )

    req = SteadyDancerPreprocessRequest(
        ref_image=ref_image_path,
        driving_video=motion_video_path,
        output_dir=exp_paths.input_dir,
        prompt=prompt,
    )

    result = run_preprocess_pipeline(req)
    return result.to_dict()
