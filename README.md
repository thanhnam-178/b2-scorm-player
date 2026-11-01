# B2 – Trình phát SCORM 1.2/2004

Dịch vụ trình phát SCORM 1.2/2004 và lưu kết quả học đúng người học (đề tài B2).

- **Giảng viên hướng dẫn:** ThS. Mai Vân Phương Vũ
- **Sinh viên thực hiện:** (Nguyễn Thành Nam, Nguyễn Trường Phúc)

## Công nghệ
- Python 3.12, FastAPI
- PostgreSQL 16
- Docker, Docker Compose
- CI: GitLab CI (lint → test)

## Cách chạy nhanh

**Yêu cầu:** đã cài và mở Docker Desktop.

1. Chạy toàn bộ hệ thống bằng một lệnh:
   ```
   docker compose -f deploy/docker-compose.yml --env-file .env up -d --build
   ```

2. Kiểm tra: mở http://localhost:8004/api/v1/health, kết quả đúng là:
   ```json
   {"status": "ok"}
   ```

3. Tắt hệ thống:
   ```
   docker compose -f deploy/docker-compose.yml down
   ```

## Chạy kiểm thử trên máy
```
pip install -r requirements.txt
ruff check .
mypy src
pytest
```

## Cấu trúc thư mục
| Thư mục / tệp | Nội dung |
|---|---|
| `docs/` | Khảo sát, thiết kế, mô hình đe dọa, báo cáo kiểm thử, ADR |
| `api/openapi.yaml` | Hợp đồng API |
| `src/` | Mã nguồn |
| `tests/` | Kiểm thử (unit, integration, security, load) |
| `deploy/` | Dockerfile, docker-compose.yml |
| `.env.example` | Mẫu biến môi trường (không chứa giá trị thật) |
| `.gitlab-ci.yml` | Pipeline CI |

## Tiến độ
- Tuần 1: kho mã, CI, môi trường Docker, API `/health`.