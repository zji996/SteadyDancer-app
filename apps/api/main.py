from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Header, status

from apps.api.db import engine, init_db
from apps.api.errors import invalid_api_key_error
from apps.api.routes.projects import router as projects_router
from apps.api.routes.steadydancer import router as steadydancer_router
from libs.py_core.config import get_models_dir


API_KEY_HEADER_NAME = "X-API-Key"
API_KEY_ENV_NAME = "STEADYDANCER_API_KEY"


def require_api_key(api_key: str | None = Header(None, alias=API_KEY_HEADER_NAME)) -> None:
    """
    Simple API key guard based on the X-API-Key header.

    Behavior:
    - If STEADYDANCER_API_KEY is unset or empty, authentication is effectively disabled;
    - Otherwise, all protected routes must provide a matching X-API-Key header,
      or a 401 INVALID_API_KEY error is returned.
    """
    expected = os.getenv(API_KEY_ENV_NAME)
    if not expected:
        # Auth disabled when no key is configured.
        return

    if api_key != expected:
        # Always respond with a generic invalid key error.
        raise invalid_api_key_error()


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

# Protect business APIs with API key authentication.
app.include_router(
    projects_router,
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    steadydancer_router,
    dependencies=[Depends(require_api_key)],
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
    auth_required = bool(os.getenv(API_KEY_ENV_NAME))
    return {
        "models_dir": str(models_dir),
        "env_MODELS_DIR": os.getenv("MODELS_DIR", ""),
        "auth_required": auth_required,
        "auth_header": API_KEY_HEADER_NAME if auth_required else "",
    }
