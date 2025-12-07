from __future__ import annotations

import os

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from apps.api.main import API_KEY_ENV_NAME, API_KEY_HEADER_NAME, require_api_key
from libs.py_core.projects import get_repo_root, resolve_repo_relative


def _create_test_app() -> FastAPI:
    """
    Create a minimal app that only exercises the API key dependency.
    """
    app = FastAPI(dependencies=[Depends(require_api_key)])

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_require_api_key_disabled(monkeypatch) -> None:
    """
    When STEADYDANCER_API_KEY is not set, the guard is effectively disabled.
    """
    monkeypatch.delenv(API_KEY_ENV_NAME, raising=False)
    app = _create_test_app()
    client = TestClient(app)

    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_require_api_key_enabled(monkeypatch) -> None:
    """
    When STEADYDANCER_API_KEY is set, requests without a matching X-API-Key are rejected.
    """
    monkeypatch.setenv(API_KEY_ENV_NAME, "secret-key")
    app = _create_test_app()
    client = TestClient(app)

    # Missing or wrong key -> 401 with INVALID_API_KEY.
    resp_missing = client.get("/ping")
    assert resp_missing.status_code == 401
    body_missing = resp_missing.json()
    assert isinstance(body_missing, dict)
    assert body_missing.get("detail", {}).get("code") == "INVALID_API_KEY"

    resp_wrong = client.get("/ping", headers={API_KEY_HEADER_NAME: "wrong"})
    assert resp_wrong.status_code == 401
    body_wrong = resp_wrong.json()
    assert body_wrong.get("detail", {}).get("code") == "INVALID_API_KEY"

    # Correct key -> 200.
    resp_ok = client.get("/ping", headers={API_KEY_HEADER_NAME: "secret-key"})
    assert resp_ok.status_code == 200
    assert resp_ok.json() == {"status": "ok"}


def test_resolve_repo_relative_absolute_path() -> None:
    """
    Absolute paths are returned as-is (normalized), regardless of repo root.
    """
    # Use a generic absolute path; we only assert basic properties.
    abs_path = os.path.abspath(os.sep)
    resolved = resolve_repo_relative(abs_path)

    assert resolved.is_absolute()
    # Normalization should not change the logical target directory.
    assert os.path.abspath(str(resolved)) == abs_path


def test_resolve_repo_relative_relative_path() -> None:
    """
    Relative paths are resolved under the monorepo root.
    """
    repo_root = get_repo_root()
    rel = "some/subdir/file.txt"

    resolved = resolve_repo_relative(rel)

    assert resolved.is_absolute()
    # Resolved path should live under the repo root.
    assert str(resolved).startswith(str(repo_root))
    # And it should end with the relative suffix (path-separator aware).
    assert str(resolved).endswith(os.path.join("some", "subdir", "file.txt"))

