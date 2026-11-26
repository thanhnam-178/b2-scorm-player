
import logging
import mimetypes
import re
from pathlib import PurePosixPath
from urllib.parse import unquote

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from scorm_service import storage
from scorm_service.api_runtime_session import (
    kiem_tra_quyen_runtime,
    lay_person_code,
)
from scorm_service.db import phien_lam_viec
from scorm_service.models import AttemptScoState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/content", tags=["SCORM Content"])


def chuan_hoa_duong_dan(path: str) -> str:
    """Kiem tra va chuan hoa duong dan tep trong goi SCORM."""
    try:
        decoded = unquote(path, errors="strict")
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Duong dan tep khong hop le",
        ) from exc

    if (
        not decoded
        or "\x00" in decoded
        or "\\" in decoded
        or decoded.startswith("/")
        or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", decoded)
        or any(ord(char) < 32 or ord(char) == 127 for char in decoded)
    ):
        raise HTTPException(
            status_code=400,
            detail="Duong dan tep khong hop le",
        )

    parts = decoded.split("/")

    if any(part in {"", ".", ".."} for part in parts):
        raise HTTPException(
            status_code=400,
            detail="Duong dan tep khong hop le",
        )

    return PurePosixPath(*parts).as_posix()


@router.get("/attempts/{attempt_id}/scos/{sco_id}/{path:path}")
def phan_phoi_noi_dung(
    attempt_id: int,
    sco_id: int,
    path: str,
    request: Request,
):
    """Phan phoi tep SCORM sau khi xac thuc nguoi hoc."""
    person_code = lay_person_code(request)
    duong_dan = chuan_hoa_duong_dan(path)

    with phien_lam_viec() as s:
        _, sco, package_version = kiem_tra_quyen_runtime(
            s,
            attempt_id,
            sco_id,
            person_code,
        )

        state = s.scalar(
            select(AttemptScoState).where(
                AttemptScoState.attempt_id == attempt_id,
                AttemptScoState.sco_id == sco_id,
            )
        )

        if state is None:
            raise HTTPException(
                status_code=404,
                detail="Khong tim thay trang thai SCO trong Attempt",
            )

        if not sco.href:
            raise HTTPException(
                status_code=404,
                detail="SCO chua co tep khoi chay",
            )

        try:
            tep_khoi_chay = chuan_hoa_duong_dan(sco.href)
            danh_sach_tep = (sco.params or {}).get("files", [])

            tep_duoc_phep = {
                tep_khoi_chay,
                *(chuan_hoa_duong_dan(tep) for tep in danh_sach_tep),
            }
        except (HTTPException, TypeError):
            raise HTTPException(
                status_code=409,
                detail="Danh sach tep cua SCO khong hop le",
            )

        if duong_dan not in tep_duoc_phep:
            raise HTTPException(
                status_code=404,
                detail="Tep khong thuoc tai nguyen cua SCO",
            )

        prefix = package_version.storage_prefix.strip("/")
        if (
            not prefix
            or any(part in {"", ".", ".."} for part in prefix.split("/"))
            or "\\" in prefix
        ):
            logger.error(
                "Storage prefix khong hop le: package_version_id=%s",
                package_version.id,
            )
            raise HTTPException(
                status_code=500,
                detail="Cau hinh duong dan goi SCORM khong hop le",
            )

        key = f"{prefix}/{duong_dan}"

        try:
            obj = storage.get_object(key)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in {"NoSuchKey", "NoSuchObject", "404"}:
                raise HTTPException(
                    status_code=404,
                    detail="Khong tim thay tep SCORM",
                ) from exc

            logger.exception("Loi doc object MinIO")
            raise HTTPException(
                status_code=502,
                detail="Khong the doc noi dung SCORM",
            ) from exc
        except BotoCoreError as exc:
            logger.exception("Loi ket noi MinIO")
            raise HTTPException(
                status_code=503,
                detail="Dich vu luu tru tam thoi khong kha dung",
            ) from exc

        content_type = (
            obj.get("ContentType")
            or mimetypes.guess_type(duong_dan)[0]
            or "application/octet-stream"
        )

        headers = {
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
            "Content-Disposition": "inline",
        }

        return StreamingResponse(
            obj["Body"].iter_chunks(chunk_size=64 * 1024),
            media_type=content_type,
            headers=headers,
        )
