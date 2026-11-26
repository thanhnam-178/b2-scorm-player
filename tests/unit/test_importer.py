import zipfile
from pathlib import Path

import pytest

from scorm_service.importer import (
    PackageRejected,
    import_package,
    parse_manifest,
    validate_manifest_href,
)

GOI_MAU = Path(__file__).parents[1] / "fixtures" / "INT1234-demo-scorm12.zip"

MANIFEST_HOP_LE = """<?xml version="1.0"?>
<manifest xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2">
  <metadata><schemaversion>1.2</schemaversion></metadata>
  <resources>
    <resource identifier="res1" type="webcontent"
      adlcp:scormtype="sco" href="index.html"/>
  </resources>
</manifest>"""


def tao_zip(duong_dan, tep):
    with zipfile.ZipFile(duong_dan, "w", zipfile.ZIP_DEFLATED) as z:
        for ten, noi_dung in tep.items():
            z.writestr(ten, noi_dung)
    return duong_dan


def test_goi_hop_le(tmp_path):
    kq = import_package(GOI_MAU, tmp_path / "dich")
    assert kq["scorm_version"] == "1.2"
    assert len(kq["scos"]) >= 1


def test_zip_slip(tmp_path):
    z = tao_zip(tmp_path / "x.zip", {
        "../evil.txt": "x",
        "imsmanifest.xml": MANIFEST_HOP_LE,
    })
    with pytest.raises(PackageRejected, match="Zip Slip"):
        import_package(z, tmp_path / "dich")
    assert not (tmp_path / "evil.txt").exists()


def test_lien_ket_tuong_trung(tmp_path):
    z = tmp_path / "x.zip"
    with zipfile.ZipFile(z, "w") as f:
        info = zipfile.ZipInfo("link.txt")
        info.external_attr = 0o120777 << 16
        f.writestr(info, "/etc/passwd")
    with pytest.raises(PackageRejected, match="link.txt"):
        import_package(z, tmp_path / "dich")


def test_zip_bomb(tmp_path):
    z = tao_zip(tmp_path / "x.zip", {
        "big.txt": "0" * (10 * 1024 * 1024),
        "imsmanifest.xml": MANIFEST_HOP_LE,
    })
    with pytest.raises(PackageRejected, match="zip bomb"):
        import_package(z, tmp_path / "dich")


def test_tep_php_bi_chan(tmp_path):
    z = tao_zip(tmp_path / "x.zip", {
        "shell.php": "<?php echo 1; ?>",
        "imsmanifest.xml": MANIFEST_HOP_LE,
    })
    with pytest.raises(PackageRejected, match="shell.php"):
        import_package(z, tmp_path / "dich")


def test_manifest_xxe(tmp_path):
    manifest = """<?xml version="1.0"?>
<!DOCTYPE manifest [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<manifest><metadata><schemaversion>&xxe;</schemaversion></metadata></manifest>"""
    z = tao_zip(tmp_path / "x.zip", {
        "imsmanifest.xml": manifest,
        "index.html": "<html></html>",
    })
    with pytest.raises(PackageRejected, match="XXE"):
        import_package(z, tmp_path / "dich")


def test_thieu_manifest(tmp_path):
    z = tao_zip(tmp_path / "x.zip", {"index.html": "<html></html>"})
    with pytest.raises(PackageRejected, match="imsmanifest.xml"):
        import_package(z, tmp_path / "dich")


def test_manifest_sai_cau_truc_xml(tmp_path):
    z = tao_zip(tmp_path / "x.zip", {
        "imsmanifest.xml": "<manifest><metadata>",
    })
    with pytest.raises(PackageRejected, match="XML"):
        import_package(z, tmp_path / "dich")


def test_manifest_thieu_resources(tmp_path):
    manifest = """<?xml version="1.0"?>
    <manifest>
      <metadata><schemaversion>1.2</schemaversion></metadata>
      <organizations>
        <organization identifier="ORG1">
          <title>Test</title>
        </organization>
      </organizations>
    </manifest>"""

    z = tao_zip(tmp_path / "x.zip", {
        "imsmanifest.xml": manifest,
    })
    with pytest.raises(PackageRejected, match="resources"):
        import_package(z, tmp_path / "dich")


