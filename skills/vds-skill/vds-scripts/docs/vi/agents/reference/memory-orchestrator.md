<!-- diátaxis: reference -->

# Điều Phối Viên Bộ Nhớ

> Tìm kiếm, lưu trữ và gợi nhớ kiến thức xuyên phiên cũng như các quan sát.

## Phạm vi

- **Thực hiện:** Tìm kiếm ngữ nghĩa trong kho lưu trữ bộ nhớ, lưu trữ quan sát mới, gợi nhớ quyết định trước đó.
- **Không thực hiện:** Thay thế lịch sử git, lưu trữ tệp nhị phân lớn.
- **Người dùng chính:** AI agent (truy xuất ngữ cảnh), người vận hành (khảo cổ quyết định).

## Điểm vào CLI

```bash
# Qua bộ định tuyến thống nhất
vds-cli memory --help

# Điểm vào trực tiếp
vds-cli memory --help
```

## Các Lệnh Chính

| Lệnh | Mục đích | Cờ thường dùng |
|------|----------|----------------|
| `search` | Tìm kiếm ngữ nghĩa | `--limit`, `--tool` |
| `store` | Lưu trữ quan sát | `--tag`, `--priority` |
| `recall` | Gợi nhớ theo ID hoặc thẻ | `--id` |
| `health` | Kiểm tra sức khỏe kho lưu trữ bộ nhớ | — |

## Quy Trình Thường Gặp

### Quy trình: Nghiên Cứu với Gợi Nhớ Bộ Nhớ

1. Tìm kiếm công việc trước đó: `vds-cli memory search "giao thức MCP" --limit 5`
2. Xem xét các quan sát đã lưu trữ
3. Lưu trữ phát hiện mới: `vds-cli memory store --tag "mcp-research-2026"`
4. Đối chiếu với nhiệm vụ hiện tại

## Liên Quan

- **Điều phối viên:** [research](research-orchestrator.md), [audit](audit-triage-playbook.md)
- **Skill:** [memory-orchestrator-skill](../../../../vds-skills/skills/memory-orchestrator-skill/SKILL.md)
- **Confluence:** [WHO Memory](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
