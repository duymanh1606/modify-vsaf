<!-- diátaxis: reference -->

# Điều Phối Viên MCP

> Bộ định tuyến MCP (Model Context Protocol) và quản lý công cụ.

## Phạm vi

- **Thực hiện:** Định tuyến lệnh gọi công cụ MCP, quản lý đăng ký công cụ, xử lý vòng đời máy chủ MCP.
- **Không thực hiện:** Thay thế lệnh gọi API trực tiếp, quản lý xác thực nhà cung cấp LLM.
- **Người dùng chính:** AI agent (phan phối công cụ), nhà phát triển (tích hợp MCP).

## Điểm vào CLI

```bash
# Qua bộ định tuyến thống nhất
vds-cli mcp --help

# Điểm vào trực tiếp
vds-cli mcp-server --help
```

## Các Lệnh Chính

| Lệnh | Mục đích | Cờ thường dùng |
|------|----------|----------------|
| `list` | Liệt kê công cụ có sẵn | — |
| `call` | Thực thi lệnh gọi công cụ | `--tool`, `--args` |
| `health` | Kiểm tra sức khỏe máy chủ MCP | — |

## Liên Quan

- **Điều phối viên:** [research](research-orchestrator.md), [memory](memory-orchestrator.md)
- **Confluence:** [WHO MCP](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
