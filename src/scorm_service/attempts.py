"""Quy tac attempt: mot nguoi, mot phien ban goi, mot attempt."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models.attempt import Attempt


def lay_hoac_tao_attempt(s: Session, person_code: str, package_version_id: int) -> Attempt:
    attempt = s.scalar(
        select(Attempt).where(
            Attempt.person_code == person_code,
            Attempt.package_version_id == package_version_id,
        )
    )
    if attempt is not None:
        return attempt  # mo lan hai: dung lai, khong dong vao diem/trang thai cu

    attempt = Attempt(person_code=person_code, package_version_id=package_version_id)
    s.add(attempt)
    s.flush()  # gui INSERT de co attempt.id, chua commit
    return attempt