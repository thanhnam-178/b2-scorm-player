from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()
TRANG = Path(__file__).parent / "static" / "demo.html"


@router.get("/", include_in_schema=False)
def trang_demo():
    return FileResponse(TRANG)