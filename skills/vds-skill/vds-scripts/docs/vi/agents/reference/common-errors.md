---
diátaxis: reference
audience: both
complexity: basic
last_updated: 2026-04-30
phase_ref: 180
language: vi
---

# Các lỗi Thường gặp

## Lỗi CLI

### `ModuleNotFoundError: no module named 'xxx'`

**Nguyên nhân:** Thư viện chưa được cài đặt hoặc sai môi trường venv.

**Sửa:**
```bash
uv sync
source .venv/bin/activate
```

**Phòng ngừa:** Luôn chạy `uv sync` sau khi pull thay đổi.

### `subprocess.CalledProcessError: uv run ...`

**Nguyên nhân:** Điểm vào orchestrator chưa được cài đặt.

**Sửa:**
```bash
# Cài đặt lại orchestrator
cd <orchestrator_dir> && uv pip install -e .
```

**Phòng ngừa:** Chạy `uv sync` từ thư mục gốc vds-scripts sau mọi thay đổi orchestrator.

## Lỗi Xác thực (Validation)

### `ValidationError: 1 validation error for Settings`

**Nguyên nhân:** Thiếu hoặc sai biến môi trường.

**Sửa:**
```bash
# Kiểm tra các biến bắt buộc
vds-cli env status

# Đặt biến thiếu
export CONFLUENCE_INTERNAL_URL=https://confluence.example.com
```

**Phòng ngừa:** Sử dụng template `~/.vds/.env` có chú thích từ [Tài liệu tham khảo Cấu hình](../reference/configuration-reference.md).

## Lỗi Cơ sở dữ liệu

### `Connection refused: postgres:5432`

**Nguyên nhân:** Container Postgres chưa chạy.

**Sửa:**
```bash
docker compose up -d postgres
```

**Phòng ngừa:** Thêm `docker compose ps` vào danh sách kiểm tra khởi động.

### `sqlalchemy.exc.ProgrammingError: relation "xxx" does not exist`

**Nguyên nhân:** Schema chưa được khởi tạo.

**Sửa:**
```bash
# Chạy migration (nếu có)
vds-cli db-query --run-migrations
```

## Lỗi API Bên ngoài

### `401 Unauthorized: Confluence`

**Nguyên nhân:** Token không hợp lệ hoặc đã hết hạn.

**Sửa:**
```bash
# Tạo token mới trong giao diện Confluence
# Cập nhật ~/.vds/.env
```

**Phòng ngừa:** Đặt lịch nhắc luân chuyển token mỗi 90 ngày.

### `Connection timeout: SonarQube`

**Nguyên nhân:** Không thể kết nối tới máy chủ SonarQube.

**Sửa:**
```bash
# Kiểm tra kết nối
curl -I $SONARQUBE_URL

# Kiểm tra VPN nếu cần
```

## Lỗi Git

### `fatal: not a git repository`

**Nguyên nhân:** Chạy lệnh git bên ngoài repository.

**Sửa:**
```bash
cd /path/to/git/repo
# hoặc
vds-cli git worktree-list
```

### `error: pathspec 'branch-name' did not match`

**Nguyên nhân:** Nhánh không tồn tại.

**Sửa:**
```bash
# Liệt kê các nhánh
git branch -a

# Tạo nhánh
git checkout -b branch-name
```

## Xem thêm

- [Hướng dẫn Khắc phục lỗi](../how-to/troubleshooting-guide.md)
- [Tài liệu tham khảo Cấu hình](../reference/configuration-reference.md)
