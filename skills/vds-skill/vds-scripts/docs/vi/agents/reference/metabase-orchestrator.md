<!-- diátaxis: reference -->

# Điều Phối Viên Metabase

> Thao tác analytics và dashboard Metabase.

## Phạm vi

- **Thực hiện:** Truy vấn questions, export kết quả, kiểm tra collections.
- **Không thực hiện:** Tạo dashboards mới, thay thế Metabase UI.
- **Người dùng chính:** AI agent (truy xuất dữ liệu), analyst.

## Điểm vào CLI

```bash
vds-cli metabase --help
vds-cli metabase --help
```

## Các Lệnh Chính

| Lệnh | Mục đích |
|---------|---------|
| `query` | Chạy Metabase question |
| `export` | Export kết quả |
| `collection` | Liệt kê collection |

## Liên Quan

- **Điều phối viên:** [grafana](grafana-orchestrator.md), [db-query](db-query-orchestrator.md)