def test_manifest_thieu_organizations(tmp_path):
    manifest = """<?xml version="1.0"?>
    <manifest>
      <metadata><schemaversion>1.2</schemaversion></metadata>
      <resources>
        <resource identifier="RES1" adlcp:scormtype="sco"
          xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
          href="index.html"/>
      </resources>
    </manifest>"""

    z = tao_zip(tmp_path / "x.zip", {
        "imsmanifest.xml": manifest,
    })
    with pytest.raises(PackageRejected, match="organizations"):
        import_package(z, tmp_path / "dich")


def test_manifest_khong_co_sco_hop_le(tmp_path):
    manifest = """<?xml version="1.0"?>
    <manifest xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2">
      <metadata><schemaversion>1.2</schemaversion></metadata>
      <organizations>
        <organization identifier="ORG1">
          <title>Test</title>
          <item identifier="ITEM1" identifierref="RES1">
            <title>Asset</title>
          </item>
        </organization>
      </organizations>
      <resources>
        <resource identifier="RES1" type="webcontent"
          adlcp:scormtype="asset" href="index.html"/>
      </resources>
    </manifest>"""

    z = tao_zip(tmp_path / "x.zip", {
        "imsmanifest.xml": manifest,
        "index.html": "<html></html>",
    })
    with pytest.raises(PackageRejected, match="SCO"):
        import_package(z, tmp_path / "dich")


def test_manifest_khong_nhan_dien_phien_ban(tmp_path):
    manifest = """<?xml version="1.0"?>
    <manifest>
      <metadata><schemaversion>SCORM 9999</schemaversion></metadata>
    </manifest>"""

    z = tao_zip(tmp_path / "x.zip", {
        "imsmanifest.xml": manifest,
    })
    with pytest.raises(PackageRejected, match="phiên bản SCORM"):
        import_package(z, tmp_path / "dich")


def test_zip_slip_windows(tmp_path):
    z = tao_zip(tmp_path / "x.zip", {
        r"..\..\evil.txt": "x",
        "imsmanifest.xml": MANIFEST_HOP_LE,
    })

    with pytest.raises(PackageRejected, match="Zip Slip"):
        import_package(z, tmp_path / "dich")


def test_duong_dan_tuyet_doi_windows(tmp_path):
    z = tao_zip(tmp_path / "x.zip", {
        r"C:\Windows\Temp\evil.txt": "x",
        "imsmanifest.xml": MANIFEST_HOP_LE,
    })

    with pytest.raises(PackageRejected, match="Zip Slip"):
        import_package(z, tmp_path / "dich")


def test_qua_nhieu_tep(tmp_path):
    tep = {
        "imsmanifest.xml": MANIFEST_HOP_LE,
    }
    tep.update({
        f"file_{i}.txt": "data"
        for i in range(5000)
    })

    z = tao_zip(tmp_path / "x.zip", tep)

    with pytest.raises(PackageRejected, match="Quá nhiều tệp"):
        import_package(z, tmp_path / "dich")


def test_zip_vuot_gioi_han_dung_luong(tmp_path, monkeypatch):
    z = tao_zip(tmp_path / "x.zip", {
        "imsmanifest.xml": MANIFEST_HOP_LE,
    })

    from scorm_service import importer

    monkeypatch.setattr(importer, "MAX_ZIP_BYTES", 10)

    with pytest.raises(PackageRejected, match="vượt giới hạn dung lượng"):
        import_package(z, tmp_path / "dich")


def test_tong_dung_luong_giai_nen_vuot_gioi_han(
    tmp_path, monkeypatch
):
    # Dùng gói SCORM mẫu có manifest hợp lệ
    z = GOI_MAU

    from scorm_service import importer

    monkeypatch.setattr(importer, "MAX_UNZIPPED_BYTES", 10)

    with pytest.raises(
        PackageRejected,
        match="Dung lượng giải nén vượt giới hạn",
    ):
        import_package(z, tmp_path / "dich")


