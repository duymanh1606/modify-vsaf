<!-- diátaxis: reference -->

# Chỉ Mục Điều Phối Viên

> Tham khảo nhanh cho tất cả 28 điều phối viên VDS.

## Nền Tảng Cốt Lõi

| Điều phối viên | Mục đích | Điểm vào CLI | Tài liệu |
|---------------|----------|--------------|----------|
| audit | Thực thi và báo cáo audit | `vds-cli audit` | [audit-triage-playbook](audit-triage-playbook.md) |
| bitbucket | Thao tác Bitbucket | `vds-cli bitbucket-cli` | [cli-commands](cli-commands.md) |
| brd | Tài liệu yêu cầu nghiệp vụ | `vds-cli brd` | [brd-orchestrator](brd-orchestrator.md) |
| circular-dependency | Phát hiện phụ thuộc vòng | `vds-cli circular-dependency` | [circular-dependency-orchestrator](circular-dependency-orchestrator.md) |
| confluence | Thao tác Confluence | `vds-cli confluence-cli` | [cli-commands](cli-commands.md) |
| db-query | Thao tác truy vấn cơ sở dữ liệu | `vds-cli db-query` | [db-query-orchestrator](db-query-orchestrator.md) |
| diagrams | Tạo sơ đồ | `vds-cli diagrams` | [diagrams-orchestrator](diagrams-orchestrator.md) |
| elastic | Thao tác Elasticsearch | `vds-cli elastic` | [elastic-orchestrator](elastic-orchestrator.md) |
| evolution | Vòng lặp tiến hóa hệ sinh thái | `vds-cli evolution` | [evolution-orchestrator](evolution-orchestrator.md) |
| excel | Xử lý Excel | `vds-cli excel` | [excel-orchestrator](excel-orchestrator.md) |
| git | Thao tác kho lưu trữ git | `vds-cli git-orchestrator` | [cli-commands](cli-commands.md) |
| google-sheets | Tích hợp Google Sheets | `vds-cli google-sheets` | [google-sheets-orchestrator](google-sheets-orchestrator.md) |
| grafana | Log và chỉ số Grafana | `vds-cli grafana` | [grafana-orchestrator](grafana-orchestrator.md) |
| hexagonal | Tuân thủ hexagonal | `vds-cli hexagonal` | [hexagonal-orchestrator](hexagonal-orchestrator.md) |
| intellij | Thao tác plugin IntelliJ | `vds-cli intellij` | [intellij-orchestrator](intellij-orchestrator.md) |
| jira | Thao tác JIRA | `vds-cli jira-cli` | [cli-commands](cli-commands.md) |
| links | Xác thực liên kết | `vds-cli links` | [links-orchestrator](links-orchestrator.md) |
| lsp | Giao thức máy chủ ngôn ngữ | `vds-cli lsp` | [lsp-orchestrator](lsp-orchestrator.md) |
| markdown | Xử lý Markdown | `vds-cli markdown` | [markdown-orchestrator](markdown-orchestrator.md) |
| mcp | Bộ định tuyến và công cụ MCP | `vds-cli mcp-server` | [mcp-orchestrator](mcp-orchestrator.md) |
| memory | Tìm kiếm và lưu trữ bộ nhớ | `vds-cli memory` | [memory-orchestrator](memory-orchestrator.md) |
| metabase | Phân tích Metabase | `vds-cli metabase` | [metabase-orchestrator](metabase-orchestrator.md) |
| multi-agent | Điều phối đa agent | `vds-cli multi-agent` | [multi-agent-orchestrator](multi-agent-orchestrator.md) |
| openapi | Thao tác schema OpenAPI | `vds-cli openapi` | [openapi-orchestrator](openapi-orchestrator.md) |
| pdf | Tạo PDF | `vds-cli pdf` | [pdf-orchestrator](pdf-orchestrator.md) |
| progress | Báo cáo tiến độ | `vds-cli progress` | [progress-orchestrator](progress-orchestrator.md) |
| public-interface | Phân tích API công khai | `vds-cli public-interface` | [public-interface-orchestrator](public-interface-orchestrator.md) |
| research | Nghiên cứu và bằng chứng | `vds-cli research` | [research-orchestrator](research-orchestrator.md) |
| schema | Chuyển đổi schema | `vds-cli schema-convert` | [schema-orchestrator](schema-orchestrator.md) |
| sonarqube | Tích hợp SonarQube | `vds-cli sonarqube` | [sonarqube-orchestrator](sonarqube-orchestrator.md) |
| spec | Tạo đặc tả | `vds-cli spec` | [spec-orchestrator](spec-orchestrator.md) |
| structure | Phân tích cấu trúc mã | `vds-cli structure` | [structure-orchestrator](structure-orchestrator.md) |
| tasks | Quản lý tác vụ | `vds-cli tasks` | [tasks-orchestrator](tasks-orchestrator.md) |

## Theo Danh Mục

### Audit & Báo Cáo
- [audit](audit-triage-playbook.md), [progress](progress-orchestrator.md), [spec](spec-orchestrator.md)

### Dữ Liệu & Phân Tích
- [db-query](db-query-orchestrator.md), [elastic](elastic-orchestrator.md), [grafana](grafana-orchestrator.md), [metabase](metabase-orchestrator.md), [google-sheets](google-sheets-orchestrator.md), [excel](excel-orchestrator.md)

### Chất Lượng Mã
- [circular-dependency](circular-dependency-orchestrator.md), [hexagonal](hexagonal-orchestrator.md), [sonarqube](sonarqube-orchestrator.md), [structure](structure-orchestrator.md), [public-interface](public-interface-orchestrator.md), [intellij](intellij-orchestrator.md), [lsp](lsp-orchestrator.md)

### Tài Liệu
- [confluence](cli-commands.md), [markdown](markdown-orchestrator.md), [pdf](pdf-orchestrator.md), [diagrams](diagrams-orchestrator.md), [brd](brd-orchestrator.md)

### Nghiên Cứu & Trí Tuệ
- [research](research-orchestrator.md), [memory](memory-orchestrator.md), [mcp](mcp-orchestrator.md)

### DevOps
- [git](cli-commands.md), [bitbucket](cli-commands.md), [jira](cli-commands.md), [links](links-orchestrator.md), [openapi](openapi-orchestrator.md), [schema](schema-orchestrator.md)

### Điều Phối
- [tasks](tasks-orchestrator.md), [multi-agent](multi-agent-orchestrator.md), [evolution](evolution-orchestrator.md)

## Liên Quan

- [Kiến Trúc Điều Phối Viên](orchestrator-architecture.md)
- [Tham Khảo Lệnh CLI](cli-commands.md)
- [Ma Trận Trợ Giúp CLI](cli-help-matrix.md)
- [Tham Khảo Skill](skills-reference.md)
