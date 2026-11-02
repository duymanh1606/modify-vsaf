<!-- diátaxis: how-to -->

# Elasticsearch → Grafana → Metabase Analytics Pipeline

> Combine the Elastic, Grafana, and Metabase orchestrators to query logs, build visualizations, and deliver analytics dashboards.

## Prerequisites

- `vds-scripts` cloned and bootstrapped (`./scripts/worktree_uv.sh sync`)
- `vds-cli doctor` passes with Elastic, Grafana, and Metabase profiles green
- `~/.vds/.env` contains `ELASTIC_HOST`, `GRAFANA_HOST`, `METABASE_HOST`, and corresponding credentials
- Index patterns created in Elasticsearch (e.g., `vds-logs-*`)

## Workflow Overview

```
Elastic (query logs/export data)
    ↓
Grafana (visualize metrics)
    ↓
Metabase (deliver dashboards)
```

## Step 1: Query Logs in Elasticsearch

Run a targeted log search to extract raw analytics data.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli elastic search --index "vds-logs-*" \
  --query '{"bool":{"filter":[{"range":{"@timestamp":{"gte":"now-7d"}}},{"term":{"level":"ERROR"}}]}}' \
  --size 5000 --output /tmp/elastic-errors.json
```

Expected output:

```
[elastic] Index: vds-logs-*
[elastic] Hits: 3,421
[elastic] Output: /tmp/elastic-errors.json
[elastic] Duration: 1.2s
```

Aggregate errors by service for downstream visualization:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli elastic aggregate --index "vds-logs-*" \
  --field "service.name" --metric "count" \
  --time-range "now-7d" --output /tmp/error-agg.json
```

Expected output:

```
[elastic] Buckets: 12
[elastic] Top: audit-orchestrator (847)
[elastic] Output: /tmp/error-agg.json
```

## Step 2: Build Grafana Visualizations

Import the aggregated data into a Grafana datasource and create a panel.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli grafana datasource test --name "vds-elastic"
```

Expected output:

```
[grafana] Datasource "vds-cli elastic" status: OK
[grafana] Version: 10.4.1
```

Create a dashboard with a time-series panel from the Elastic query:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli grafana dashboard create --title "VDS Error Analytics" \
  --datasource "vds-cli elastic" --panel-type timeseries \
  --query '{"index":"vds-logs-*","body":{"aggs":{"services":{"terms":{"field":"service.name"}}}}}' \
  --folder "VDS Operations"
```

Expected output:

```
[grafana] Dashboard created: /d/vds-error-analytics
[grafana] UID: vds-error-analytics
[grafana] Folder: VDS Operations
```

Generate a snapshot link for sharing:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli grafana snapshot create --dashboard "vds-error-analytics" \
  --name "Error Analytics Snapshot $(date +%Y-%m-%d)"
```

Expected output:

```
[grafana] Snapshot created: https://grafana.example.com/dashboard/snapshot/vds-error-analytics-2026-04-22
```

## Step 3: Export Analytics to Metabase

Sync the aggregated dataset to Metabase for self-service exploration.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli metabase card create --database "vds-analytics" \
  --name "Weekly Error Distribution" --query-file /tmp/error-agg.json
```

Expected output:

```
[metabase] Card created: 2143
[metabase] Database: vds-analytics
[metabase] Visualization: table
```

Add the card to a Metabase dashboard:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli metabase dashboard add-card --dashboard "VDS Operational Metrics" \
  --card 2143 --col 0 --row 0
```

Expected output:

```
[metabase] Dashboard updated: VDS Operational Metrics
[metabase] Cards: 8
```

Publish the dashboard for public or embedding access:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli metabase dashboard publish --dashboard "VDS Operational Metrics" \
  --enable-public-link
```

Expected output:

```
[metabase] Public link enabled
[metabase] URL: https://metabase.example.com/public/dashboard/vds-operational-metrics
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `elastic search` returns zero hits | Index pattern mismatch or timestamp field name | Verify index with `vds-cli elastic indices list` |
| `grafana datasource test` fails | Credentials missing or network egress blocked | Check `GRAFANA_API_KEY` in `~/.vds/.env` |
| `grafana dashboard create` panel empty | Query JSON malformed | Validate query with `vds-cli elastic search --dry-run` first |
| `metabase card create` fails | Database connection or schema mismatch | Check `vds-cli metabase database sync --db "vds-analytics"` |
| Dashboard links return 404 | UID or slug changed after rename | Re-run `vds-cli grafana dashboard list --search "VDS"` |
