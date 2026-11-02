# STEP 05: VALIDATION GATE & OPEN QUESTIONS (§5)

> **Thực hiện bởi:** Agent UXS0 (UX Sketch Lead — Sally) + User (PM/BA/PO)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — emphasize **R6, R10**.

## 1. Mục tiêu

2 task:
1. **Validation gate (R6):** Trình parts §1-§4 cho PM/BA/PO review. Capture feedback, loop back nếu cần.
2. **Capture Open Questions for HLD (§5):** Document câu hỏi technical mà UX không tự trả lời được — cần Tech Lead trả lời ở Stage 2.

## 2. Đầu vào

- §1 Executive Brief (Step 01)
- §2 Rough Personas (Step 02)
- §3 Rough IA + §4 Primary Journey (Step 03 + 04)

## 3. Chỉ thị thực thi

### 3.1. Validation Gate với User

Trình bày cho User (PM/BA/PO):

1. **Recap §1-§4:** đường link parts + tóm tắt 1 đoạn cho mỗi section.
2. **Critical questions trước khi approve:**
   - Personas có capture đúng user thật không, có actor nào miss không?
   - Navigation tree có match user mental model không?
   - Integration points (§3.2) có đúng existing systems list không?
   - Primary journey có cover happy path đúng không, có step nào miss không?

3. **Loop back logic:**
   - Persona issues → loop back Step 02 (UXS1)
   - IA issues → loop back Step 03 (UXS0)
   - Journey issues → loop back Step 04 (UXS0)

**KHÔNG approve nếu:** PM/BA/PO không xác nhận → loop back, không bypass (R6).

### 3.1b. Sketch preview **HI-FI** — render + annotate (`sketch_preview: lavish` — default **ON**)

Preview là **review surface chính** của gate này, không phải phụ lục của §3.1: human mở HTML trong lavish, click ĐÚNG element cần đổi, comment tại chỗ → agent map comment về part file, sửa, re-render. Fidelity mặc định là **hi-fi** (trông như sản phẩm thật, dùng component + token thật) — KHÔNG phải wireframe grayscale, vì reviewer PM/BA/PO phản hồi chính xác hơn nhiều khi thấy giao diện thật thay vì hộp xám.

| `sketch_preview` | Hành vi |
|:--|:--|
| `lavish` (**default**) | Hi-fi render (§(a)+(b)) + vòng annotate lavish (§(c)) |
| `lofi` | Wireframe grayscale inline-CSS, không CDN (hành vi v1) — chọn khi PM chỉ cần soi flow và muốn tránh anchor visual sớm |
| `off` | Không render (vd Figma đã có hi-fi — xem `bmm-config.template.yaml`) |

#### (a) Resolve design source — 3 bậc, dừng ở bậc đầu tiên có kết quả

1. **User chỉ định** look / design system cụ thể trong prompt → dùng cái đó.
2. **Master DS của project** (đường mặc định — Stage 0 `/ntapp-ds-bootstrap` chạy TRƯỚC Stage 1 trong happy path): resolve DS root theo `{design_system_root}/_shared/ds-resolution.md` **nhánh F** (cosmetic, read-only: family root → 1 DS thì lấy DS đó → ≥2 DS lấy `default_ds`; không có `default_ds` thì hỏi user 1 lần, headless thì lấy system đầu + WARN). Đọc `{ds_root}/master_token.json`, **dereference** mọi ref `{global.*}` về giá trị literal, map sang theme vars DaisyUI:

   | DaisyUI var | master_token.json (semantic tier ưu tiên) |
   |:--|:--|
   | `--color-primary` / `--color-primary-content` | `semantic.color.action.primary` / `semantic.color.text.on-action` (thiếu → tính contrast từ primary) |
   | `--color-base-100` / `--color-base-200` / `--color-base-300` | `semantic.color.background.default` / `background.subtle` (alt) / `border.default` |
   | `--color-base-content` | `semantic.color.text.main` |
   | `--color-info` / `--color-success` / `--color-warning` / `--color-error` | `semantic.color.status.*` |
   | `--radius-box` / `--radius-field` / `--radius-selector` | `semantic.layout.radius-lg` / `radius-base` / `radius-sm` |
   | `body { font-family }` | `global.font.family.*` (sans mặc định của product) |

   Có `{ds_root}/_reference/` (screenshots + visual-notes từ ds-bootstrap) → xem 1-2 ảnh để bám **style character thật** của product (mật độ, cách dùng border/shadow), đừng chỉ đúng màu.
