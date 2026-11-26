"""Luu goi da giai nen len MinIO: src/scorm_service/storage.py"""
import logging
import mimetypes
import os
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

# Windows hay doan sai kieu tep; nosniff khong cho trinh duyet doan lai
KIEU_TEP = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".xml": "application/xml",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
}


def _client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT"],
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        region_name="us-east-1",
        config=Config(signature_version="s3v4"),
    )



def upload_dir(local_dir, prefix: str) -> int:
    """Tai tep len MinIO; neu that bai thi xoa cac object da tai."""
    s3 = _client()
    bucket = os.environ["S3_BUCKET"]
    local_dir = Path(local_dir)
    cac_key_da_tai = []

    try:
        for f in sorted(local_dir.rglob("*")):
            if not f.is_file():
                continue

            key = f"{prefix}/{f.relative_to(local_dir).as_posix()}"
            kieu = (
                KIEU_TEP.get(f.suffix.lower())
                or mimetypes.guess_type(f.name)[0]
                or "application/octet-stream"
            )

            s3.upload_file(
                str(f),
                bucket,
                key,
                ExtraArgs={"ContentType": kieu},
            )
            cac_key_da_tai.append(key)

    except Exception:
        if cac_key_da_tai:
            try:
                s3.delete_objects(
                    Bucket=bucket,
                    Delete={
                        "Objects": [{"Key": key} for key in cac_key_da_tai],
                        "Quiet": True,
                    },
                )
            except (BotoCoreError, ClientError):
                # Khong de loi don dep che mat loi upload ban dau.
                logger.exception(
                    "Khong the don dep object MinIO sau khi upload that bai"
                )
        raise

    return len(cac_key_da_tai)



def next_version(ten: str) -> int:
    """So phien ban ke tiep cua goi: nhin cac thu muc v1, v2... da co tren MinIO."""
    s3 = _client()
    bucket = os.environ["S3_BUCKET"]
    cao_nhat = 0
    for trang in s3.get_paginator("list_objects_v2").paginate(
        Bucket=bucket, Prefix=f"{ten}/", Delimiter="/"
    ):
        for p in trang.get("CommonPrefixes", []):
            so = p["Prefix"].rstrip("/").rsplit("/", 1)[-1]
            if so.startswith("v") and so[1:].isdigit():
                cao_nhat = max(cao_nhat, int(so[1:]))
    return cao_nhat + 1


def get_object(key: str):
    """Doc mot object tu bucket MinIO rieng tu."""
    s3 = _client()
    bucket = os.environ["S3_BUCKET"]

    return s3.get_object(
        Bucket=bucket,
        Key=key,
    )