import zipfile
from pathlib import Path

import pytest

from scorm_service.importer import PackageRejected, import_package

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