3. **Chưa có Master DS** (greenfield thuần, Stage 0 chưa chạy) → DaisyUI theme `{sketch_preview_theme}` (default `corporate`) as-is; ghi rõ ở header preview: *"placeholder look — project chưa bootstrap Master DS"*.

**Guardrail token (R3):** token chỉ để **skin** preview. KHÔNG sinh token mới, KHÔNG ghi lại `master_token.json`, KHÔNG suy ra component mapping. Preview hi-fi **không phải** visual đã được DS approve — quyền chốt token/component vẫn ở Stage 4b (`[REUSE AUDIT]` + contrast pre-check). Token thiếu key → để DaisyUI default, KHÔNG bịa giá trị.

#### (b) Render preview HTML — LUÔN chạy, kể cả headless

Preview là artifact retained cho downstream nên render không phụ thuộc lavish/npx (agent tự viết HTML).

1. **Slug:** `{feature_slug}` = kebab-case tên feature / yêu cầu nâng cấp đang sketch (từ §1 Executive Brief hoặc intent triage; sketch v0 toàn dự án lần đầu → slug tên project). Vd: `merchant-kyc-upgrade`.
2. **Path:** `{planning_artifacts}/previews/{feature_slug}_ux_sketch_preview.html` (default resolve: `NTAPP-output/Stage_1_Discovery/ux_sketch/previews/`). File **RETAINED — commit cùng sketch** (render-evidence + visual seed cho feature-design Stage 4a). KHÔNG phải SSoT: `ux_sketch.md` + parts vẫn canonical — sửa flow thì sửa part rồi re-render, KHÔNG sửa tay HTML. *(Pre-commit hook không soi `.html` — `CODE_EXTENSIONS` không chứa `html` → commit preview không vướng Rule 1/4/6/9.)*
3. **`<head>`:** CDN snippet của lavish (`npx -y lavish-axi design` để lấy version hiện hành — Tailwind browser v4 + DaisyUI v5 + themes) + `<style>` override theme vars từ (a) bậc 2 + **inline base fallback ~20 dòng** (font, `card` border, spacing, table) để file vẫn đọc được khi mở offline không có CDN. Set `<html data-theme="...">`. KHÔNG `@apply` class DaisyUI trong `<style type="text/tailwindcss">` (1 utility lạ làm sập toàn bộ compile).
4. **Nội dung:**
   - **Header:** feature slug, số journey / số frame, **design source dòng 1** (`ds_id` + path `master_token.json`, hoặc "placeholder DaisyUI `{theme}`"), 1 dòng cảnh báo *"visual chưa qua DS audit — Stage 4b mới chốt component/token"*, và 1 dòng **cách mở lại để annotate**: *"Đang xem bản tĩnh (`file://`)? Comment trực tiếp lên element chỉ có khi mở qua lavish: `npx -y lavish-axi \"<path>\"`"* — kèm chính lệnh đó ở comment dòng đầu file (`<!-- lavish: npx -y lavish-axi "…" -->`) để người mở bằng editor cũng thấy. Lý do bắt buộc: chrome annotate do server inject, bản trên đĩa tĩnh có chủ đích ((d)).

     `<path>` viết **relative từ repo root** (vd `NTAPP-output/Stage_1_Discovery/ux_sketch/previews/x_ux_sketch_preview.html`), TUYỆT ĐỐI không ghi absolute path — file này commit vào repo, `/Users/<tên bạn>/...` vừa vô dụng với người khác vừa lộ layout máy. Và **KHÔNG ghi session URL vào preview / `ux_sketch.md` / Preview Index**: URL chỉ đúng trên máy đang chạy session (xem (d) mục 5), commit vào là link chết cho mọi người khác.
   - **§3 IA:** render nav tree bằng `menu` / `navbar` thật (không phải `<pre>` ASCII tree), item cấp 2 nằm trong submenu.
   - **Mỗi journey:** flow đặt trong `<pre class="mermaid">` với ĐÚNG Mermaid sequence của §4 + snippet init Mermaid theme-aware từ `lavish-axi design`. **KHÔNG tự vẽ box-and-arrow bằng div/flex** — lavish biến `.mermaid` thành whiteboard Excalidraw sửa được, div thì không.
   - **Mỗi screen của Screen Intent Table (§4) = 1 frame hi-fi:** chọn component DaisyUI theo cột `Role` — form → `fieldset`+`input`/`select`/`textarea`; list/table → `table table-zebra` trong `overflow-x-auto`; dashboard → `stats` + `card`; review/confirm → `card` + `modal-box` look; empty/loading state → `skeleton`/`alert`. CTA = `btn btn-primary` với label ĐÚNG cell `Primary CTA`. Branch = `alert alert-warning` (hoặc `badge badge-warning`) ghi trigger ĐÚNG cell `Branch`. Bọc frame trong `mockup-window` / `mockup-phone` theo platform.
   - **Placeholder content:** dữ liệu đại diện đúng kiểu + đúng domain (tên/mã/số/ngày format thật của nghiệp vụ). KHÔNG lorem ipsum, KHÔNG bịa business rule mới (R3) — thiếu thông tin thì để `[TBD - cần PM/BA confirm]` hiển thị nguyên văn trên frame.
   - **Gate decision block (cuối trang):** mỗi section §1-§4 một cặp radio `Approve` / `Cần sửa` + `textarea` note (playbook `input` của lavish). Human quyết ngay trong artifact, khỏi paste lại vào chat.
