---
name: ntapp-brownfield
description: 'Chạy trọn luồng Brownfield (Track A) khi hệ thống ĐÃ CÓ CODE chạy nhưng không có (hoặc thiếu) tài liệu: phát hiện code repo → design system từ code FE → system-overview baseline → reproduce kiến trúc as-is (HLD + Module 0 + WBS) → REVIEW đối chiếu code → (SA duyệt) → nếu có yêu cầu mới: grill → triage → append WBS → slice plan (hoặc chia slice WBS as-is). Tự nhận biết đã xong tới đâu và chạy tiếp; dừng ở mỗi gate HITL. Sử dụng khi người dùng nói "chạy brownfield", "đã có code", "dựng tài liệu từ code", "onboard hệ thống cũ".'
---

# NTAPP Brownfield — một lệnh từ code có sẵn tới slice plan

Orchestrator mỏng: KHÔNG tự viết baseline/HLD/WBS/slice, chỉ gọi đúng skill theo đúng thứ tự (Track A trong `CLAUDE.md` + `reproduce_architecture.yaml`). Chạy được nhiều lần — mỗi lần đọc state rồi làm bước kế tiếp.

Đối số (`$ARGUMENTS`, tuỳ chọn): flag forward cho reproduce (`--repos a,b`, `--workspace-root <path>`, `--force`, `--skip-qa`) và/hoặc mô tả yêu cầu mới cần phát triển trên hệ cũ.

Đường dẫn: `OUT = NTAPP-output`, `S1 = OUT/Stage_1_Discovery`, `S2 = OUT/Stage_2_Architecture`.

## Bước 0 — Preflight (luôn chạy)

1. Phải đứng ở spec repo (có `NTAPP-output/` và `CLAUDE.md`).
2. **Tìm code repo**: thư mục cùng cấp với spec repo (hoặc `--workspace-root` / `--repos`) có marker `package.json` / `pom.xml` / `build.gradle` / `go.mod` / `pyproject.toml` / `Cargo.toml` / `*.csproj` / `Package.swift` … Liệt kê repo tìm được, phân loại FE / BE theo stack.
   Không có repo nào → **DỪNG**: hướng dẫn clone code repo cạnh spec repo (cùng thư mục cha) rồi gõ lại lệnh; hoặc nếu thật sự chưa có code → `/NTAPP-docs-to-slice`.
3. Kiểm tra skill gọi được: `NTAPP-system-overview`, `NTAPP-vsaf-reproduce-architecture`, `NTAPP-slice-planning` `bmad-review-adversarial-general` (+ `NTAPP-ds-bootstrap` nếu có FE repo; + `grill-with-docs`, `NTAPP-feature-triage`, `NTAPP-architecture-design` cho bước yêu cầu mới).
   Thiếu → **DỪNG**, hướng dẫn `! vsaf sync NTAPP --skills-only`, thoát và mở lại `claude`, gõ lại lệnh.
4. Bootstrap chưa chạy với repo mới (code repo chưa có `.bmm-config.yaml`) → nhắc `! ./scripts/bootstrap.sh --upgrade`.

## Bước 1 — Xác định state và chọn bước

Chọn bước ĐẦU TIÊN chưa xong rồi nhảy tới đó. In bảng state ngắn trước khi làm.

| # | Bước | Xong khi |
|---|---|---|
| A | Design system | không có FE repo, HOẶC có `OUT/design-system/` master DS (`registry.yaml` nếu ≥2 FE repo) |
| B | System overview | có `S1/system_overview/_overview.md` |
| C | Reproduce kiến trúc | có `S2/project_wbs.md` + `architecture_design.md` + `00_system_connectivity_integration.md` |
| R | Review tài liệu | `S2/reviews/stage2_review.md` có `reviewed:` khớp `body_sha` hiện tại của 3 file C (+ `_overview.md`) |
| D | Duyệt Stage 2 | 3 file C có `approved_by` + `approved_at`, review không còn 🔴 `open` (hoặc đã ký `approved_with_open`), workflow đã resume qua gate |
| E | Yêu cầu mới? | người dùng đã trả lời |
| F | Grill + triage | có `S1/CONTEXT.md` cho yêu cầu này + decision file của triage |
| G | Append WBS | unit mới đã có trong `project_wbs.md` (chỉ lane-3/4) |
| H | Slice plan | có `S2/slices/SLICE-*.md` mới hơn lần duyệt D/G |

Hash nội dung (bỏ front-matter — ký `approved_by` không làm review bị coi là cũ):
```bash
body_sha() { awk 'NR==1&&/^---$/{f=1;next} f&&/^---$/{f=0;next} !f' "$1" | sha256sum | cut -c1-12; }
```

## Bước 2 — Thực thi

Mỗi bước gọi qua `Skill(...)` — bắt buộc, KHÔNG thay bằng tự viết. Xong một bước → cập nhật bảng rồi sang bước kế; chỉ dừng ở gate hoặc khi cần người trả lời.

