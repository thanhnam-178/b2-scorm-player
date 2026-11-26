from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from decimal import Decimal, InvalidOperation

from .db import phien_lam_viec
from .models.attempt import Attempt
from .models.base import bay_gio
from .models.person import Person
from .models.runtime_session import RuntimeSession
from .models.sco_state import ScoState
from .runtime_rules import (
    KHOA_EXIT_TRUOC,
    KetQuaLo,
    ap_dung_lo,
    bat_dau_phien,
    cmi_cho_sco,
    rut_cot,
)
from .sessions import doi_ma_lay_token, nguoi_hoc_tu_token

router = APIRouter(
    prefix="/api/v1/runtime",
    tags=["SCORM Runtime"]
)


def get_db():
    """Moi yeu cau mot phien DB; thoat thanh cong thi commit, loi thi rollback."""
    with phien_lam_viec() as s:
        yield s


def _phien_tu_token(s: Session, token: str | None) -> RuntimeSession:
    if not token:
        raise HTTPException(status_code=401, detail="Thieu token")
    phien = nguoi_hoc_tu_token(s, token)
    if phien is None:
        raise HTTPException(status_code=401, detail="Token khong hop le hoac het han")
    return phien


def phien_hien_tai(
    authorization: str | None = Header(default=None),
    s: Session = Depends(get_db),
) -> RuntimeSession:
    """Lay phien tu header 'Authorization: Bearer <token>'. Nguoi hoc xac dinh o day."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Thieu token")
    return _phien_tu_token(s, authorization[len("Bearer "):])


def _lay_state(s: Session, phien: RuntimeSession) -> ScoState:
    state = s.scalar(
        select(ScoState).where(
            ScoState.attempt_id == phien.attempt_id,
            ScoState.sco_id == phien.sco_id,
        )
    )
    if state is None:
        raise HTTPException(status_code=409, detail="Chua Initialize")
    return state

def _doi_session_time_sang_giay(value: str) -> Decimal:
    """Chuyen thoi gian SCORM 1.2 HHHH:MM:SS.SS sang giay."""
    try:
        gio, phut, giay = value.split(":")
        tong = (
            Decimal(gio) * 3600
            + Decimal(phut) * 60
            + Decimal(giay)
        )
        if tong < 0 or not tong.is_finite():
            raise ValueError
        return tong
    except (ValueError, InvalidOperation):
        raise HTTPException(
            status_code=400,
            detail="session_time khong hop le"
        )


def _ghi_lo(state: ScoState, seq: int, changes: dict) -> KetQuaLo:
    """Ap mot lo len state va ghi cot rieng. Dung chung cho commit va terminate."""
    kq = ap_dung_lo(state.cmi, changes)
    state.cmi = kq.cmi
    for ten_cot, gia_tri in rut_cot(kq.cmi).items():
        setattr(state, ten_cot, gia_tri)
    state.last_seq = seq
    state.updated_at = bay_gio()
    return kq


class SessionRequest(BaseModel):
    code: str


@router.post("/session")
def tao_phien(data: SessionRequest, s: Session = Depends(get_db)):
    kq = doi_ma_lay_token(s, data.code)
    if kq is None:
        raise HTTPException(status_code=401, detail="Ma khoi chay khong hop le, het han hoac da dung")
    token, phien = kq
    return {"token": token, "sco_id": phien.sco_id}


@router.post("/initialize")
def initialize(
    phien: RuntimeSession = Depends(phien_hien_tai),
    s: Session = Depends(get_db),
):
    attempt = s.get(Attempt, phien.attempt_id)
    nguoi = s.get(Person, attempt.person_code)

    state = s.scalar(
        select(ScoState).where(
            ScoState.attempt_id == phien.attempt_id,
            ScoState.sco_id == phien.sco_id,
        )
    )
    if state is None:
        state = ScoState(attempt_id=phien.attempt_id, sco_id=phien.sco_id)
        s.add(state)
        cmi_cu = {}
    else:
        cmi_cu = state.cmi

    entry, cmi_moi = bat_dau_phien(cmi_cu)
    state.cmi = cmi_moi
    state.last_seq = 0  # phien moi: so thu tu lo bat dau lai
    s.flush()

    ra = cmi_cho_sco(cmi_moi, entry)
    ra["cmi.core.student_id"] = attempt.person_code
    ra["cmi.core.student_name"] = f"{nguoi.family_name}, {nguoi.given_name}"
    return {"cmi": ra}


class CommitRequest(BaseModel):
    seq: int = Field(ge=1)
    changes: dict[str, Any]


@router.post("/commit")
def commit(
    data: CommitRequest,
    phien: RuntimeSession = Depends(phien_hien_tai),
    s: Session = Depends(get_db),
):
    state = _lay_state(s, phien)
    if data.seq <= state.last_seq:
        # lo cu hoac trung: bo qua, khong ghi lai (TC-14)
        return {"ok": True, "duplicate": True, "last_seq": state.last_seq,
                "errors": {}, "locked": []}
    kq = _ghi_lo(state, data.seq, data.changes)
    return {"ok": True, "duplicate": False, "last_seq": state.last_seq,
            "errors": kq.loi, "locked": kq.bi_khoa}


class TerminateRequest(BaseModel):
    token: str | None = None  # sendBeacon cua trinh duyet khong gui duoc header
    seq: int | None = Field(default=None, ge=1)
    changes: dict[str, Any] = Field(default_factory=dict)


@router.post("/terminate")
def terminate(
    data: TerminateRequest,
    authorization: str | None = Header(default=None),
    s: Session = Depends(get_db),
):
    token = data.token
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):]
    phien = _phien_tu_token(s, token)
    state = _lay_state(s, phien)

    ra = {"ok": True, "errors": {}, "locked": []}
    if data.changes and data.seq is not None and data.seq > state.last_seq:
        kq = _ghi_lo(state, data.seq, data.changes)
        ra["errors"], ra["locked"] = kq.loi, kq.bi_khoa

    cmi = dict(state.cmi)

    session_time = cmi.pop("cmi.core.session_time", None)
    if session_time is not None:
        so_giay = _doi_session_time_sang_giay(session_time)
        state.total_time_seconds = (
            Decimal(str(state.total_time_seconds or 0)) + so_giay
    )
    cmi.pop(KHOA_EXIT_TRUOC, None)
    state.cmi = cmi
    state.updated_at = bay_gio()
    phien.token_expires_at = bay_gio()  # thu hoi token
    return ra