<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo từ tài liệu gốc tiếng Anh tại [`../../../agents/reference/multi-agent-orchestrator.md`](../../../agents/reference/multi-agent-orchestrator.md).
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải được con người dịch trước khi được coi là tài liệu chính thức. Một biên dịch viên con người phải rà soát, chỉnh sửa thành ngữ và thuật ngữ kỹ thuật, đồng thời gỡ bỏ biểu ngữ này trước khi tệp trở nên có hiệu lực.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md) (độ sâu đường dẫn có thể khác — điều chỉnh nếu cần)

# Điều phối đa tác tử

> Phối hợp nhiều AI agent cho các tác vụ song song phức tạp.

## Phạm vi

- **Thực hiện:** Điều phối tác vụ tới các đội agent, tổng hợp kết quả, quản lý xung đột và theo dõi tiến độ đội.
- **Không thực hiện:** Thay thế việc ra quyết định của từng agent, bảo đảm đồng thuận, hoặc quản lý đội con người.
- **Người dùng chính:** AI agent (phối hợp đội), trưởng nhóm con người (giám sát), người chạy tác vụ phức tạp.

## Điểm vào CLI

```bash
# Qua bộ định tuyến thống nhất
vds-cli multi-agent --help

# Điểm vào trực tiếp
vds-cli multi-agent --help
```

## Các lệnh chính

| Lệnh | Mục đích | Cờ thường dùng |
|---------|---------|-------------|
| `dispatch` | Điều phối tác vụ tới các agent | `--task`, `--agents`, `--strategy` |
| `aggregate` | Tổng hợp kết quả từ các agent | `--run-id`, `--method` |
| `resolve` | Giải quyết xung đột | `--run-id`, `--strategy` |
| `status` | Kiểm tra trạng thái đội | `--run-id` |

## Quy trình thường gặp

### Quy trình: rà soát mã nguồn song song

1. Điều phối tác vụ rà soát: `vds-cli multi-agent dispatch --task "review PR #123" --agents reviewer-1,reviewer-2,reviewer-3`
2. Chờ hoàn thành
3. Tổng hợp kết quả: `vds-cli multi-agent aggregate --run-id <id> --method consensus`
4. Giải quyết xung đột nếu những người rà soát không đồng thuận

## Liên quan

- **Điều phối viên:** [audit](audit-triage-playbook.md), [evolution](evolution-orchestrator.md), [tasks](tasks-orchestrator.md)
- **Confluence:** [WHO Multi-Agent](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Xử lý sự cố

| Vấn đề | Nguyên nhân | Hướng xử lý |
|-------|-------|------------|
| Không tìm thấy lệnh | Chưa cài điều phối viên | Chạy `uv sync --all-packages` |
| Thiếu cấu hình | Chưa thiết lập `~/.vds/.env` | Thêm các thông tin đăng nhập cần thiết theo [AGENTS.md](../../../AGENTS.md) |
| Từ chối quyền | Không đủ quyền hạn | Kiểm tra phạm vi token Bitbucket/Confluence |
