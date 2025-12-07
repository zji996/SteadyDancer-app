from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


def api_error(
    status_code: int,
    code: str,
    message: str,
    *,
    extra: dict[str, Any] | None = None,
) -> HTTPException:
    """
    Helper to construct a consistent HTTPException payload.

    Response shape:
    {
      "detail": {
        "code": "<ERROR_CODE>",
        "message": "<human readable message>",
        "extra": { ... }  # optional
      }
    }
    """
    detail: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if extra:
        detail["extra"] = extra
    return HTTPException(status_code=status_code, detail=detail)


def invalid_api_key_error() -> HTTPException:
    return api_error(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="INVALID_API_KEY",
        message="Invalid or missing API key.",
    )

