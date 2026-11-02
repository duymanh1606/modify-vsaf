<!-- diátaxis: reference -->

# Điều Phối Viên Truy Vấn Cơ Sở Dữ Liệu

> Thực thi truy vấn cơ sở dữ liệu trên VDS Postgres và các kho phân tích.

## Phạm vi

- **Thực hiện:** Chạy truy vấn SQL, kiểm tra lược đồ, xuất kết quả, quản lý kết nối.
- **Không thực hiện:** Sửa đổi lược đồ (chỉ đọc theo mặc định), thay thế pgAdmin.
- **Người dùng chính:** AI agent (truy xuất dữ liệu), vận hành viên (truy vấn ad-hoc).

## Điểm vào CLI

```bash
# Qua bộ định tuyến thống nhất
vds-cli db-query --help

# Điểm vào trực tiếp
vds-cli db-query --help
```

## Các Lệnh Chính

| Lệnh | Mục đích | Cờ thường dùng |
|------|----------|----------------|
| `query` | Thực thi truy vấn SQL | `--sql`, `--format` |
| `schema` | Kiểm tra lược đồ bảng | `--table` |
| `export` | Xuất kết quả truy vấn | `--output` |

## Liên Quan

- **Điều phối viên:** [audit](audit-triage-playbook.md), [grafana](grafana-orchestrator.md)
- **Confluence:** [WHO DB Query](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
