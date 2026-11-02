<!-- diátaxis: how-to -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo từ tài liệu gốc tiếng Anh tại [`../../../../agents/how-to/orchestrator-workflows/research-spec-audit-workflow.md`](../../../../agents/how-to/orchestrator-workflows/research-spec-audit-workflow.md).
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải được con người dịch trước khi được coi là tài liệu chính thức. Một biên dịch viên con người phải rà soát, chỉnh sửa thành ngữ và thuật ngữ kỹ thuật, đồng thời gỡ bỏ biểu ngữ này trước khi tệp trở nên có hiệu lực.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../../TRANSLATION-BACKLOG.md) (độ sâu đường dẫn có thể khác — điều chỉnh nếu cần)

# Quy trình Research → Spec → Audit

> Kết hợp các điều phối viên research, spec và audit để thu thập bằng chứng, chính thức hóa yêu cầu và kiểm định việc triển khai.

## Điều kiện tiên quyết

- `vds-scripts` đã được clone và khởi tạo (`./scripts/worktree_uv.sh sync`)
- `vds-cli doctor` thành công
- (Các) repo mục tiêu truy cập được qua Bitbucket
- `~/.vds/.env` chứa `VDS_USERNAME`, `VDS_PASSWORD`, và `OPENAI_API_KEY`

## Tổng quan quy trình

```
research (thu thập bằng chứng)
    ↓
spec (tạo/kiểm định spec)
    ↓
audit (thực thi kiểm định)
```

## Bước 1: Thu thập bằng chứng với Research

Chạy truy vấn research có mục tiêu để thu thập bằng chứng cho tính năng hoặc khoảng trống bạn cần xử lý.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli research search "hexagonal architecture compliance patterns"
```

Kết quả mong đợi:

```
[research] Query: hexagonal architecture compliance patterns
[research] Sources found: 12
[research] Top result: https://example.com/hexagonal-guide
[research] Evidence saved to: /tmp/vds-research-evidence-<timestamp>.json
```

Chấm điểm chất lượng bằng chứng trước khi tiếp tục:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli research score --evidence /tmp/vds-research-evidence-<timestamp>.json
```

Kết quả mong đợi:

```
[score] Total evidence items: 12
[score] High quality: 8
[score] Medium quality: 3
[score] Low quality: 1
[score] Average score: 0.78
```

## Bước 2: Tạo hoặc kiểm định Spec

Dùng điều phối viên spec để tạo một spec mới từ bằng chứng research.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli spec create hexagonal-compliance --evidence /tmp/vds-research-evidence-<timestamp>.json
```

Kết quả mong đợi:

```
[spec] Created: .gpt-5.4/specs/hexagonal-compliance/requirements.md
[spec] Created: .gpt-5.4/specs/hexagonal-compliance/design.md
[spec] Created: .gpt-5.4/specs/hexagonal-compliance/tasks.md
[spec] Next: run validation
```

Kiểm định bộ ba tệp spec:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli spec validate --spec-dir .gpt-5.4/specs/hexagonal-compliance
```

Kết quả mong đợi:

```
[validate] requirements.md: PASS
[validate] design.md: PASS
[validate] tasks.md: PASS
[validate] 3/3 files valid
```

Chạy kiểm tra căn chỉnh:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli spec check-alignment --spec-dir .gpt-5.4/specs/hexagonal-compliance
```

## Bước 3: Thực thi kiểm định Audit

Chạy điều phối viên audit đối với repo mục tiêu sử dụng spec đã được kiểm định.

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit run --repo vds-scripts --scope full --spec hexagonal-compliance
```

Kết quả mong đợi:

```
[audit] Profile: default
[audit] Scope: full
[audit] Spec: hexagonal-compliance
[audit] Rules: 47
[audit] Violations: 3
[audit] Report: /tmp/vds-audit-report-<timestamp>.json
```

Tạo báo cáo hợp nhất:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli research report --evidence /tmp/vds-research-evidence-<timestamp>.json \
  --audit /tmp/vds-audit-report-<timestamp>.json
```

## Xử lý sự cố

| Triệu chứng | Nguyên nhân | Khắc phục |
|---------|-------|-----|
| `research search` trả về không có kết quả | MCP router không khả dụng hoặc đã hết hạn ngạch Tavily | Chạy `vds-cli research health` để chẩn đoán |
| `spec validate` báo thiếu FR | `requirements.md` có khoảng trống | Bổ sung các yêu cầu chức năng còn thiếu và chạy lại |
| `audit run` báo lỗi `--spec not found` | Tên spec không khớp | Dùng đúng tên thư mục spec, hoặc bỏ `--spec` để dùng mặc định |
| `check-alignment` báo lệch | Design và tasks không đồng bộ | Chạy `vds-cli spec consolidate` rồi kiểm tra lại |
