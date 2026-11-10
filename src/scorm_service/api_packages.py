import re
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from scorm_service.importer import PackageRejected, import_package
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
        phien_ban = next_version(ten)
        prefix = f"{ten}/v{phien_ban}"
        upload_dir(dich, prefix)

    return {"package": ten, "version": phien_ban, "path": prefix, **kq}