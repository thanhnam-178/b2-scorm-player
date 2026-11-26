"""Nhập gói SCORM an toàn: src/scorm_service/importer.py"""

import hashlib
import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import unquote, urlsplit
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

def validate_manifest_href(href: str) -> str:
    """Kiểm tra href trong SCORM Manifest phải là đường dẫn nội bộ hợp lệ."""
    if not href or not href.strip():
        raise PackageRejected("Manifest chứa href rỗng")

    href = href.strip()

    # Không chấp nhận URL bên ngoài, scheme, query hoặc fragment.
    parsed = urlsplit(href)

    if (
        parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or href.startswith(("/", "\\"))
        or "\\" in href
    ):
        raise PackageRejected(
            f"Manifest chứa đường dẫn không hợp lệ: {href}"
        )

    # Giải mã URL để phát hiện cả dạng mã hóa như %2e%2e.
    decoded = unquote(parsed.path)

    if (
        not decoded
        or decoded.startswith("/")
        or "\\" in decoded
        or "\x00" in decoded
    ):
        raise PackageRejected(
            f"Manifest chứa đường dẫn không hợp lệ: {href}"
        )

    parts = decoded.split("/")

    if any(part in ("", ".", "..") for part in parts):
        raise PackageRejected(
            f"Manifest chứa đường dẫn không hợp lệ: {href}"
        )

    return href

def parse_manifest(data: bytes) -> dict:
    try:
        root = ET.fromstring(data)
    except DefusedXmlException as e:
        raise PackageRejected(
            f"Manifest chứa cấu trúc XML bị cấm (XXE): {type(e).__name__}"
        ) from e
    except ParseError as e:
        raise PackageRejected(f"Manifest không phải XML hợp lệ: {e}") from e

    def children(element, name):
        return [
            child for child in element
            if _local(child.tag) == name
        ]

    def first_child(element, name):
        return next(iter(children(element, name)), None)

    def get_text(element, name):
        child = first_child(element, name)
        return (child.text or "").strip() if child is not None else None

    # 1. Nhận diện phiên bản SCORM
    raw = ""
    for element in root.iter():
        if _local(element.tag) == "schemaversion":
            raw = (element.text or "").strip()
            break

    if raw == "1.2":
        version = "1.2"
    elif "2004" in raw or "1.3" in raw:
        version = "2004"
    else:
        raise PackageRejected(
            f"Không nhận diện được phiên bản SCORM (schemaversion='{raw}')"
        )

    # 2. Đọc resources, phân biệt SCO và Asset
    resources_element = first_child(root, "resources")
    if resources_element is None:
        raise PackageRejected("Manifest thiếu phần resources")

    resources = {}

    for element in children(resources_element, "resource"):
        attrs = {_local(k).lower(): v for k, v in element.attrib.items()}
        identifier = attrs.get("identifier")

        if not identifier:
            raise PackageRejected("Resource thiếu identifier")

        scorm_type = attrs.get("scormtype", "").lower()
        files = [
            validate_manifest_href(file_element.attrib.get("href"))
            for file_element in children(element, "file")
            if (file_element.attrib.get("href") or "").strip()
        ]

        resource_href = attrs.get("href")

        if scorm_type == "sco":
            if not resource_href:
                raise PackageRejected("SCO thiếu href trong Manifest")

            resource_href = validate_manifest_href(resource_href)

        resources[identifier] = {
            "identifier": identifier,
            "href": resource_href,
            "scorm_type": scorm_type,
            "files": files,
        }

    # 3. Đọc organization mặc định
    organizations_element = first_child(root, "organizations")
    if organizations_element is None:
        raise PackageRejected("Manifest thiếu phần organizations")

    organizations = children(organizations_element, "organization")
    default_org = organizations_element.attrib.get("default")

    organization = next(
        (
            org for org in organizations
            if org.attrib.get("identifier") == default_org
        ),
        None,
    )

    if organization is None and organizations:
        organization = organizations[0]

    if organization is None:
        raise PackageRejected("Manifest không có organization hợp lệ")

    organization_info = {
        "identifier": organization.attrib.get("identifier"),
        "title": get_text(organization, "title"),
    }

    # 4. Liên kết item với resource qua identifierref
    scos = []

    def collect_items(parent):
        for item in children(parent, "item"):
            item_identifier = item.attrib.get("identifier")
            resource_identifier = item.attrib.get("identifierref")
            title = get_text(item, "title")

            resource = resources.get(resource_identifier)

            if resource and resource["scorm_type"] == "sco":
                scos.append({
                    **resource,
                    "item_identifier": item_identifier,
                    "title": title,
                })

            collect_items(item)

    collect_items(organization)

    if not scos:
        raise PackageRejected(
            "Organization mặc định không tham chiếu tới SCO nào hợp lệ"
        )

    return {
        "scorm_version": version,
        "schemaversion": raw,
        "manifest_identifier": root.attrib.get("identifier"),
        "organization": organization_info,
        "scos": scos,
    }



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
            wp = PureWindowsPath(i.filename)

            if (
                p.is_absolute()
                or ".." in p.parts
                or wp.is_absolute()
                or bool(wp.drive)
            ):
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

        # Giải nén vào thư mục tạm; chỉ chuyển sang đích khi hoàn tất.
        dest_dir.parent.mkdir(parents=True, exist_ok=True)

        if dest_dir.exists():
            raise PackageRejected("Thư mục đích đã tồn tại")

        with tempfile.TemporaryDirectory(
            dir=dest_dir.parent,
            prefix=".scorm-import-",
        ) as tmp:
            staging_dir = Path(tmp)

            total = 0
            for i in infos:
                target = (staging_dir / i.filename).resolve()
                if not target.is_relative_to(staging_dir.resolve()):
                    raise PackageRejected(f"Zip Slip: {i.filename}")

                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(i) as src, open(target, "wb") as out:
                    while chunk := src.read(64 * 1024):
                        total += len(chunk)
                        if total > MAX_UNZIPPED_BYTES:
                            raise PackageRejected(
                                "Dung lượng giải nén vượt giới hạn"
                            )
                        out.write(chunk)

            staging_dir.rename(dest_dir)

    return {"sha256": sha256, "files": len(infos), **manifest}