---
diátaxis: how-to
audience: human
complexity: basic
last_updated: 2026-04-30
phase_ref: 180
language: vi
---

# Hướng dẫn Giải quyết Sự cố

## Các lỗi phổ biến

| Vấn đề | Kiểm tra | Giải quyết |
|---------|----------|-------------|
| Python không mở | `which python3` | Cài Python 3.14+ với uv |
| `uv` không tìm thấy | `which uv` | `uv self update` hoặc cài lại |
| Postgres không khởi động | `docker compose ps` | `docker compose up -d` |

## Vấn đề xưổng chóp

```bash
# Khởi động tất cả dịch vụ
docker compose up -d

# Kiểm tra trạng thái của mọi dịch vụ
docker compose ps

# Xem log
docker compose logs postgres
```

## Xem thêm

- Tiếng Anh: [troubleshooting-guide.md](../../agents/how-to/troubleshooting-guide.md)
- [Hệ sinh thái WHO](../../explanation/who-ecosystem-introduction.md)
