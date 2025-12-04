from __future__ import annotations

import os

from celery import Celery


def _get_broker_and_backend() -> tuple[str, str]:
    broker = (
        os.getenv("CELERY_BROKER_URL")
        or os.getenv("JOB_QUEUE_URL")
        or "redis://localhost:6379/1"
    )
    backend = os.getenv("CELERY_RESULT_BACKEND") or broker
    return broker, backend


broker_url, result_backend = _get_broker_and_backend()

celery_client = Celery(
    "steadydancer_api_client",
    broker=broker_url,
    backend=result_backend,
)

