FROM python:3.13-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY apps/worker/pyproject.toml /app/pyproject.toml
RUN pip install --upgrade pip && pip install uv
RUN uv sync --group default

COPY . /app

ENV MODELS_DIR=/models

CMD ["uv", "run", "--project", "apps/worker", "celery", "-A", "apps.worker.celery_app", "worker", "-l", "info"]
