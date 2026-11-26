import os
import sys
from pathlib import Path

for dong in Path("deploy/.env").read_text(encoding="utf-8").splitlines():
    if "=" in dong and not dong.lstrip().startswith("#"):
        k, v = dong.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
sys.path.insert(0, "src")

from sqlalchemy import select

from scorm_service.db import phien_lam_viec
from scorm_service.models import PackageVersion, Sco

with phien_lam_viec() as s:
    pv = PackageVersion(package="thu-db", version=1, scorm_version="1.2",
                        sha256="x" * 64, storage_prefix="thu-db/v1")
    pv.scos.append(Sco(identifier="RES1", href="index.html"))
    s.add(pv)

with phien_lam_viec() as s:
    pv = s.scalars(select(PackageVersion).where(PackageVersion.package == "thu-db")).one()
    print("Doc lai:", pv.package, pv.version, pv.status, [x.identifier for x in pv.scos])
    s.delete(pv)

with phien_lam_viec() as s:
    con_lai = s.scalars(select(PackageVersion).where(PackageVersion.package == "thu-db")).all()
    print("Sau khi xoa con", len(con_lai), "dong")