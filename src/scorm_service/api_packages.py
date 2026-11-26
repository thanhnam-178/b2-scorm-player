import re
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from scorm_service.db import phien_lam_viec
from scorm_service.importer import PackageRejected, import_package
from scorm_service.models import Enrollment, PackageVersion, Person, Sco
from scorm_service.storage import next_version, upload_dir

router = APIRouter(prefix="/api/v1")
def kiem_tra_quyen_upload(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Chua dang nhap")

    person_code = request.session.get("person_code")
    if not person_code:
        raise HTTPException(
            status_code=401,
            detail="Phien dang nhap khong hop le",
        )

    with phien_lam_viec() as s:
        person = s.get(Person, person_code)

        if person is None or person.person_type != "staff":
            raise HTTPException(
                status_code=403,
                detail="Khong co quyen upload goi SCORM",
            )

        enrollment = s.scalar(
            select(Enrollment).where(
                Enrollment.person_code == person_code,
                Enrollment.role.in_(["teacher", "editingteacher"]),
                Enrollment.status == "registered",
            ).limit(1)
        )

        if enrollment is None:
            raise HTTPException(
                status_code=403,
                detail="Khong co quyen upload goi SCORM",
            )


@router.post("/packages")
def tai_goi(request: Request, file: UploadFile = File(...)):  # noqa: B008
    kiem_tra_quyen_upload(request)
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
                        Sco(
                            identifier=sco["identifier"] or "",
                            title=sco.get("title"),
                            href=sco.get("href"),
                            position=vi_tri,
                            params={
                                "item_identifier": sco.get("item_identifier"),
                                "scorm_type": sco.get("scorm_type"),
                                "files": sco.get("files", []),
                            },
                        )
                    )
                s.add(pv)
                s.flush()  # DB xac nhan so phien ban chua bi trung
                upload_dir(dich, prefix)
                id_pv = pv.id
        except IntegrityError:
            raise HTTPException(status_code=409, detail="Trung so phien ban, hay tai lai")

    return {"id": id_pv, "package": ten, "version": phien_ban, "path": prefix, **kq}