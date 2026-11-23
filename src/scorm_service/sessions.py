"""Ma khoi chay (dung 1 lan, 60 giay) va token phien. Nguoi hoc xac dinh tu token."""
import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .models.base import bay_gio
from .models.runtime_session import RuntimeSession

HAN_MA = timedelta(seconds=60)
HAN_TOKEN = timedelta(minutes=30)  # sau nay commit se gia han


def _bam(chuoi: str) -> str:
    return hashlib.sha256(chuoi.encode()).hexdigest()


def cap_ma_khoi_chay(s: Session, attempt_id: int, sco_id: int) -> str:
    ma = secrets.token_urlsafe(32)  # chuoi ngau nhien kho doan
    s.add(RuntimeSession(
        attempt_id=attempt_id,
        sco_id=sco_id,
        code_hash=_bam(ma),
        code_expires_at=bay_gio() + HAN_MA,
    ))
    s.flush()
    return ma


def doi_ma_lay_token(s: Session, ma: str) -> tuple[str, RuntimeSession] | None:
    """Doi ma lay token. Ma sai, het han, hoac da dung -> None."""
    bam = _bam(ma)
    # Mot cau UPDATE duy nhat: kiem tra va danh dau "da dung" cung luc.
    # Hai yeu cau gui cung ma cung luc thi chi mot yeu cau thang.
    kq = s.execute(
        update(RuntimeSession)
        .where(
            RuntimeSession.code_hash == bam,
            RuntimeSession.code_used.is_(False),
            RuntimeSession.code_expires_at > bay_gio(),
        )
        .values(code_used=True)
    )
    if kq.rowcount != 1:
        return None

    phien = s.scalar(select(RuntimeSession).where(RuntimeSession.code_hash == bam))
    token = secrets.token_urlsafe(32)
    phien.token_hash = _bam(token)
    phien.token_expires_at = bay_gio() + HAN_TOKEN
    s.flush()
    return token, phien


def nguoi_hoc_tu_token(s: Session, token: str) -> RuntimeSession | None:
    """Tu token tim ra phien (co attempt_id, sco_id). Sai hoac het han -> None."""
    return s.scalar(
        select(RuntimeSession).where(
            RuntimeSession.token_hash == _bam(token),
            RuntimeSession.token_expires_at > bay_gio(),
        )
    )