---
diátaxis: explanation
audience: human
complexity: basic
last_updated: 2026-04-30
phase_ref: 180
language: vi
---

# Có gì Mới

Theo dõi các thay đổi gần đây và xác minh môi trường của bạn đang cập nhật.

## 2026-04-30 — Tài liệu toàn diện (Phase 180)

Tài liệu mới bao gồm 8 phần mục tiêu:
- Giới thiệu, Bắt đầu nhanh, Yêu cầu hệ thống, Tài liệu Cấu hình
- Tổng quan Tính năng, Hướng dẫn Tiến triển, Ma trận So sánh Orchestrator
- Tài liệu Kiến trúc, Kiến trúc Hệ thống, Luồng Dữ liệu

## 2026-04-29 — Telegram Bridge & Lint Hygiene

- **Telegram Bridge**: Bot thông báo với hỗ trợ multi-runner
- **Lint Hygiene**: Sửa Track-α cho Phase 220

## Kiểm tra sức khỏe nhanh

```bash
vds-cli docs validate
pytest --co -q | tail -1
vds-cli docs freshness-report --days 30
```

## Xem thêm

- Tiếng Anh: [whats-new.md](../../agents/explanation/whats-new.md)
- [Hệ sinh thái WHO](../../explanation/who-ecosystem-introduction.md)
