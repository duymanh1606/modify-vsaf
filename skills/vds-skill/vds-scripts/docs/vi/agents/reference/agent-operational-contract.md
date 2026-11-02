<!-- diátaxis: reference -->

# Hợp Đồng Vận Hành cho AI Agent

> Quy tắc và chiến lược để AI agent vận hành hiệu quả trong hệ sinh thái VDS.

---

## 1. Quy tắc ngân sách ngữ cảnh

**Ngữ cảnh là tài nguyên hạn chế.** Mỗi phiên có giới hạn token. Sử dụng khôn ngoan.

| Chiến lược | Mô tả |
|------------|-------|
| **Ưu tiên cục bộ** | Đọc tệp gần thay vì quét toàn repo |
| **Tóm tắt sớm** | Tóm tắt phát hiện trước khi chuyển sang bước tiếp theo |
| **Tránh lặp lại** | Không đọc lại tệp đã đọc trừ khi có thay đổi |
| **Skill trước, tìm kiếm sau** | Dùng `cat skills/<skill-name>/SKILL.md` trước khi dùng `rg` rộng |

**Ngưỡng cảnh báo**: Khi đã sử dụng >70% ngân sách, bắt đầu tóm tắt hoặc chia nhỏ nhiệm vụ.

## 2. Chiến lược tải skill

**Khi nào dùng `cat skills/<skill-name>/SKILL.md`:**
- Nhiệm vụ phức tạp, đa bước
- Lĩnh vực chuyên biệt (audit, spec, research)
- Cần quy trình chuẩn hóa

**Khi nào KHÔNG dùng:**
- Tra cứu chuỗi đơn giản (`rg` đủ nhanh)
- Kiểm tra tệp tồn tại
- Câu hỏi không cần quy trình

**Lệnh**:
```bash
cat WHO-project/vds-skills/skills/<skill-name>
```

## 3. Mẫu sử dụng công cụ

| Công cụ | Khi nào dùng | Khi nào KHÔNG dùng |
|---------|--------------|-------------------|
| `rg` | Tìm chuỗi chính xác | Khám phá kiến trúc rộng |
| `sg` | Tìm mẫu cấu trúc | Tìm chuỗi đơn giản |
| `grepai` | Tìm kiếm ngữ nghĩa | Tra cứu chính xác |
| `graphify` | Tổng quan kiến trúc | Tìm nhanh |
| `read file` | Đọc nội dung tệp | Khám phá repo |

**Quy tắc vàng**: Ưu tiên `rg`/`sg` hơn `read file` cho việc khám phá.

## 4. Giao thức gọi lại bộ nhớ

**Trước khi bắt đầu nhiệm vụ mới:**
```bash
vds-cli memory search "<chủ đề>" --limit 3
```

**Nếu có kết quả**:
- Áp dụng phát hiện trước đó
- Bỏ qua nghiên cứu lại trên sự thật đã xác nhận
- Ghi chú mâu thuẫn nếu có

**Nếu không có kết quả**:
- Tiến hành nghiên cứu đầy đủ
- Lưu phát hiện khi kết thúc

## 5. Quy tắc leo thang

| Tình huống | Hành động |
|------------|-----------|
| Lỗi cú pháp đơn giản | Tự sửa, không hỏi |
| Thiếu thông tin | Tìm kiếm thêm 1-2 lần |
| Kết quả tìm kiếm mâu thuẫn | Hỏi người dùng xác nhận |
| Lỗi hệ thống không rõ | Hỏi người dùng + ghi log |
| Nghi ngờ bảo mật | Dừng ngay, hỏi người dùng |

**Nguyên tắc**: Hỏi khi không chắc chắn. Tự sửa khi chắc chắn.

## 6. Quản lý compaction

Khi ngữ cảnh đầy:

1. **Tóm tắt quan trọng** — Lưu quyết định, phát hiện, hành động đang chờ
2. **Loại bỏ tạm thời** — Xóa output dài, giữ kết luận
3. **Tiếp tục** — Khởi động lại với tóm tắt làm ngữ cảnh ban đầu

**Mẫu tóm tắt**:
```
## Tóm tắt phiên
- Quyết định: <quyết định chính>
- Phát hiện: <phát hiện quan trọng>
- Hành động chờ: <việc cần làm tiếp>
- Ngữ cảnh cần giữ: <thông tin quan trọng>
```

---

**Tiếp theo**: [Hướng dẫn cài đặt](../how-to/install-and-bootstrap-who-scripts-and-skills.md)