def test_file_khong_phai_zip(tmp_path):
    z = tmp_path / "x.zip"
    z.write_text("Day khong phai file ZIP", encoding="utf-8")

    with pytest.raises(PackageRejected, match="ZIP hợp lệ"):
        import_package(z, tmp_path / "dich")


def test_giai_nen_that_bai_khong_de_lai_file(
    tmp_path, monkeypatch
):
    from scorm_service import importer

    dich = tmp_path / "dich"

    monkeypatch.setattr(
        importer,
        "MAX_UNZIPPED_BYTES",
        10,
    )

    with pytest.raises(
        PackageRejected,
        match="Dung lượng giải nén vượt giới hạn",
    ):
        import_package(GOI_MAU, dich)

    assert not dich.exists() or not any(dich.iterdir())



def test_thu_muc_dich_da_ton_tai_khong_bi_ghi_de(tmp_path):
    dich = tmp_path / "dich"
    dich.mkdir()
    tep_cu = dich / "du_lieu_cu.txt"
    tep_cu.write_text("Du lieu cu", encoding="utf-8")

    with pytest.raises(PackageRejected, match="Thư mục đích đã tồn tại"):
        import_package(GOI_MAU, dich)

    assert tep_cu.read_text(encoding="utf-8") == "Du lieu cu"



def test_manifest_nhan_dien_scorm_2004():
    manifest = b"""<?xml version="1.0"?>
    <manifest xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
      xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3">
      <metadata><schemaversion>2004 4th Edition</schemaversion></metadata>
      <organizations>
        <organization identifier="ORG1">
          <title>Test</title>
          <item identifier="ITEM1" identifierref="RES1">
            <title>Bai hoc</title>
          </item>
        </organization>
      </organizations>
      <resources>
        <resource identifier="RES1" adlcp:scormType="sco"
          href="index.html"/>
      </resources>
    </manifest>"""

    result = parse_manifest(manifest)

    assert result["scorm_version"] == "2004"


def test_resource_thieu_identifier():
    manifest = b"""<?xml version="1.0"?>
    <manifest>
      <metadata><schemaversion>1.2</schemaversion></metadata>
      <resources>
        <resource href="index.html"/>
      </resources>
    </manifest>"""

    with pytest.raises(PackageRejected, match="Resource"):
        parse_manifest(manifest)


def test_manifest_khong_co_organization_hop_le():
    manifest = b"""<?xml version="1.0"?>
    <manifest>
      <metadata><schemaversion>1.2</schemaversion></metadata>
      <organizations/>
      <resources>
        <resource identifier="RES1" href="index.html"/>
      </resources>
    </manifest>"""

    with pytest.raises(PackageRejected, match="organization"):
        parse_manifest(manifest)


def test_duong_dan_resolve_vuot_khoi_staging(
    tmp_path,
    monkeypatch,
):
    from scorm_service import importer

    zip_path = GOI_MAU
    resolve_goc = Path.resolve

    def resolve_gia(path, strict=False):
        if path.parent.name.startswith(".scorm-import-"):
            return tmp_path / "outside.txt"

        return resolve_goc(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", resolve_gia)

    with pytest.raises(PackageRejected, match="Zip Slip"):
        importer.import_package(zip_path, tmp_path / "dich")

    assert not (tmp_path / "dich").exists()


@pytest.mark.parametrize(
    "href",
    [
        "../secret.txt",
        "../../etc/passwd",
        "/etc/passwd",
        r"..\secret.txt",
        r"C:\Windows\win.ini",
        "https://evil.example/payload.html",
        "//evil.example/payload.html",
        "content/../secret.html",
        "content/%2e%2e/secret.html",
        "content/lesson.html?token=abc",
        "content/lesson.html#section",
    ],
)
def test_manifest_href_khong_hop_le(href):
    with pytest.raises(PackageRejected):
        validate_manifest_href(href)


@pytest.mark.parametrize(
    "href",
    [
        "index.html",
        "content/lesson.html",
        "content/module1/lesson.html",
        "media/video.mp4",
    ],
)
def test_manifest_href_hop_le(href):
    assert validate_manifest_href(href) == href