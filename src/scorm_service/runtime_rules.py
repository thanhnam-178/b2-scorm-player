"""Quy tac trang thai SCO (SCORM 1.2). Ham thuan: khong cham DB, khong cham HTTP."""
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

ENTRY = "cmi.core.entry"
LESSON_STATUS = "cmi.core.lesson_status"
LOCATION = "cmi.core.lesson_location"
EXIT = "cmi.core.exit"
SESSION_TIME = "cmi.core.session_time"
SUSPEND_DATA = "cmi.suspend_data"
SCORE_RAW = "cmi.core.score.raw"
SCORE_MIN = "cmi.core.score.min"
SCORE_MAX = "cmi.core.score.max"

# khoa noi bo cua may chu, SCO khong duoc doc/ghi
KHOA_NOI_BO = "_khoa_ket_qua"

GHI_DUOC = {LESSON_STATUS, LOCATION, EXIT, SESSION_TIME, SUSPEND_DATA,
            SCORE_RAW, SCORE_MIN, SCORE_MAX}
CHI_DOC = {ENTRY, "cmi.core.student_id", "cmi.core.student_name"}
KHOA_DIEM = {SCORE_RAW, SCORE_MIN, SCORE_MAX}

TRANG_THAI_HOP_LE = {"passed", "completed", "failed", "incomplete", "browsed", "not attempted"}
TRANG_THAI_DA_XONG = {"completed", "passed"}
EXIT_HOP_LE = {"time-out", "suspend", "logout", ""}
KHOA_KHI_DA_XONG = {LESSON_STATUS} | KHOA_DIEM
KHOA_EXIT_TRUOC = "_exit_truoc"  # exit cua phien truoc, giu den khi terminate


@dataclass
class KetQuaLo:
    cmi: dict
    loi: dict[str, str] = field(default_factory=dict)  # khoa -> ma loi SCORM 1.2
    bi_khoa: list[str] = field(default_factory=list)   # khoa bi bo qua vi da hoan thanh


def bat_dau_phien(cmi_cu: dict | None) -> tuple[str, dict]:
    """Goi khi SCO Initialize. Tra ve (entry, cmi moi can luu)."""
    cmi = dict(cmi_cu or {})
    cmi.pop(SESSION_TIME, None)
    chua_hoc = not any(k.startswith("cmi.") for k in cmi)
    # exit cua phien truoc: con trong cmi thi lay ra; neu da chuyen vao
    # khoa noi bo (trang bi tai lai) thi lay o do
    exit_truoc = cmi.pop(EXIT) if EXIT in cmi else cmi.get(KHOA_EXIT_TRUOC)
    cmi[KHOA_EXIT_TRUOC] = exit_truoc
    if chua_hoc:
        entry = "ab-initio"
    elif exit_truoc == "suspend":
        entry = "resume"
    else:
        entry = ""
    # chot luc bat dau phien: neu da xong thi phien nay khong duoc doi ket qua
    cmi[KHOA_NOI_BO] = cmi.get(LESSON_STATUS) in TRANG_THAI_DA_XONG
    return entry, cmi


def kiem_tra_gia_tri(khoa: str, gia_tri) -> str | None:
    """Tra ve ma loi SCORM 1.2 hoac None neu hop le."""
    if khoa in CHI_DOC:
        return "403"
    if khoa not in GHI_DUOC:
        return "401"
    if not isinstance(gia_tri, str):
        return "405"
    if khoa == LESSON_STATUS and gia_tri not in TRANG_THAI_HOP_LE:
        return "405"
    if khoa == EXIT and gia_tri not in EXIT_HOP_LE:
        return "405"
    if khoa == LOCATION and len(gia_tri) > 255:
        return "405"
    if khoa == SUSPEND_DATA and len(gia_tri) > 4096:
        return "405"
    if khoa in KHOA_DIEM:
        try: 
            so = Decimal(gia_tri)
        except InvalidOperation:
            return "405"
        if not so.is_finite() or not (0 <= so <= 100):
            return "405"
    return None


def ap_dung_lo(cmi_hien_tai: dict, thay_doi: dict) -> KetQuaLo:
    """Ap mot lo SetValue len cmi. Khong sua doi doi tuong dau vao."""
    cmi = dict(cmi_hien_tai)
    kq = KetQuaLo(cmi=cmi)
    khoa_ket_qua = bool(cmi.get(KHOA_NOI_BO))
    for khoa, gia_tri in thay_doi.items():
        ma = kiem_tra_gia_tri(khoa, gia_tri)
        if ma:
            kq.loi[khoa] = ma
            continue
        if khoa_ket_qua and khoa in KHOA_KHI_DA_XONG:
            kq.bi_khoa.append(khoa)
            continue
        cmi[khoa] = gia_tri
    return kq


def _so(cmi: dict, khoa: str) -> Decimal | None:
    v = cmi.get(khoa)
    return Decimal(v) if v not in (None, "") else None


def rut_cot(cmi: dict) -> dict:
    """Rut cac gia tri can luu thanh cot rieng trong sco_states."""
    return {
        "lesson_status": cmi.get(LESSON_STATUS, "not attempted"),
        "score_raw": _so(cmi, SCORE_RAW),
        "score_min": _so(cmi, SCORE_MIN),
        "score_max": _so(cmi, SCORE_MAX),
    }


def cmi_cho_sco(cmi: dict, entry: str) -> dict:
    """Gia tri tra cho SCO khi GetValue (bo khoa noi bo va cac khoa chi ghi)."""
    ra = {k: v for k, v in cmi.items() if k in GHI_DUOC and k not in (EXIT, SESSION_TIME)}
    ra.setdefault(LESSON_STATUS, "not attempted")
    ra[ENTRY] = entry
    return ra