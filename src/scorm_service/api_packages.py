import re
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from scorm_service.db import phien_lam_viec
from scorm_service.importer import PackageRejected, import_package
from scorm_service.models import PackageVersion, Sco
from scorm_service.storage import next_version, upload_dir

router = APIRouter(prefix="/api/v1")


@router.post("/packages")
def tai_goi(file: UploadFile = File(...)):
    ten = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(file.filename or "goi").stem)

    with tempfile.TemporaryDirectory() as tmp:
        tam = Path(tmp) / "goi.zip"
        dich = Path(tmp) / "noi-dung"
        with open(tam, "wb") as f:
            shutil.copyfileobj(file.file, f)
        try:
            kq = import_package(tam, dich)
        except PackageRejected as e:
            raise HTTPException(status_code=400, detail=str(e))

        try:
            with phien_lam_viec() as s:
                so_db = s.scalar(
                    select(func.max(PackageVersion.version)).where(PackageVersion.package == ten)
                ) or 0
                phien_ban = max(so_db + 1, next_version(ten))
                prefix = f"{ten}/v{phien_ban}"
                pv = PackageVersion(
                    package=ten,
                    version=phien_ban,
                    scorm_version=kq["scorm_version"],
                    sha256=kq["sha256"],
                    storage_prefix=prefix,
                    status="ready",
                )
                for vi_tri, sco in enumerate(kq["scos"]):
                    pv.scos.append(
                        Sco(identifier=sco["identifier"] or "", href=sco["href"], position=vi_tri)
                    )
                s.add(pv)
                s.flush()  # DB xac nhan so phien ban chua bi trung
                upload_dir(dich, prefix)
                id_pv = pv.id
        except IntegrityError:
            raise HTTPException(status_code=409, detail="Trung so phien ban, hay tai lai")

    return {"id": id_pv, "package": ten, "version": phien_ban, "path": prefix, **kq}