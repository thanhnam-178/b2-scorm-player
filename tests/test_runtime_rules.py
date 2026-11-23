from decimal import Decimal

import pytest

from scorm_service.runtime_rules import (
    ENTRY, EXIT, KHOA_NOI_BO, LESSON_STATUS, LOCATION, SCORE_MAX, SCORE_RAW,
    SUSPEND_DATA, ap_dung_lo, bat_dau_phien, cmi_cho_sco, rut_cot,
)

DA_XONG = {LESSON_STATUS: "completed", SCORE_RAW: "8", SCORE_MAX: "10", EXIT: "logout"}


def test_lan_dau_la_ab_initio():
    entry, _ = bat_dau_phien(None)
    assert entry == "ab-initio"


def test_muc_tieu_3_suspend_thi_lan_sau_resume_va_giu_location():
    cmi = ap_dung_lo({}, {LOCATION: "trang-5", SUSPEND_DATA: "abc", EXIT: "suspend"}).cmi
    entry, cmi2 = bat_dau_phien(cmi)
    assert entry == "resume"
    tra_ve = cmi_cho_sco(cmi2, entry)
    assert tra_ve[LOCATION] == "trang-5"
    assert tra_ve[SUSPEND_DATA] == "abc"
    assert EXIT not in cmi2


def test_logout_thi_lan_sau_khong_resume():
    cmi = ap_dung_lo({}, {LOCATION: "trang-9", EXIT: "logout"}).cmi
    entry, _ = bat_dau_phien(cmi)
    assert entry == ""


def test_muc_tieu_4_hoan_thanh_ghi_diem_8_tren_10():
    _, cmi = bat_dau_phien(None)
    kq = ap_dung_lo(cmi, DA_XONG)
    cot = rut_cot(kq.cmi)
    assert cot["lesson_status"] == "completed"
    assert cot["score_raw"] == Decimal("8")
    assert cot["score_max"] == Decimal("10")
    assert not kq.loi and not kq.bi_khoa


def test_trong_cung_phien_van_ghi_duoc_diem_sau_khi_dat_completed():
    _, cmi = bat_dau_phien(None)
    cmi = ap_dung_lo(cmi, {LESSON_STATUS: "completed"}).cmi
    kq = ap_dung_lo(cmi, {SCORE_RAW: "8"})
    assert kq.cmi[SCORE_RAW] == "8" and not kq.bi_khoa


def test_muc_tieu_5_mo_lan_hai_giu_nguyen_diem_va_trang_thai():
    _, cmi = bat_dau_phien(None)
    cmi = ap_dung_lo(cmi, DA_XONG).cmi
    _, cmi = bat_dau_phien(cmi)  # mo lan hai
    kq = ap_dung_lo(cmi, {LESSON_STATUS: "incomplete", SCORE_RAW: "2", SCORE_MAX: "10"})
    assert kq.cmi[LESSON_STATUS] == "completed"
    assert kq.cmi[SCORE_RAW] == "8"
    assert set(kq.bi_khoa) == {LESSON_STATUS, SCORE_RAW, SCORE_MAX}


def test_sco_khong_tu_mo_khoa_duoc():
    kq = ap_dung_lo({}, {KHOA_NOI_BO: False})
    assert kq.loi[KHOA_NOI_BO] == "401"


@pytest.mark.parametrize("khoa,gia_tri,ma", [
    (LESSON_STATUS, "xong", "405"),
    (SCORE_RAW, "abc", "405"),
    (SCORE_RAW, "101", "405"),
    (SCORE_RAW, "NaN", "405"),
    (SUSPEND_DATA, "x" * 4097, "405"),
    (LOCATION, 5, "405"),
    (ENTRY, "resume", "403"),
    ("cmi.foo", "1", "401"),
])
def test_gia_tri_khong_hop_le_bi_tu_choi(khoa, gia_tri, ma):
    kq = ap_dung_lo({}, {khoa: gia_tri})
    assert kq.loi[khoa] == ma
    assert khoa not in kq.cmi