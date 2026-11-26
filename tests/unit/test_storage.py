
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from scorm_service import storage


@pytest.fixture
def thu_muc_mau(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "style.css").write_text("body {}", encoding="utf-8")
    return tmp_path


def test_upload_dir_thanh_cong(monkeypatch, thu_muc_mau):
    s3 = MagicMock()

    monkeypatch.setattr(storage, "_client", lambda: s3)
    monkeypatch.setenv("S3_BUCKET", "scorm-test")

    so_tep = storage.upload_dir(thu_muc_mau, "goi-test/v1")

    assert so_tep == 2
    assert s3.upload_file.call_count == 2

    cac_key = {
        call.args[2]
        for call in s3.upload_file.call_args_list
    }
    assert cac_key == {
        "goi-test/v1/index.html",
        "goi-test/v1/style.css",
    }


def test_upload_dir_that_bai_don_object_da_tai(
    monkeypatch,
    thu_muc_mau,
):
    s3 = MagicMock()
    loi_upload = RuntimeError("MinIO upload failed")

    s3.upload_file.side_effect = [
        None,
        loi_upload,
    ]

    monkeypatch.setattr(storage, "_client", lambda: s3)
    monkeypatch.setenv("S3_BUCKET", "scorm-test")

    with pytest.raises(RuntimeError, match="MinIO upload failed"):
        storage.upload_dir(thu_muc_mau, "goi-test/v1")

    # Sau khi lỗi, phải yêu cầu xóa object đã upload thành công.
    s3.delete_objects.assert_called_once()

    args = s3.delete_objects.call_args.kwargs
    assert args["Bucket"] == "scorm-test"

    keys = {
        item["Key"]
        for item in args["Delete"]["Objects"]
    }
    assert len(keys) == 1
    assert next(iter(keys)) in {
        "goi-test/v1/index.html",
        "goi-test/v1/style.css",
    }

def test_upload_that_bai_va_don_dep_cung_that_bai(
    monkeypatch,
    thu_muc_mau,
):
    s3 = MagicMock()
    loi_upload = RuntimeError("MinIO upload failed")

    s3.upload_file.side_effect = [
        None,
        loi_upload,
    ]
    s3.delete_objects.side_effect = ClientError(
        {
            "Error": {
                "Code": "InternalError",
                "Message": "MinIO cleanup failed",
            }
        },
        "DeleteObjects",
    )

    monkeypatch.setattr(storage, "_client", lambda: s3)
    monkeypatch.setenv("S3_BUCKET", "scorm-test")

    with pytest.raises(RuntimeError, match="MinIO upload failed"):
        storage.upload_dir(thu_muc_mau, "goi-test/v1")

    s3.delete_objects.assert_called_once()

def test_next_version_khi_chua_co_phien_ban(
    monkeypatch,
):
    s3 = MagicMock()
    paginator = MagicMock()

    paginator.paginate.return_value = [
        {"CommonPrefixes": []}
    ]
    s3.get_paginator.return_value = paginator

    monkeypatch.setattr(storage, "_client", lambda: s3)
    monkeypatch.setenv("S3_BUCKET", "scorm-test")

    ket_qua = storage.next_version("goi-test")

    assert ket_qua == 1
    s3.get_paginator.assert_called_once_with("list_objects_v2")
    paginator.paginate.assert_called_once_with(
        Bucket="scorm-test",
        Prefix="goi-test/",
        Delimiter="/",
    )


def test_next_version_tang_tu_phien_ban_lon_nhat(
    monkeypatch,
):
    s3 = MagicMock()
    paginator = MagicMock()

    paginator.paginate.return_value = [
        {
            "CommonPrefixes": [
                {"Prefix": "goi-test/v1/"},
                {"Prefix": "goi-test/v2/"},
                {"Prefix": "goi-test/v5/"},
            ]
        }
    ]
    s3.get_paginator.return_value = paginator

    monkeypatch.setattr(storage, "_client", lambda: s3)
    monkeypatch.setenv("S3_BUCKET", "scorm-test")

    ket_qua = storage.next_version("goi-test")

    assert ket_qua == 6


def test_next_version_bo_qua_ten_thu_muc_khong_hop_le(
    monkeypatch,
):
    s3 = MagicMock()
    paginator = MagicMock()

    paginator.paginate.return_value = [
        {
            "CommonPrefixes": [
                {"Prefix": "goi-test/v2/"},
                {"Prefix": "goi-test/vabc/"},
                {"Prefix": "goi-test/latest/"},
                {"Prefix": "goi-test/v10beta/"},
            ]
        }
    ]
    s3.get_paginator.return_value = paginator

    monkeypatch.setattr(storage, "_client", lambda: s3)
    monkeypatch.setenv("S3_BUCKET", "scorm-test")

    ket_qua = storage.next_version("goi-test")

    assert ket_qua == 3


def test_upload_dir_upload_file_trong_thu_muc_con(
    monkeypatch,
    thu_muc_mau,
):
    (thu_muc_mau / "subfolder").mkdir()
    (thu_muc_mau / "subfolder" / "nested.html").write_text(
        "<html>nested</html>",
        encoding="utf-8",
    )

    s3 = MagicMock()

    monkeypatch.setattr(storage, "_client", lambda: s3)
    monkeypatch.setenv("S3_BUCKET", "scorm-test")

    so_tep = storage.upload_dir(thu_muc_mau, "goi-test/v1")

    assert so_tep == 3
    assert s3.upload_file.call_count == 3

    cac_key = {
        call.args[2]
        for call in s3.upload_file.call_args_list
    }

    assert cac_key == {
        "goi-test/v1/index.html",
        "goi-test/v1/style.css",
        "goi-test/v1/subfolder/nested.html",
    }


def test_client_khoi_tao_s3_dung_cau_hinh(monkeypatch):
    s3_gia = MagicMock()
    thong_tin = {}

    def fake_boto3_client(service_name, **kwargs):
        thong_tin["service_name"] = service_name
        thong_tin.update(kwargs)
        return s3_gia

    monkeypatch.setattr(
        storage.boto3,
        "client",
        fake_boto3_client,
    )
    monkeypatch.setenv("S3_ENDPOINT", "http://minio-test:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "test-access")
    monkeypatch.setenv("S3_SECRET_KEY", "test-secret")

    ket_qua = storage._client()

    assert ket_qua is s3_gia
    assert thong_tin["service_name"] == "s3"
    assert thong_tin["endpoint_url"] == "http://minio-test:9000"
    assert thong_tin["aws_access_key_id"] == "test-access"
    assert thong_tin["aws_secret_access_key"] == "test-secret"
    assert thong_tin["region_name"] == "us-east-1"
    assert isinstance(thong_tin["config"], storage.Config)


def test_get_object_thanh_cong(monkeypatch):
    s3 = MagicMock()
    phan_hoi = {
        "Body": MagicMock(),
        "ContentType": "text/html",
    }
    s3.get_object.return_value = phan_hoi

    monkeypatch.setattr(storage, "_client", lambda: s3)
    monkeypatch.setenv("S3_BUCKET", "scorm")

    ket_qua = storage.get_object("INT1234/v1/index.html")

    assert ket_qua is phan_hoi
    s3.get_object.assert_called_once_with(
        Bucket="scorm",
        Key="INT1234/v1/index.html",
    )