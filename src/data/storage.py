"""MinIO storage helpers for processed dataframes.

Replaces the old `data/processed/` local sink. Reads connection settings from
environment variables (loaded via python-dotenv if a `.env` is present):

    MINIO_ENDPOINT     (default: localhost:${MINIO_PORT:-9000})
    MINIO_ACCESS_KEY
    MINIO_SECRET_KEY
    MINIO_SECURE       (default: false)
    BUCKET_NAME        (default: ds-salary)
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from minio import Minio
from minio.commonconfig import CopySource, Tags
from minio.error import S3Error


def _bool_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_minio_client() -> Minio:
    """Build a MinIO client from env vars."""
    load_dotenv()
    port = os.getenv("MINIO_PORT", "9000")
    endpoint = os.getenv("MINIO_ENDPOINT", f"localhost:{port}")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    if not access_key or not secret_key:
        raise RuntimeError("MINIO_ACCESS_KEY / MINIO_SECRET_KEY must be set")
    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=_bool_env("MINIO_SECURE", False),
    )


def get_bucket_name() -> str:
    load_dotenv()
    return os.getenv("BUCKET_NAME", "ds-salary")


def ensure_bucket(client: Minio, bucket: str) -> None:
    """Create bucket if it does not exist."""
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload_dataframe(
    df: pd.DataFrame,
    object_key: str,
    bucket: str | None = None,
    fmt: str = "csv",
    client: Minio | None = None,
) -> str:
    """Serialize `df` and upload to `bucket/object_key`.

    fmt: "csv" or "parquet". Returns the full s3-style URI.
    """
    client = client or get_minio_client()
    bucket = bucket or get_bucket_name()
    ensure_bucket(client, bucket)

    buf = io.BytesIO()
    if fmt == "csv":
        df.to_csv(buf, index=False)
        content_type = "text/csv"
    elif fmt == "parquet":
        df.to_parquet(buf, index=False)
        content_type = "application/octet-stream"
    else:
        raise ValueError(f"Unsupported fmt: {fmt}")

    size = buf.tell()
    buf.seek(0)
    client.put_object(bucket, object_key, buf, length=size, content_type=content_type)
    uri = f"s3://{bucket}/{object_key}"
    print(f"Uploaded {len(df)} rows ({size:,} bytes) -> {uri}")
    return uri


def download_dataframe(
    object_key: str,
    bucket: str | None = None,
    fmt: str = "csv",
    client: Minio | None = None,
) -> pd.DataFrame:
    """Download an object from MinIO and parse as a DataFrame."""
    client = client or get_minio_client()
    bucket = bucket or get_bucket_name()
    response = client.get_object(bucket, object_key)
    try:
        data = response.read()
    finally:
        response.close()
        response.release_conn()

    buf = io.BytesIO(data)
    if fmt == "csv":
        return pd.read_csv(buf)
    if fmt == "parquet":
        return pd.read_parquet(buf)
    raise ValueError(f"Unsupported fmt: {fmt}")


def object_exists(object_key: str, bucket: str | None = None, client: Minio | None = None) -> bool:
    client = client or get_minio_client()
    bucket = bucket or get_bucket_name()
    try:
        client.stat_object(bucket, object_key)
        return True
    except S3Error as e:
        if e.code == "NoSuchKey":
            return False
        raise


def upload_file(
    local_path: str | Path,
    object_key: str,
    bucket: str | None = None,
    client: Minio | None = None,
) -> str:
    """Upload an existing local file (e.g. a JSON metadata blob)."""
    client = client or get_minio_client()
    bucket = bucket or get_bucket_name()
    ensure_bucket(client, bucket)
    local_path = Path(local_path)
    client.fput_object(bucket, object_key, str(local_path))
    return f"s3://{bucket}/{object_key}"


def copy_object(
    src_key: str,
    dst_key: str,
    src_bucket: str | None = None,
    dst_bucket: str | None = None,
    client: Minio | None = None,
) -> str:
    """Server-side copy an object within MinIO. Returns dst URI."""
    client = client or get_minio_client()
    src_bucket = src_bucket or get_bucket_name()
    dst_bucket = dst_bucket or src_bucket
    ensure_bucket(client, dst_bucket)
    client.copy_object(dst_bucket, dst_key, CopySource(src_bucket, src_key))
    return f"s3://{dst_bucket}/{dst_key}"


def set_object_tags(
    object_key: str,
    tags: dict[str, str],
    bucket: str | None = None,
    client: Minio | None = None,
) -> None:
    """Replace the tag set on an object. MinIO tag keys must be ASCII."""
    client = client or get_minio_client()
    bucket = bucket or get_bucket_name()
    tag_obj = Tags.new_object_tags()
    for k, v in tags.items():
        tag_obj[k] = str(v)
    client.set_object_tags(bucket, object_key, tag_obj)


def get_object_tags(
    object_key: str,
    bucket: str | None = None,
    client: Minio | None = None,
) -> dict[str, str]:
    client = client or get_minio_client()
    bucket = bucket or get_bucket_name()
    tags = client.get_object_tags(bucket, object_key)
    return dict(tags) if tags else {}