5. **Anchor + annotation traceability contract (BẮT BUỘC — đây là thứ làm comment map được về part file):**

   | Element | Attribute bắt buộc |
   |:--|:--|
   | Frame | `<section id="{screen_slug}" data-journey="{journey_slug}" data-screen-name="{Screen}" data-sketch-src="§4.{j} row {n}">` |
   | Content block | `data-block="{tên đúng cell Content blocks}"` |
   | CTA | `data-cta="{label}"` |
   | Branch indicator | `data-branch="{trigger}"` |
   | Nav item | `data-nav="{path}"` (section IA: `id="ia-tree"`) |
   | Persona card (nếu render §2) | `data-persona="{name}"` |

   `{screen_slug}` = kebab-case của cột `Screen` trong Screen Intent Table §4 (1-1) — phải khớp bảng **Preview Index** step-06 ghi vào cuối §4. Mỗi frame có footer 1 dòng nhỏ: `Trace: Epic X / Story Y — §4.{j} row {n}`.
6. **Emoji:** KHÔNG dùng emoji trong preview — icon thì inline SVG hoặc bỏ (giữ đồng bộ với pre-commit Rule 9 downstream).

#### (c) Vòng annotate lavish — mặc định khi session interactive

Headless/CI bỏ qua (c) — (b) vẫn render, review markdown như §3.1. Opt-out: `.bmm-config.yaml` block `ntapp-ux-sketch:` đặt `sketch_preview: off` (hoặc `lofi` nếu chỉ muốn hạ fidelity).

1. **Mở review — AGENT chạy lệnh, không phải user:** `npx -y lavish-axi "{planning_artifacts}/previews/{feature_slug}_ux_sketch_preview.html"` rồi poll:
   `npx -y lavish-axi poll "…_ux_sketch_preview.html" --agent-reply "UX Sketch {feature_slug}: {X} journey / {Y} frame, skin bằng {design source}. Click element nào cần đổi rồi comment tại chỗ; quyết Approve/Cần sửa ở block cuối trang."`

   Lệnh mở tự bật browser (trừ `--no-open` / `LAVISH_AXI_NO_OPEN=1`) và in **session URL** `http://127.0.0.1:4387/session/{key}` — **báo URL này cho user ngay**, vì đó là surface annotate được DUY NHẤT (xem (d)). Browser không tự bật (sandbox/headless-ish) → đưa URL để user tự click, KHÔNG bắt user gõ lệnh.

   Poll để **foreground** (hoặc background job harness tự track được — Claude Code `run_in_background`); TUYỆT ĐỐI không `&` / `nohup` / detached. Poll bị kill → chạy lại, feedback đã queue không mất.
