---
name: sdlc-e2e
description: Nối SRS đã duyệt của vsaf thành bộ E2E Robot Framework chạy được + CI. Điều phối project-docs → test-scenarios → rf-* → jenkins. Trigger /sdlc-e2e <feature> [--platform web|android|ios|api].
user-invocable: true
argument-hint: "<feature> [--platform web|android|ios|api]"
disable-model-invocation: true
---

# sdlc-e2e — E2E pipeline bridge (vsaf → rf-agentskills)

> Ngôn ngữ giao tiếp: tiếng Việt. Không sửa skill rf-agentskills. Chỉ commit khi user yêu cầu.

## Tiền đề & cấu hình
Đọc `vsaf-e2e.config.json` ở gốc workspace: `srsRoot`, `vsafRoot`, `productBaseUrls`.
`FEATURE` = argument đầu; `PLATFORM` = cờ `--platform` (mặc định `web`).

## Guard (dừng sớm — chạy TRƯỚC mọi việc)
```bash
python3 .claude/skills/sdlc-e2e/scripts/vsaf_e2e_bridge.py check "<FEATURE>" --srs-root "<srsRoot>" --cwd .
```
- exit 2 → in lý do, DỪNG (SRS thiếu / đang ở template repo). Không đoán.
- exit 0, dòng `GATE: APPROVED_MARKER` → SRS có marker duyệt máy-đọc → tiếp tục.
- exit 0, dòng `GATE: NEEDS_CONFIRM` → in phần "gate context" cho user, rồi **HỎI**:
  "SRS `<FEATURE>` đã được duyệt (APPROVED/GO) để chạy E2E chưa? Trả lời 'yes' để tiếp tục."
  CHỈ tiếp tục khi user xác nhận `yes`; nếu không → DỪNG. (Guard KHÔNG tự quyết định — SRS thật không có field gate đáng tin.)

## Bước 1 — Seed domain-docs từ SRS
Gọi skill **project-docs** ở mode "từ file/text", nguồn = `<srsRoot>/<FEATURE>/05-srs.md`
(+ `06-testcases-e2e.md` nếu có). Sau bước này BẮT BUỘC có `.claude/skills/<project>-domain/`;
nếu chưa có → DỪNG, báo user.

## Bước 2 — Sinh kịch bản E2E
Gọi skill **test-scenarios** `<FEATURE>` (Mode A) → `docs/test-cases/<FEATURE>/<FEATURE>.md` (TC-NNN, 6 góc nhìn).

## Bước 3 — (tùy chọn) Chiến lược
Gọi skill **test-strategy** `<FEATURE>` → `docs/test-strategy/<FEATURE>/strategy.md`.
Trách nhiệm: KHÔNG lặp case đã có ở tầng RestAssured contract test (D4).

## Bước 4 — Tự động hoá
Theo `PLATFORM` gọi đúng skill: **rf-web** | **rf-android** | **rf-ios** | **rf-api**
(rf-db tự kích hoạt khi TC cần DB). URL/endpoint lấy từ `productBaseUrls[<FEATURE>]`.
Chạy `robot` tới khi TC pass (hoặc fail ở bước dự kiến) với staging.

## Bước 5 — (tùy chọn) CI + traceability
- Gọi skill **jenkins** dựng/cập nhật pipeline (CI E2E = Jenkins, D3).
- Ghi con trỏ traceability:
```bash
python3 .claude/skills/sdlc-e2e/scripts/vsaf_e2e_bridge.py trace "<FEATURE>" --vsaf-root "<vsafRoot>" \
  --tc "docs/test-cases/<FEATURE>/<FEATURE>.md" \
  --suite "tests/<FEATURE>.robot" [--jenkins "<job>"]
```

## KHÔNG được
- Sửa file trong `.claude/skills/rf-*`, `project-docs`, `test-scenarios`… (chạy nguyên bản).
- Hardcode URL/credential (đọc từ config / `global-data.md`).
- Commit `results/` hay secret.
