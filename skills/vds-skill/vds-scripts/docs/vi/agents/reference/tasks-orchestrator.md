<!-- diátaxis: reference -->

# Điều Phối Viên Tác Vụ

> Quản lý và theo dõi tác vụ xuyên các giai đoạn và gói công việc VDS.

## Phạm vi

- **Thực hiện:** Tạo tác vụ, cập nhật trạng thái, theo dõi hoàn thành, tạo báo cáo tác vụ.
- **Không thực hiện:** Thay thế Jira cho quản lý dự án phức tạp, tự động phân công tác vụ.
- **Người dùng chính:** AI agent (theo dõi tác vụ), người phụ trách (xem xét tiến độ).

## Điểm vào CLI

```bash
# Qua bộ định tuyến thống nhất
vds-cli tasks --help

# Điểm vào trực tiếp
vds-cli tasks --help
```

## Các Lệnh Chính

| Lệnh | Mục đích | Cờ thường dùng |
|------|----------|----------------|
| `list` | Liệt kê tác vụ đang hoạt động | `--phase`, `--status` |
| `create` | Tạo tác vụ mới | `--title`, `--owner` |
| `update` | Cập nhật trạng thái tác vụ | `--id`, `--status` |
| `report` | Tạo báo cáo tác vụ | `--format` |

## Quy Trình Thường Gặp

### Quy trình: Theo Dõi Tác Vụ Giai Đoạn

1. Chạy `vds-cli tasks list --phase 174` để xem tác vụ đang hoạt động
2. Cập nhật trạng thái tác vụ: `vds-cli tasks update --id ORCH-001 --status in_progress`
3. Đánh dấu hoàn thành: `vds-cli tasks update --id ORCH-001 --status completed`
4. Tạo báo cáo: `vds-cli tasks report --phase 174`

## Liên Quan

- **Điều phối viên:** [spec](spec-orchestrator.md), [progress](progress-orchestrator.md), [audit](audit-triage-playbook.md)
- **Skill:** [cli-development-skill](../../../../vds-skills/skills/cli-development-skill/SKILL.md)
- **Confluence:** [WHO Tasks](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
