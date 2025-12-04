from __future__ import annotations

"""
Utility script to download / prepare model weights into MODELS_DIR.

This script is intentionally minimal and does not embed any
provider-specific credentials or large binaries. Extend it as needed.
"""

import os
from pathlib import Path

from libs.py_core.config import get_models_dir


def main() -> None:
    models_dir = get_models_dir()
    models_dir.mkdir(parents=True, exist_ok=True)

    print(f"MODELS_DIR resolved to: {models_dir}")
    print("This is a placeholder script. Add your own")
    print("download logic here (e.g. from object storage).")
    print("Do not commit downloaded weights to Git.")


if __name__ == "__main__":
    main()

