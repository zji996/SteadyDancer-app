from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, NoCredentialsError


@dataclass
class S3Settings:
    """
    Thin wrapper around S3-related environment variables.

    This module intentionally keeps semantics minimal and generic so it can be
    reused by both API and worker code without pulling in application-specific
    concepts.
    """

    endpoint_url: str
    access_key: str
    secret_key: str
    bucket_name: str
    region_name: Optional[str] = None
    use_ssl: bool = True
    addressing_style: str = "path"  # or "virtual"


def _read_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def get_s3_settings() -> Optional[S3Settings]:
    """
    Read S3 settings from environment variables.

    Required:
    - S3_ENDPOINT
    - S3_ACCESS_KEY
    - S3_SECRET_KEY
    - S3_BUCKET_NAME

    Optional:
    - S3_REGION
    - S3_USE_SSL (default: true)
    - S3_ADDRESSING_STYLE ("path" or "virtual", default: "path")
    """
    endpoint = os.getenv("S3_ENDPOINT")
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_KEY")
    bucket = os.getenv("S3_BUCKET_NAME")

    if not endpoint or not access_key or not secret_key or not bucket:
        return None

    region = os.getenv("S3_REGION") or None
    use_ssl = _read_bool_env("S3_USE_SSL", True)
    addressing_style = os.getenv("S3_ADDRESSING_STYLE") or "path"

    return S3Settings(
        endpoint_url=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        bucket_name=bucket,
        region_name=region,
        use_ssl=use_ssl,
        addressing_style=addressing_style,
    )


def is_s3_enabled() -> bool:
    """
    Return True when all required S3 environment variables are present.
    """
    return get_s3_settings() is not None


def _create_s3_client(settings: S3Settings):
    session = boto3.session.Session()
    config = BotoConfig(
        s3={"addressing_style": settings.addressing_style},
        retries={"max_attempts": 3, "mode": "standard"},
    )
    return session.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        aws_access_key_id=settings.access_key,
        aws_secret_access_key=settings.secret_key,
        region_name=settings.region_name,
        use_ssl=settings.use_ssl,
        config=config,
    )


def upload_file_to_s3(local_path: Path | str, key: str) -> str:
    """
    Upload a local file into the configured S3 bucket under the given key.

    Returns an s3://bucket/key URL on success.
    Raises RuntimeError if S3 is not configured or upload fails.
    """
    settings = get_s3_settings()
    if settings is None:
        raise RuntimeError("S3 is not configured (missing env vars).")

    path = Path(local_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    client = _create_s3_client(settings)
    try:
        client.upload_file(str(path), settings.bucket_name, key)
    except (BotoCoreError, NoCredentialsError) as exc:  # pragma: no cover - network errors
        raise RuntimeError(f"Failed to upload to S3: {exc}") from exc

    return f"s3://{settings.bucket_name}/{key}"


def parse_s3_url(url: str) -> Tuple[str, str]:
    """
    Parse a simple s3://bucket/key URL into (bucket, key).
    """
    if not url.startswith("s3://"):
        raise ValueError(f"Not an s3 URL: {url}")

    without_scheme = url[len("s3://") :]
    parts = without_scheme.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid s3 URL: {url}")
    bucket, key = parts
    return bucket, key


def generate_presigned_get_url(url: str, expires_in: int = 3600) -> str:
    """
    Generate a presigned GET URL for a given s3://bucket/key URL.
    """
    settings = get_s3_settings()
    if settings is None:
        raise RuntimeError("S3 is not configured (missing env vars).")

    bucket, key = parse_s3_url(url)
    client = _create_s3_client(settings)
    try:
        return client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    except BotoCoreError as exc:  # pragma: no cover - network errors
        raise RuntimeError(f"Failed to generate presigned URL: {exc}") from exc

