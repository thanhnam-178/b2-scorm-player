"""Luu goi da giai nen len MinIO: src/scorm_service/storage.py"""
import mimetypes
import os
from pathlib import Path

import boto3
from botocore.config import Config

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
    """Tai moi tep trong local_dir len bucket duoi tien to prefix; tra ve so tep."""
    s3 = _client()
    bucket = os.environ["S3_BUCKET"]
    local_dir = Path(local_dir)
    dem = 0
    for f in local_dir.rglob("*"):
        if not f.is_file():
            continue
        key = f"{prefix}/{f.relative_to(local_dir).as_posix()}"
        kieu = (KIEU_TEP.get(f.suffix.lower())
                or mimetypes.guess_type(f.name)[0]
                or "application/octet-stream")
        s3.upload_file(str(f), bucket, key, ExtraArgs={"ContentType": kieu})
        dem += 1
    return dem


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