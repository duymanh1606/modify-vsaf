<!-- diátaxis: reference -->

# Điều Phối Viên Tiến Hóa

> Vòng lặp tiến hóa hệ sinh thái WHO — quản lý chuyển tiếp phase, theo dõi hoàn thành.

## Phạm vi

- **Thực hiện:** Theo dõi hoàn thành phase, quản lý trạng thái tiến hóa, đề xuất phase tiếp theo, tạo báo cáo tiến hóa.
- **Không thực hiện:** Thực thi tác vụ riêng lẻ, thay thế công cụ quản lý dự án.
- **Người dùng chính:** AI agent (điều phối phase), người phụ trách (lập kế hoạch).

## Điểm vào CLI

```bash
vds-cli evolution --help
vds-cli evolution --help
```

## Các Lệnh Chính

| Lệnh | Mục đích |
|---------|---------|
| `status` | Hiển thị trạng thái tiến hóa |
| `next` | Đề xuất phase tiếp theo |
| `report` | Tạo báo cáo tiến hóa |
| `sync` | Đồng bộ trạng thái |

## Liên Quan

- **Điều phối viên:** [spec](spec-orchestrator.md), [tasks](tasks-orchestrator.md), [progress](progress-orchestrator.md)
