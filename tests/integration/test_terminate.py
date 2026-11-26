from helpers import API, dung_phien


def test_muc_tieu_3_suspend_roi_vao_lai(env):
    client, _ = env
    h1 = dung_phien(env)
    client.post(f"{API}/initialize", headers=h1)
    r = client.post(f"{API}/terminate", headers=h1, json={"seq": 1, "changes": {
        "cmi.core.lesson_location": "trang-7",
        "cmi.suspend_data": "q=3",
        "cmi.core.exit": "suspend"}})
    assert r.status_code == 200

    h2 = dung_phien(env)  # vào lại sau khi thoát
    cmi = client.post(f"{API}/initialize", headers=h2).json()["cmi"]
    assert cmi["cmi.core.entry"] == "resume"
    assert cmi["cmi.core.lesson_location"] == "trang-7"
    assert cmi["cmi.suspend_data"] == "q=3"


def test_tai_lai_trang_van_la_resume_roi_het_resume_sau_terminate(env):
    client, _ = env
    h1 = dung_phien(env)
    client.post(f"{API}/initialize", headers=h1)
    client.post(f"{API}/terminate", headers=h1, json={"seq": 1, "changes": {
        "cmi.core.lesson_location": "trang-7", "cmi.core.exit": "suspend"}})

    h2 = dung_phien(env)
    for _ in range(2):  # Initialize hai lan lien tiep = tai lai trang
        cmi = client.post(f"{API}/initialize", headers=h2).json()["cmi"]
        assert cmi["cmi.core.entry"] == "resume"
    client.post(f"{API}/terminate", headers=h2, json={})  # phien 2 ket thuc, khong suspend

    h3 = dung_phien(env)
    cmi = client.post(f"{API}/initialize", headers=h3).json()["cmi"]
    assert cmi["cmi.core.entry"] == ""  # khong con resume


def test_terminate_thu_hoi_token(env):
    client, _ = env
    h = dung_phien(env)
    client.post(f"{API}/initialize", headers=h)
    assert client.post(f"{API}/terminate", headers=h, json={}).status_code == 200
    r = client.post(f"{API}/commit", headers=h, json={"seq": 1, "changes": {}})
    assert r.status_code == 401


def test_terminate_nhan_token_trong_body_cho_sendbeacon(env):
    client, _ = env
    h = dung_phien(env)
    client.post(f"{API}/initialize", headers=h)
    token = h["Authorization"].removeprefix("Bearer ")
    r = client.post(f"{API}/terminate", json={"token": token})  # khong co header
    assert r.status_code == 200