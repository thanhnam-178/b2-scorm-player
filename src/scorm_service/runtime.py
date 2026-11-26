
"""Xu ly SCORM Runtime CMI cho SCORM 1.2 va SCORM 2004."""

import math

from fastapi import HTTPException

SCORM_12 = "1.2"
SCORM_2004 = "2004"

# Cac trang thai hop le theo tung chuan.
SCORM_12_LESSON_STATUS = {
    "passed",
    "completed",
    "failed",
    "incomplete",
    "browsed",
    "not attempted",
}

SCORM_2004_COMPLETION_STATUS = {
    "completed",
    "incomplete",
    "not attempted",
    "unknown",
}

SCORM_2004_SUCCESS_STATUS = {
    "passed",
    "failed",
    "unknown",
}

SCORM_SCORE_FIELDS = {
    SCORM_12: {
        "cmi.core.score.raw",
        "cmi.core.score.min",
        "cmi.core.score.max",
    },
    SCORM_2004: {
        "cmi.score.raw",
        "cmi.score.min",
        "cmi.score.max",
        "cmi.score.scaled",
    },
}

def chuan_hoa_phien_ban(scorm_version: str) -> str:
    """Chuan hoa phien ban SCORM."""
    if scorm_version == SCORM_12:
        return SCORM_12

    if scorm_version == SCORM_2004:
        return SCORM_2004

    raise HTTPException(
        status_code=409,
        detail="Phien ban SCORM khong duoc ho tro",
    )

def tao_cmi_mac_dinh(version: str) -> dict[str, str]:
    """Tao CMI mac dinh theo phien ban SCORM."""
    version = chuan_hoa_phien_ban(version)

    if version == SCORM_12:
        return {
            "cmi.core.lesson_status": "not attempted",
        }

    return {
        "cmi.completion_status": "not attempted",
        "cmi.success_status": "unknown",
    }

def kiem_tra_gia_tri_cmi(
    scorm_version: str,
    ten_truong: str,
    gia_tri: object,
) -> None:
    """Kiem tra mot gia tri CMI theo phien ban SCORM."""
    version = chuan_hoa_phien_ban(scorm_version)

    if not isinstance(gia_tri, str):
        raise HTTPException(
            status_code=400,
            detail="Gia tri CMI phai la chuoi",
        )

    if ten_truong in SCORM_SCORE_FIELDS[version]:
        try:
            diem = float(gia_tri)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Gia tri diem so phai la so",
            ) from exc

        if not math.isfinite(diem):
            raise HTTPException(
                status_code=400,
                detail="Gia tri diem so khong hop le",
            )

        if (
            ten_truong == "cmi.score.scaled"
            and not -1 <= diem <= 1
        ):
            raise HTTPException(
                status_code=400,
                detail="score.scaled phai nam trong khoang -1 den 1",
            )

        return

    if version == SCORM_12 and ten_truong == "cmi.core.lesson_status":
        if gia_tri not in SCORM_12_LESSON_STATUS:
            raise HTTPException(
                status_code=400,
                detail="lesson_status khong hop le theo SCORM 1.2",
            )
        return

    if version == SCORM_2004:
        if ten_truong == "cmi.completion_status":
            if gia_tri not in SCORM_2004_COMPLETION_STATUS:
                raise HTTPException(
                    status_code=400,
                    detail="completion_status khong hop le theo SCORM 2004",
                )
            return

        if ten_truong == "cmi.success_status":
            if gia_tri not in SCORM_2004_SUCCESS_STATUS:
                raise HTTPException(
                    status_code=400,
                    detail="success_status khong hop le theo SCORM 2004",
                )
            return

    raise HTTPException(
        status_code=400,
        detail="Truong CMI khong duoc ho tro",
    )


def cap_nhat_cmi(
    scorm_version: str,
    cmi_data: dict,
    ten_truong: str,
    gia_tri: object,
) -> dict:
    """Cap nhat mot truong CMI sau khi kiem tra."""
    if not isinstance(cmi_data, dict):
        raise HTTPException(
            status_code=500,
            detail="Du lieu CMI trong database khong hop le",
        )

    kiem_tra_gia_tri_cmi(
        scorm_version,
        ten_truong,
        gia_tri,
    )

    du_lieu_moi = dict(cmi_data)
    du_lieu_moi[ten_truong] = gia_tri

    return du_lieu_moi

