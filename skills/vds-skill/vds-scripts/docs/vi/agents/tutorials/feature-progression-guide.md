---
diátaxis: tutorial
audience: human
complexity: basic
last_updated: 2026-04-30
phase_ref: 180
language: vi
---

# Hướng dẫn Tiến bộ Tính năng

Tiếp tục hành trình khám phá hệ sinh thái WHO sau khi hoàn thành [Hướng dẫn Zero-to-Productive Developer](zero-to-productive-developer.md).

## Ngày 8 — Đánh giá đa dự án

Chạy kiểm tra trên nhiều repository chỉ với một lệnh.

```bash
# Đánh giá tất cả dự án trong một phòng ban
vds-cli audit --department INSURANCE --checklist DEP-001

# Đánh giá các repo cụ thể
vds-cli audit --repo repo-a,repo-b,repo-c --checklist PAR-001
```

**Học được:** Cấu hình audit, chọn checklist, diễn giải báo cáo.

## Ngày 9 — Tích hợp Confluence

Tải bằng chứng audit và báo cáo lên Confluence tự động.

```bash
# Đồng bộ bằng chứng sau audit
vds-cli docs confluence-sync --repo my-service

# Tạo báo cáo điểm chất lượng
vds-cli docs quality-score
```

**Học được:** Đích đồng bộ Confluence, định dạng bằng chứng, cấu trúc trang.

## Ngày 10 — Kiểm tra kiến trúc Hexagonal

Xác minh dịch vụ tuân thủ nguyên tắc kiến trúc sạch.

```bash
# Kiểm tra tuân thủ hexagonal
vds-cli hexagonal --repo my-service

# Xem báo cáo ranh giới chi tiết
vds-cli hexagonal --repo my-service --format json
```

**Học được:** Ranh giới port/adapter, hướng phụ thuộc, mẫu vi phạm.

## Ngày 11 — Phát hiện phụ thuộc vòng lặp

Xác định chu trình phụ thuộc có rủi ro giữa các microservice.

```bash
# Phát hiện chu trình trong dự án
vds-cli circular-dependency --project INSURANCE

# Xuất biểu đồ để trực quan hóa
vds-cli circular-dependency --project INSURANCE --format mermaid
```

**Học được:** Danh sách phụ thuộc, phân loại chu trình, chiến lược khắc phục.

## Ngày 12 — Quản lý Git Worktree

Sử dụng worktree để phát triển tính năng song song mà không cần chuyển nhánh.

```bash
# Tạo worktree cho tính năng
vds-cli git worktree-create --branch feature/my-change

# Liệt kê tất cả worktree
vds-cli git worktree-list
```

**Học được:** Vòng đời worktree, sửa chữa, dọn dẹp, luồng đa repo.

## Ngày 13 — Khám phá orchestrator tùy chỉnh

Khám phá các orchestrator nâng cao cho tác vụ chuyên biệt.

```bash
# Nghiên cứu chủ đề kết hợp tìm kiếm local và web
vds-cli research --query "best practices for API pagination"

# Tạo biểu đồ từ code
vds-cli diagrams --repo my-service --format png

# Chuyển đổi định dạng schema
vds-cli schema --input openapi.yaml --output jsonschema
```

**Học được:** Chọn orchestrator, định dạng đầu ra, xâu chuỗi lệnh.

## Ngày 14 — Luồng đa tác nhân

Điều phối các nhóm tác nhân song song cho tác vụ phức tạp.

```bash
# Chạy luồng đa tác nhân
vds-cli multi-agent --workflow spec-to-impl --spec my-spec.md

# Theo dõi tiến độ tác nhân
vds-cli multi-agent --status
```

**Học được:** Định nghĩa luồng, vai trò tác nhân, tổng hợp kết quả.

## Ngoài Ngày 14

- [Đóng góp orchestrator mới](../how-to/contribute-new-orchestrator.md)
- Viết skill tùy chỉnh
- [Khám phá chỉ mục orchestrator đầy đủ](../../reference/orchestrator-index.md)

## Xem thêm

- Tiếng Anh: [feature-progression-guide.md](../../agents/tutorials/feature-progression-guide.md)
- [Hệ sinh thái WHO](../../explanation/who-ecosystem-introduction.md)