- **A. Design system** — có FE repo → `Skill("NTAPP-ds-bootstrap")` (Figma → hỏi trước, có thì chạy `/ntapp-figma-ingest --tokens-only` rồi ds-bootstrap `--external-tokens`). **≥2 FE repo: BẮT BUỘC xong A trước C** (WBS audit dùng `registry.yaml` để bind `unit → repo → DS`). Không có FE → skip.
- **B. System overview** — `Skill("NTAPP-system-overview")` mode baseline. Chạy TRONG phiên để Q&A với SA được hỏi đáp trực tiếp (workflow headless sẽ reuse baseline đã có, không chạy lại). Có thể chạy song song với A (write set rời nhau).
- **C. Reproduce kiến trúc** — `Skill("NTAPP-vsaf-reproduce-architecture")`, forward flag từ `$ARGUMENTS` (`--repos`, `--workspace-root`, `--force`). KHÔNG truyền `--force` nếu người dùng không nói. Ghi lại `runId` workflow trả về.
  - `input-gate` fail "WBS đã lock" → hỏi người dùng: thêm unit lẻ (sang E) hay dựng lại toàn bộ (`--force`).
- **R. Review tài liệu sinh từ code** — tài liệu reproduce chỉ đáng tin khi khớp code, nên review đối chiếu NGƯỢC về code:
  1. `Skill("bmad-review-adversarial-general")` trên `_overview.md` + `architecture_design.md` + `00_system_connectivity_integration.md` + `project_wbs.md`, đối chiếu code repo (chỉ ĐỌC): route/màn hình/API/job có trong code mà WBS thiếu unit; unit trong WBS không trỏ được tới code thật (bịa); contract trong Module 0 lệch request/response thật; tích hợp ngoài (SDK, URL, env key) bị bỏ sót; `consumes`/`used_by` hai chiều lệch; ID sai prefix (`SCR-*`/`WGT-*` cho UI); mô tả nghiệp vụ suy diễn quá mức so với code.
  2. Gộp vào `S2/reviews/stage2_review.md`: front-matter `reviewed: { <file>: <body_sha>, ... }` + `reviewed_at`, bảng `ID | Mức 🔴/🟡/⚪ | File | Vấn đề | Bằng chứng (path:line trong code) | Đề xuất sửa | Trạng thái`. Finding không có bằng chứng code → hạ xuống ⚪.
- **D. Duyệt Stage 2 (HITL — DỪNG)** — in số finding theo mức + danh sách 🔴, chờ người dùng gõ:
  - **"sửa F1,F3"** → sửa qua skill sở hữu file (WBS/HLD: `Skill("NTAPP-architecture-design", "--append")`; baseline: `Skill("NTAPP-system-overview")`); chạm contract Module 0 → hỏi trước khi chạy FULL. Đánh `fixed`, quay lại R.
  - **"bỏ qua F2 vì …"** → `dismissed` + lý do (không xoá dòng).
  - **"duyệt, tên <X>"** → ghi `approved_by: "<X>"` + `approved_at: <ISO-8601 UTC>` vào front-matter 3 file C (còn 🔴 `open` → nhắc 1 lần; vẫn duyệt → thêm `approved_with_open: [IDs]`). Rồi tự chạy `! vsaf run NTAPP/reproduce_architecture --resume <runId>` (runId từ C; mất thì `! vsaf status`) để workflow qua gate, sau đó sang E.
  - KHÔNG bao giờ ký khi người dùng chưa nói "duyệt" kèm tên.
- **E. Yêu cầu mới?** — hỏi: có tính năng mới cần làm trên hệ này không? `$ARGUMENTS` đã mô tả thì dùng luôn.
  - Có → F.
  - Không → hỏi tiếp: chia slice cho WBS as-is (dùng khi cần làm lại / refactor / viết test theo lát) → H; hoặc dừng ở baseline tài liệu.
- **F. Grill + triage** — `Skill("grill-with-docs")` (output `S1/CONTEXT.md`, ADR `S1/adr/` theo CLAUDE.md §Override path; nhiều chức năng → grill TỪNG story). Rồi `Skill("NTAPP-feature-triage", "<intent đã grill>")` → đọc `lane`:
  - `lane-1-express` / `lane-2-quick-dev` → báo lệnh lane tương ứng (bảng §Chọn lane trong CLAUDE.md), DỪNG — không cần slice plan.
  - `lane-3-full-slice` / `lane-4-ad-hoc` → sang G.
  - `refused` → đọc lý do trong decision file, báo người dùng, DỪNG.
- **G. Append WBS** — unit chưa có trong WBS → `Skill("NTAPP-architecture-design", "--append")`. Skill escalate FULL (chạm contract Module 0 / đổi module boundary) → báo người dùng, KHÔNG tự chạy FULL. Lane-4 → báo `/NTAPP-vsaf-ad-hoc-per-unit <unit_id>`, DỪNG.
- **H. Slice plan** (lane-3, hoặc as-is theo E) — `Skill("NTAPP-slice-planning")`. In bảng slice (ID · tên · AFK/HITL · units · blocked_by). Có drift finding → báo; nhắc slice plan cần SeniorDev + SA duyệt trước khi chạy `/NTAPP-vsaf-slice-loop <slice_id>`.

## Quy tắc

- Không bao giờ ghi `approved_by` nếu người dùng chưa nói rõ.
- Hook BLOCK → báo lý do, KHÔNG lách bằng `BROWNFIELD_REPRODUCE=1` / `SKIP_PRECOMMIT=1` trừ khi người dùng yêu cầu.
- Lệch giữa code và PRD/Epics (nếu có) → **code (as-built) thắng**, flag cho SA reconcile, không tự sửa.
- KHÔNG đọc/ghi gì trong code repo ngoài việc skill con làm; mọi artifact vào `NTAPP-output/`.
- Cuối mỗi lượt: in bảng state A–H (✅ / ⏸ chờ ký / ⏭ skip / ⬜) + lệnh tiếp theo người dùng cần làm.
