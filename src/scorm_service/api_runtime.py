from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import phien_lam_viec
from .models.attempt import Attempt
from .models.person import Person
from .models.runtime_session import RuntimeSession
from .models.sco_state import ScoState
from .runtime_rules import bat_dau_phien, cmi_cho_sco
from .sessions import doi_ma_lay_token, nguoi_hoc_tu_token

router = APIRouter(
    prefix="/api/v1/runtime",
    tags=["SCORM Runtime"]
)


def get_db():
    """Moi yeu cau mot phien DB; thoat thanh cong thi commit, loi thi rollback."""
    with phien_lam_viec() as s:
        yield s


def phien_hien_tai(
    authorization: str | None = Header(default=None),
    s: Session = Depends(get_db),
) -> RuntimeSession:
    """Lay phien tu header 'Authorization: Bearer <token>'. Nguoi hoc xac dinh o day."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Thieu token")
    phien = nguoi_hoc_tu_token(s, authorization[len("Bearer "):])
    if phien is None:
        raise HTTPException(status_code=401, detail="Token khong hop le hoac het han")
    return phien


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