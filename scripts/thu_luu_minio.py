import os
import sys
import tempfile
from pathlib import Path

# Doc deploy/.env (khong in ra man hinh)
for dong in Path("deploy/.env").read_text(encoding="utf-8").splitlines():
    if "=" in dong and not dong.lstrip().startswith("#"):
        k, v = dong.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
os.environ["S3_ENDPOINT"] = "http://localhost:9000"  # chay tren may, khong trong Docker

sys.path.insert(0, "src")
from scorm_service.importer import import_package
from scorm_service.storage import _client, upload_dir

bucket = os.environ["S3_BUCKET"]
tam = tempfile.mkdtemp()
import_package("tests/fixtures/INT1234-demo-scorm12.zip", tam)

print("Da tai len", upload_dir(tam, "thu-nghiem/v1"), "tep")

s3 = _client()
ds = s3.list_objects_v2(Bucket=bucket, Prefix="thu-nghiem/").get("Contents", [])
for o in ds:
    print(o["Key"], o["Size"])

h = s3.head_object(Bucket=bucket, Key="thu-nghiem/v1/index.html")
print("Content-Type index.html:", h["ContentType"])

for o in ds:
    s3.delete_object(Bucket=bucket, Key=o["Key"])
print("Da xoa", len(ds), "tep thu nghiem")