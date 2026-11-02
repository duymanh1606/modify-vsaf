<!-- diátaxis: reference -->

# Điều Phối Viên Phụ Thuộc Vòng Tròn

> Phát hiện và trực quan hóa phụ thuộc vòng tròn trong codebase.

## Phạm vi

- **Thực hiện:** Phân tích import graph, phát hiện chu kỳ, đề xuất điểm cắt.
- **Không thực hiện:** Tự động sửa chu kỳ, thay thế review kiến trúc.

## Điểm vào CLI

```bash
vds-cli circular-dependency --help
vds-circular-dependency --help
```

## Các Lệnh Chính

| Lệnh | Mục đích |
|---------|---------|
| `analyze` | Phân tích chu kỳ |
| `visualize` | Tạo đồ thị |
| `suggest` | Đề xuất điểm cắt |

## Liên Quan

- **Skill:** [circular-dependency-skill](../../../../vds-skills/skills/circular-dependency-skill/SKILL.md)
