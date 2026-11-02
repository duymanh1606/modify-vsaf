<!-- diátaxis: how-to -->

# Hướng dẫn cài đặt và khởi tạo WHO Scripts và Skills

> Hướng dẫn từng bước để cài đặt hệ sinh thái WHO-project từ đầu.

---

## Yêu cầu tiên quyết

Trước khi bắt đầu, hãy đảm bảo bạn có:

- **Python 3.12+** — Cài đặt từ [python.org](https://python.org)
- **uv** — Trình quản lý gói Python. `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Git** — Hỗ trợ worktree. `git --version` >= 2.40
- **Truy cập** — Tài khoản Bitbucket và Confluence được cấp quyền
- **~/.vds/.env** — Tệp môi trường với thông tin xác thực (xem bước 3)

## Bước 1: Clone các repository

```bash
# Tạo thư mục dự án
mkdir -p WHO-project
cd WHO-project

# Clone các repository chính
git clone http://bitbucket.digital.vn/scm/WHO/vds-scripts.git
git clone http://bitbucket.digital.vn/scm/WHO/vds-skills.git
git clone http://bitbucket.digital.vn/scm/WHO/vds-skills.git
```

## Bước 2: Đồng bộ workspace Python

```bash
cd vds-scripts
./scripts/worktree_uv.sh sync --all-packages
```

Nếu `uv sync` báo lỗi:
- Xác minh `pyproject.toml` tồn tại
- Kiểm tra quyền thư mục `.venv/`
- Thử xóa `.venv/` và chạy lại

## Bước 3: Cấu hình môi trường (`~/.vds/.env`)

> **Tham khảo đầy đủ**: phiên bản tiếng Anh §11 ([install-and-bootstrap-who-scripts-and-skills.md](../../../agents/how-to/install-and-bootstrap-who-scripts-and-skills.md)) chứa định nghĩa chuẩn cho `~/.vds/.env` theo `who-ecosystem-alignment` Phase 5 FR-18..FR-25 (merged tại `bd162539`).

Cấu trúc tối thiểu (giá trị bên dưới là placeholder — thay bằng credentials thật của bạn, KHÔNG commit):

```bash
mkdir -p ~/.vds
cat > ~/.vds/.env << 'ENVAR_EOF'
# Atlassian shared identity (Bitbucket + Confluence + JIRA dùng chung)
VDS_USERNAME=<your-corporate-username>
VDS_PASSWORD=<your-corporate-password>

# Optional per-product tokens (Bitbucket + JIRA: token được ưu tiên hơn basic;
# Confluence: basic vẫn là primary path, token là fallback)
BITBUCKET_TOKEN=<your-bbdc-pat>
JIRA_TOKEN=<your-jira-pat>
INTERNAL_CONFLUENCE_TOKEN=<your-internal-confluence-token>
EXTERNAL_CONFLUENCE_TOKEN=<your-external-confluence-token>

# Isolated-prefix (Grafana / SonarQube / Elastic — KHÔNG dùng chung VDS_PASSWORD)
VDS_GRAFANA_USER=<your-grafana-user>
VDS_GRAFANA_PASSWORD=<your-grafana-password>
VDS_SONAR_USER=<your-sonar-user>
VDS_SONAR_PASSWORD=<your-sonar-password>
VDS_ELASTIC_USER=<your-elastic-user>
VDS_ELASTIC_PASSWORD=<your-elastic-password>

# Memory service (local)
VDS_MEMORY_API_URL=http://localhost:8010
ENVAR_EOF

chmod 600 ~/.vds/.env
```

> **Quan trọng**: Không bao giờ commit `.env` hoặc thông tin xác thực vào Git (NFR-12).

### Cài đặt git credential helper (FR-23)

Helper được quản lý duy nhất qua `vds-cli env *` subcommands. KHÔNG cài thủ công bằng `cp` / `chmod` / `git config`.

```bash
# Cài helper canonical tại $HOME/.vds/bin/git-credential-vds (mode 0o700)
./scripts/worktree_uv.sh run --project vds_cli vds-cli env install-git-helper

# Kiểm tra trạng thái cài đặt
./scripts/worktree_uv.sh run --project vds_cli vds-cli env verify-git-helper

# Khi cần reset cooldown (sau khi sửa creds bị lock)
./scripts/worktree_uv.sh run --project vds_cli vds-cli env verify-git-helper --reset-cooldown

# Gỡ cài đặt (idempotent)
./scripts/worktree_uv.sh run --project vds_cli vds-cli env remove-git-helper [--purge]
```

Helper bảo vệ chống Bitbucket account-lock thông qua: (a) host allowlist (mặc định `bitbucket.digital.vn`), (b) lockout-prevention (3 failures trong 60s → 300s cooldown), (c) token preference (BITBUCKET_TOKEN ưu tiên hơn VDS_PASSWORD khi cả hai có).

## Bước 4: Xác minh cài đặt

```bash
# Kiểm tra vds-cli
./scripts/worktree_uv.sh run --project vds_cli vds-cli --help

# Kiểm tra trạng thái môi trường
./scripts/worktree_uv.sh run --project vds_cli vds-cli env status

# Chạy kiểm thử tập trung
./scripts/worktree_uv.sh run --project vds_cli vds-cli doctor
```

Bạn sẽ thấy bảng màu với các hàng:
- ✅ Shared env file present
- ✅ VDS credentials
- ✅ Bitbucket auth
- ✅ Confluence auth

## Bước 5: Cài đặt skills

```bash
cd ../vds-skills
cat WHO-project/vds-skills/skills/
vds-cli skills sync --agent claude
```

## Bước 6: Cài đặt Claude hooks (tùy chọn)

```bash
cd ../vds-skills
bash scripts/deploy.sh
bash scripts/test-hooks-smoke.sh
```

## Bước 7: Xác thực toàn bộ

```bash
cd ../vds-scripts
./.venv/bin/vds-cli docs validate --repo-root . --check-vi --check-diataxis
```

Kết quả mong đợi: ✅ docs validate passed (với cảnh báo về bản dịch tiếng Việt nếu chưa hoàn thành)

## Khắc phục sự cố thường gặp

| Triệu chứng | Nguyên nhân | Khắc phục |
|-------------|-------------|-----------|
| `Module not found` | Chưa đồng bộ workspace | Chạy `./scripts/worktree_uv.sh sync --all-packages` |
| `Auth failures` | Thiếu biến môi trường | Kiểm tra `~/.vds/.env` |
| `Worktree issues` | `core.symlinks=false` | `git config --global core.symlinks true` |
| `vds-cli not found` | Chưa cài đặt entrypoint | `./scripts/worktree_uv.sh run --project vds_cli ...` |

---

**Tiếp theo**: [Con đường từ Zero đến Productive Developer](../tutorials/zero-to-productive-developer.md)
