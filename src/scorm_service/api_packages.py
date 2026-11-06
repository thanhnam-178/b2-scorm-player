import re
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from scorm_service.importer import PackageRejected, import_package

router = APIRouter(prefix="/api/v1")
THU_MUC_GOI = Path("data/packages")


@router.post("/packages")
def tai_goi(file: UploadFile = File(...)):
    ten = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(file.filename or "goi").stem)
    goc = THU_MUC_GOI / ten
    phien_ban = len(list(goc.glob("v*"))) + 1
    dich = goc / f"v{phien_ban}"

    with tempfile.TemporaryDirectory() as tmp:
        tam = Path(tmp) / "goi.zip"
        with open(tam, "wb") as f:
            shutil.copyfileobj(file.file, f)
        try:
            kq = import_package(tam, dich)
        except PackageRejected as e:
            shutil.rmtree(dich, ignore_errors=True)
            raise HTTPException(status_code=400, detail=str(e))

    return {"package": ten, "version": phien_ban, "path": str(dich), **kq}