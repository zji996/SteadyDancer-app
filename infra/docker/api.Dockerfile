FROM python:3.13-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY apps/api/pyproject.toml /app/pyproject.toml
RUN pip install --upgrade pip && pip install uv
RUN uv sync --group default

COPY . /app

ENV MODELS_DIR=/models
ENV STEADYDANCER_DATA_DIR=/data/steadydancer

CMD ["uv", "run", "--project", "apps/api", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
