from __future__ import annotations

from celery import Celery

from apps.worker.config import get_celery_config
from libs.py_core.config import get_models_dir


celery_config = get_celery_config()

celery_app = Celery(
    "steadydancer_worker",
    broker=celery_config.broker_url,
    backend=celery_config.result_backend,
)

celery_app.conf.update(
    task_default_queue=celery_config.default_queue,
    worker_concurrency=celery_config.concurrency,
)


@celery_app.task(name="worker.health_check")
def health_check() -> dict[str, str]:
    """
    Simple Celery task to verify worker & broker connectivity.
    """
    models_dir = get_models_dir()
    return {
        "status": "ok",
        "models_dir": str(models_dir),
    }

