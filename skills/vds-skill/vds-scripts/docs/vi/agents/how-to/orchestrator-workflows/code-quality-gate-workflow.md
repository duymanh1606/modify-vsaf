<!-- diátaxis: how-to -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../../agents/how-to/orchestrator-workflows/code-quality-gate-workflow.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../../TRANSLATION-BACKLOG.md)

# Quy trình cổng chất lượng mã

> Chạy pipeline chất lượng mã toàn diện kết hợp SonarQube, tuân thủ hexagonal, kiểm tra cấu trúc, và phát hiện phụ thuộc vòng.

## Điều kiện tiên quyết

- `vds-scripts` đã được clone và khởi tạo
- Server SonarQube đã được cấu hình trong `~/.vds/.env`
- Repository đích có `pyproject.toml` hoặc `package.json`

## Tổng quan quy trình

```
SonarQube (phân tích tĩnh)
    ↓
Hexagonal (tuân thủ kiến trúc)
    ↓
Structure (tổ chức mã nguồn)
    ↓
Circular Dependency (vòng lặp import)
    ↓
Báo cáo chất lượng tổng hợp
```

## Bước 1: Phân tích tĩnh SonarQube

Chạy phân tích SonarQube trên repo đích:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli sonarqube analyze --repo vds-scripts --branch main
```

Kết quả mong đợi:

```
[sonarqube] Project: vds-scripts
[sonarqube] Issues: 12 (3 critical, 5 major, 4 minor)
[sonarqube] Coverage: 78%
[sonarqube] Duplications: 2.1%
```

Xuất báo cáo:

```bash
vds-cli sonarqube report --repo vds-scripts --format json --output sonar-report.json
```

## Bước 2: Kiểm tra tuân thủ hexagonal

Kiểm tra tính tuân thủ kiến trúc hexagonal:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli hexagonal check --path . --strict
```

Kết quả mong đợi:

```
[hexagonal] Checking dependency direction...
[hexagonal] Port/adapter boundaries: 24
[hexagonal] Violations: 2
[hexagonal] Report: hexagonal-report.json
```

## Bước 3: Kiểm tra cấu trúc

Kiểm tra cấu trúc và tổ chức mã nguồn:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli structure validate --path . --mode target-state
```

Kết quả mong đợi:

```
[structure] Validating folder structure...
[structure] Modules: 18
[structure] Violations: 1 (missing __init__.py)
[structure] Report: structure-report.json
```

## Bước 4: Phát hiện phụ thuộc vòng

Phát hiện vòng lặp import:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli circular-dependency analyze --path . --language python
```

Kết quả mong đợi:

```
[circular_dependency] Analyzing imports...
[circular_dependency] Cycles found: 0
[circular_dependency] Status: PASS
```

## Bước 5: Báo cáo chất lượng tổng hợp

Sinh báo cáo chất lượng hợp nhất:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli docs quality-report \
  --sonar sonar-report.json \
  --hexagonal hexagonal-report.json \
  --structure structure-report.json \
  --circular circular-report.json \
  --output quality-report.md
```

## Tích hợp CI

Thêm vào `.github/workflows/quality.yml`:

```yaml
- name: Code Quality Gate
  run: |
    vds-cli sonarqube analyze --repo ${{ github.repository }}
    vds-cli hexagonal check --path . --strict
    vds-cli structure validate --path . --mode target-state
    vds-cli circular-dependency analyze --path . --language python
```

## Xử lý sự cố

| Triệu chứng | Nguyên nhân | Cách khắc phục |
|---------|-------|-----|
| Xác thực SonarQube thất bại | Token hết hạn | Làm mới `SONAR_TOKEN` trong `~/.vds/.env` |
| Kiểm tra hexagonal quá nghiêm ngặt | Dùng cờ `--strict` | Dùng `--strict=false` để tuân thủ dần |
| Phụ thuộc vòng báo dương tính giả | Import từ test | Thêm `--exclude tests/` |
| Kiểm tra cấu trúc thất bại ở module mới | Thiếu cấu hình | Cập nhật `target-state.yaml` |
