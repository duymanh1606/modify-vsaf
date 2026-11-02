<!-- diátaxis: how-to -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo từ tài liệu gốc tiếng Anh tại [`../../../../agents/how-to/orchestrator-workflows/confluence-bitbucket-sync-workflow.md`](../../../../agents/how-to/orchestrator-workflows/confluence-bitbucket-sync-workflow.md).
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải được con người dịch trước khi được coi là tài liệu chính thức. Một biên dịch viên con người phải rà soát, chỉnh sửa thành ngữ và thuật ngữ kỹ thuật, đồng thời gỡ bỏ biểu ngữ này trước khi tệp trở nên có hiệu lực.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../../TRANSLATION-BACKLOG.md) (độ sâu đường dẫn có thể khác — điều chỉnh nếu cần)

# Quy trình đồng bộ Confluence → Bitbucket

> Kiểm định tình trạng tài liệu, đẩy lên Confluence và xác minh liên kết Bitbucket trong một luồng duy nhất.

## Điều kiện tiên quyết

- `vds-scripts` đã được clone và khởi tạo (`./scripts/worktree_uv.sh sync`)
- `vds-cli doctor` thành công
- `~/.vds/.env` chứa `VDS_USERNAME`, `VDS_PASSWORD`, `CONFLUENCE_HOST`
- Đã biết slug dự án Bitbucket và repo mục tiêu

## Tổng quan quy trình

```
docs validate (kiểm tra tình trạng)
    ↓
confluence sync (đẩy các trang)
    ↓
bitbucket verify (kiểm tra liên kết)
```

## Bước 1: Kiểm định tình trạng tài liệu

Chạy công cụ kiểm định tài liệu để kiểm tra header diátaxis, tính toàn vẹn liên kết và cấu trúc.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli docs validate --check-diataxis --check-links
```

Kết quả mong đợi:

```
[docs] Scanning: docs/agents/
[docs] Files checked: 42
[docs] Diátaxis headers: 42/42 PASS
[docs] Broken links: 0
[docs] Warnings: 2 (orphaned images)
[docs] Result: PASS
```

Chạy kiểm tra nghiêm ngặt hơn trước CI:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli docs validate --check-diataxis --check-links --fail-on-warning
```

## Bước 2: Đồng bộ lên Confluence

Đẩy tài liệu đã được kiểm định lên không gian Confluence.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli confluence sync --source docs/agents/how-to/ --space WHO --parent-page 88722450
```

Kết quả mong đợi:

```
[confluence] Connected: https://confluence.digital.vn
[confluence] Pages to sync: 12
[confluence] Created: 3
[confluence] Updated: 9
[confluence] Unchanged: 0
[confluence] Errors: 0
[confluence] Sync complete
```

Đồng bộ một hướng dẫn duy nhất với tiêu đề chỉ định rõ:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli confluence sync --source docs/agents/how-to/first-audit-run.md \
  --space WHO --parent-page 88722450 --title "First Audit Run"
```

## Bước 3: Xác minh liên kết Bitbucket

Sau khi các trang Confluence đã hoạt động, xác minh rằng các liên kết repo Bitbucket phân giải đúng.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli bitbucket verify-links --project vds-scripts --check-confluence-refs
```

Kết quả mong đợi:

```
[bitbucket] Repos scanned: 1
[bitbucket] README links: 14
[bitbucket] Confluence refs: 6
[bitbucket] Broken: 0
[bitbucket] Result: PASS
```

## Tích hợp CI

Thêm job sau vào `.github/workflows/docs-sync.yml`:

```yaml
  docs-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate docs
        run: |
          ./scripts/worktree_uv.sh run --project vds_cli \
            vds-cli docs validate --check-diataxis --check-links --fail-on-warning
      - name: Sync to Confluence
        run: |
          ./scripts/worktree_uv.sh run --project vds_cli \
            vds-cli confluence sync --source docs/agents/ --space WHO --parent-page ${{ vars.CONFLUENCE_PARENT_PAGE }}
      - name: Verify Bitbucket links
        run: |
          ./scripts/worktree_uv.sh run --project vds_cli \
            vds-cli bitbucket verify-links --project vds-scripts --check-confluence-refs
```

## Xử lý sự cố

| Triệu chứng | Nguyên nhân | Khắc phục |
|---------|-------|-----|
| `docs validate` thất bại với diátaxis | Thiếu header `<!-- diátaxis: how-to -->` | Thêm header vào tệp vi phạm và chạy lại |
| `confluence sync` lỗi xác thực | Thiếu hoặc hết hạn thông tin đăng nhập | Kiểm tra `~/.vds/.env` đối với `VDS_USERNAME` và `VDS_PASSWORD` |
| `confluence sync` xung đột trang | Trùng tiêu đề trang trong không gian | Dùng ghi đè `--title` hoặc xóa trang trùng thủ công |
| `bitbucket verify-links` phát hiện tham chiếu hỏng | ID trang Confluence đã thay đổi | Cập nhật các ID trang đang hardcode trong README hoặc tài liệu |
| Đồng bộ chậm | Các tệp đính kèm ảnh kích thước lớn | Thêm `--skip-attachments` cho đồng bộ chỉ văn bản |
