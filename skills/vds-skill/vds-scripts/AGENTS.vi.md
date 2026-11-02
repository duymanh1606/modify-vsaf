# AGENTS.md — Không gian làm việc VDS Scripts

> Không gian làm việc Python tự động hóa cho các điều phối viên và lệnh CLI được định tuyến của VDS.

## Phạm vi

- Repository: `WHO-project/vds-scripts`
- Trách nhiệm chính:
  - Bề mặt lệnh được định tuyến `vds-cli`
  - Các điều phối viên audit/spec/task/progress/research
  - Hợp đồng runtime và môi trường chia sẻ
- Tệp này là hợp đồng vận hành Tier-0 (giữ ngắn gọn). Chi tiết lệnh sâu và giai đoạn nằm trong tài liệu tham khảo.

## Khởi động nhanh

```bash
cd WHO-project/vds-scripts
./scripts/worktree_uv.sh run --project vds_cli vds-cli --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli env status
./scripts/worktree_uv.sh run --project audit_orchestrator vds-audit --help
./scripts/worktree_uv.sh run --project spec_orchestrator vds-spec --help
```

## Quy tắc

- Sử dụng `./scripts/worktree_uv.sh` để thực thi Python an toàn cho worktree.
- Runtime ưu tiên Postgres-first. Không thêm dự phòng filesystem cho trạng thái audit hoặc bằng chứng.
- Sử dụng bề mặt SDK VDS cho các thao tác Confluence/Bitbucket.
- Giữ lịch sử giai đoạn và câu chuyện lệnh dài ở ngoài AGENTS.md.

### Quy tắc kiểm thử

- Các bài kiểm thử phải giả lập tất cả dịch vụ bên ngoài (Confluence, Bitbucket, nhà cung cấp LLM, điểm cuối HTTP).
- Kiểm soát biến môi trường bằng `monkeypatch.setenv` / `delenv`; không đọc thông tin xác thực cục bộ thực.
- Ưu tiên các bài kiểm thử tập trung cho các mô-đun đã thay đổi trong quá trình phát triển; chạy bộ kiểm thử rộng ở cổng merge.

## Điểm vào

- Bộ định tuyến thống nhất:
  - `./scripts/worktree_uv.sh run --project vds_cli vds-cli <service> ...`
- Các nhóm dịch vụ cốt lõi:
  - `vds-cli audit ...`
  - `vds-cli spec ...`
  - `vds-cli tasks ...`
  - `vds-cli progress ...`
  - `vds-cli research ...`
  - `vds-cli memory ...`

## Tìm kiếm & Điều hướng

- Bắt đầu bằng `rg` cho các ký hiệu và chuỗi chính xác.
- Sử dụng `sg` / tìm kiếm cấu trúc để khám phá mẫu mức độ mã.
- Để hiểu phạm vi lớn, ưu tiên graphify/gitnexus trước khi quét tệp rộng.
- Sự thật về giai đoạn và đường cơ sở runtime được duy trì trong tài liệu tham khảo (bên dưới), không nội tuyến ở đây.

## Trí tuệ mã

Repo này được GitNexus lập chỉ mục là **vds-scripts**.

- Trước khi thay đổi ký hiệu, chạy phân tích tác động:
  - `gitnexus_impact({target: "SymbolName", direction: "upstream"})`
- Trước khi commit, chạy phát hiện phạm vi:
  - `gitnexus_detect_changes({scope: "staged"})`
- Đối với các luồng chưa biết, bắt đầu bằng:
  - `gitnexus_query({query: "concept"})`
  - `gitnexus_context({name: "symbol"})`

### Rào cản GitNexus

- Coi kết quả tác động CAO/QUAN TRỌNG là rào cản rủi ro rõ ràng và trình bày chúng trước khi tiếp tục chỉnh sửa.
- Không bao giờ thực hiện đổi tên ký hiệu qua tìm/thay thế thông thường; sử dụng quy trình đổi tên có nhận thức đồ thị.
- Lập chỉ mục lại có chủ đích sau các thay đổi mã quan trọng:
  - `npx gitnexus analyze`
  - `npx gitnexus analyze --embeddings` (khi embeddings đang được sử dụng)

## Tài liệu

- Tài liệu tham khảo lệnh CLI: `docs/agents/reference/cli-commands.md`
- Lưu trữ giai đoạn: `docs/phases/CHANGELOG.md`
- Hợp đồng viết script: `scripts/README.md`
- Bộ định tuyến gốc: `../AGENTS.md`

### Xử lý Symlink

- `CLAUDE.md` trong repo này là symlink → `AGENTS.md`.
- Trên các hệ thống tệp nơi `core.symlinks=false`, trình xác thực báo cáo:
  `CLAUDE.md is not a symlink to AGENTS.md (ERROR)`.
- Khắc phục: bật Git symlinks (`git config --global core.symlinks true`) hoặc clone lại.

## Ngôn ngữ / Language
- [English](./AGENTS.md)
- [Tiếng Việt](./AGENTS.vi.md)
