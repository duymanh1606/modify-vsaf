<!-- diátaxis: reference -->

# Điều Phối Viên Elasticsearch

> Thao tác Elasticsearch qua Kibana proxy.

## Phạm vi

- **Thực hiện:** Truy vấn ES indices, kiểm tra mappings, chạy aggregations.
- **Không thực hiện:** Quản lý cluster topology, thay thế Kibana UI.
- **Người dùng chính:** AI agent (phân tích log), operator.

## Điểm vào CLI

```bash
vds-cli elastic --help
vds-cli elastic --help
```

## Các Lệnh Chính

| Lệnh | Mục đích |
|---------|---------|
| `query` | Chạy ES query |
| `mapping` | Kiểm tra index mapping |
| `aggregate` | Chạy aggregation |

## Liên Quan

- **Điều phối viên:** [grafana](grafana-orchestrator.md), [db-query](db-query-orchestrator.md)
