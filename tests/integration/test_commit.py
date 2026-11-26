from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scorm_service.models.attempt import Attempt

from helpers import API, dung_phien, trang_thai


def test_tc08_bo_qua_ma_nguoi_do_trinh_duyet_gui(env):
    client, _ = env
    h = dung_phien(env, "SV000001")
    client.post(f"{API}/initialize", headers=h)
    r = client.post(f"{API}/commit", headers=h, json={
        "seq": 1,
        "person_code": "SV000002",  # trình duyệt cố gửi mã người khác
        "changes": {"cmi.core.lesson_status": "completed", "cmi.core.score.raw": "8"},
    })
    assert r.status_code == 200
    assert trang_thai(env, "SV000001").lesson_status == "completed"
    assert trang_thai(env, "SV000002") is None  # không ai khác bị ghi


def test_tc09_token_luot_nay_khong_ghi_vao_luot_khac(env):
    client, _ = env
    ha = dung_phien(env, "SV000001")
    hb = dung_phien(env, "SV000002")
    for h in (ha, hb):
        client.post(f"{API}/initialize", headers=h)
    client.post(f"{API}/commit", headers=ha, json={
        "seq": 1, "changes": {"cmi.core.lesson_location": "trang-5"}})
    assert trang_thai(env, "SV000001").cmi["cmi.core.lesson_location"] == "trang-5"
    assert "cmi.core.lesson_location" not in trang_thai(env, "SV000002").cmi


def test_tc14_lo_trung_khong_ghi_lai(env):
    client, _ = env
    h = dung_phien(env)
    client.post(f"{API}/initialize", headers=h)

    def gui(seq, diem):
        return client.post(f"{API}/commit", headers=h, json={
            "seq": seq, "changes": {"cmi.core.score.raw": diem}})

    assert gui(1, "5").json()["duplicate"] is False
    assert gui(1, "9").json()["duplicate"] is True   # gửi lại seq cũ, giá trị khác
    assert trang_thai(env, "SV000001").score_raw == 5  # vẫn là 5
    assert gui(2, "6").json()["duplicate"] is False


def test_muc_tieu_5_mo_lan_hai_diem_va_trang_thai_giu_nguyen(env):
    client, engine = env
    h1 = dung_phien(env)
    client.post(f"{API}/initialize", headers=h1)
    client.post(f"{API}/commit", headers=h1, json={"seq": 1, "changes": {
        "cmi.core.lesson_status": "completed",
        "cmi.core.score.raw": "8", "cmi.core.score.max": "10"}})

    h2 = dung_phien(env)  # mở lần hai, cùng người
    client.post(f"{API}/initialize", headers=h2)
    r = client.post(f"{API}/commit", headers=h2, json={"seq": 1, "changes": {
        "cmi.core.lesson_status": "incomplete", "cmi.core.score.raw": "3"}})

    assert set(r.json()["locked"]) == {"cmi.core.lesson_status", "cmi.core.score.raw"}
    st = trang_thai(env, "SV000001")
    assert st.lesson_status == "completed" and st.score_raw == 8
    with Session(engine) as s:
        so_attempt = s.scalar(select(func.count()).select_from(Attempt)
                              .where(Attempt.person_code == "SV000001"))
    assert so_attempt == 1  # không sinh attempt mới