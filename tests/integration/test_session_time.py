
from decimal import Decimal

from helpers import API, dung_phien, trang_thai


def test_session_time_chi_cong_khi_terminate(env):
    """Commit không cộng thời gian; Terminate mới cộng vào tổng."""
    client, _ = env
    h = dung_phien(env, person_code="SV_TIME_001")

    # Khởi tạo phiên học
    r = client.post(f"{API}/initialize", headers=h)
    assert r.status_code == 200

    # Gửi session_time qua Commit
    r = client.post(f"{API}/commit", headers=h, json={
        "seq": 1,
        "changes": {
            "cmi.core.session_time": "00:10:00.00"
        }
    })
    assert r.status_code == 200

    # Commit chưa được cộng vào tổng thời gian
    state = trang_thai(env, "SV_TIME_001")
    assert Decimal(str(state.total_time_seconds or 0)) == Decimal("0")

    # Kết thúc phiên học
    r = client.post(f"{API}/terminate", headers=h, json={})
    assert r.status_code == 200

    # 10 phút = 600 giây
    state = trang_thai(env, "SV_TIME_001")
    assert Decimal(str(state.total_time_seconds)) == Decimal("600")


def test_session_time_cong_don_qua_nhieu_phien(env):
    """Hai phiên học phải cộng dồn thời gian, không ghi đè."""
    client, _ = env
    person = "SV_TIME_002"

    # Phiên học thứ nhất: 10 phút
    h1 = dung_phien(env, person_code=person)
    assert client.post(f"{API}/initialize", headers=h1).status_code == 200

    r = client.post(f"{API}/terminate", headers=h1, json={
        "seq": 1,
        "changes": {
            "cmi.core.session_time": "00:10:00.00"
        }
    })
    assert r.status_code == 200

    state = trang_thai(env, person)
    assert Decimal(str(state.total_time_seconds)) == Decimal("600")

    # Phiên học thứ hai: 5 phút
    h2 = dung_phien(env, person_code=person)
    assert client.post(f"{API}/initialize", headers=h2).status_code == 200

    r = client.post(f"{API}/terminate", headers=h2, json={
        "seq": 1,
        "changes": {
            "cmi.core.session_time": "00:05:00.00"
        }
    })
    assert r.status_code == 200

    # Tổng thời gian phải là 15 phút = 900 giây
    state = trang_thai(env, person)
    assert Decimal(str(state.total_time_seconds)) == Decimal("900")


def test_session_time_khong_hop_le(env):
    """Session_time sai định dạng phải trả HTTP 400."""
    client, _ = env
    h = dung_phien(env, person_code="SV_TIME_003")

    assert client.post(f"{API}/initialize", headers=h).status_code == 200

    r = client.post(f"{API}/terminate", headers=h, json={
        "seq": 1,
        "changes": {
            "cmi.core.session_time": "abc"
        }
    })

    assert r.status_code == 400
