<!-- diátaxis: how-to -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../../agents/how-to/orchestrator-workflows/memory-progress-workflow.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../../TRANSLATION-BACKLOG.md)

# Quy trình Memory → theo dõi tiến độ

> Lưu quan sát vào VDS AI Memory, gọi lại ngữ cảnh trước đó, và sinh báo cáo tiến độ để theo dõi mức hoàn thành phase.

## Điều kiện tiên quyết

- `vds-scripts` đã được clone và khởi tạo (`./scripts/worktree_uv.sh sync`)
- `vds-cli doctor` đạt trạng thái xanh
- `~/.vds/.env` chứa thông tin xác thực backend memory (DSN Postgres hoặc đường dẫn file cục bộ)

## Tổng quan quy trình

```
memory store (lưu quan sát)
    ↓
memory recall (truy hồi ngữ cảnh)
    ↓
progress report (theo dõi mức hoàn thành)
```

## Bước 1: Lưu quan sát vào Memory

Lưu các quan sát quan trọng sau mỗi phiên làm việc để các agent về sau có thể tiếp cận.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli memory store --tag "phase174,spec,fr-3" \
  --content "FR-3 requires multi-step workflow guides combining 2+ orchestrators"
```

Kết quả mong đợi:

```
[memory] Stored observation: obs-20260422-001
[memory] Tags: phase174, spec, fr-3
[memory] Content length: 72 characters
[memory] Timestamp: 2026-04-22T08:00:00Z
```

Lưu nhiều quan sát từ một phiên làm việc gộp:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli memory store --tag "phase174,audit" \
  --content "Audit run completed with 3 violations in hexagonal-compliance rules"
```

## Bước 2: Truy hồi ngữ cảnh trước đó

Trước khi bắt đầu phiên mới, tìm trong memory các công việc liên quan đã thực hiện trước đây.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli memory search "phase174 workflow guides"
```

Kết quả mong đợi:

```
[memory] Query: phase174 workflow guides
[memory] Results: 2
[memory] obs-20260422-001 — phase174, spec, fr-3
[memory] obs-20260422-002 — phase174, audit
[memory] Retrieved in 0.12s
```

Truy hồi với bộ lọc tag để thu hẹp phạm vi:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli memory search "fr-3" --tag spec
```

## Bước 3: Sinh báo cáo tiến độ

Tạo báo cáo tiến độ từ các quan sát đã lưu và trạng thái audit hiện tại.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli progress report --phase 174 --format markdown
```

Kết quả mong đợi:

```
[progress] Phase: 174
[progress] Spec items: 8/12 complete
[progress] Audit violations: 3 open
[progress] Report: /tmp/vds-progress-phase174.md
```

Sinh báo cáo tổng hợp qua nhiều phase:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli progress report --phase 174,175,176 --format json
```

Theo dõi mức hoàn thành phase với tích hợp checklist:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli progress checklist --phase 174 --update-status
```

Kết quả mong đợi:

```
[checklist] Phase: 174
[checklist] Items: 12
[checklist] Completed: 8
[checklist] Blocked: 1
[checklist] Not started: 3
[checklist] State saved to: checklist-progress.state
```

## Mẹo tự động hóa

Thêm vào shell profile hoặc hook của agent để tự lưu sau mỗi lệnh:

```bash
vds_memory_store() {
  local tag="$1"
  local content="$2"
  ./scripts/worktree_uv.sh run --project vds_cli \
    vds-cli memory store --tag "$tag" --content "$content"
}
```

## Xử lý sự cố

| Triệu chứng | Nguyên nhân | Cách khắc phục |
|---------|-------|-----|
| `memory store` lỗi xác thực | Thiếu DSN hoặc thông tin xác thực | Kiểm tra `~/.vds/.env` cho `VDS_MEMORY_DSN` hoặc đường dẫn cục bộ |
| `memory search` trả về rỗng | Không có tag hoặc nội dung khớp | Mở rộng truy vấn hoặc kiểm tra các tag đã lưu bằng `memory list` |
| `progress report` hiển thị dữ liệu cũ | File trạng thái chưa được cập nhật | Chạy `vds-cli progress checklist --update-status` trước |
| `progress checklist` báo mục bị chặn | Thiếu phụ thuộc hoặc nguyên liệu | Kiểm tra cờ `blocked_by_materials` trong trạng thái checklist |
| Thao tác memory chậm | Kho quan sát lớn | Thêm `--limit 50` vào lệnh search hoặc xóa bớt quan sát cũ |
