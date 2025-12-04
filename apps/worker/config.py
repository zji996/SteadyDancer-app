from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class CeleryConfig:
    broker_url: str
    result_backend: str | None
    default_queue: str
    concurrency: int


def get_celery_config() -> CeleryConfig:
    """
    Load Celery configuration from environment variables.

    Priority:
    - CELERY_BROKER_URL (recommended)
    - JOB_QUEUE_URL (fallback)
    - redis://localhost:6379/1 (dev default)
    """
    broker_url = (
        os.getenv("CELERY_BROKER_URL")
        or os.getenv("JOB_QUEUE_URL")
        or "redis://localhost:6379/1"
    )
    result_backend = os.getenv("CELERY_RESULT_BACKEND") or broker_url
    default_queue = os.getenv("CELERY_DEFAULT_QUEUE", "steadydancer")
    concurrency = int(os.getenv("WORKER_CONCURRENCY", "4"))

    return CeleryConfig(
        broker_url=broker_url,
        result_backend=result_backend,
        default_queue=default_queue,
        concurrency=concurrency,
    )

