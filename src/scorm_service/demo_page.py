
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from scorm_service.api_packages import kiem_tra_quyen_upload

router = APIRouter()

STATIC_DIR = Path(__file__).parent / "static"


@router.get("/", include_in_schema=False)
def trang_dang_nhap():
    return FileResponse(STATIC_DIR / "login.html")


@router.get("/demo", include_in_schema=False)
def trang_demo(request: Request):
    kiem_tra_quyen_upload(request)
    return FileResponse(STATIC_DIR / "demo.html")