def kiem_tra_khoang_diem(
    scorm_version: str,
    cmi_data: dict,
) -> None:
    """Kiem tra diem raw nam trong khoang min va max."""
    version = chuan_hoa_phien_ban(scorm_version)

    if not isinstance(cmi_data, dict):
        raise HTTPException(
            status_code=500,
            detail="Du lieu CMI trong database khong hop le",
        )

    tien_to = (
        "cmi.core.score."
        if version == SCORM_12
        else "cmi.score."
    )

    def doc_diem(ten_truong: str) -> float | None:
        gia_tri = cmi_data.get(ten_truong)

        if gia_tri is None:
            return None

        if not isinstance(gia_tri, str):
            raise HTTPException(
                status_code=500,
                detail="Du lieu diem so trong database khong hop le",
            )

        try:
            diem = float(gia_tri)
        except ValueError as exc:
            raise HTTPException(
                status_code=500,
                detail="Du lieu diem so trong database khong hop le",
            ) from exc

        if not math.isfinite(diem):
            raise HTTPException(
                status_code=500,
                detail="Du lieu diem so trong database khong hop le",
            )

        return diem

    raw = doc_diem(f"{tien_to}raw")
    minimum = doc_diem(f"{tien_to}min")
    maximum = doc_diem(f"{tien_to}max")

    if (
        minimum is not None
        and maximum is not None
        and minimum > maximum
    ):
        raise HTTPException(
            status_code=400,
            detail="Diem min khong duoc lon hon diem max",
        )

    if raw is None:
        return

    if minimum is not None and raw < minimum:
        raise HTTPException(
            status_code=400,
            detail="Diem raw khong duoc nho hon diem min",
        )

    if maximum is not None and raw > maximum:
        raise HTTPException(
            status_code=400,
            detail="Diem raw khong duoc lon hon diem max",
        )

def tong_hop_trang_thai_attempt(
    scorm_version: str,
    danh_sach_cmi: list[dict],
) -> str:
    """Tong hop trang thai Attempt tu CMI cua tat ca SCO."""
    version = chuan_hoa_phien_ban(scorm_version)

    if not danh_sach_cmi:
        return "in_progress"

    ket_qua = []

    for cmi_data in danh_sach_cmi:
        if not isinstance(cmi_data, dict):
            raise HTTPException(
                status_code=500,
                detail="Du lieu CMI trong database khong hop le",
            )

        if version == SCORM_12:
            status = cmi_data.get("cmi.core.lesson_status")

            if status in {"passed", "failed", "completed"}:
                ket_qua.append(status)
            else:
                return "in_progress"

        else:
            completion = cmi_data.get("cmi.completion_status")

            if completion != "completed":
                return "in_progress"

            success = cmi_data.get("cmi.success_status")

            if success in {"passed", "failed"}:
                ket_qua.append(success)
            else:
                ket_qua.append("completed")

    if "failed" in ket_qua:
        return "failed"

    if all(status == "passed" for status in ket_qua):
        return "passed"

    return "completed"

def tong_hop_diem_attempt(
    scorm_version: str,
    danh_sach_cmi: list[dict],
) -> tuple[float, float, float] | None:
    """Tong hop diem cac SCO ve thang 0-100 bang trung binh cong."""
    version = chuan_hoa_phien_ban(scorm_version)

    if not isinstance(danh_sach_cmi, list):
        raise HTTPException(
            status_code=500,
            detail="Danh sach CMI khong hop le",
        )

    if not danh_sach_cmi:
        return None

    tien_to = (
        "cmi.core.score."
        if version == SCORM_12
        else "cmi.score."
    )

    danh_sach_diem = []

    for cmi_data in danh_sach_cmi:
        kiem_tra_khoang_diem(version, cmi_data)

        raw = cmi_data.get(tien_to + "raw")
        minimum = cmi_data.get(tien_to + "min")
        maximum = cmi_data.get(tien_to + "max")

        diem_phan_tram = None

        if (
            raw is not None
            and minimum is not None
            and maximum is not None
        ):
            raw_num = float(raw)
            min_num = float(minimum)
            max_num = float(maximum)

            if max_num > min_num:
                diem_phan_tram = (
                    (raw_num - min_num)
                    / (max_num - min_num)
                    * 100
                )

        if (
            diem_phan_tram is None
            and version == SCORM_2004
        ):
            scaled = cmi_data.get("cmi.score.scaled")

            if scaled is not None:
                kiem_tra_gia_tri_cmi(
                    version,
                    "cmi.score.scaled",
                    scaled,
                )
                diem_phan_tram = float(scaled) * 100

        if diem_phan_tram is None:
            return None

        danh_sach_diem.append(diem_phan_tram)

    diem_trung_binh = round(
        sum(danh_sach_diem) / len(danh_sach_diem),
        2,
    )

    return diem_trung_binh, 0.0, 100.0