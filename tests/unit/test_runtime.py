
import pytest
from fastapi import HTTPException

from scorm_service.runtime import (
    SCORM_12,
    SCORM_2004,
    cap_nhat_cmi,
    chuan_hoa_phien_ban,
    kiem_tra_gia_tri_cmi,
    kiem_tra_khoang_diem,
    tao_cmi_mac_dinh,
    tong_hop_diem_attempt,
    tong_hop_trang_thai_attempt,
)


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("1.2", SCORM_12),
        ("2004", SCORM_2004),
    ],
)
def test_chuan_hoa_phien_ban_hop_le(version, expected):
    assert chuan_hoa_phien_ban(version) == expected


def test_phien_ban_khong_duoc_ho_tro():
    with pytest.raises(HTTPException) as exc:
        chuan_hoa_phien_ban("unknown")

    assert exc.value.status_code == 409


@pytest.mark.parametrize(
    "status",
    [
        "passed",
        "completed",
        "failed",
        "incomplete",
        "browsed",
        "not attempted",
    ],
)
def test_scorm_12_lesson_status_hop_le(status):
    kiem_tra_gia_tri_cmi(
        SCORM_12,
        "cmi.core.lesson_status",
        status,
    )


def test_scorm_12_lesson_status_khong_hop_le():
    with pytest.raises(HTTPException) as exc:
        kiem_tra_gia_tri_cmi(
            SCORM_12,
            "cmi.completion_status",
            "completed",
        )

    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    "status",
    ["completed", "incomplete", "not attempted", "unknown"],
)
def test_scorm_2004_completion_status_hop_le(status):
    kiem_tra_gia_tri_cmi(
        SCORM_2004,
        "cmi.completion_status",
        status,
    )


@pytest.mark.parametrize(
    "status",
    ["passed", "failed", "unknown"],
)
def test_scorm_2004_success_status_hop_le(status):
    kiem_tra_gia_tri_cmi(
        SCORM_2004,
        "cmi.success_status",
        status,
    )


def test_scorm_2004_tu_choi_lesson_status():
    with pytest.raises(HTTPException) as exc:
        kiem_tra_gia_tri_cmi(
            SCORM_2004,
            "cmi.core.lesson_status",
            "completed",
        )

    assert exc.value.status_code == 400


def test_gia_tri_cmi_phai_la_chuoi():
    with pytest.raises(HTTPException) as exc:
        kiem_tra_gia_tri_cmi(
            SCORM_12,
            "cmi.core.lesson_status",
            100,
        )

    assert exc.value.status_code == 400


def test_cap_nhat_cmi_thanh_cong():
    cmi_cu = {
        "cmi.core.lesson_location": "page-1",
    }

    cmi_moi = cap_nhat_cmi(
        SCORM_12,
        cmi_cu,
        "cmi.core.lesson_status",
        "completed",
    )

    assert cmi_moi == {
        "cmi.core.lesson_location": "page-1",
        "cmi.core.lesson_status": "completed",
    }

    # Du lieu ban dau khong bi thay doi.
    assert "cmi.core.lesson_status" not in cmi_cu


def test_cap_nhat_cmi_tu_choi_truong_khong_ho_tro():
    with pytest.raises(HTTPException) as exc:
        cap_nhat_cmi(
            SCORM_12,
            {},
            "cmi.completion_status",
            "completed",
        )

    assert exc.value.status_code == 400


def test_cmi_database_khong_phai_dict():
    with pytest.raises(HTTPException) as exc:
        cap_nhat_cmi(
            SCORM_12,
            [],
            "cmi.core.lesson_status",
            "completed",
        )

    assert exc.value.status_code == 500


@pytest.mark.parametrize(
    ("trang_thai", "expected"),
    [
        ("passed", "passed"),
        ("failed", "failed"),
        ("completed", "completed"),
        ("incomplete", "in_progress"),
        ("browsed", "in_progress"),
        ("not attempted", "in_progress"),
    ],
)
def test_tong_hop_attempt_scorm_12(trang_thai, expected):
    states = [
        {"cmi.core.lesson_status": trang_thai},
    ]

    assert (
        tong_hop_trang_thai_attempt(SCORM_12, states)
        == expected
    )


def test_tong_hop_attempt_scorm_12_nhieu_sco_tat_ca_passed():
    states = [
        {"cmi.core.lesson_status": "passed"},
        {"cmi.core.lesson_status": "passed"},
    ]

    assert (
        tong_hop_trang_thai_attempt(SCORM_12, states)
        == "passed"
    )


def test_tong_hop_attempt_scorm_12_co_sco_failed():
    states = [
        {"cmi.core.lesson_status": "passed"},
        {"cmi.core.lesson_status": "failed"},
    ]

    assert (
        tong_hop_trang_thai_attempt(SCORM_12, states)
        == "failed"
    )


