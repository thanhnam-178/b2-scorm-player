import io
import os
import sys
from pathlib import Path

for dong in Path("deploy/.env").read_text(encoding="utf-8").splitlines():
    if "=" in dong and not dong.lstrip().startswith("#"):
        k, v = dong.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
os.environ["S3_ENDPOINT"] = "http://localhost:9000"

sys.path.insert(0, "src")
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from scorm_service.api_packages import router
from scorm_service.db import phien_lam_viec
from scorm_service.models import PackageVersion
from scorm_service.storage import _client

app = FastAPI()
app.include_router(router)
c = TestClient(app)
zip_mau = Path("tests/fixtures/INT1234-demo-scorm12.zip").read_bytes()

for lan in (1, 2):
    r = c.post("/api/v1/packages", files={"file": ("thu-api-db.zip", zip_mau, "application/zip")})
    print("Lan", lan, "->", r.status_code, "version", r.json()["version"], r.json()["path"])

r = c.post("/api/v1/packages", files={"file": ("hong.zip", io.BytesIO(b"khong phai zip"), "application/zip")})
print("File hong ->", r.status_code)

with phien_lam_viec() as s:
    ds = s.scalars(
        select(PackageVersion)
        .where(PackageVersion.package == "thu-api-db")
        .order_by(PackageVersion.version)
    ).all()
    print("Trong DB:", [(p.version, p.status, [x.identifier for x in p.scos]) for p in ds])
    for p in ds:
        s.delete(p)

s3 = _client()
bucket = os.environ["S3_BUCKET"]
for o in s3.list_objects_v2(Bucket=bucket, Prefix="thu-api-db/").get("Contents", []):
    s3.delete_object(Bucket=bucket, Key=o["Key"])
print("Da don DB va MinIO")