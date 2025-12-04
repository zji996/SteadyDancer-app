from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from libs.py_core.config import get_models_dir


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan hook.

    Place startup / shutdown logic here (DB connections, model warmup, etc.).
    """
    # TODO: initialize DB connections, model clients, etc.
    yield
    # TODO: gracefully shutdown connections


app = FastAPI(
    title="SteadyDancer API",
    version="0.1.0",
    lifespan=lifespan,
)


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

