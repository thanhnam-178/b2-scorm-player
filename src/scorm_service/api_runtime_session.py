
import json
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select

from scorm_service.db import phien_lam_viec
from scorm_service.models import (
    Attempt,
    AttemptScoState,
    Enrollment,
    PackageVersion,
    Person,
    Sco,
)
from scorm_service.models.base import bay_gio
from scorm_service.runtime import (
    cap_nhat_cmi,
    kiem_tra_khoang_diem,
    tong_hop_diem_attempt,
    tong_hop_trang_thai_attempt,
)

router = APIRouter(prefix="/api/v1", tags=["SCORM Runtime"])
class CapNhatCMIRequest(BaseModel):
    """Du lieu CMI gui len tu SCO."""

    cmi_data: dict[str, object]


def lay_person_code(request: Request) -> str:
    """Lay person_code cua nguoi dung da dang nhap."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Chua dang nhap")

    person_code = request.session.get("person_code")
    if not person_code:
        raise HTTPException(
            status_code=401,
            detail="Phien dang nhap khong hop le",
        )

    return person_code


def kiem_tra_quyen_runtime(
    s,
    attempt_id: int,
    sco_id: int,
    person_code: str,
    cho_phep_attempt_da_dong: bool = False,
):
    """Kiem tra quyen truy cap Attempt va SCO."""
    attempt = s.get(Attempt, attempt_id)

    if attempt is None:
        raise HTTPException(
            status_code=404,
            detail="Khong tim thay Attempt",
        )

    if attempt.person_code != person_code:
        raise HTTPException(
            status_code=403,
            detail="Ban khong co quyen truy cap Attempt nay",
        )

    if (
        attempt.status != "in_progress"
        and not cho_phep_attempt_da_dong
    ):
        raise HTTPException(
            status_code=409,
            detail="Attempt khong con trong trang thai hoc",
        )

    enrollment = s.get(
        Enrollment,
        (attempt.section_code, person_code),
    )

    if enrollment is None or enrollment.status != "registered":
        raise HTTPException(
            status_code=403,
            detail="Ban khong con quyen hoc lop hoc phan nay",
        )

    person = s.get(Person, person_code)

    if (
        person is None
        or person.person_type != "student"
        or enrollment.role != "student"
    ):
        raise HTTPException(
            status_code=403,
            detail="Chi nguoi hoc moi co quyen truy cap Runtime",
        )

    sco = s.get(Sco, sco_id)

    if sco is None or sco.package_version_id != attempt.package_version_id:
        raise HTTPException(
            status_code=404,
            detail="SCO khong thuoc phien ban goi cua Attempt",
        )

    package_version = s.get(
        PackageVersion,
        attempt.package_version_id,
    )

    if package_version is None or package_version.status != "ready":
        raise HTTPException(
            status_code=409,
            detail="Phien ban goi SCORM khong san sang",
        )

    return attempt, sco, package_version

@router.get(
    "/attempts/{attempt_id}/scos/{sco_id}/launch",
    response_class=HTMLResponse,
)
def mo_scorm_wrapper(
    attempt_id: int,
    sco_id: int,
    request: Request,
):
    """Mo Wrapper va nap SCO sau khi kiem tra quyen Runtime."""
    person_code = lay_person_code(request)

    with phien_lam_viec() as s:
        attempt, sco, package_version = kiem_tra_quyen_runtime(
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
                status_code=409,
                detail="SCO chua co duong dan launch",
            )

        launch_url = (
            f"/content/attempts/{attempt.id}/scos/{sco.id}/"
            f"{quote(sco.href, safe='/')}"
        )

        config = {
            "attemptId": attempt.id,
            "scoId": sco.id,
            "scormVersion": package_version.scorm_version,
            "launchUrl": launch_url,
        }

    config_json = json.dumps(config, ensure_ascii=True)
    config_json = (
        config_json
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )

    wrapper_path = (
        Path(__file__).resolve().parent
        / "static"
        / "scorm_launch.html"
    )

    if not wrapper_path.is_file():
        raise HTTPException(
            status_code=500,
            detail="Khong tim thay SCORM Launch Wrapper",
        )

    html = wrapper_path.read_text(encoding="utf-8")
    html = html.replace("__SCORM_CONFIG__", config_json)

    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "no-store"},
    )

@router.post("/attempts/{attempt_id}/scos/{sco_id}/initialize")
def khoi_tao_runtime(
    attempt_id: int,
    sco_id: int,
    request: Request,
):
    """Khoi tao hoac tiep tuc Runtime cua mot SCO."""
    person_code = lay_person_code(request)

    with phien_lam_viec() as s:
        attempt, sco, package_version = kiem_tra_quyen_runtime(
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
                detail="Khong tim thay trang thai CMI cua SCO",
            )

        if attempt.status != "in_progress" and not state.runtime_terminated:
            raise HTTPException(
                status_code=409,
                detail="Attempt khong con trong trang thai hoc",
            )

        if state.runtime_terminated:
            state.runtime_terminated = False

        state.runtime_initialized = True

        return {
            "attempt_id": attempt.id,
            "sco_id": sco.id,
            "scorm_version": package_version.scorm_version,
            "cmi_data": state.cmi_data,
            "initialized": state.runtime_initialized,
            "terminated": state.runtime_terminated,
        }

@router.get("/attempts/{attempt_id}/scos/{sco_id}/cmi")
def doc_cmi(
    attempt_id: int,
    sco_id: int,
    request: Request,
):
    """Doc du lieu CMI cua mot SCO trong Attempt."""
    person_code = lay_person_code(request)

    with phien_lam_viec() as s:
        attempt, sco, package_version = kiem_tra_quyen_runtime(
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

        state = s.scalar(
            select(AttemptScoState).where(
                AttemptScoState.attempt_id == attempt_id,
                AttemptScoState.sco_id == sco_id,
            )
        )

        if state is None:
            raise HTTPException(
                status_code=404,
                detail="Khong tim thay trang thai CMI cua SCO",
            )

        return {
            "attempt_id": attempt.id,
            "sco_id": sco.id,
            "scorm_version": package_version.scorm_version,
            "cmi_data": state.cmi_data,
        }


@router.put("/attempts/{attempt_id}/scos/{sco_id}/cmi")
def cap_nhat_du_lieu_cmi(
    attempt_id: int,
    sco_id: int,
    data: CapNhatCMIRequest,
    request: Request,
):
    """Cap nhat du lieu CMI cua mot SCO trong Attempt."""
    person_code = lay_person_code(request)

    with phien_lam_viec() as s:
        attempt, sco, package_version = kiem_tra_quyen_runtime(
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
                detail="Khong tim thay trang thai CMI cua SCO",
            )

        if not state.runtime_initialized:
            raise HTTPException(
                status_code=409,
                detail="Runtime chua duoc Initialize",
            )

        if state.runtime_terminated:
            raise HTTPException(
                status_code=409,
                detail="Runtime da Terminate",
            )

        cmi_data = state.cmi_data

        for ten_truong, gia_tri in data.cmi_data.items():
            cmi_data = cap_nhat_cmi(
                package_version.scorm_version,
                cmi_data,
                ten_truong,
                gia_tri,
            )

        kiem_tra_khoang_diem(
            package_version.scorm_version,
            cmi_data,
        )

        state.cmi_data = cmi_data

        return {
            "attempt_id": attempt.id,
            "sco_id": sco.id,
            "scorm_version": package_version.scorm_version,
            "cmi_data": state.cmi_data,
        }

@router.post("/attempts/{attempt_id}/scos/{sco_id}/terminate")
def ket_thuc_runtime(
    attempt_id: int,
    sco_id: int,
    request: Request,
    data: CapNhatCMIRequest | None = None,
):
    """Ket thuc Runtime cua mot SCO."""
    person_code = lay_person_code(request)

    with phien_lam_viec() as s:
        attempt, sco, package_version = kiem_tra_quyen_runtime(
            s,
            attempt_id,
            sco_id,
            person_code,
            cho_phep_attempt_da_dong=True,
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
                detail="Khong tim thay trang thai CMI cua SCO",
            )

        if attempt.status != "in_progress" and not state.runtime_terminated:
            raise HTTPException(
                status_code=409,
                detail="Attempt khong con trong trang thai hoc",
            )

        if not state.runtime_initialized:
            raise HTTPException(
                status_code=409,
                detail="Runtime chua duoc Initialize",
            )

        if state.runtime_terminated:
            if data is not None and data.cmi_data:
                raise HTTPException(
                    status_code=409,
                    detail="Khong the cap nhat CMI sau khi Terminate",
                )

            return {
                "attempt_id": attempt.id,
                "sco_id": sco.id,
                "scorm_version": package_version.scorm_version,
                "terminated": True,
                "attempt_status": attempt.status,
            }

        if data is not None:
            cmi_data = state.cmi_data

            for ten_truong, gia_tri in data.cmi_data.items():
                cmi_data = cap_nhat_cmi(
                    package_version.scorm_version,
                    cmi_data,
                    ten_truong,
                    gia_tri,
                )

            kiem_tra_khoang_diem(
                package_version.scorm_version,
                cmi_data,
            )

            state.cmi_data = cmi_data

        s.flush()

        state.runtime_terminated = True
        s.flush()

        danh_sach_state = s.scalars(
            select(AttemptScoState).where(
                AttemptScoState.attempt_id == attempt.id,
            )
        ).all()

        tat_ca_sco_da_terminate = all(
            item.runtime_initialized and item.runtime_terminated
            for item in danh_sach_state
        )

        if tat_ca_sco_da_terminate:
            danh_sach_cmi = [
                item.cmi_data for item in danh_sach_state
            ]

            trang_thai = tong_hop_trang_thai_attempt(
                package_version.scorm_version,
                danh_sach_cmi,
            )

            if trang_thai != "in_progress":
                attempt.status = trang_thai
                attempt.completed_at = bay_gio()

                ket_qua_diem = tong_hop_diem_attempt(
                    package_version.scorm_version,
                    danh_sach_cmi,
                )

                if ket_qua_diem is None:
                    attempt.score_raw = None
                    attempt.score_min = None
                    attempt.score_max = None
                else:
                    (
                        attempt.score_raw,
                        attempt.score_min,
                        attempt.score_max,
                    ) = ket_qua_diem

        return {
            "attempt_id": attempt.id,
            "sco_id": sco.id,
            "scorm_version": package_version.scorm_version,
            "terminated": state.runtime_terminated,
            "attempt_status": attempt.status,
        }