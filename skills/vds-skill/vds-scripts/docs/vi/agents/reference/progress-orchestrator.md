<!-- diátaxis: reference -->

# Điều Phối Viên Tiến Độ

> Báo cáo và trực quan hóa tiến độ xuyên các giai đoạn và làn audit VDS.

## Phạm vi

- **Thực hiện:** Tạo báo cáo tiến độ, theo dõi chỉ số hoàn thành, trực quan hóa trạng thái giai đoạn.
- **Không thực hiện:** Thực thi audit, sửa đổi trạng thái tác vụ trực tiếp.
- **Người dùng chính:** Người phụ trách (xem xét trạng thái), AI agent (tự báo cáo).

## Điểm vào CLI

```bash
# Qua bộ định tuyến thống nhất
vds-cli progress --help

# Điểm vào trực tiếp
vds-cli progress --help
```

## Các Lệnh Chính

| Lệnh | Mục đích | Cờ thường dùng |
|------|----------|----------------|
| `report` | Tạo báo cáo tiến độ | `--phase`, `--lane` |
| `summary` | Tóm tắt trạng thái một dòng | `--format` |
| `visualize` | Dòng thời gian ASCII hoặc HTML | `--output` |

## Quy Trình Thường Gặp

### Quy trình: Kiểm Tra Tiến Độ Giai Đoạn

1. Chạy `vds-cli progress report --phase 174`
2. Xem xét tỷ lệ phần trăm hoàn thành theo wave
3. Xác định tác vụ bị chặn
4. Xuất cho standup: `vds-cli progress summary --format markdown`

## Liên Quan

- **Điều phối viên:** [tasks](tasks-orchestrator.md), [audit](audit-triage-playbook.md), [spec](spec-orchestrator.md)
- **Confluence:** [WHO Progress](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
