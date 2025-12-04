from __future__ import annotations

"""
Utility entry point for running ad-hoc worker-side tasks.

The actual background processing is handled by the Celery worker
defined in `apps.worker.celery_app` and started via:

    uv run --project apps/worker celery -A apps.worker.celery_app worker -l info
"""

from libs.py_core.config import get_models_dir


def main() -> None:
    models_dir = get_models_dir()
    print(f"SteadyDancer worker utilities. MODELS_DIR={models_dir}")


if __name__ == "__main__":
    main()

