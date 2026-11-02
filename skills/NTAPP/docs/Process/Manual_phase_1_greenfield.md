# Manual Phase 1 — Track Greenfield (dự án mới từ con số 0)

> **File này = workflow chi tiết cho dự án greenfield.** Đọc theo thứ tự từ trên xuống.
>
> Set up onboard (bootstrap → skill check → repo), vai trò & approve, bảng slash command, pre-commit rules, multi-repo — đều là **cơ chế dùng chung**, nằm ở **[Manual_phase_1.md](Manual_phase_1.md)** (Hub). Làm xong PHẦN A của Hub (onboard) rồi quay lại đây chạy workflow.
>
> Bức tranh tổng 2-phase (batch → per-slice loop): Hub [mục 2](Manual_phase_1.md#2-bức-tranh-tổng-quan--5-stage). Vai trò ai approve stage nào: Hub [mục 4](Manual_phase_1.md#4-vai-trò-quyền-approve--handoff). Bảng slash command đầy đủ: Hub [mục 5](Manual_phase_1.md#5-bảng-slash-command--skill-xung-đột).

---

## 1. Greenfield là gì

Dự án mới — **chưa có code / hệ thống đang chạy**. Foundation (kiến trúc, WBS) được **build mới hoàn toàn từ PRD**, không reconstruct từ cái có sẵn. **Design System** không dựng ở batch phase — chuẩn hoá thành 1 pass sau khi xong toàn bộ slice ([mục 7](#7-chuẩn-hoá-design-system--sau-khi-xong-toàn-bộ-slice)).

**Multi-repo vẫn áp dụng:** spec repo riêng + code repo riêng (giống brownfield). Code repo lúc đầu có thể trống / chỉ scaffold — vẫn tách repo để giữ portability và đồng nhất với pattern brownfield. Setup workspace: Hub [§3 Set up onboard](Manual_phase_1.md#3-set-up-onboard--bootstrap--skill-check--repo) + [§7 Multi-repo](Manual_phase_1.md#7-multi-repo-nếu-áp-dụng).

---

## 2. Đường đi (sequence khởi động)

> **Chạy `./scripts/bootstrap.sh` TRƯỚC mọi skill.** Bootstrap script auto-detect spec repo + code repo (greenfield code repo có thể trống / chỉ scaffold — vẫn cần detect), sinh `<project>.code-workspace` + `.bmm-config.yaml` per repo, symlink `.agent/skills/` cross-repo. Chưa chạy → skill không nhận diện đúng các repo trong workspace (đặc biệt khi tới pass chuẩn hoá DS `/ntapp-ds-bootstrap` ở [mục 7](#7-chuẩn-hoá-design-system--sau-khi-xong-toàn-bộ-slice) cần multi-root). Lần đầu: `./scripts/bootstrap.sh`; dev mới join: `--refresh`; nâng single → multi-repo: `--upgrade`. Chi tiết: Hub [§3 Set up onboard](Manual_phase_1.md#3-set-up-onboard--bootstrap--skill-check--repo) + [README.md](../../README.md).

Greenfield đi **thẳng pipeline batch → per-slice loop** từ Stage 1, **không** có phase reconstruct baseline.

```
— Phase batch (1 lần per project) —
Stage 1:  Discovery       → PRD + Epics & Stories   (+ UX Sketch optional)
Stage 2:  Architecture    → HLD (architecture) + Module 0 + project_wbs (function list).md (lock)
Stage 2b: Slice Planning  → SLICE-* manifest (DAG + seam cuts)
Stage 3b: System UX Spec  → ux_design.md (batch 1 lần, TOÀN hệ thống — nếu multi-screen mới)

— Phase per-slice (lặp cho từng SLICE-N) —
Stage 3a → Stage 4a (kế thừa UX Spec) → Stage 4c → Stage 5 → demo SLICE-N → học → điều chỉnh slice tiếp

— Sau khi xong TẤT CẢ slice (1 lượt đầy đủ) —
Chuẩn hoá Design System: /ntapp-ds-bootstrap (extract từ code đã build) → /ntapp_ui_generation + /ntapp-ds-build-component
```

**Có Figma vẽ trước thì thứ tự trên đảo một chỗ** — xem [mục 5b](#5b-stage-08--figma-ingest-chỉ-khi-có-figma-vẽ-trước):

```
— Phase batch (khi có Figma) —
Stage 0 pre:  /ntapp-figma-ingest --tokens-only     → figma-tokens.w3c.json
Stage 0:      /ntapp-ds-bootstrap --external-tokens → master_token.json  ← SỚM, seed từ Figma (không phải từ code)
Stage 1 → Stage 2 (WBS lock) → Stage 2b
Stage 0.8:    /ntapp-figma-ingest (full)            → mapping unit↔frame + layout spec + PNG   ← có cổng ký của người
Stage 3b → vòng lặp per-slice (offline, không gọi Figma)
```

> **Quy tắc vàng (cả 2 track):** không skip stage trong cùng 1 vòng (code unit U chỉ bắt đầu sau khi DD(U) + UI Schema(U) approve); không batch spec (Stage 3a-4 chỉ chạy cho unit thuộc SLICE-N đang build). *Ngoại lệ: Stage 3b (UX Spec) là batch toàn feature 1 lần TRƯỚC vòng lặp — không per-slice.*

Các mục dưới đây là cơ chế chi tiết từng stage **theo thứ tự greenfield**.

---

## 3. Stage 1 — Discovery (PM/BA/PO)

**Mục tiêu:** từ idea → PRD + danh sách Epic & Story — điểm bắt đầu của greenfield.

### Stage 1 pre-step — Làm rõ ý tưởng `/grill-with-docs` (optional)

**Khi nào dùng:** Mới chỉ có **ý tưởng** xây mới / nâng cấp nhưng **chưa làm rõ luồng, kịch bản và các edge case** có thể có. Chạy `/grill-with-docs` trước khi triage để biến ý tưởng mơ hồ thành mô tả đủ rõ — tránh `/ntapp-feature-triage` refuse early vì yêu cầu chưa rõ ràng.

**Người làm:** Bất kỳ ai khởi tạo feature (PM/BA/Dev).

**Cách làm:**
1. Gõ `/grill-with-docs`. Skill phỏng vấn liên tục từng câu một (one-at-a-time), đào từng nhánh decision tree: luồng chính, actor, kịch bản, edge case, ranh giới khái niệm — đối chiếu với `CONTEXT.md` (glossary domain) + code hiện có, bắt mâu thuẫn thuật ngữ tại chỗ.
2. Khi một khái niệm/quyết định chốt, skill cập nhật **`context.md`** (glossary domain) inline; quyết định khó đảo ngược + có trade-off thật → offer ghi ADR (`docs/adr/`).
3. Trả lời tới khi đạt shared understanding → có **`context.md`** mô tả rõ luồng + kịch bản + edge case.

**Output:** `context.md` (+ ADR nếu có). **Dùng làm đầu vào cho Triage:** `/ntapp-feature-triage --file=context.md` (thay cho mô tả 1 câu ở §3.1).

**Approve:** không cần — đây là bước làm rõ, không phải gate.

> Skip được khi ý tưởng đã có tài liệu mô tả chi tiết và rõ ràng (đi thẳng `/bmad-create-prd`). `/grill-with-docs` **không thay** PRD — nó chỉ sharpen intent đầu vào.

**Cách làm:**
1. Mở IDE, gõ `/bmad-create-prd`. Cung cấp intent (1-2 đoạn: vấn đề + user — hoặc nội dung `context.md` từ pre-step trên).
2. Agent hỏi clarification — trả lời từng câu, không skip.
3. Có PRD draft → gõ `/bmad-create-epics-and-stories` để sinh Epic + Story.
4. PM/PO/BA review, request iterate. OK → commit `prd.md`, `epics.md`.

**Output:** `{planning_artifacts}/prd.md`, `epics.md`.

**Approve:** PM (PRD), BA (Epic & Story).

> Stage 1 **KHÔNG sinh `project_wbs.md`**. WBS sẽ do Agent C tạo và Agent E lock ở Stage 2 — sau khi kiến trúc xác định module thật. Đừng tự viết WBS thủ công.

### Stage 1 sub-step — UX Sketch (optional)

**Người làm:** UX Designer. PO co-approve.

**Khi nào dùng:** Sau khi PRD + Epics approved, trước khi trigger Stage 2. Hữu ích khi PRD/Epics còn nhiều ambiguity về user interaction (sketch buộc PM/BA chi tiết hóa) hoặc Tech Lead muốn xem UX flow trước khi design HLD.

**Cách làm:**
1. Gõ `/ntapp-ux-sketch`. Skill đọc PRD + Epics, sinh sketch nhẹ (5 phần: Executive Brief + Rough Personas + Rough IA + Primary Journey (Mermaid + Screen Intent Table) + Open Questions for HLD).
2. Skill chạy 2 sub-agent, ~1-2 ngày.
3. Output: `ux_sketch.md` (latest) + snapshot trong `archive/` + **preview hi-fi** `previews/{feature_slug}_ux_sketch_preview.html` (skin bằng token Master DS nếu Stage 0 đã chạy).
4. UX Designer trình PM/BA/PO review **trên preview trong lavish** — reviewer click thẳng element cần đổi và comment tại chỗ, agent map về Screen Intent Table rồi re-render (hạ fidelity: `sketch_preview: lofi`; tắt: `off`). **Agent tự mở session và đưa link `http://127.0.0.1:4387/session/{key}`** — reviewer không phải gõ lệnh gì; session giữ sống tới lúc bàn giao xong nên comment muộn vẫn được ghi ngược vào sketch. Mở lại sau này: `npx -y lavish-axi "<đường dẫn preview>"` (URL không đổi). Mở thẳng file `.html` bằng browser hoặc dùng `lavish-axi export` thì chỉ **xem** được, không comment được — đó là thiết kế của lavish (chrome annotate do local server inject).
5. Handoff cho SA: Rough IA inform module breakdown, Open Questions là input cho HLD/Module 0.

**Output:** `{planning_artifacts}/ux_sketch/ux_sketch.md`. **Approve:** UX Designer + PO.

> **Sketch ≠ Master UX Spec.** Sketch là v0 nhẹ để inform HLD. Master UX Spec đầy đủ vẫn cần ở **Stage 3b** sau khi HLD ra. Pre-commit hook Stage 5 check `ux_design.md` (full Master), KHÔNG check sketch.
>
> **Khi skip sketch:** Greenfield đơn giản (≤ 3 modules, không tích hợp hệ thống ngoài) → skip được. Stage 3b vẫn generate Master UX Spec from scratch.

---

## 4. Stage 2 — Architecture (SA)

**Mục tiêu:** HLD toàn hệ + Module 0 (contract giữa các sub-system) + **`project_wbs.md`** (lock — binding source cho cả workflow).

> **Greenfield không có baseline.** HLD + Module 0 + WBS dựng **fresh** từ PRD/Epics — không có hệ thống cũ để scan, bỏ qua hẳn `/ntapp-system-overview` (skill này default mode `baseline`).

**Cách làm:**
1. Đảm bảo Stage 1 đã approve.
2. Gõ `/ntapp-architecture-design`. Skill chạy 6 sub-agent (Context, Research, Architect, Security, Module-0, Orchestrator).
3. **2 gate quan trọng:**
   - **Gate WBS Audit:** Agent C tạo `project_wbs.md` từ template 4-cột (theo PRD/Epics + module boundary trong HLD). Agent E audit 100% coverage vs PRD/Epics. Phải PASS thì workflow mới chạy tiếp. Fail → Agent C buộc sửa WBS.
   - **Gate handshake:** nếu `project_wbs.md` đã tồn tại sai format → Agent E hỏi SA: backup `.bak` rồi tạo lại, hay SA tự sửa? Đừng để agent ghi đè work cũ.
4. SA review HLD + Module 0 + WBS. Đặc biệt chú ý Module 0 — **đây là contract khoá**, đổi sau này tốn nhiều.
5. Module 0 thay đổi ảnh hưởng compliance → submit Compliance review trước khi merge.

**Output:** `architecture_design.md` + `00_system_connectivity_integration.md` + **`project_wbs.md`** (lock).

**Cấu trúc WBS:** Mỗi module khai báo 1 trong 4 type, mỗi type liệt kê đơn vị work tương ứng:

| Module type | Đơn vị work | Naming convention | Đặc tính |
|---|---|---|---|
| `backend-service` | `features` | `{MODULE_PREFIX}-NN` (vd `HUB-01`) | BE component: API endpoint, consumer, job |
| `frontend-app` | `screens` + `widgets` | `SCR-{NAME}` + `WGT-{NAME}` | Screen = top-level route. Widget = cross-cutting (sidebar, banner, wrapper) |
| `integration-contract` | `contracts` | `INT-{SRC}-NN` | API/event contract giữa 2 module |
| `infrastructure` | `features` | `{MODULE_PREFIX}-NN` | Observability, ops, platform |

Quan hệ giữa các đơn vị work khai báo tường minh trong WBS: mỗi `screen` ghi `consumes: [<feature_id>...]`; mỗi `widget` ghi `used_by: [<screen_id>...]` nếu cross-screen; mỗi `contract` ghi `provider` + `consumers`. Đây là source-of-truth cho Stage 4c story bridge và pre-commit hook ID lookup.

**Approve:** SA. Compliance co-approve nếu có Module 0 changes.

> **Sau khi WBS lock,** mọi `feature_id` / `screen_id` / `widget_id` / `contract_id` ở Stage 3+ phải lấy từ `project_wbs.md`. Cần thêm/đổi đơn vị work sau lock → trigger lại Agent C cập nhật + Agent E re-audit, **không sửa thủ công**.


---

## 5. Stage 2b — Slice Planning (Senior Dev / SA / BA)

**Mục tiêu:** Gom các unit trong `project_wbs.md` thành các **vertical slice** (tracer bullet) demoable end-to-end, sort theo dependency. Slice plan là input cho vòng lặp Stage 3-5.

**Khi nào chạy:** Sau khi Stage 2 lock `project_wbs.md` + Module 0. Trước khi trigger bất kỳ skill Stage 3.

**Cách làm:**
1. Gõ `/ntapp-slice-planning`. Skill đọc `project_wbs.md` (bắt buộc) + Module 0 + Epics. KHÔNG cần DD.
2. Skill đề xuất slice theo seam test: **Ownership** (không vắt qua quá nhiều team owner), **Auth-foundation** (slice auth build trước slice consume auth), **Resilience** (slice external dependency tách khỏi in-house-only), **In-house vs external** (giữ in-house slice AFK-able tối đa).
3. 2 gate: **Coverage** (mọi unit P0 nằm trong ≥1 slice) + **DAG** (slice N chỉ depend 1..N-1, no cycle).
4. Output: `Stage_2_Architecture/slices/SLICE-{n}-{title}.md` — front-matter gồm `slice_id`, `title`, `type` (AFK/HITL), `units: [{id, type, story}]`, `blocked_by`, `enhanced_by`, `parent_epics`, `demoable`, `seam_rationale`.
5. Review: Slice 1 (tracer bullet) phải đụng đủ layer (BE + FE + contract); không slice ≥8 unit; DAG hợp capacity team.
6. Approve → commit slice manifests.

**Output:** `NTAPP-output/Stage_2_Architecture/slices/SLICE-*.md`. **Approve:** Senior Dev + SA.

> **Slice rule:** Group không merge (mỗi unit vẫn sinh story riêng ở 4c); slice được cross-epic; AC sống trong story file (4c), slice chỉ link; **slice plan không lock cứng như WBS** — học từ slice N → update slice N+1 (re-run `/ntapp-slice-planning`). Phát hiện cần thêm unit → quay lại Stage 2 update WBS rồi re-run slice planning.
>
> **Khi skip Stage 2b:** Greenfield siêu nhỏ (≤ 3 unit toàn bộ) hoặc PoC throwaway — mỗi unit chạy spec-build độc lập theo thứ tự ad-hoc. Vượt 3 unit → bắt buộc chạy 2b.

---

## 5b. Stage 0.8 — Figma Ingest (chỉ khi có Figma vẽ trước)

**Bỏ qua toàn bộ mục này nếu không có Figma.** Greenfield mặc định đi đường ở [mục 7](#7-chuẩn-hoá-design-system--sau-khi-xong-toàn-bộ-slice): build trước, chuẩn hoá DS sau.

**Figma vẽ trước làm đảo thứ tự đó** — và đây là điểm quan trọng nhất của mục này. Lý do greenfield hoãn DS là *"seed rỗng khi chưa có gì"*. Có Figma thì không còn rỗng: **Figma chính là nguồn để seed DS**, dù chưa có một dòng code FE nào. Nên với greenfield + Figma:

| | Greenfield mặc định | Greenfield + Figma vẽ trước |
|---|---|---|
| `/ntapp-ds-bootstrap` chạy khi nào | **Sau** khi xong toàn bộ slice (extract từ code thật) | **Trước** Stage 1 (seed từ Figma qua `--external-tokens`) |
| Nguồn `master_token.json` | Code FE đã build | Figma Variables / Styles / Tokens Studio export |
| `components_metadata.json` lúc đầu | Đầy đủ (quét code thật) | **Gần như rỗng** (chưa có code) → `figma-ds-map.md` chỉ có phần token, phần component mỏng |
| Pre-commit Rule 4/6/7 | Tự skip trong lúc build, enforce lại từ pass chuẩn hoá | **Enforce ngay từ slice đầu** (vì `master_token.json` đã tồn tại) |

Cột cuối là cái đắt nhất phải biết trước: **kỷ luật token siết ngay từ slice 1**, dev không còn giai đoạn "styling tạm". Đó là đánh đổi có lợi khi đã có Figma (token đã chốt sẵn, không phải đoán), nhưng phải nói với team trước khi bắt đầu, đừng để họ gặp hook chặn rồi mới biết.

**Hai pass, không gộp được.** `ds-bootstrap` cần file token từ Figma để hoà giải; full ingest cần `master_token.json` để snap giá trị về token. Chạy một lượt là deadlock.

**Cách làm:**
1. **Pass 0 — token** (trước Stage 1): từ **spec repo**, `export FIGMA_TOKEN=...` rồi `/ntapp-figma-ingest --tokens-only` + link Figma → `figma-tokens.w3c.json`.
2. **Seed DS**: từ **code repo**, `/ntapp-ds-bootstrap --external-tokens <path file trên>`. Code repo greenfield còn trống → skill quét được 0 component (log greenfield, bỏ qua bước visual reference) và `master_token.json` gần như thuần từ Figma. Đúng như mong đợi, không phải lỗi.
3. Chạy Stage 1 → Stage 2 (WBS lock) → Stage 2b như thường.
4. **Pass 2 — full ingest** (sau Stage 2b, trước vòng lặp): `/ntapp-figma-ingest`. Skill harvest frame, gom state (`default`/`empty`/`loading`/`error`), rồi **dừng ở cổng HITL** để bạn ký bảng `WBS unit ↔ frame`. Ký xong nó trích layout spec (Auto Layout → **Layout Groups** gần như 1-1), export PNG, đối chiếu DS, ghi checksum.
5. Commit spec repo. Vòng lặp per-slice từ đây chạy **offline** — không gọi Figma.
6. **Sau vài slice có code FE thật → chạy lại `/ntapp-figma-ingest`.** Lúc này `components_metadata.json` đã có nội dung nên phần component của `figma-ds-map.md` mới thực sự hữu ích (bậc reuse C-1 ở Stage 4b). Lần đầu ingest map component mỏng là bình thường.

**Bốn tình huống lệch:** giống brownfield — xem [§3.3b](Manual_phase_1_brownfield.md#33b-stage-08--figma-ingest-chỉ-khi-feature-có-figma-vẽ-trước) (frame mồ côi là màn thật → thêm unit vào WBS trước, không để Figma sinh unit; unit thiếu frame → author mode, không chặn).

**Ai là nguồn sự thật cho cái gì:** bảng phân vai ở Hub [§2](Manual_phase_1.md#2-bức-tranh-tổng-quan--5-stage) — Figma thắng về bố cục/chữ; Master DS thắng về token; DD §3 + Module 0 thắng về dữ liệu; `ux_conventions.md` thắng về thông báo lỗi/nhãn trạng thái; WBS thắng về danh sách unit.

**Output:** `design-system/.../_reference/figma/` (`figma-manifest.yaml`, `specs/`, `frames/`, `figma-ds-map.md`, `token-gap-report.md`). **Approve:** người ký bảng mapping.

---

## 6. Vòng lặp per-slice — Stage 3 → 4 → 5

**Mặc định: chạy engine `vsaf`.** Sau khi slice plan approve ([mục 5](#5-stage-2b--slice-planning-senior-dev--sa--ba)), build một SLICE-N = gõ MỘT lệnh:

```
/NTAPP-vsaf-slice-loop <slice_id>     # vd /NTAPP-vsaf-slice-loop SLICE-01
```

Engine chạy nguyên DAG Stage 3→4→5 (techspec → UX → DD → ui-schema → DS-build → story → ATDD → dev → commit), **dừng ở HITL demo gate**; resume bằng `/NTAPP-vsaf-resume <runId>`. Lặp cho từng SLICE-N theo `blocked_by` — slice trước demo PASS → mở slice tiếp. Spec **on-demand** (chỉ chạy unit thuộc slice đang build), không batch upfront: slice 1 build xong → học → spec slice 2 dựa kiến thức đó.

> **Prerequisite:** `project_wbs.md` lock (Stage 2) + slice plan approve (Stage 2b). Chưa có cả 2 → KHÔNG trigger.

> ⚠️ **Greenfield — lưu ý Design System:** DAG của engine có cả node Stage 4b (ui-schema + ds-build), trong khi greenfield cố ý **hoãn** chuẩn hoá DS sang [mục 7](#7-chuẩn-hoá-design-system--sau-khi-xong-toàn-bộ-slice) (Master DS chưa tồn tại trong vòng loop). Muốn giữ đúng mô hình hoãn-DS của greenfield → chạy **fallback thủ công** bên dưới (bỏ qua Stage 4b trong vòng) cho tới khi xong toàn bộ slice rồi mới chuẩn hoá DS.
>
> **Project có Figma vẽ trước thì lưu ý trên KHÔNG áp dụng** — Master DS đã seed từ Figma từ đầu ([mục 5b](#5b-stage-08--figma-ingest-chỉ-khi-có-figma-vẽ-trước)), nên chạy engine full DAG (gồm Stage 4b) là đúng, không cần fallback thủ công để né. Trong vòng lặp, unit `figma_status: mapped` → Stage 4a chạy **TRANSCRIBE mode** (chép từ `specs/` + `frames/`, ghi `figma_ref` + Deviation log) và Stage 4b thêm bậc reuse "Figma-mapped". Engine **không gọi Figma** ở bất kỳ node nào. Designer sửa Figma sau khi DD đã ký → Hook 3 chặn (so checksum), chạy lại `/ntapp-figma-ingest` **ngoài** vòng lặp rồi `/NTAPP-vsaf-resume <runId>`.

**Fallback khi engine lỗi / cần can thiệp từng bước:** chạy tay tuần tự theo phần dưới — cùng thứ tự, cùng gate, cùng approver, chỉ khác là gõ từng lệnh thay vì engine tự lái.

### Fallback thủ công — chạy tuần tự từng stage (khi engine lỗi)

> Dùng khi engine `vsaf` lỗi, cần dừng/can thiệp ở một stage cụ thể, hoặc giữ mô hình hoãn-DS của greenfield. Đây là **đúng chuỗi stage mà engine tự động hoá**; gõ tuần tự, lặp cho từng SLICE-N.

#### Stage 3b — System UX Spec (batch, toàn hệ thống) → Stage 3a — TechSpec per module (per-slice)

**Thứ tự:** 3b chạy **batch 1 lần TRƯỚC vòng lặp**; 3a chạy **per-slice TRONG vòng lặp**. Cả hai consume PRD + HLD.

- **Stage 3b (`/ntapp-ux-design`)** — thiết kế **1 Master UX Spec cho TOÀN BỘ hệ thống cần build** (union mọi `SCR/WGT`, **không per-slice** — SCR/WGT liên quan trải rải rác nhiều slice nên trải nghiệm phải design holistic 1 lần), chạy ngay sau slice plan approve, trước khi mở vòng per-slice. **Có điều kiện:** chỉ chạy khi feature multi-screen mới (≥2 `SCR-*` nối journey / actor mới) — *pass khởi tạo greenfield mặc nhiên qualify vì mọi journey đều mới*; feature mở rộng về sau reuse-journey / single-screen / BE-only → **skip** (gate SSoT: `ntapp-ux-design` step-01 §2.0).
- **Stage 3a (`/ntapp-technical-design`)** — per-slice, trigger chỉ cho module có unit thuộc SLICE-N (chưa có → tạo mới; đã có → update incremental). `feature-design` (4a) trong vòng kế thừa phần liên quan từ Master UX Spec đã có.

> **Prerequisite:** `project_wbs.md` lock (Stage 2) + slice plan approve (Stage 2b). Chưa có cả 2 → KHÔNG trigger Stage 3.

**Stage 3a — TechSpec per module** (Tech Lead / Module Owner):
1. Gõ `/ntapp-technical-design`, cung cấp tên module.
2. Skill chạy 4 sub-agent (Scope Audit, Strategy, Modeling, Implementation). Scope Audit check module declare đủ đơn vị work trong WBS.
3. Output: `{module}_techspec.md` + snapshot. Tech Lead review. Cần đổi Module 0 → quay lại Stage 2.

**Approve:** Tech Lead.

> **Scope rule:** TechSpec chỉ đặc tả đơn vị work thuộc module sở hữu — BE module liệt kê features; FE module liệt kê screens + widgets; integration module liệt kê contracts. UI control consume 1 BE feature → đặt trong techspec FE module, KHÔNG copy sang BE.

**Stage 3b — System UX Spec** (UX Designer chính, PO + BA co-approve):
1. Gõ `/ntapp-ux-design`. Skill đọc PRD + Epics + HLD + Module 0 (state enum) + Master DS (nếu đã có — greenfield chưa chuẩn hoá DS thì bỏ qua), optionally `ux_sketch.md`. Sinh 1 master UX Spec cho cả hệ thống.
2. Step đầu chạy Inheritance Audit — lock actor list từ HLD, module list từ WBS, state enum từ Module 0.
3. Skill chạy 5 sub-agent qua 14 step → document gồm 5 layer: Foundation, Architecture, Core Journeys, Cross-cutting, Appendix.
4. Output: `ux_design.md` + snapshot.

**Approve:** UX Designer + PO + BA.

#### Stage 4a — Detailed Design (Senior Dev)

**Per slice:** chỉ chạy cho unit thuộc SLICE-N đang build. (Greenfield **không chạy Stage 4b UI Schema trong vòng slice** — UI Schema + Design System gom vào pass chuẩn hoá sau toàn bộ slice, xem [mục 7](#7-chuẩn-hoá-design-system--sau-khi-xong-toàn-bộ-slice).)

**Stage 4a — Detailed Design per đơn vị work** (Senior Dev cho BE feature / FE screen/widget logic; UI Engineer cho FE UI behavior):
1. Đảm bảo TechSpec module + UX Spec đã approve.
2. Gõ `/ntapp-feature-design`, cung cấp ID đơn vị work (`feature_id` / `screen_id` / `widget_id` từ WBS).
3. Skill chạy 5 sub-agent (Overview, Logic, Data, UI, QA) song song. UI auto-skip khi ID là BE feature; Data auto-skip khi widget không state riêng.
4. **Wireframe convention** (chỉ FE artifact — sub-agent F3 emit §2.2):
   - Mỗi control trong ASCII wireframe có annotation `[control_id]` snake_case, khớp 1:1 cột "Tên control" bảng UI Controls (§2.3). Vd `[input_merchant_code] [button_search 🔍[search]]`.
   - Emoji = **visual hint**, KHÔNG phải UI element thực. Mỗi emoji kèm `🔍[icon-name]` (kebab-case). Content emoji thực: prefix `content:` vd `🎉[content:celebration]`.
   - **Bảng Icon Legend** dưới wireframe — bắt buộc khi có ≥1 emoji (3 cột: Emoji | Icon name | Mục đích).
   - **Bảng Layout Groups** dưới Icon Legend — bắt buộc khi có ≥2 sibling control hoặc form multi-field (4 cột: Group ID | Type | Members | Props). `Type` chọn từ 10 canonical layout primitive (Stack/Cluster/Grid/Spacer/Center/Box/FormField/FieldGrid/Sidebar/Switcher). Pass chuẩn hoá DS (mục 7) consume bảng này khi sinh `ui_schema`.
5. Output: `{id}_detailed_design.md` (wireframe + Icon Legend + Layout Groups khi áp dụng).
6. Senior Dev review (logic matrix + KBKT).

**Approve:** Senior Dev.

#### Stage 4c — Story Bridge (Senior Dev / BA)

**Chạy SAU 4a cho unit của SLICE-N, TRƯỚC Stage 5.** Vai trò duy nhất: bridge từ NTAPP layered design (DD) sang BMAD story file format mà `/bmad-dev-story` và `/bmad-testarch-atdd` consume.

**Cách làm:** (gate: slice plan có ở 2b, 4a cho unit của SLICE-N approve)
1. **Xác định scope mỗi story** (chỉ unit thuộc SLICE-N):
   - **BE story:** 1 story per `feature_id` của BE module trong SLICE-N.
   - **FE story:** 1 story per `screen_id` thuộc SLICE-N — cover toàn màn hình + widget mà screen consume.
   - **Widget story:** chỉ tạo riêng khi (a) cross-screen widget có thay đổi đáng kể, hoặc (b) widget build trước screen consumer.
2. Gõ `/bmad-create-story` cho từng story scope. **Bắt buộc tag `slice_id: SLICE-N`.** Input bridge từ NTAPP artifacts:
   - **Story foundation** (Story statement + AC) ← DD §1 + DD §5.2 (KBKT) — case `P0` convert sang Given/When/Then.
   - **Tasks/Subtasks** ← DD §3.2 (Logic Matrix); FE story bổ sung wireframe + Layout Groups (DD §2.2).
   - **Dev Notes** ← HLD (Stage 2) + TechSpec (3a) của module sở hữu.
   - **Testing Requirements** ← KBKT P0/P1 từ DD §5.2.
   - **Demo context** ← `demoable` của SLICE-N manifest.
3. Skill tự exhaustive analyze: previous story intelligence, git intelligence, latest tech research.
4. Output: `NTAPP-output/Stage_5_Build_Verify/{epic}-{story}-{title}.md`.
5. Senior Dev review: AC khớp KBKT P0; Dev Notes đủ context; Tasks khớp Logic Matrix; `slice_id` trỏ SLICE-N manifest tồn tại; status `ready-for-dev`.

**Approve:** Senior Dev.

> **Khi skip 4c:** Path B quick-dev (bug fix, refactor nhỏ, chore) không cần story file — gõ `/bmad-quick-dev` trực tiếp.
>
> **Sprint tracking (optional):** dùng `sprint-status.yaml` → chạy `/bmad-sprint-planning` 1 lần per epic để initialize.

#### Stage 5 — Build & Verify (Dev / QA)

**Per slice:** build **theo thứ tự SLICE-N** — chỉ pick story có `slice_id = SLICE-currently-active`. Slice trước build xong + demo PASS → mới mở slice tiếp.

**Cách làm:**
1. Tạo branch `feature/{id}` ở code repo (id = unit ID của story scope thuộc SLICE-N active). Khuyến nghị `/superpowers-using-git-worktrees` cho parallel work nội bộ slice.
2. **Phân loại ATDD trước khi code** — tiêu chí canonical ở Hub [§5.1 Phân loại Mandatory ATDD](Manual_phase_1.md#51-phân-loại-mandatory-atdd-canonical); enforce bằng Hook 8 `atdd_classifier.sh`.
   - **Mandatory** nếu khớp ≥1 trigger: **Nhóm A (test-level)** A1 cross-system (≥2 service) · A2 multi-actor/stateful (duyệt, handoff, đa-trạng-thái) · A3 async/eventual-consistency/resilience; **Nhóm B (blast-radius)** B1 critical-domain (money/auth/RBAC/PII-audit) · B2 destructive/irreversible.
   - **Fallback:** không khớp A/B nhưng fail gây thiệt hại đo được hoặc có audit requirement → **Mandatory** (QA Lead ghi `atdd: mandatory|optional` vào front-matter story — override thắng classifier).
   - **Optional** cho còn lại (UI tweak, copy/i18n, config, refactor không đổi behavior, spike/POC). *Bugfix-regression KHÔNG ở gate này — thuộc pipeline bugfix.*
   - **Khi Mandatory, trước bước 3:**
     - a. **Setup framework (1 lần per module):** multi-root workspace mở cả spec + code repo. Code repo chưa có framework → `/bmad-testarch-framework` (tự nhận stack, scaffold vào `<code-repo>/tests/`). Setup log `framework-setup-progress.md` ở `<code-repo>/NTAPP-output/test-artifacts/` (live, KHÔNG sync). Có legacy framework → SKIP.
     - b. **Generate red-phase tests per feature:** `/bmad-testarch-atdd` với story file làm input. Output: test code → `<code-repo>/tests/{e2e,api,...}/{id}.spec.*`; live checklist → `<code-repo>/NTAPP-output/test-artifacts/atdd-checklist-{story_key}.md`.
     - c. Chạy test — verify FAIL vì assertion (chưa code), KHÔNG vì syntax/import error.
     - d. Commit tests riêng: `test(<id>): add ATDD red-phase scaffolds`. Trước khi commit implementation.
3. **Chọn path code-gen:**
   - **Path A — Story-driven (formal):** `/bmad-dev-story` đọc story file. Skill enforce red-green-refactor per subtask + DoD gate. KHÔNG cần lặp lại `/superpowers-test-driven-development`.
   - **Path B — Quick (informal):** `/bmad-quick-dev` cho bug fix, refactor nhỏ, chore — không cần 4c. KHÔNG enforce test-first → dev follow up `/superpowers-test-driven-development` cho logic phức tạp.
4. Mỗi file code phải có header `// id: <ID> | dd_version: <vN>` (1 key `id:`, loại unit qua ID prefix). Hook reject nếu thiếu / sai prefix vs đuôi file. Chi tiết: Hub [§6](Manual_phase_1.md#6-quy-tắc-bắt-buộc--không-bypass).
5. Trước khi tạo PR, dev tự kiểm (lần lượt): `/superpowers-systematic-debugging` (khi gặp bug); `/superpowers-verification-before-completion` (chạy thật test/build/lint, lưu output trước khi nói "xong"); `/bmad-code-review` (3 lớp adversarial — đọc findings, sửa lỗi rõ, ghi lý do nếu chọn không sửa); nếu Mandatory ATDD: kiểm tests đã FAIL → PASS.
6. **Tạo PR bằng `/superpowers-finishing-a-development-branch`** (Option 2 — Push and create PR). Skill chạy lại test suite trước push (gate cuối), sinh PR template chuẩn, giữ worktree để sửa khi có feedback.
7. **QA Lead review PR** — workflow riêng QA, Manual không enforce cách cụ thể. Tối thiểu: execute KBKT manual từ Stage 4a (human exploratory). Có thể mở rộng: đọc diff bằng judgment, chạy `/bmad-code-review` lần 2, pair review.
8. Dev nhận feedback → `/superpowers-receiving-code-review` (chống "yes-man" + push back mơ hồ).
9. QA sign-off + merge. Audit trail (commit SHA, timestamps, PR body, comment) lưu trong git history.

**Approve:** Dev review (peer) + QA sign-off.

> **Demo SLICE-N** → học → quay lại Stage 2b update slice tiếp theo nếu cần. Build story phải thuộc `slice_id` đang active (chỉ build story trong slice active).
>
> **Dual-repo Stage 5:** Code repo giữ live artifacts (test code, configs, framework setup log, atdd-checklist). Spec repo không lưu doc per-feature — audit trail dựa git history code repo. KHÔNG sync live artifacts giữa 2 repo. Phân loại artifact: CLAUDE.md §"Dual-repo cho Stage 5".

---

## 7. Chuẩn hoá Design System — sau khi xong toàn bộ slice

Sau khi build + demo PASS **toàn bộ slice** (1 lượt đầy đủ), code FE thật đã tồn tại → giờ mới chạy bộ skill DS để **chuẩn hoá Design System**. Greenfield cố ý hoãn DS tới đây: `/ntapp-ds-bootstrap` extract DS từ **code thật đã build** (đúng thế mạnh của nó), thay vì seed rỗng khi chưa có gì.

> **Ngoại lệ — project có Figma vẽ trước:** DS đã được seed từ Figma **ngay từ đầu** ([mục 5b](#5b-stage-08--figma-ingest-chỉ-khi-có-figma-vẽ-trước)), nên mục này không còn là "pass chuẩn hoá đầu tiên" mà là **pass làm giàu**: chạy `/ntapp-ds-bootstrap` chế độ incremental để bổ sung component thật đã build vào `components_metadata.json` (token đã có từ Figma, chỉ đối soát lại), rồi chạy lại `/ntapp-figma-ingest` để phần component của `figma-ds-map.md` có nội dung. Ghi chú pre-commit ở cuối mục này **không áp dụng** — Rule 4/6/7 đã enforce từ slice đầu vì `master_token.json` tồn tại sẵn.

**Người làm:** Design System Owner (+ UI Engineer cho UI Schema).

**Cách làm:**
1. **Extract Master DS** — mở multi-root workspace (spec + code repo). `/ntapp-ds-bootstrap` scan toàn bộ FE code đã build → `master_token.json` + `components_metadata.json` + `stack-profile.json` + `bootstrap_report.md`; DSO duyệt HIGH/MEDIUM/LOW. Nhiều FE repo → chạy 1 lần/repo, mỗi repo 1 DS (registry — [Hub §7.6](Manual_phase_1.md#76-multi-ds--nhiều-fe-repo-nhiều-design-system)). Cơ chế chi tiết (cùng skill): brownfield [Bước A1](Manual_phase_1_brownfield.md#bước-a1--design-system-bootstrap-từ-code-hiện-tại).
2. **Sinh UI Schema + delta** — `/ntapp_ui_generation` per `screen_id` / `widget_id` đã build → `ui_schema_{id}.json` + `proposed_ds_updates.md`. `layout` tree build từ wireframe + Layout Groups trong DD (Stage 4a §2.2).
3. **Apply delta** — `proposed_ds_updates.md` có `[NEW]` → `/ntapp-ds-build-component`: cập nhật Master DS, export token runtime sang code repo (`stack-profile.runtime_token_path`), scaffold/patch component. Thứ tự commit cross-repo: Hub [§7.2](Manual_phase_1.md#72-quy-trình-commit-khi-skill-chạy-xong).
4. **Refactor UI về token** — thay hardcoded color / px / font trong UI code bằng token Master DS; gắn header `id:` + đảm bảo `ui_schema_{id}.json` + `build_report.md` tồn tại cho từng UI unit.

**Approve:** Design System Owner + UI Engineer.

> **Pre-commit:** trong vòng build (Stage 5) UI dùng styling tạm, chưa có Master DS → token discipline (Rule 4), `ui_schema` (Rule 6), `build_report` (Rule 7) **tự skip khi `master_token.json` chưa tồn tại**, và **enforce trở lại TỪ pass chuẩn hoá này** (khi Master DS đã sinh). Chi tiết: CLAUDE.md §Workflow guardrails.
>
> Sau pass chuẩn hoá, mọi thay đổi DS đi qua Stage 4b (`/ntapp-ds-build-component`) như brownfield; feature mới đi qua Triage ([mục 8](#8-feature-đến-sau--triage--4-lane)).

---

## 8. Feature đến sau — Triage + 4 lane

Sau khi foundation đã có (PRD + WBS + HLD + Module 0 + DS), **mọi yêu cầu mới KHÔNG tự động đi full per-slice loop** — đi qua Feature Triage trước, **giống brownfield Phase B**.

1. **Mỗi feature mới → `/ntapp-feature-triage "1 câu mô tả"` TRƯỚC khi viết code/spec.** Skill scan state hiện tại + hỏi dev cheap-to-expensive (intent, module, scope, contract change, critical domain, audience, actor change), áp HARD GATES (refuse early nếu WBS missing / intent vague / multi-feature batch / Module 0 contract change / module mới / unit mới chưa trong WBS) → decision tree (first-match) chọn 1 trong 4 lane.
2. **4 lane:**

   | Tình huống | Lane | Đi tiếp |
   |---|---|---|
   | Lỗi nhỏ khớp 1/5 preset (typo/config/log/lint/test) | **Express hotfix** (L1) | `/NTAPP-vsaf-express-hotfix <preset> \| <intent>` (mini-DD + PR remote, compensate 48h — Hub [§6 Express lane](Manual_phase_1.md#6-quy-tắc-bắt-buộc--không-bypass)) |
   | Unit cũ có DD sẵn, chỉ fix/refactor | **Path B quick-dev** (L2) | `/NTAPP-vsaf-path-b-quick-dev <unit_id> \| <intent>` (Stage 5 Path B ở trên) |
   | Unit mới độc lập, chưa có DD, no contract change | **Ad-hoc per-unit** (L4) | `/NTAPP-vsaf-ad-hoc-per-unit <unit_id>` (skip Stage 2b → Stage 4-5) |
   | Feature lớn theo WBS + slice plan | **Full per-slice loop** (L3) | `/NTAPP-vsaf-slice-loop <slice_id>` (Stage 2b → vòng lặp Stage 3-4-5, mục 5-6 ở trên) |

   > **Lỗi phát hiện khi test / demo / UAT không nằm trong 4 lane này** — đi bug lane ([mục 8b](#8b-bug-lane--log--fix-sau-demo)): `/ntapp-log-bug` → `/ntapp-fix-bug` \| `/NTAPP-vsaf-fix-bug`. Ngược lại, yêu cầu dạng "sửa hành vi cho đúng ý mới" (chưa từng là lỗi được log) vẫn đi Triage → thường ra Lane 2.

3. Lane modifiers: `touches_critical_domain` (money/auth/RBAC/PII) → Mandatory ATDD trước first commit; `demo_audience=regulator` → `/bmad-testarch-nfr` + `/bmad-testarch-trace` trước sign-off; `introduces_new_actor` AND lane=3 → `/ntapp-ux-sketch` trước TechSpec; DS chưa bootstrap AND UI module → `/ntapp-ds-bootstrap` first.
4. Output decision file: `NTAPP-output/Stage_1_Discovery/triage/{YYYY-MM-DD}-{slug}.md` (recommended lane + reasoning + next command + refused paths + honest limits). Dev confirm bằng cách chạy command recommend.

**Bảng so sánh 4 workflow build:**

| | `express-hotfix` (L1) | `path-b-quick-dev` (L2) | `ad-hoc-per-unit` (L4) | `slice-loop` (L3) |
|---|---|---|---|---|
| **Input** | `preset_type + intent` | `unit_id + intent` | `unit_id` | `slice_id` |
| **Tiền điều kiện** | Preset khớp 5 loại | WBS + DD sẵn | WBS sẵn | WBS + slice plan + HLD + Master DS |
| **Sinh DD** | mini-DD ≤ 30 phút | ❌ (DD sẵn) | ✅ full | ✅ full per unit |
| **UI schema / DS / Story / ATDD** | ❌ | ❌ | ✅ | ✅ |
| **Code review** | ❌ | ✅ | ✅ | ✅ |
| **Output cuối** | **PR remote** | local commit | local commit | local commit |
| **HITL demo / close-out** | ❌ | ❌ | ❌ | ✅ flip `demo_status` + ghi ledger (`slice-ledger` + `knowledge/`) |
| **Technical debt** | ✅ compensate 48h | ❌ | ❌ | ❌ |

> **Honest limits — triage KHÔNG detect:** True scope, contract drift implicit, cross-slice ripple, DS token gaps tinh tế, test-first discipline trong Lane 2, stale slice plan. Ghi đầy đủ trong mỗi decision file.

---

## 8b. Bug lane — log & fix (sau demo)

Lỗi phát hiện khi test / demo / UAT **KHÔNG đi qua Triage** — triage là cổng vào của *yêu cầu mới*, không phải của *defect trên thứ đã build*. Bug có đường riêng 2 chặng: **log trước, fix sau** (đừng fix mò).

| Chặng | Lệnh | Làm gì |
|---|---|---|
| **1 — Ghi nhận** | `/ntapp-log-bug` | Mô tả bug (+ màn hình & ảnh **dán trong chat**, + API path/method) → skill suy WBS unit (màn → `SCR-*`/`WGT-*` trong `project_wbs.md`; API → grep techspec/DD/code) → suy SLICE từ `slices/*.md` → append entry `Open` vào `Stage_1_Discovery/Bugs_Issues/BUGS-{SLICE}-{account}.md` + copy ảnh vào `assets/{SLICE}/{account}/`. Opt-in đẩy Jira: `Bug` (lệch spec/DD) vs `Issue` (chạy đúng thiết kế nhưng nghiệp vụ chưa hợp lý → **cần người chốt**) |
| **2a — Vá tuần tự** | `/ntapp-fix-bug` | Nhận 1 file `BUGS-*.md` **hoặc** 1 mã Jira / URL `/browse/<KEY>`. Vá `in-place-nocommit` (**không commit**), doc-sync spec inline, flip trạng thái → `Fixed`. 2 HITL gate: duyệt fix plan · duyệt nội dung ghi lên Jira |
| **2b — Vá batch song song** | `/NTAPP-vsaf-fix-bug` | Nhận `--all` \| `SLICE-01,SLICE-02` \| path `BUGS-*.md`. Gom nhóm parallel-safe (`foundation` / `parallel` / `serial` / `needs-investigation`) → **1 HITL gate** `approve-plan` (`touch <batch_dir>/APPROVED` + `/NTAPP-vsaf-resume <runId>`) → fix song song trên `git worktree` riêng → `bug_batch_integration.md` + **MERGE ORDER**. KHÔNG merge, KHÔNG push, KHÔNG flip trạng thái |

**Bất biến của file log:** 1 file / 1 slice / 1 account · **append-only** (thêm bug mới không sửa bug cũ; ngoại lệ duy nhất là chèn dòng `Jira:` vào entry vừa tạo) · đánh số theo từng file (`account` nằm trong mã bug nên `{SLICE}-{account}-BUG-NN` vẫn duy nhất toàn project) · **không bịa** ảnh / steps / expected / actual — thiếu thì để trống. Khi đẩy Jira: **ghi file TRƯỚC, tạo Jira SAU** để Jira lỗi không làm mất bug.

**Việc "fix đúng 1 bug trên 1 unit" nằm ở engine dùng chung `NTAPP-bug-fix-engine`** (root-cause → DD gate → ATDD gate → fix tối thiểu → pre-commit 9 rule → verify → code-review → doc-sync), **ceremony thích ứng**: bug critical-domain / đổi contract → test-first RED→GREEN + DD reconstruct; bug vặt → fix + verify tĩnh. `severity` chỉ để sắp thứ tự, KHÔNG bật gate.

**Sau batch (thứ tự bắt buộc):** merge theo MERGE ORDER (foundation trước) → dọn worktree (`git -C <repo> worktree remove <wt>`) → **rồi mới** flip trạng thái bug trong `BUGS-*.md`. Flip trước khi merge = spec nói đã fix trong khi code chưa land.

> Greenfield có một đặc thù: trước pass chuẩn hoá Design System ([mục 7](#7-chuẩn-hoá-design-system--sau-khi-xong-toàn-bộ-slice)), UI còn dùng styling tạm nên Rule 4/6/7 tự skip — bug UI log ở giai đoạn này thường là *lệch styling tạm*, không phải lệch token. Đừng vá bằng cách hardcode giá trị; nếu cần token thật thì chạy chuẩn hoá DS trước.
>
> Chi tiết đầy đủ (bảng bất biến, phân loại `Bug` vs `Issue`, chuẩn bị Jira `env.md` / `project_key`, xử lý ảnh + TCC macOS, bug `needs-investigation`): [brownfield §3.6](Manual_phase_1_brownfield.md#36-bug-lane--log--fix-sau-demo) — quy trình bug lane **giống nhau ở cả 2 track**.

---

## 9. Khác biệt so với brownfield

| | Greenfield (file này) | Brownfield |
|---|---|---|
| **Bước đầu** | Stage 1 Discovery (PRD from scratch) | Reconstruct baseline (DS + arch từ code) |
| **Design System** | Chuẩn hoá SAU khi xong toàn bộ slice (extract từ code đã build) | Reconstruct từ codebase ngay đầu (Phase A) |
| **Nếu có Figma vẽ trước** | DS seed từ Figma **ngay đầu** (đảo thứ tự mặc định) → Rule 4/6/7 enforce từ slice 1; map component mỏng tới khi có code — [mục 5b](#5b-stage-08--figma-ingest-chỉ-khi-có-figma-vẽ-trước) | Figma chỉ bổ sung `--external-tokens` cho DS đã extract từ code; ingest per-feature ở Phase B ([§3.3b](Manual_phase_1_brownfield.md#33b-stage-08--figma-ingest-chỉ-khi-feature-có-figma-vẽ-trước)) |
| **Baseline discovery** | Skip — không có hệ thống cũ | `/ntapp-system-overview --mode baseline` + Contract Matrix |
| **WBS** | Build mới từ PRD/Epics | Derive từ hệ thống hiện có + yêu cầu mới |
| **Cửa ngõ việc mới** | Per-slice loop; feature đến sau cũng triage | Feature Triage ngay từ đầu (Phase B) |

→ Hệ thống đã tồn tại? Dùng **[Manual_phase_1_brownfield.md](Manual_phase_1_brownfield.md)** thay vì file này.
