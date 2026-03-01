"""
Storage service for generating signed URLs (S3/MinIO compatible).

Set the following environment variables for production:
- S3_BUCKET
- S3_REGION (optional)
- S3_ENDPOINT_URL (for MinIO or custom endpoint, optional)
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- S3_SIGNED_URL_EXPIRES (seconds, default 900)

If S3_BUCKET is not set, the service will raise at runtime (keeps dev simple).
"""

import os
from typing import Optional, Dict

_boto3 = None


def _get_boto3():
    global _boto3
    if _boto3 is None:
        try:
            import boto3  # type: ignore
        except ImportError as e:
            raise RuntimeError("boto3 is required for signed URL generation. Please install boto3.") from e
        _boto3 = boto3
    return _boto3


def _client():
    boto3 = _get_boto3()
    endpoint = os.getenv("S3_ENDPOINT_URL")
    region = os.getenv("S3_REGION", "us-east-1")
    return boto3.client(
        "s3",
        endpoint_url=endpoint or None,
        region_name=region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def _bucket() -> str:
    bucket = os.getenv("S3_BUCKET", "").strip()
    if not bucket:
        raise RuntimeError("S3_BUCKET is not configured.")
    return bucket


def _expires() -> int:
    try:
        return int(os.getenv("S3_SIGNED_URL_EXPIRES", "900"))
    except ValueError:
        return 900


def presign_upload(key: str, content_type: str = "application/octet-stream") -> Dict:
    """Return a pre-signed PUT URL and headers."""
    client = _client()
    url = client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": _bucket(), "Key": key, "ContentType": content_type},
        ExpiresIn=_expires(),
    )
    return {"url": url, "method": "PUT", "headers": {"Content-Type": content_type}, "key": key}


def presign_download(key: str) -> Dict:
    """Return a pre-signed GET URL."""
    client = _client()
    url = client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": _bucket(), "Key": key},
        ExpiresIn=_expires(),
    )
    return {"url": url, "method": "GET", "key": key}
