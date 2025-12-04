from __future__ import annotations

"""
Download and cache SteadyDancer-14B model weights into MODELS_DIR.

Supports two sources:
- ModelScope  (default): https://modelscope.cn/models/MCG-NJU/MCG-NJU-SteadyDancer-14B
- HuggingFace: https://huggingface.co/MCG-NJU/SteadyDancer-14B

Usage examples (from repo root):

  # Use MODELS_DIR or ./models as root, download from ModelScope
  uv run --project apps/api python scripts/download_models.py

  # Explicitly select HuggingFace as source
  uv run --project apps/api python scripts/download_models.py --source huggingface

  # Override models root
  uv run --project apps/api python scripts/download_models.py --models-dir /models

The script is idempotent: repeated runs reuse underlying caches.
It does NOT commit any downloaded files to Git (models/ is .gitignored).
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Literal


MODELSCOPE_MODEL_ID = "MCG-NJU/MCG-NJU-SteadyDancer-14B"
HUGGINGFACE_MODEL_ID = "MCG-NJU/SteadyDancer-14B"
DEFAULT_MODEL_SUBDIR = "SteadyDancer-14B"


def resolve_models_root(explicit: str | None) -> Path:
    """
    Resolve the MODELS_DIR root, following the repo-wide convention:

    - If --models-dir is provided, use it.
    - Else if MODELS_DIR env var is set, use it.
    - Else default to <repo_root>/models.
    """
    if explicit:
        root = Path(explicit)
    else:
        env_value = os.getenv("MODELS_DIR")
        if env_value:
            root = Path(env_value)
        else:
            repo_root = Path(__file__).resolve().parents[1]
            root = repo_root / "models"

    return root.expanduser().resolve()


def download_from_modelscope(target_dir: Path) -> Path:
    """
    Download SteadyDancer-14B from ModelScope into target_dir.

    Requires:
      pip install "modelscope>=1.9"
    """
    try:
        from modelscope.hub.snapshot_download import snapshot_download  # type: ignore[import]
    except ImportError as exc:  # pragma: no cover - runtime dependency
        print(
            "ERROR: Python package 'modelscope' is not installed.\n"
            "Install it first, for example:\n"
            "  pip install 'modelscope>=1.9'\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    target_dir = target_dir.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"[ModelScope] Downloading {MODELSCOPE_MODEL_ID} into {target_dir} ...")

    # Prefer placing files directly under target_dir where supported.
    try:
        local_path_str = snapshot_download(  # type: ignore[call-arg]
            MODELSCOPE_MODEL_ID,
            cache_dir=str(target_dir),
        )
    except TypeError:
        # Fallback for older versions: use cache_dir only.
        local_path_str = snapshot_download(MODELSCOPE_MODEL_ID, cache_dir=str(target_dir))  # type: ignore[call-arg]

    local_path = Path(local_path_str).expanduser().resolve()
    print(f"[ModelScope] Model cached at: {local_path}")
    print(
        "You can set STEADYDANCER_CKPT_DIR to this path if it differs from "
        f"{target_dir}."
    )
    return local_path


def download_from_huggingface(target_dir: Path) -> Path:
    """
    Download SteadyDancer-14B from HuggingFace into target_dir.

    Requires:
      pip install 'huggingface_hub>=0.23'
    """
    try:
        from huggingface_hub import snapshot_download  # type: ignore[import]
    except ImportError as exc:  # pragma: no cover - runtime dependency
        print(
            "ERROR: Python package 'huggingface_hub' is not installed.\n"
            "Install it first, for example:\n"
            "  pip install 'huggingface_hub>=0.23'\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    target_dir = target_dir.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"[HuggingFace] Downloading {HUGGINGFACE_MODEL_ID} into {target_dir} ...")

    # Use HF's local_dir so files live exactly under target_dir.
    local_path_str = snapshot_download(  # type: ignore[call-arg]
        repo_id=HUGGINGFACE_MODEL_ID,
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
    )
    local_path = Path(local_path_str).expanduser().resolve()

    print(f"[HuggingFace] Model cached at: {local_path}")
    return local_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download SteadyDancer-14B weights into MODELS_DIR."
    )
    parser.add_argument(
        "--source",
        choices=["modelscope", "huggingface"],
        default="modelscope",
        help="Download source (default: modelscope).",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=None,
        help="Override MODELS_DIR root. Defaults to $MODELS_DIR or <repo_root>/models.",
    )
    parser.add_argument(
        "--subdir",
        type=str,
        default=DEFAULT_MODEL_SUBDIR,
        help=f"Subdirectory under models root (default: {DEFAULT_MODEL_SUBDIR}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    models_root = resolve_models_root(args.models_dir)
    target_dir = (models_root / args.subdir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"Resolved MODELS_DIR root: {models_root}")
    print(f"Target model directory: {target_dir}")

    source: Literal["modelscope", "huggingface"] = args.source
    if source == "modelscope":
        local_path = download_from_modelscope(target_dir)
    else:
        local_path = download_from_huggingface(target_dir)

    print("\nDone.")
    print(f"Final model path: {local_path}")
    print(
        "\nFor inference, ensure the environment variable STEADYDANCER_CKPT_DIR "
        f"is set to this path, or leave it empty to let the code default to "
        f\"{models_root / DEFAULT_MODEL_SUBDIR}\"."
    )


if __name__ == "__main__":
    main()