def test_tong_hop_attempt_scorm_12_mot_sco_chua_hoan_thanh():
    states = [
        {"cmi.core.lesson_status": "passed"},
        {"cmi.core.lesson_status": "incomplete"},
    ]

    assert (
        tong_hop_trang_thai_attempt(SCORM_12, states)
        == "in_progress"
    )


def test_tong_hop_attempt_scorm_12_completed_va_passed():
    states = [
        {"cmi.core.lesson_status": "passed"},
        {"cmi.core.lesson_status": "completed"},
    ]

    assert (
        tong_hop_trang_thai_attempt(SCORM_12, states)
        == "completed"
    )


def test_tong_hop_attempt_scorm_2004_passed():
    states = [
        {
            "cmi.completion_status": "completed",
            "cmi.success_status": "passed",
        },
    ]

    assert (
        tong_hop_trang_thai_attempt(SCORM_2004, states)
        == "passed"
    )


def test_tong_hop_attempt_scorm_2004_failed():
    states = [
        {
            "cmi.completion_status": "completed",
            "cmi.success_status": "failed",
        },
    ]

    assert (
        tong_hop_trang_thai_attempt(SCORM_2004, states)
        == "failed"
    )


def test_tong_hop_attempt_scorm_2004_chua_co_success_status():
    states = [
        {
            "cmi.completion_status": "completed",
        },
    ]

    assert (
        tong_hop_trang_thai_attempt(SCORM_2004, states)
        == "completed"
    )


def test_tong_hop_attempt_scorm_2004_chua_hoan_thanh():
    states = [
        {
            "cmi.completion_status": "completed",
            "cmi.success_status": "passed",
        },
        {
            "cmi.completion_status": "incomplete",
            "cmi.success_status": "unknown",
        },
    ]

    assert (
        tong_hop_trang_thai_attempt(SCORM_2004, states)
        == "in_progress"
    )


def test_tong_hop_attempt_khong_co_sco():
    assert (
        tong_hop_trang_thai_attempt(SCORM_12, [])
        == "in_progress"
    )


def test_tong_hop_attempt_cmi_khong_phai_dict():
    with pytest.raises(HTTPException) as exc:
        tong_hop_trang_thai_attempt(
            SCORM_12,
            [{"cmi.core.lesson_status": "passed"}, None],
        )

    assert exc.value.status_code == 500


@pytest.mark.parametrize(
    ("version", "field"),
    [
        (SCORM_12, "cmi.core.score.raw"),
        (SCORM_12, "cmi.core.score.min"),
        (SCORM_12, "cmi.core.score.max"),
        (SCORM_2004, "cmi.score.raw"),
        (SCORM_2004, "cmi.score.min"),
        (SCORM_2004, "cmi.score.max"),
    ],
)
@pytest.mark.parametrize("value", ["8", "8.5", "0", "100"])
def test_diem_so_hop_le(version, field, value):
    kiem_tra_gia_tri_cmi(version, field, value)

@pytest.mark.parametrize(
    "value",
    ["-1", "-0.5", "0", "0.5", "1"],
)
def test_scorm_2004_score_scaled_hop_le(value):
    kiem_tra_gia_tri_cmi(
        SCORM_2004,
        "cmi.score.scaled",
        value,
    )


@pytest.mark.parametrize(
    "value",
    ["-1.01", "1.01", "abc", "NaN", "Infinity"],
)
def test_scorm_2004_score_scaled_khong_hop_le(value):
    with pytest.raises(HTTPException) as exc:
        kiem_tra_gia_tri_cmi(
            SCORM_2004,
            "cmi.score.scaled",
            value,
        )

    assert exc.value.status_code == 400

@pytest.mark.parametrize(
    ("version", "field"),
    [
        (SCORM_12, "cmi.score.raw"),
        (SCORM_2004, "cmi.core.score.raw"),
    ],
)
def test_tu_choi_truong_diem_sai_phien_ban(version, field):
    with pytest.raises(HTTPException) as exc:
        kiem_tra_gia_tri_cmi(version, field, "8")

    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    "value",
    ["abc", "NaN", "Infinity", "-Infinity"],
)
def test_diem_so_khong_hop_le(value):
    with pytest.raises(HTTPException) as exc:
        kiem_tra_gia_tri_cmi(
            SCORM_12,
            "cmi.core.score.raw",
            value,
        )

    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    ("cmi_data", "expected_error"),
    [
        (
            {
                "cmi.core.score.raw": "8",
                "cmi.core.score.min": "0",
                "cmi.core.score.max": "10",
            },
            False,
        ),
        (
            {
                "cmi.core.score.raw": "8",
                "cmi.core.score.min": "9",
                "cmi.core.score.max": "10",
            },
            True,
        ),
        (
            {
                "cmi.core.score.raw": "11",
                "cmi.core.score.min": "0",
                "cmi.core.score.max": "10",
            },
            True,
        ),
        (
            {
                "cmi.core.score.min": "10",
                "cmi.core.score.max": "0",
            },
            True,
        ),
    ],
)
def test_kiem_tra_khoang_diem_scorm_12(
    cmi_data,
    expected_error,
):
    if expected_error:
        with pytest.raises(HTTPException) as exc:
            kiem_tra_khoang_diem(SCORM_12, cmi_data)

        assert exc.value.status_code == 400
    else:
        kiem_tra_khoang_diem(SCORM_12, cmi_data)


