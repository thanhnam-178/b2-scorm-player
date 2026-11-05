# B2 – Trình phát SCORM 1.2/2004

Dịch vụ trình phát SCORM 1.2/2004 và lưu kết quả học đúng người học.

- **Đề tài:** B2
- **Giảng viên hướng dẫn:** ThS. Mai Vân Phương Vũ
- **Sinh viên thực hiện:** Nguyễn Thành Nam, Nguyễn Trường Phúc

## 1. Công nghệ sử dụng

- Python 3.12
- FastAPI
- PostgreSQL 16
- Docker, Docker Compose
- Nginx phục vụ nội dung SCORM
- GitLab CI (lint → test)

## 2. Cách chạy hệ thống

### Yêu cầu

- Đã cài đặt và mở Docker Desktop.
- Đã cài Docker Compose.
- Đang ở thư mục gốc của dự án.

### Bước 1: Tạo file môi trường

```powershell
Copy-Item .env.example .env
```

Mở file `.env` và thiết lập mật khẩu PostgreSQL cho biến `DB_PASSWORD`.

### Bước 2: Build Docker image

```powershell
docker buildx build --builder scorm-builder --platform linux/amd64 --load -f deploy/Dockerfile -t b2-scorm-player-test .
```

### Bước 3: Khởi chạy hệ thống

```powershell
docker compose --env-file .env -f deploy/docker-compose.yml up -d
```

### Bước 4: Kiểm tra dịch vụ

**SCORM Service (FastAPI)**

- http://localhost:8004/health
- http://localhost:8004/api/v1/health

Kết quả mong đợi:

```json
{
  "status": "ok"
}
```

**SCORM Content (Nginx)**

Truy cập:

http://localhost:8104/

Nginx phục vụ các tệp trong thư mục `data/packages/`.

### Bước 5: Tắt hệ thống

```powershell
docker compose --env-file .env -f deploy/docker-compose.yml down
```

Lệnh trên không xóa dữ liệu trong các thư mục được lưu trên máy.

## 3. Cổng dịch vụ

| Dịch vụ | Cổng |
|---|---:|
| SCORM Service (FastAPI) | 8004 |
| SCORM Content (Nginx) | 8104 |
| PostgreSQL | 5432 (nội bộ Docker) |

Có thể thay đổi cổng thông qua các biến môi trường trong file `.env`.

## 4. Biến môi trường

| Biến | Mô tả | Giá trị mẫu |
|---|---|---|
| `DB_PASSWORD` | Mật khẩu PostgreSQL | Tự thiết lập |
| `SCORM_SERVICE_PORT` | Cổng truy cập FastAPI | 8004 |
| `SCORM_CONTENT_PORT` | Cổng phục vụ nội dung SCORM | 8104 |

## 5. Chạy kiểm thử trên máy

Cài đặt thư viện:

```powershell
pip install -r requirements.txt
```

Kiểm tra mã nguồn:

```powershell
ruff check .
mypy src
```

Chạy kiểm thử:

```powershell
pytest
```

## 6. Cấu trúc thư mục

| Thư mục / tệp | Nội dung |
|---|---|
| `docs/` | Khảo sát, thiết kế, mô hình đe dọa, báo cáo kiểm thử, ADR |
| `api/openapi.yaml` | Hợp đồng API |
| `src/` | Mã nguồn FastAPI |
| `tests/` | Kiểm thử |
| `deploy/` | Dockerfile, Docker Compose, cấu hình Nginx |
| `data/packages/` | Nội dung các gói SCORM lưu trữ cục bộ |
| `.env.example` | Mẫu biến môi trường |
| `.gitlab-ci.yml` | Cấu hình GitLab CI |

## 7. Tiến độ thực hiện

- Tuần 1: Khởi tạo kho mã nguồn, CI, môi trường Docker, API kiểm tra trạng thái và cấu hình cổng SCORM.
- Các chức năng tiếp theo: Phát triển theo kế hoạch và tài liệu thiết kế của đề tài.