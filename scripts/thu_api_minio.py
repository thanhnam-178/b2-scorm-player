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

from scorm_service.api_packages import router
from scorm_service.storage import _client

app = FastAPI()
app.include_router(router)
c = TestClient(app)
zip_mau = Path("tests/fixtures/INT1234-demo-scorm12.zip").read_bytes()

for lan in (1, 2):
    r = c.post("/api/v1/packages", files={"file": ("thu-api.zip", zip_mau, "application/zip")})
    print("Lan", lan, "->", r.status_code, r.json()["version"], r.json()["path"])

r = c.post("/api/v1/packages", files={"file": ("hong.zip", io.BytesIO(b"khong phai zip"), "application/zip")})
print("File hong ->", r.status_code)

s3 = _client()
bucket = os.environ["S3_BUCKET"]
ds = s3.list_objects_v2(Bucket=bucket, Prefix="thu-api/").get("Contents", [])
print("Tren MinIO:", [o["Key"] for o in ds])
for o in ds:
    s3.delete_object(Bucket=bucket, Key=o["Key"])
print("Da xoa", len(ds), "tep thu nghiem")