2. **Map feedback → sửa part → re-render:**

   | Loại feedback lavish trả về | Xử lý |
   |:--|:--|
   | Annotation trên element có `data-block` / `data-cta` / `data-branch` | Sửa ĐÚNG cell đó của Screen Intent Table trong `uxs0_journey_part.md` (Step 04) |
   | Annotation trên `data-nav` / section `ia-tree` | Sửa §3 nav tree (Step 03) |
   | Annotation trên `data-persona` | Loop back Step 02 (UXS1) |
   | Prompt tag `whiteboard` (user sửa flow trong Excalidraw) | Đọc `summary` trước, mở `scenePath`/`previewPath` chỉ khi cần → cập nhật **Mermaid source** trong part; KHÔNG ghi scene ngược lại |
   | Gate decision block | Section nào `Cần sửa` → loop back step tương ứng §3.1; tất cả `Approve` → gate pass |

   Sửa part xong → re-render (b), giữ `{screen_slug}` ổn định trừ khi screen đổi tên (đổi tên thì sửa cả Preview Index step-06). Rồi poll lại kèm `--agent-reply` báo đã áp gì.
3. **Layout issue:** lavish chỉ trả `layout-warnings` khi user tự queue → sửa file preview, KHÔNG coi là finding của sketch. Fatal `artifact_failures` (review surface không dùng được) → sửa HTML ngay rồi mở lại.
4. **Guardrails** như CLAUDE.md: **CẤM `lavish-axi share`**; telemetry tắt `LAVISH_AXI_TELEMETRY=0`. `npx` fail (offline / sandbox exit lạ) → thử `node "$(npm root -g)/lavish-axi/dist/cli.mjs" …`; vẫn fail → fallback review §3.1 markdown, KHÔNG block gate ((b) đã render nên downstream không ảnh hưởng).
5. **KHÔNG `lavish-axi end` ở step này** — session phải sống tiếp tới bàn giao Step 06. Xem (d).

#### (d) Vòng đời session — mở 1 lần ở (c), đóng ở bàn giao Step 06

**Sự thật kỹ thuật phải nhớ (đừng để user tự khám phá):** file `.html` trên đĩa là **tĩnh có chủ đích** — lavish giữ artifact portable và chỉ inject chrome annotate (`/chrome-client.js`) vào bản **server phục vụ**. Hệ quả:

| Cách mở | Annotate được? |
|:--|:--|
| Session URL `http://127.0.0.1:4387/session/{key}` (sau `lavish-axi <file>`) | ✅ — đây là đường duy nhất |
| Double-click / `file://` bản trong `previews/` | ❌ read-only, xem thôi |
| `lavish-axi export` (bản portable inline asset) | ❌ — export/share KHÔNG bao giờ kèm annotation SDK. **KHÔNG bao giờ chỉ user chạy `export` để "tương tác"** — đó là bản đọc offline |

Vì vậy:

1. **Mở 1 lần** ở (c) rồi **giữ nguyên** qua mọi vòng loop-back (§3.1 → Step 02/03/04 → quay lại đây) và qua Step 06. Re-render (b) ghi đè đúng file → lavish watch file, browser tự reload; KHÔNG cần mở lại session.
2. `npx -y lavish-axi end` chỉ chạy **một lần duy nhất** ở [step-06](./step-06-assembly.md) §3.4, sau khi user xác nhận xong bàn giao.
3. User bấm **Send & End** trong browser (poll trả về tín hiệu kết thúc) → session đã đóng bởi user: KHÔNG tự mở lại. Step 06 §3.4 chỉ đưa lệnh reopen cho user, không tự chạy (`--reopen` chỉ khi user yêu cầu review tiếp).
4. **Mở lại sau này** (ngày hôm sau, người khác review): đúng 1 lệnh, và URL không đổi vì `{key}` = sha256(absolute path) của file preview:
   ```bash
   npx -y lavish-axi "{planning_artifacts}/previews/{feature_slug}_ux_sketch_preview.html"
   ```
   Server tự tắt khi idle (~30 phút, `LAVISH_AXI_IDLE_TIMEOUT_MS`) — URL cũ chết tạm thời, chạy lại lệnh trên là sống lại **cùng URL**. Lệnh này phải nằm trong: header preview + comment đầu file HTML ((b) mục 4) + báo cáo bàn giao step-06 §5.
