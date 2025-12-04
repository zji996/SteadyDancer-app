from __future__ import annotations

import os
from pathlib import Path


def get_models_dir() -> Path:
    """
    Compute the models root directory from MODELS_DIR.

    - If MODELS_DIR is set, use it as-is.
    - Otherwise, default to <repo_root>/models based on this file's location.
    """
    env_value = os.getenv("MODELS_DIR")
    if env_value:
        return Path(env_value).expanduser().resolve()

    # libs/py_core/config.py -> libs/py_core -> libs -> repo_root
    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / "models").resolve()

