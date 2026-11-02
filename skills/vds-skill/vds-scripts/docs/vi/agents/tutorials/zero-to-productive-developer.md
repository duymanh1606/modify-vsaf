<!-- diátaxis: tutorial -->

# Con Đường Từ Zero Đến Productive Developer

> Hướng dẫn 7 ngày để trở thành developer productive trong hệ sinh thái WHO.

---

## Ngày 0: Cài đặt môi trường

**Mục tiêu**: Clone repo, đồng bộ workspace, cấu hình token.

```bash
cd WHO-project/vds-scripts
./scripts/worktree_uv.sh sync --all-packages
cp .env.example ~/.vds/.env
# Chỉnh sửa ~/.vds/.env với thông tin xác thực của bạn
```

**Kiểm tra**: `vds-cli env status` hiển thị ✅ cho tất cả các hàng.

## Ngày 1: Chạy `vds-cli doctor` lần đầu

**Mục tiêu**: Hiểu công cụ chẩn đoán và khắc phục lỗi cơ bản.

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli doctor
```

Đọc từng phần của output:
- **Environment**: Biến môi trường có đúng không?
- **Dependencies**: Có gói nào thiếu không?
- **Services**: Confluence/Bitbucket có thể truy cập không?

## Ngày 2: Chạy audit đầu tiên

**Mục tiêu**: Hiểu luồng audit cơ bản.

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli audit run --dry-run
```

**Ghi chú**: Audit khô (`--dry-run`) không ghi vào cơ sở dữ liệu. An toàn để thử.

## Ngày 3: Đóng góp skill hoặc hook đầu tiên

**Mục tiêu**: Hiểu quy trình đóng góp.

### Tùy chọn A: Skill

```bash
cd ../vds-skills
# Đọc hướng dẫn
cat WHO-project/vds-skills/skills/skill-creator
# Tạo skill mới
mkdir -p skills/my-first-skill
cat > skills/my-first-skill/SKILL.md << 'SKILLEOF'
---
name: my-first-skill
description: Mô tả khi nào sử dụng skill này.
---

# Skill đầu tiên của tôi

## Workflow

1. Bước 1
2. Bước 2
3. Bước 3
SKILLEOF
```

### Tùy chọn B: Hook

```bash
cd ../vds-skills
# Đọc hướng dẫn
cat docs/agents/how-to/author-hook.md
# Tạo hook mới
cat > vds-hooks-core/scripts/hooks/my_hook.py << 'HOOKEOF'
#!/usr/bin/env python3
import json, sys
event = json.load(sys.stdin)
print(json.dumps({"status": "ok"}))
HOOKEOF
chmod +x vds-hooks-core/scripts/hooks/my_hook.py
```

## Ngày 4: Triển khai môi trường thử nghiệm

**Mục tiêu**: Hiểu quy trình triển khai.

```bash
cd WHO-project/vds-scripts
# Chạy kiểm thử tập trung
uv run --project audit_orchestrator pytest tests/unit/ -q --tb=short

# Kiểm tra độ phủ
uv run --project audit_orchestrator pytest --cov=src --cov-report=term-missing
```

## Ngày 5: Điều hướng Confluence/Bitbucket

**Mục tiêu**: Tìm tài liệu và theo dõi tiến độ.

- **Confluence**: Trang WHO-Project Ecosystem Documentation (pageId 98997962)
- **Bitbucket**: Duyệt repo tại `http://bitbucket.digital.vn/projects/WHO`
- **vds-cli**: `vds-cli progress report --help`

## Ngày 6–7: Nhiệm vụ thực tế đầu tiên

**Mục tiêu**: Hoàn thành nhiệm vụ có giá trị.

1. Chọn một issue từ backlog hoặc yêu cầu từ team lead
2. Tạo worktree riêng: `git worktree add -b feat/my-task ../worktrees/my-task`
3. Làm việc trong worktree, commit thường xuyên
4. Chạy kiểm thử trước khi tạo PR
5. Tạo PR trên Bitbucket, chờ review

---

## Kiểm tra tiến độ

| Ngày | Kiểm tra | Tiêu chí thành công |
|------|----------|---------------------|
| 0 | `vds-cli env status` | Tất cả ✅ |
| 1 | `vds-cli doctor` | Không có lỗi nghiêm trọng |
| 2 | `vds-cli audit --dry-run` | Hoàn thành không lỗi |
| 3 | Skill/Hook được tạo | `SKILL.md` hoặc hook script tồn tại |
| 4 | Kiểm thử chạy | pytest exits 0 |
| 5 | Tìm thấy tài liệu | Truy cập được Confluence page |
| 6–7 | PR được tạo | PR trên Bitbucket với mô tả rõ ràng |

---

**Tiếp theo**: [Hợp đồng vận hành cho AI Agent](../reference/agent-operational-contract.md)
