"""Nhập gói SCORM an toàn: src/scorm_service/importer.py"""
import hashlib
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree as ET  # tắt XXE / thực thể ngoài
from defusedxml.common import DefusedXmlException

MAX_ZIP_BYTES = 500 * 1024 * 1024        
MAX_UNZIPPED_BYTES = 1024 * 1024 * 1024  
MAX_FILES = 5000
MAX_RATIO = 100                        
ALLOWED_EXT = {
    ".html", ".htm", ".js", ".css", ".json", ".xml", ".xsd", ".dtd", ".txt",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".mp3", ".mp4", ".webm", ".ogg", ".wav", ".pdf",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
}


class PackageRejected(Exception):
    """Gói bị từ chối; message là lý do cụ thể (FR-02)."""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_manifest(data: bytes) -> dict:
    try:
        root = ET.fromstring(data)
    except DefusedXmlException as e:
        raise PackageRejected(f"Manifest chứa cấu trúc XML bị cấm (XXE): {type(e).__name__}") from e
    except ParseError as e:
        raise PackageRejected(f"Manifest không phải XML hợp lệ: {e}") from e
    raw = ""
    for el in root.iter():
        if _local(el.tag) == "schemaversion":
            raw = (el.text or "").strip()
    if raw == "1.2":
        version = "1.2"
    elif "2004" in raw or "1.3" in raw:
        version = "2004"
    else:
        version = None
    if version is None:
        raise PackageRejected(f"Không nhận diện được phiên bản SCORM (schemaversion='{raw}')")

    scos = []
    for el in root.iter():
        if _local(el.tag) != "resource":
            continue
        attrs = {_local(k).lower(): v for k, v in el.attrib.items()}
        if attrs.get("scormtype", "").lower() == "sco":
            scos.append({"identifier": attrs.get("identifier"), "href": attrs.get("href")})
    if not scos:
        raise PackageRejected("Manifest không có SCO nào (scormtype=sco)")
    return {"scorm_version": version, "schemaversion": raw, "scos": scos}


def import_package(zip_path: str | Path, dest_dir: str | Path) -> dict:
    zip_path, dest_dir = Path(zip_path), Path(dest_dir).resolve()
    if zip_path.stat().st_size > MAX_ZIP_BYTES:
        raise PackageRejected("Gói nén vượt giới hạn dung lượng")

    sha256 = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as e:
        raise PackageRejected("Tệp không phải ZIP hợp lệ") from e

    with zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        if len(infos) > MAX_FILES:
            raise PackageRejected("Quá nhiều tệp trong gói")

        # Kiểm tra toàn bộ trước, chưa ghi gì ra đĩa
        for i in infos:
            p = PurePosixPath(i.filename.replace("\\", "/"))
            if p.is_absolute() or ".." in p.parts:
                raise PackageRejected(f"Zip Slip: {i.filename}")
            if (i.external_attr >> 16) & 0o170000 == 0o120000:
                raise PackageRejected(f"Liên kết tượng trưng: {i.filename}")
            if p.suffix.lower() not in ALLOWED_EXT:
                raise PackageRejected(f"Loại tệp không cho phép: {i.filename}")
            if i.compress_size and i.file_size / i.compress_size > MAX_RATIO:
                raise PackageRejected(f"Tỷ lệ nén bất thường (zip bomb?): {i.filename}")

        if "imsmanifest.xml" not in {i.filename for i in infos}:
            raise PackageRejected("Thiếu imsmanifest.xml ở thư mục gốc")
        manifest = parse_manifest(zf.read("imsmanifest.xml"))

        # Giải nén, đếm byte thực tế (kích thước khai báo có thể bị làm giả)
        total = 0
        for i in infos:
            target = (dest_dir / i.filename).resolve()
            if not target.is_relative_to(dest_dir):
                raise PackageRejected(f"Zip Slip: {i.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(i) as src, open(target, "wb") as out:
                while chunk := src.read(64 * 1024):
                    total += len(chunk)
                    if total > MAX_UNZIPPED_BYTES:
                        raise PackageRejected("Dung lượng giải nén vượt giới hạn")
                    out.write(chunk)

    return {"sha256": sha256, "files": len(infos), **manifest}