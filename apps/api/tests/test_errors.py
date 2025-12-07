from __future__ import annotations

from fastapi import HTTPException

from apps.api.errors import api_error, invalid_api_key_error


def test_api_error_shape() -> None:
    exc = api_error(
        status_code=400,
        code="TEST_CODE",
        message="Something went wrong.",
        extra={"foo": "bar"},
    )

    assert isinstance(exc, HTTPException)
    assert exc.status_code == 400

    detail = exc.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "TEST_CODE"
    assert detail["message"] == "Something went wrong."
    assert detail["extra"] == {"foo": "bar"}


def test_invalid_api_key_error() -> None:
    exc = invalid_api_key_error()

    assert isinstance(exc, HTTPException)
    assert exc.status_code == 401

    detail = exc.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "INVALID_API_KEY"
    assert "message" in detail

