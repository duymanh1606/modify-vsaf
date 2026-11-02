<!-- diátaxis: how-to -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../../agents/how-to/orchestrator-workflows/analytics-pipeline-workflow.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../../TRANSLATION-BACKLOG.md)

# Pipeline phân tích Elasticsearch → Grafana → Metabase

> Kết hợp các orchestrator Elastic, Grafana và Metabase để truy vấn log, dựng biểu đồ và phân phối dashboard phân tích.

## Điều kiện tiên quyết

- `vds-scripts` đã được clone và khởi tạo (`./scripts/worktree_uv.sh sync`)
- `vds-cli doctor` đạt trạng thái xanh cho các profile Elastic, Grafana và Metabase
- `~/.vds/.env` chứa `ELASTIC_HOST`, `GRAFANA_HOST`, `METABASE_HOST`, và các thông tin xác thực tương ứng
- Các index pattern đã được tạo trong Elasticsearch (ví dụ: `vds-logs-*`)

## Tổng quan quy trình

```
Elastic (truy vấn log / xuất dữ liệu)
    ↓
Grafana (trực quan hóa số liệu)
    ↓
Metabase (phân phối dashboard)
```

## Bước 1: Truy vấn log trong Elasticsearch

Chạy tìm kiếm log có mục tiêu để trích xuất dữ liệu phân tích thô.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli elastic search --index "vds-logs-*" \
  --query '{"bool":{"filter":[{"range":{"@timestamp":{"gte":"now-7d"}}},{"term":{"level":"ERROR"}}]}}' \
  --size 5000 --output /tmp/elastic-errors.json
```

Kết quả mong đợi:

```
[elastic] Index: vds-logs-*
[elastic] Hits: 3,421
[elastic] Output: /tmp/elastic-errors.json
[elastic] Duration: 1.2s
```

Tổng hợp lỗi theo dịch vụ để phục vụ bước trực quan hóa tiếp theo:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli elastic aggregate --index "vds-logs-*" \
  --field "service.name" --metric "count" \
  --time-range "now-7d" --output /tmp/error-agg.json
```

Kết quả mong đợi:

```
[elastic] Buckets: 12
[elastic] Top: audit-orchestrator (847)
[elastic] Output: /tmp/error-agg.json
```

## Bước 2: Dựng biểu đồ trong Grafana

Nạp dữ liệu đã tổng hợp vào một datasource Grafana và tạo panel.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli grafana datasource test --name "vds-elastic"
```

Kết quả mong đợi:

```
[grafana] Datasource "vds-cli elastic" status: OK
[grafana] Version: 10.4.1
```

Tạo một dashboard với panel time-series từ truy vấn Elastic:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli grafana dashboard create --title "VDS Error Analytics" \
  --datasource "vds-cli elastic" --panel-type timeseries \
  --query '{"index":"vds-logs-*","body":{"aggs":{"services":{"terms":{"field":"service.name"}}}}}' \
  --folder "VDS Operations"
```

Kết quả mong đợi:

```
[grafana] Dashboard created: /d/vds-error-analytics
[grafana] UID: vds-error-analytics
[grafana] Folder: VDS Operations
```

Sinh link snapshot để chia sẻ:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli grafana snapshot create --dashboard "vds-error-analytics" \
  --name "Error Analytics Snapshot $(date +%Y-%m-%d)"
```

Kết quả mong đợi:

```
[grafana] Snapshot created: https://grafana.example.com/dashboard/snapshot/vds-error-analytics-2026-04-22
```

## Bước 3: Xuất dữ liệu phân tích sang Metabase

Đồng bộ tập dữ liệu đã tổng hợp sang Metabase để phục vụ khai thác tự phục vụ.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli metabase card create --database "vds-analytics" \
  --name "Weekly Error Distribution" --query-file /tmp/error-agg.json
```

Kết quả mong đợi:

```
[metabase] Card created: 2143
[metabase] Database: vds-analytics
[metabase] Visualization: table
```

Thêm card vào dashboard Metabase:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli metabase dashboard add-card --dashboard "VDS Operational Metrics" \
  --card 2143 --col 0 --row 0
```

Kết quả mong đợi:

```
[metabase] Dashboard updated: VDS Operational Metrics
[metabase] Cards: 8
```

Công khai dashboard để truy cập public hoặc để nhúng:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli metabase dashboard publish --dashboard "VDS Operational Metrics" \
  --enable-public-link
```

Kết quả mong đợi:

```
[metabase] Public link enabled
[metabase] URL: https://metabase.example.com/public/dashboard/vds-operational-metrics
```

## Xử lý sự cố

| Triệu chứng | Nguyên nhân | Cách khắc phục |
|---------|-------|-----|
| `elastic search` trả về 0 kết quả | Index pattern không khớp hoặc sai tên trường timestamp | Xác minh index bằng `vds-cli elastic indices list` |
| `grafana datasource test` thất bại | Thiếu thông tin xác thực hoặc bị chặn kết nối ra ngoài | Kiểm tra `GRAFANA_API_KEY` trong `~/.vds/.env` |
| `grafana dashboard create` panel rỗng | JSON truy vấn sai định dạng | Xác thực truy vấn bằng `vds-cli elastic search --dry-run` trước |
| `metabase card create` thất bại | Kết nối database hoặc schema không khớp | Chạy `vds-cli metabase database sync --db "vds-analytics"` |
| Link dashboard trả về 404 | UID hoặc slug thay đổi sau khi đổi tên | Chạy lại `vds-cli grafana dashboard list --search "VDS"` |
