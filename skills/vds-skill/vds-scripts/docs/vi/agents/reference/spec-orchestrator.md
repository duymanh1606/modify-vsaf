<!-- diátaxis: reference -->

# Điều Phối Viên Đặc Tả

> Tạo, xác thực và duy trì bộ ba đặc tả VDS chuẩn.

## Phạm vi

- **Thực hiện:** Dựng khung thư mục đặc tả, xác thực tính nhất quán của bộ ba, kiểm tra sự liên kết giữa requirements/design/tasks, thực thi dòng đồng bộ AGENTS.md.
- **Không thực hiện:** Viết nội dung đặc tả thay bạn, tự động tạo thiết kế từ không khí, thay thế xem xét của con người.
- **Người dùng chính:** AI agent (tạo đặc tả), người phụ trách (xem xét và phê duyệt).

## Điểm vào CLI

```bash
# Qua bộ định tuyến thống nhất
vds-cli spec --help

# Điểm vào trực tiếp
vds-cli spec --help
```

## Các Lệnh Chính

| Lệnh | Mục đích | Cờ thường dùng |
|------|----------|----------------|
| `validate <path>` | Xác thực một bộ ba đặc tả | — |
| `check-alignment <path>` | Đối chiếu chéo FR và task | — |
| `validate-sync <name>` | Kiểm tra đồng bộ với AGENTS.md | `--agents-label` |
| `create <name>` | Dựng khung thư mục đặc tả mới | — |

## Quy Trình Thường Gặp

### Quy trình: Tạo Đặc Tả Giai Đoạn Mới

1. Xác định phạm vi và tiêu chí chấp nhận
2. Chạy `vds-cli spec create <tên>` để dựng khung bộ ba
3. Điền `requirements.md`, `design.md`, `tasks.md`
4. Chạy `vds-cli spec validate <đường_dẫn>` để xác minh cấu trúc
5. Chạy `vds-cli spec check-alignment <đường_dẫn>` để đối chiếu chéo
6. Cập nhật dòng đồng bộ AGENTS.md
7. Chạy `vds-cli spec validate-sync <tên> --agents-label "..."`

### Quy trình: Xác Thực Đặc Tả Hiện Có

1. Chạy `vds-cli spec validate <đường_dẫn>` — kiểm tra sự liên kết phiên bản, sự hiện diện của FR, gói task
2. Chạy `vds-cli spec check-alignment <đường_dẫn>` — xác minh tham chiếu chéo FR/task
3. Sửa các khoảng trống được báo cáo
4. Chạy lại cho đến khi tất cả kiểm tra đều đạt

## Liên Quan

- **Điều phối viên:** [tasks](tasks-orchestrator.md), [audit](audit-triage-playbook.md), [research](research-orchestrator.md)
- **Skill:** [spec-creation-skill](../../../../vds-skills/skills/spec-creation-skill/SKILL.md)
- **Confluence:** [WHO Specs](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
- **Bitbucket:** [vds-scripts source](https://bitbucket.digital.vn/projects/WHO/repos/vds-scripts/browse)
