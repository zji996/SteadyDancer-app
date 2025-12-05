from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from apps.api.db import engine, init_db
from apps.api.routes.projects import router as projects_router
from apps.api.routes.steadydancer import router as steadydancer_router
from libs.py_core.config import get_models_dir


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan hook.

    Place startup / shutdown logic here (DB connections, model warmup, etc.).
    """
    # Initialize database schema (development convenience).
    await init_db()
    try:
        yield
    finally:
        # Gracefully dispose DB connections.
        await engine.dispose()


app = FastAPI(
    title="SteadyDancer API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(projects_router)
app.include_router(steadydancer_router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """
    Liveness probe endpoint.
    """
    return {"status": "ok"}


@app.get("/models/info", tags=["models"])
async def models_info() -> dict[str, str]:
    """
    Return basic information about the models directory.
    """
    models_dir = get_models_dir()
    return {
        "models_dir": str(models_dir),
        "env_MODELS_DIR": os.getenv("MODELS_DIR", ""),
    }
