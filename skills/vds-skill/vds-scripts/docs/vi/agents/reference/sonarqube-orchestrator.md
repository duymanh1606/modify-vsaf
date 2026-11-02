<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../agents/reference/sonarqube-orchestrator.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md)

# SonarQube orchestrator

> Quét chất lượng mã và quản lý issue SonarQube cho các repo VDS.

## Phạm vi

- **Làm:** Truy vấn project SonarQube, liệt kê issue và hotspot, kiểm tra health, và xuất chỉ số chất lượng.
- **Không làm:** Thực thi quét (cần Maven hoặc sonar-scanner trong PATH), quản lý cấu hình SonarQube server.
- **Người dùng chính:** AI agent (kiểm tra quality gate), nhà phát triển (xử lý issue).

## Điểm vào CLI

```bash
# Qua router thống nhất
vds-cli sonarqube --help

# Direct entry
vds-cli sonarqube --help
```

## Lệnh chính

| Lệnh | Mục đích | Flag thường dùng |
|------|----------|------------------|
| `ping` | Kiểm tra kết nối và xác thực | — |
| `projects` | Liệt kê project SonarQube truy cập được | `--query`, `--limit` |
| `issues` | Liệt kê issue của project | `--project`, `--status`, `--severity` |
| `hotspots` | Liệt kê security hotspot | `--project`, `--status` |
| `measures` | Lấy chỉ số chất lượng của project | `--project`, `--metrics` |

## Ví dụ quy trình

```bash
# Health check
vds-cli sonarqube ping

# Liệt kê project
vds-cli sonarqube projects --limit 50

# Liệt kê issue OPEN
vds-cli sonarqube issues list --project ekyc-business --status OPEN

# Liệt kê issue mức cao
vds-cli sonarqube issues list --project ekyc-business --severity CRITICAL,BLOCKER

# Lấy chỉ số chất lượng
vds-cli sonarqube measures --project ekyc-business --metrics coverage,bugs,vulnerabilities

# JSON-only
vds-cli sonarqube --json-only ping
```

## Cấu hình

Yêu cầu `VDS_SONAR_TOKEN` hoặc `VDS_SONAR_USER`/`VDS_SONAR_PASSWORD` trong `~/.vds/.env`.

## Liên quan

- **Orchestrators:** [grafana](grafana-orchestrator.md), [elastic](elastic-orchestrator.md)
- **Confluence:** [WHO SonarQube](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
