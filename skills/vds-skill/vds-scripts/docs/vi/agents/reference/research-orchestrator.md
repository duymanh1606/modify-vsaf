<!-- diátaxis: reference -->

# Điều Phối Viên Nghiên Cứu

> Nghiên cứu kỹ thuật ưu tiên bằng chứng, kết hợp bằng chứng kho lưu trữ cục bộ với các nguồn bên ngoài.

## Phạm vi

- **Thực hiện:** Tìm kiếm mã nguồn cục bộ (rg, sg, grepai), truy vấn API bên ngoài (Tavily, Exa, Context7), chấm điểm bằng chứng, tạo gói nghiên cứu.
- **Không thực hiện:** Đưa ra quyết định thay bạn, thay thế phán đoán của con người về các lựa chọn chiến lược.
- **Người dùng chính:** AI agent (xác thực sự thật), người phụ trách (đánh giá công nghệ).

## Điểm vào CLI

```bash
# Qua bộ định tuyến thống nhất
vds-cli research --help

# Điểm vào trực tiếp
vds-cli research --help
```

## Các Lệnh Chính

| Lệnh | Mục đích | Cờ thường dùng |
|------|----------|----------------|
| `search` | Tìm kiếm thống nhất | `--tool`, `--json` |
| `health` | Kiểm tra khả dụng công cụ | — |
| `score` | Chấm điểm chất lượng bằng chứng | `--threshold` |

## Quy Trình Thường Gặp

### Quy trình: Xác Thực Khẳng Định Kỹ Thuật

1. Tìm kiếm bằng chứng cục bộ: `vds-cli research search "nội dung khẳng định"`
2. Truy vấn nguồn bên ngoài: `vds-cli research search "chủ đề" --tool tavily`
3. Thu thập và tổ chức phát hiện
4. Chấm điểm chất lượng bằng chứng
5. Xuất báo cáo sẵn sàng quyết định

## Liên Quan

- **Điều phối viên:** [memory](memory-orchestrator.md), [spec](spec-orchestrator.md), [audit](audit-triage-playbook.md)
- **Skill:** [research-skill](../../../../vds-skills/skills/research-skill/SKILL.md)
- **Confluence:** [WHO Research](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
