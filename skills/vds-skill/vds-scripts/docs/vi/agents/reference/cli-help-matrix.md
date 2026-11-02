<!-- diátaxis: reference -->

# Verified CLI help matrix (Tiếng Việt)

Tài liệu tham khảo giúp AI agent và operator chọn đúng entry point VDS CLI.
**`vds-cli` là entry point duy nhất hợp lệ cho ngườI dùng.** Các executable trực tiếp
củA package chỉ là chi tiết triển khai router nội bộ, không được gọI trực tiếp.

## Cách sử dụng ma trận này

1. **Luôn** sử dụng dạng routed `vds-cli <service> <command>` cho mọI thao tác.
2. **Không bao giờ** gọI trực tiếp các executable package (`vds-audit`, `vds-spec`, v.v.) —
   đây là nội bộ của router.
3. Sử dụng `--help` làm bề mặt phát hiện chính thống trước khi giả định tên lệnh.
4. Trong worktree `vds-scripts` riêng, ưu tiên `./scripts/worktree_uv.sh ...`
   cho lệnh `uv` để tránh rò rỉ trạng thái `VIRTUAL_ENV` cha vào worktree sai.

## Routed command families

| Routed family | Dạng `vds-cli` | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| platform | `vds-cli --help` | đã xác minh | Router entrypoint thống nhất |
| audit | `vds-cli audit ...` | đã xác minh | Bề mặt workflow chuyên môn |
| spec | `vds-cli spec ...` | đã xác minh | Tooling vòng đờI spec |
| jira | `vds-cli jira ...` | đã xác minh | |
| confluence | `vds-cli confluence ...` | đã xác minh | |
| bitbucket | `vds-cli bitbucket ...` | đã xác minh | |
| git | `vds-cli git ...` | đã xác minh | |
| elastic | `vds-cli elastic ...` | đã xác minh | |
| sonarqube | `vds-cli sonarqube ...` | đã xác minh | |
| grafana | `vds-cli grafana ...` | đã xác minh | |
| schema | `vds-cli schema ...` | đã xác minh | |
| diagrams | `vds-cli diagrams ...` | đã xác minh | |
| google-sheets | `vds-cli google-sheets ...` | đã xác minh | |
| tasks | `vds-cli tasks ...` | đã xác minh | |
| openapi | `vds-cli openapi ...` | đã xác minh | |
| pdf | `vds-cli pdf ...` | đã xác minh | |
| markdown | `vds-cli markdown ...` | đã xác minh | Dùng `vds-cli markdown format` để format |
| intellij | `vds-cli intellij ...` | đã xác minh | |
| links | `vds-cli links ...` | đã xác minh | |
| structure | `vds-cli structure ...` | đã xác minh | |
| lsp | `vds-cli lsp ...` | đã xác minh | |
| brd | `vds-cli brd ...` | đã xác minh | |
| excel | `vds-cli excel ...` | đã xác minh | |
| circular-dependency | `vds-cli circular-dependency ...` | đã xác minh | |
| progress | `vds-cli progress ...` | đã xác minh | |
| hexagonal | `vds-cli hexagonal ...` | đã xác minh | |
| multi-agent | `vds-cli multi-agent ...` | đã xác minh | |
| public-interface | `vds-cli public-interface ...` | đã xác minh | |
| metabase | `vds-cli metabase ...` | đã xác minh | |
| mcp | `vds-cli mcp ...` | đã xác minh | |
| research | `vds-cli research ...` | đã xác minh | |
| memory | `vds-cli memory ...` | đã xác minh | |

## Ví dụ worktree-safe

> Tất cả ví dụ **phải** dùng `vds-cli` routing — các executable trực tiếp chỉ dùng nội bộ.

- `./scripts/worktree_uv.sh run --project vds_cli vds-cli --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli spec --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli tasks --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli schema --help`

## Ghi chú nguồn

Ma trận này được duy trì từ:

- Xác minh `--help` trực tiếp trong worktree Phase 3
- Tài liệu routed-family từ `vds_cli/README.md`, `cli-commands.md`, và `vds-cli-reference.md`
- Chuẩn chính thức: `vds-cli` là entry point duy nhất cho ngườI dùng
