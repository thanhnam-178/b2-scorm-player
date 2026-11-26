from sqlalchemy import select
from sqlalchemy.orm import Session

from scorm_service.attempts import lay_hoac_tao_attempt
from scorm_service.models.attempt import Attempt
from scorm_service.models.person import Person
from scorm_service.models.sco_state import ScoState
from scorm_service.sessions import cap_ma_khoi_chay

API = "/api/v1/runtime"
VERSION_ID = 1   # SQLite không kiểm tra khóa ngoại nên số này không cần có thật
SCO_ID = 3


def dung_phien(env, person_code="SV000001"):
    """Dựng một phiên học: người -> attempt -> mã khởi chạy -> token (qua /session).
    Trả về header Authorization để gắn vào các lời gọi sau."""
    client, engine = env
    with Session(engine) as s:
        if s.get(Person, person_code) is None:
            s.add(Person(person_code=person_code, family_name="Nguyen", given_name="An",
                         email=f"{person_code}@x.vn", person_type="student"))
        attempt = lay_hoac_tao_attempt(s, person_code, VERSION_ID)
        ma = cap_ma_khoi_chay(s, attempt.id, SCO_ID)
        s.commit()
    token = client.post(f"{API}/session", json={"code": ma}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def trang_thai(env, person_code):
    """Đọc ScoState của người đó thẳng từ DB (None nếu chưa có)."""
    _, engine = env
    with Session(engine) as s:
        return s.scalar(
            select(ScoState)
            .join(Attempt, Attempt.id == ScoState.attempt_id)
            .where(Attempt.person_code == person_code)
        )