<!-- diátaxis: reference -->

# Điều Phối Viên Grafana

> Thao tác log và metrics Grafana.

## Phạm vi

- **Thực hiện:** Truy vấn log, fetch dashboards, kiểm tra alerts.
- **Không thực hiện:** Quản lý users Grafana, thay thế Grafana UI.
- **Người dùng chính:** AI agent (phân tích log), operator.

## Điểm vào CLI

```bash
vds-cli grafana --help
vds-cli grafana --help
```

## Các Lệnh Chính

| Lệnh | Mục đích |
|---------|---------|
| `logs` | Truy vấn log |
| `dashboard` | Fetch dashboard |
| `alert` | Kiểm tra alerts |

## Liên Quan

- **Điều phối viên:** [elastic](elastic-orchestrator.md), [db-query](db-query-orchestrator.md)