5. **Phạm vi truy cập của session URL — machine-local, KHÔNG phải link chia sẻ:**

   | Sự thật | Hệ quả vận hành |
   |:--|:--|
   | Server bind `127.0.0.1` mặc định (`LAVISH_AXI_HOST` mới đổi được) | Người khác click cùng URL là gõ vào loopback **của họ** → không thấy gì. Không share URL như link review |
   | `{key}` = sha256(**absolute path**) | Khác máy = khác home dir = khác key. URL không portable kể cả khi cùng repo |
   | `/session/{key}` **không có auth** (403 trong server là chặn Host-header + cross-origin, không phải xác thực) | Key là địa chỉ, không phải mật khẩu: mọi tiến trình/người dùng chạm được `127.0.0.1:4387` trên máy đó đều mở được |

   Vì vậy: **KHÔNG commit session URL** vào bất kỳ artifact nào (preview, `ux_sketch.md`, Preview Index) — chỉ nói trong chat/handoff của phiên đang chạy. **CẤM** bind ngoài loopback (`LAVISH_AXI_HOST=0.0.0.0`) để "cho PM máy khác xem": chính CLI cảnh báo đó là server **không xác thực** có thể đọc và phục vụ file tuỳ ý trên máy. Reviewer ở máy khác → họ pull repo (preview là artifact committed) rồi tự chạy lệnh mục 4 trên máy mình; annotation của họ về agent của họ, không chảy về phiên của bạn.

### 3.2. Capture Open Questions for HLD (§5)

Sau khi parts §1-§4 approved, UXS0 review TOÀN BỘ sketch và list các câu hỏi technical chưa rõ. Mỗi câu hỏi:

| Field | Yêu cầu |
|:--|:--|
| **Question** | Câu hỏi cụ thể, không generic |
| **Why it matters** | Impact lên UX hoặc architecture |
| **Trace** | Ambiguity cụ thể trong PRD/Epics §X — KHÔNG hỏi chung chung |

**Examples of GOOD questions:**
- "State machine cho Merchant cần bao nhiêu state? PRD §3 chỉ nhắc 'pending', 'active' — có cần 'inactive' / 'on hold'?"
- "Sub-Merchant có flow delegation riêng không? PRD §5 mô tả Merchant cấp 1 + Sub Merchant nhưng không rõ ai approve sub-merchant."
- "KYC verification là sync hay async? Ảnh hưởng UX có cần 'đang xử lý' state."

**Examples of BAD questions (reject):**
- "Architecture nên dùng tech stack gì?" — không liên quan UX.
- "API có response format gì?" — TechSpec concern, không phải UX.
- "Performance cần ra sao?" — NFR concern, đã có trong PRD §NFR.

**Quality gate:** Nếu Open Questions không có câu nào → check lại, có thể đã bịa hoặc miss thinking. Sketch tốt thường phát hiện 3-7 Open Questions vì PRD/Epics không bao giờ đủ detail.

### 3.3. Append vào uxs0_journey_part.md

Append §5 Open Questions table vào cuối `{intermediate_folder}/uxs0_journey_part.md`.

## 4. Đầu ra yêu cầu

- [ ] §1-§4 approved by PM/BA/PO (validation gate pass — qua Gate decision block của preview hoặc reply markdown)
- [ ] §5 Open Questions table hoàn tất, mỗi câu hỏi có Why + Trace
- [ ] Preview hi-fi retained: `{planning_artifacts}/previews/{feature_slug}_ux_sketch_preview.html` (§3.1b (b) — design source ghi ở header + anchor/`data-*` contract cho Preview Index step-06)
- [ ] Session lavish còn **sống**, session URL đã báo cho user, CHƯA chạy `end` (§3.1b (d) — Step 06 §3.4 mới đóng). Ngoại lệ duy nhất: user tự Send & End trong browser.
- **Lưu trữ:** Append `{intermediate_folder}/uxs0_journey_part.md` (§3 + §4 + §5)
- Báo cáo: "Validation pass. §5 Open Questions hoàn tất với X câu hỏi cho Tech Lead."

## NEXT
[step-06-assembly.md](./step-06-assembly.md)