def test_kiem_tra_khoang_diem_scorm_2004():
    kiem_tra_khoang_diem(
        SCORM_2004,
        {
            "cmi.score.raw": "8",
            "cmi.score.min": "0",
            "cmi.score.max": "10",
        },
    )
@pytest.mark.parametrize(
    "cmi_data",
    [
        [],
        {"cmi.core.score.raw": 8},
        {"cmi.core.score.raw": "abc"},
        {"cmi.core.score.raw": "NaN"},
        {"cmi.core.score.min": "abc"},
        {"cmi.core.score.max": "Infinity"},
    ],
)
def test_kiem_tra_khoang_diem_du_lieu_cu_khong_hop_le(
    cmi_data,
):
    with pytest.raises(HTTPException) as exc:
        kiem_tra_khoang_diem(SCORM_12, cmi_data)

    assert exc.value.status_code == 500


def test_cap_nhat_cmi_diem_so_giu_nguyen_thang_diem():
    cmi_moi = cap_nhat_cmi(
        SCORM_12,
        {},
        "cmi.core.score.raw",
        "8",
    )

    assert cmi_moi["cmi.core.score.raw"] == "8"


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        (
            SCORM_12,
            {
                "cmi.core.lesson_status": "not attempted",
            },
        ),
        (
            SCORM_2004,
            {
                "cmi.completion_status": "not attempted",
                "cmi.success_status": "unknown",
            },
        ),
    ],
)
def test_tao_cmi_mac_dinh(version, expected):
    assert tao_cmi_mac_dinh(version) == expected


def test_tong_hop_diem_scorm_12_mot_sco():
    result = tong_hop_diem_attempt(
        SCORM_12,
        [
            {
                "cmi.core.score.raw": "8",
                "cmi.core.score.min": "0",
                "cmi.core.score.max": "10",
            },
        ],
    )

    assert result == (80.0, 0.0, 100.0)


def test_tong_hop_diem_scorm_12_nhieu_sco_trung_binh():
    result = tong_hop_diem_attempt(
        SCORM_12,
        [
            {
                "cmi.core.score.raw": "8",
                "cmi.core.score.min": "0",
                "cmi.core.score.max": "10",
            },
            {
                "cmi.core.score.raw": "6",
                "cmi.core.score.min": "0",
                "cmi.core.score.max": "10",
            },
        ],
    )

    assert result == (70.0, 0.0, 100.0)


def test_tong_hop_diem_thieu_mot_sco_tra_none():
    result = tong_hop_diem_attempt(
        SCORM_12,
        [
            {
                "cmi.core.score.raw": "8",
                "cmi.core.score.min": "0",
                "cmi.core.score.max": "10",
            },
            {
                "cmi.core.lesson_status": "completed",
            },
        ],
    )

    assert result is None


def test_tong_hop_diem_scorm_2004_bang_scaled():
    result = tong_hop_diem_attempt(
        SCORM_2004,
        [
            {
                "cmi.score.scaled": "0.85",
            },
        ],
    )

    assert result == (85.0, 0.0, 100.0)


def test_tong_hop_diem_scorm_2004_nhieu_sco():
    result = tong_hop_diem_attempt(
        SCORM_2004,
        [
            {
                "cmi.score.raw": "8",
                "cmi.score.min": "0",
                "cmi.score.max": "10",
            },
            {
                "cmi.score.scaled": "0.6",
            },
        ],
    )

    assert result == (70.0, 0.0, 100.0)


def test_tong_hop_diem_thang_diem_khong_co_khoang():
    result = tong_hop_diem_attempt(
        SCORM_12,
        [
            {
                "cmi.core.score.raw": "8",
                "cmi.core.score.min": "8",
                "cmi.core.score.max": "8",
            },
        ],
    )

    assert result is None


def test_tong_hop_diem_khong_co_sco():
    assert tong_hop_diem_attempt(SCORM_12, []) is None