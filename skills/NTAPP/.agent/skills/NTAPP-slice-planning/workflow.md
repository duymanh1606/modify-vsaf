# NTAPP Slice Planning — Workflow

Lập **kế hoạch vertical slice** từ `project_wbs.md` (lock ở Stage 2 — input bắt buộc duy nhất), enrich bằng Epics (Stage 1) + Module 0 (Stage 2) nếu có. Output là các **slice manifest** — mỗi manifest gom nhiều work unit thành một lát cắt demoable end-to-end. Chạy **NGAY SAU Stage 2 (WBS lock)**, **TRƯỚC vòng lặp per-slice Stage 3-4-5**, trả lời: *"unit nào nên build chung thành một increment tự demo được, và thứ tự build ra sao?"*

> **KHÔNG đọc DD.** Ở Stage 2b, DD (Stage 4a) chưa được tạo — DD chỉ xuất hiện on-demand cho unit thuộc slice đang active. Slice planning chỉ cần unit list + quan hệ trong WBS + contract surface từ Module 0; Epics (user story) là enrichment optional cho demoable + epic mapping. Khi hành vi của một unit chưa rõ từ WBS + Module 0, KHÔNG block → mark unit đó cần clarify ở Bước 4 (human approval gate) để SA/Senior Dev xác nhận intent trước khi commit slice.

## Nguyên tắc cốt lõi — GROUP, không MERGE

Slice là lớp grouping + ordering đặt **trên** story file, KHÔNG phải một story gộp nhiều layer:

- Mỗi work unit vẫn sinh **một story riêng** theo rule Stage 4c (BE per `feature_id`, FE per `screen_id`). Không trộn nhiều id vào một story → giữ pre-commit Rule 1/2 + scope rule Stage 3a (BE techspec ≠ UI control).
- Slice planning **không sinh story file**, chỉ quyết scope + thứ tự + grouping. Story file do `/bmad-create-story` sinh sau ở Stage 4c, tag thêm `slice_id`.
- **Acceptance criteria KHÔNG nằm trong manifest.** Story file chưa tồn tại lúc lập slice; AC sẽ sống trong story file. Manifest chỉ trỏ tới planned story ref của từng unit (link, không roll-up).
- **Một unit thuộc đúng một slice — KHÔNG bao giờ xé công việc của một unit ra nhiều slice.** Khác biệt cốt lõi so với slice tự do: granularity mịn đã có ở tầng story nên slice không cần xé nhỏ unit. Unit hub bị nhiều slice tiêu thụ → xử lý theo Bước 2 (Fan-in / hub-unit).
- Skill này **bắt buộc khi project >3 work unit** (Manual §4 Stage 2b). Skip chỉ cho PoC throwaway ≤3 unit. Bỏ qua → vòng lặp per-slice mất → quay về batch spec waterfall ở Stage 3-4 cho toàn WBS (anti-pattern, rework rate cao).

## Stage placement

```
Stage 2 (WBS lock + Module 0)
        │
        ▼
Stage 2b: /ntapp-slice-planning  (SKILL NÀY — sinh SLICE-*.md manifest)
        │
        ▼
— Vòng lặp per slice (SLICE-N) —
Stage 3a/3b   → spec on-demand cho module thuộc SLICE-N
Stage 4a/4b   → DD + UI schema cho unit thuộc SLICE-N
Stage 4c      → /bmad-create-story per unit, tag slice_id=SLICE-N
Stage 5       → Build + verify → demo SLICE-N
        │
        ▼
        học → re-run skill này update slice tiếp theo (xem mục "Re-run mode" dưới)
```

## Squad

Một agent (Amelia — `bmad-agent-dev`) chạy tuyến tính cả 5 bước; audit gate (Bước 3) là self-check theo checklist, không phải persona độc lập.

---

## Config resolution (paths)

Theo cùng cascade 3-layer như mọi NTAPP skill — đọc key chuẩn `planning_artifacts`, KHÔNG hardcode path:

- **Layer 1** — `{project-root}/_bmad/bmm/config.yaml`: default `planning_artifacts`, `stage_1_discovery`, `stage_2_architecture`, `stage_4_design`, `implementation_artifacts`, `document_output_language`.
- **Layer 2** — `{project-root}/.bmm-config.yaml` section `ntapp-slice-planning:`: override `planning_artifacts` (mặc định `{project-root}/NTAPP-output/Stage_2_Architecture/slices`).
- **Layer 3** — Interactive fallback nếu cả 2 miss.

Biến runtime sau cascade:

| Biến | Nguồn | Dùng cho |
|:--|:--|:--|
| `planning_artifacts` | Layer 1/2/3 | OUTPUT — chứa `SLICE-*.md` + `archive/` snapshot khi re-run |
| `stage_2_architecture` | Layer 1 | INPUT **bắt buộc** — đọc `project_wbs.md` (unit list + `consumes`/`used_by`) + `00_system_connectivity_integration.md` (Module 0 — contract surface giữa sub-systems, dùng cho seam Ownership + seam Trust/auth) |
| `stage_1_discovery` | Layer 1 | INPUT optional — đọc `epics.md` (Epic ID + user story = hành vi demoable) nếu có |

> **KHÔNG load `stage_4_design`.** Ở Stage 2b, DD chưa tồn tại — Stage 4a chạy on-demand cho từng slice SAU khi slice plan approved. Bất kỳ ambiguity về hành vi unit nào không suy ra được từ WBS + Module 0 → defer cho Bước 4 (human approval gate) clarify, không stop skill.

`{project-root}`: walk up từ `cwd` tìm `_bmad/` rồi `.git/`; không thấy → fallback `cwd` + warn.

---

## Quy trình

### Bước 1 — Pre-flight & load input

**Detect mode trước:**
- Slice plan chưa tồn tại trong `{planning_artifacts}/` → **Initial mode**: chạy full flow Bước 1→5.
- Slice plan đã có `SLICE-*.md` → **Re-run mode**: branch sang mục "Re-run mode" cuối file, KHÔNG chạy full flow lại.

**Stopping errors (DỪNG, không bịa) — Initial mode:**

| Điều kiện | Action |
|:--|:--|
| `project_wbs.md` không tồn tại / chưa lock | DỪNG — WBS là input bắt buộc duy nhất, làm contract cho slice. Yêu cầu chạy Stage 2 trước. |
| WBS không có work unit nào in-scope | DỪNG — không có gì để slice. |
| `00_system_connectivity_integration.md` (Module 0) thiếu | WARN — seam Ownership / seam Trust-auth giảm độ chính xác (không có contract surface map). Vẫn slice được nhưng audit Bước 3 G6/G7 sẽ ít deterministic hơn. |
| `epics.md` thiếu | WARN — vẫn slice được; derive demoable từ semantics của WBS unit, `parent_epics` để trống. |

Load 3 nguồn input:
- **WBS** (bắt buộc): unit list + `type` + `consumes`/`used_by`.
- **Module 0** (optional warn): contract surface giữa sub-systems → áp seam Ownership (in-house vs external) + seam Trust-auth (realm / shared key boundaries).
- **Epics** (optional warn): user story → enrich demoable framing + `parent_epics`.

Xác nhận với user **scope** sẽ slice (toàn bộ WBS hay một subset epic/module). CHỜ xác nhận.

### Bước 2 — Draft vertical slices

Gom work unit thành **tracer bullet** — lát cắt mỏng nhưng đi hết các layer liên quan, tự demo được.

**Rule gom slice:**

- Bắt đầu từ một **hành vi demoable** quan sát được bởi actor (vd "actor submit X và thấy kết quả Y"), không bắt đầu từ layer.
- Kéo vào slice mọi unit mà hành vi đó chạm: BE `feature_id` (API), FE `screen_id` (UI), `contract_id` (integration), `widget_id` nếu screen consume. Dùng quan hệ `consumes`/`used_by` trong WBS để tìm unit liên đới.
- Ưu tiên **nhiều slice mỏng** hơn ít slice dày — nhưng "mỏng" phải đo được, KHÔNG để cảm tính. Áp **Seam test** dưới đây để biết *cắt ở đâu*; một slice quá dày khi hai unit của nó nằm hai phía của một seam. Một slice nên demo được độc lập sau khi các `blocked_by` của nó xong.
- Phân loại `type`: **AFK** nếu build + merge không cần human; **HITL** nếu cần decision kiến trúc / design review / approval nghiệp vụ. Ưu tiên AFK.
- `parent_epics` là **list** — slice được phép cross-epic khi hành vi demoable trải nhiều epic.
- Map mỗi unit → planned story ref theo rule Stage 4c: BE → 1 story per `feature_id`; FE → 1 story per `screen_id` (cover widget mà screen consume); widget story riêng chỉ khi cross-screen đổi đáng kể hoặc build trước consumer.

**Seam test — cắt slice ở đâu (deterministic).** Một candidate slice là **quá dày** nếu hai unit của nó nằm hai phía của bất kỳ seam nào dưới đây. Cắt dọc theo seam đó:

| Seam | Cắt khi | Lý do |
|:--|:--|:--|
| **Ownership (in-house vs external)** | unit in-house vs unit do team khác / external sở hữu (contract) — kể cả khi cùng một hành vi chạm cả hai nguồn | tách: slice **AFK** (nhánh in-house, external stub/giới hạn, demo được mà không chờ external) + slice **HITL** (nối contract external) |
| **Trust / auth foundation** | quyết định nền cross-system (realm, shared key, schema gốc) vs unit *tiêu thụ* nó | cô lập quyết định kiến trúc thành 1 HITL nhỏ, phần còn lại AFK |
| **Happy-path vs resilience** | hành vi lõi vs retry / circuit-breaker / fallback | resilience đi **cùng call tiêu thụ đầu tiên** của nó, không trôi về slice sau (nơi consumer đã chạy "trần") |
| **Read vs write / sync vs async** | đọc vs ghi, đồng bộ vs bất đồng bộ | mỗi nhánh tự demo được riêng |

**AFK-first staging.** Theo seam Ownership: build slice in-house (AFK) trước, slice nối external (HITL) sau. **Một unit external/HITL đơn lẻ KHÔNG được kéo cả slice (vốn AFK) thành HITL** — đó là dấu hiệu thiếu một lần cắt theo seam Ownership.

**Fan-in / hub-unit.** Một unit bị nhiều hành vi (ở nhiều slice) tiêu thụ — điển hình là màn hình hub gom nhiều action, hoặc một BE provider / proxy / feature dùng chung. Một unit vẫn thuộc **đúng một** slice (G1) → khi provider phục vụ nhiều slice, chọn **một** trong hai cách hợp lệ dưới đây; **KHÔNG liệt kê lại unit ở slice sau**, không xé unit thành nhiều mảnh.

- **(a) [ƯU TIÊN] Tách atom per-capability ở Stage 2.** Phối hợp với `architecture-design` (A-U5): chẻ provider thành các atom nhỏ hơn theo từng khả năng, để nhu cầu của mỗi consumer trở thành một atom riêng. Mỗi atom rồi thuộc đúng slice của consumer đó → G1 giữ tự nhiên, không unit nào phải lớn dần. Ưu tiên cách này vì nó giữ **idempotent-skip đúng bản chất** — mỗi atom build một lần rồi thôi, không cần cơ chế "mở lại unit để thêm endpoint" (dễ sai).
- **(b) Đánh dấu hub `growable`.** Khi không tách được (hub thật sự là một atom cố ý lớn dần qua thời gian), đặt hub ở slice của **hành vi demoable đầu tiên** (thường là scaffold + đường đọc/xem) và đánh dấu `growable: true` ở entry của nó trong `units[]` (xem template + S-U3). Mỗi slice sau cần endpoint mới trên hub → sinh một **story mở-rộng (extension story) riêng cho slice đó**, nối về slice gốc qua `hub_extends: [<slice gốc>]`; slice gốc đối ứng khai `enhanced_by: [<các slice nối thêm>]`, và slice sau vẫn khai `blocked_by` slice chứa hub. Hub lớn lên **qua story mở-rộng**, KHÔNG qua tái-liệt-kê unit (giữ G1).

**Hub `growable` là cách hợp lệ DUY NHẤT để một unit lớn dần qua nhiều slice.** Ngoài (a) tách atom và (b) growable + extension story, mọi cách khác (xé unit thành "view" + "actions", nhân bản unit ở nhiều slice) đều vi phạm G1. Đây cũng là cách tránh xé một màn hình thành "view" + "actions" ở hai slice khác nhau.

**Slice một-unit.** Hợp lệ khi unit đó tự demo/verify độc lập, hoặc là contract external / mối lo resilience đứng riêng. Mô hình slice-trên-story (granularity mịn đã có ở tầng story) **không phải cớ** để gộp coarse khi Seam test đòi tách.

### Bước 3 — Slice Audit Gate (deterministic)

Self-check toàn bộ slice draft theo 8 invariant. **FAIL bất kỳ điểm nào → quay lại Bước 2 sửa**, không bypass:

| # | Invariant | Check |
|:--|:--|:--|
| G1 | **Coverage** | Mọi work unit in-scope thuộc **đúng một** slice — không orphan, không trùng, không unit nào bị xé công việc ra >1 slice. |
| G2 | **Demoability** | Mỗi slice có `demoable` non-empty, mô tả hành vi cắt ≥1 layer, quan sát được bởi actor. |
| G3 | **DAG** | Mọi `blocked_by` / `enhanced_by` trỏ tới `slice_id` thật; đồ thị phụ thuộc không có cycle. |
| G4 | **Type marked** | Mỗi slice gắn `AFK` hoặc `HITL`; ưu tiên AFK được tôn trọng (HITL phải có lý do). |
| G5 | **Story-mappable** | Mỗi unit map được về một story scope hợp lệ theo rule Stage 4c. |
| G6 | **AFK/HITL purity** | Không slice `AFK` nào chứa unit buộc-HITL; không unit external/cross-team nào bị bó với unit in-house vốn demo được mà không cần nó. FAIL → seam Ownership + AFK-first staging (Bước 2). |
| G7 | **Thinness** | Không hai unit nào trong cùng slice nằm hai phía của một seam (Bước 2 — Seam test) — trừ khi không thể tách mà vẫn giữ slice demo được. FAIL → cắt dọc seam đó. |
| G8 | **Precedence** | Với mỗi unit U trong slice S tiêu thụ provider P (theo `consumes` trong WBS), P phải nằm ở **chính S** hoặc ở một slice **reachable từ S qua chuỗi `blocked_by`** (tổ tiên) — tức P build **không muộn hơn** S. G3 chỉ đảm bảo đồ thị acyclic; G8 mới đảm bảo provider có mặt đúng lúc consumer cần. FAIL → hoặc kéo P vào S, hoặc thêm slice-chứa-P (trực tiếp / gián tiếp qua tổ tiên) vào `blocked_by` của S. Với hub `growable`: slice mở-rộng BẮT BUỘC khai `blocked_by` slice gốc chứa hub — nếu thiếu, endpoint mới bị tiêu thụ trước khi hub tồn tại → FAIL. |

Trình bảng kết quả audit (PASS/FAIL từng invariant G1–G8) trước khi sang Bước 4.

### Bước 4 — Approval gate (human)

Trình cho owner Stage 2b (**Senior Dev + SA**, BA co-review) bảng slice đề xuất, mỗi slice show: `title`, `type`, `blocked_by`, `units` + planned story ref, `demoable`, `seam_rationale`. Hỏi:

- Granularity hợp lý chưa (quá thô / quá mịn)?
- Quan hệ `blocked_by` đúng chưa (DAG khả thi với capacity team)?
- Slice nào nên gộp / tách thêm?
- Phân loại AFK/HITL đúng chưa?
- `seam_rationale` mỗi slice có thuyết phục — đặc biệt với SA xem có khớp Module 0 contract surface không?
- **Slice 1 (tracer bullet đầu)** đụng đủ layer chưa (BE + FE + contract) để build xong demo PASS đủ thông tin học hỏi cho slice tiếp theo?

Đây cũng là chỗ clarify mọi ambiguity về hành vi unit mà skill không suy ra được từ WBS + Module 0 (Bước 1 đã defer).

**KHÔNG emit nếu chưa approve** — loop lại Bước 2/3. Iterate đến khi owner duyệt.

### Bước 5 — Emit manifests + handoff

1. Ghi mỗi slice đã duyệt thành `{planning_artifacts}/SLICE-{n}-{kebab-title}.md` theo template dưới. `mkdir -p {planning_artifacts}` nếu chưa có.
2. Emit theo thứ tự DAG (blocker trước) để `blocked_by` tham chiếu được `slice_id` thật.
3. **Handoff message** — báo cáo vòng lặp per-slice cho user, KHÔNG batch toàn bộ stories ngay:

   ```
   Slice plan emit xong (N slices). Vòng lặp per-slice từ SLICE-1:

   Mỗi SLICE-X:
     1. Trigger Stage 3a /ntapp-technical-design cho module thuộc SLICE-X (nếu chưa có TechSpec).
     2. Trigger Stage 3b /ntapp-ux-design cho phần system SLICE-X chạm (delta).
     3. Trigger Stage 4a /ntapp-feature-design per unit thuộc SLICE-X.
     4. Trigger Stage 4b /ntapp-ui-generation per FE unit thuộc SLICE-X (nếu có).
     5. Trigger Stage 4c /bmad-create-story per unit, tag slice_id=SLICE-X.
     6. Trigger Stage 5 build → demo SLICE-X.
     7. Demo PASS → mở SLICE-(X+1). Học gì cần update slice tiếp → re-run skill này.

   KHÔNG batch spec Stage 3-4 cho mọi slice cùng lúc — vòng lặp per-slice là điểm lõi của Stage 2b.
   ```

---

## Slice manifest template

```markdown
---
slice_id: SLICE-{n}
feature: <feature-slug>             # BẮT BUỘC. Trả lời "slice này ra đời từ feature nào" — thứ manifest
                                    # trước đây KHÔNG nói, mà mọi artifact phái sinh (ledger, bài học,
                                    # node OKF `slice_set`) cần để gom nhóm.
                                    #
                                    # KHÔNG phải để chống va chạm số. Re-run mode chỉ NỐI THÊM số, không
                                    # đánh số lại: đo thật trên paybiz, snapshot _v1 có SLICE-1..22, bản
                                    # sống có SLICE-1..25 — thêm 23–25, KHÔNG số nào bị dùng cho slice
                                    # khác. Và không có đường chạy nào đánh số lại từ 1: `slices/` không
                                    # rỗng thì Bước 1 luôn rẽ sang Re-run mode.
                                    # Nên `slice_id` hiện là duy nhất toàn cục; `feature:` là lớp phòng
                                    # hờ nếu quy ước đó đổi, chứ không phải thứ đang gánh danh tính.
title: <hành vi demoable, abstract>
type: AFK | HITL
parent_epics: [<EPIC-ID>, ...]      # list → cross-epic OK
blocked_by: [<SLICE-ID>, ...]       # [] nếu start ngay; DAG, no cycle
enhanced_by: [<SLICE-ID>, ...]      # optional — slice sau wire thêm action/đường ghi vào unit hub build ở đây (fan-in). [] nếu không có
hub_extends: [<SLICE-ID>, ...]      # optional — slice gốc nơi unit hub `growable` được build lần đầu; slice HIỆN TẠI chứa story mở-rộng nối về đó (nghịch đảo của `enhanced_by`). [] nếu slice không mở rộng hub nào
demoable: "<1 câu: hành vi end-to-end quan sát được bởi actor>"
seam_rationale: "<1-2 câu: tại sao cắt slice này. Áp seam nào (Ownership / Trust-auth / Resilience / Read-write). Lý do AFK vs HITL. Audit trail cho reviewer.>"
demo_status: pending                # progress field — seed `pending`; HITL slice-demo (hoặc /ntapp-feature-complete khi auto_flip) flip → `passed`. SLICE-(N+1) chỉ build khi blocked_by slices đều `passed`. staging-deploy grep field này.
units:
  - { id: <feature_id>,  type: backend,     story: <planned epic-story ref> }
  - { id: <screen_id>,   type: frontend,    story: <planned epic-story ref> }
  - { id: <hub_id>,      type: backend,     story: <planned epic-story ref>, growable: true }   # optional — `growable: true` đánh dấu hub cố ý lớn dần qua nhiều slice (Bước 2 cách (b) + S-U2). Default = omit / false
  - { id: <contract_id>, type: integration }
---

## What to build
<Mô tả lát cắt end-to-end. Hành vi, KHÔNG mô tả layer-by-layer. KHÔNG file path / code snippet.>

## Acceptance criteria
→ Xem AC trong story file của từng unit ở `units` trên. KHÔNG copy lại tại đây.
```

> `blocked_by` / `enhanced_by` / `hub_extends` / `seam_rationale` sống ở front-matter (source of truth) — không lặp lại trong body.

> **`growable` + `hub_extends` (fan-in hub — S-U2/S-U3).** `growable: true` ở một entry `units[]` đánh dấu unit hub cố ý lớn dần qua nhiều slice (default omit = false) — đây là điều kiện để slice sau được **mở rộng** hub thay vì tái-liệt-kê nó (giữ G1). Khi một slice chứa **story mở-rộng** cho hub `growable` build ở slice khác, slice đó khai `hub_extends: [<slice gốc>]`; slice gốc đối ứng khai `enhanced_by: [<slice mở rộng>]` (hai chiều nghịch đảo). Cặp `hub_extends` ↔ `enhanced_by` phải nhất quán hai đầu, và slice mở-rộng phải `blocked_by` slice gốc (điều kiện G8 Precedence). Nếu hub được tách atom per-capability ở Stage 2 (cách ƯU TIÊN (a) ở Bước 2) thì KHÔNG cần `growable`/`hub_extends` — mỗi atom là unit độc lập trong slice của consumer nó.

> **`demo_status` là field *progress* duy nhất trong manifest** (phần còn lại là *plan*, immutable sau duyệt). Seed `pending` lúc emit; chỉ HITL `slice-demo` hoặc `/ntapp-feature-complete` (khi `auto_flip_demo_status=true`) được flip sang `passed`. Đây là as-built/progress plane sống chung file với plan — chấp nhận được vì manifest vốn mutable + không bị pre-commit hook lookup contract (khác WBS immutable).

> **Lưu ý dual-repo:** slice manifest là **snapshot planning artifact** → ghi ở **spec repo** dưới `Stage_2_Architecture/slices/` (cùng folder với `project_wbs.md`), phân loại với architecture planning. KHÔNG sync sang code repo.

---

## Re-run mode (incremental update)

**Khi nào trigger:** Sau khi build xong một slice và demo phát hiện cần điều chỉnh slice tiếp theo. Ví dụ:
- SLICE-3 build phát hiện contract X cần thêm field → cần insert unit mới vào SLICE-5.
- SLICE-2 demo gây realize hành vi Y cần tách thành slice riêng AFK trước SLICE-6.
- Capacity team thay đổi → cần merge 2 slice nhỏ thành 1, hoặc tách slice lớn.

**Trigger:** User gõ `/ntapp-slice-planning` với prompt mention scope cần update — ví dụ *"update slice plan: SLICE-3 phát hiện cần thêm INT-FOO-02 vào slice tiếp theo"* hoặc *"tách SLICE-5 thành 2 slice mỏng hơn"* hoặc *"merge SLICE-7 + SLICE-8"*.

**Workflow re-run:**

1. **Detect Re-run mode** ở Bước 1: tìm thấy `SLICE-*.md` trong `{planning_artifacts}/` → branch sang đây, KHÔNG chạy Initial full flow.
2. **Snapshot trước khi sửa:** copy toàn bộ `{planning_artifacts}/SLICE-*.md` hiện tại sang `{planning_artifacts}/archive/_v{N+1}_{YYYYMMDD-HHMMSS}/`. `N` = max version đã có trong archive + 1. Mục đích: rollback được nếu update gây fail audit.
3. **Identify slices in-flight vs untouched:**
   - **In-flight** (đã có story file `slice_id=SLICE-X` ở Stage 4c, hoặc đã có commit code) → KHÔNG sửa front-matter của slice đó (sẽ break story-slice link). Chỉ được sửa `enhanced_by` (thêm slice mới wire vào hub), KHÔNG đổi `units` / `blocked_by` / `demoable`. Cần đổi cứng → revert story Stage 4c trước, không bypass tại đây.
   - **Untouched** (chưa có story / chưa build) → toàn quyền update.
4. **Apply user-requested change** (insert / split / merge / re-order):
   - **Insert unit vào slice mới:** verify unit chưa thuộc slice nào (Coverage G1 vẫn hold sau update). Nếu unit đã ở slice in-flight → block, yêu cầu user xử lý ở slice đó (enhanced_by pattern) hoặc revert story.
   - **Split slice:** chia `units` thành 2 set, mỗi set thành slice mới. `blocked_by` chain re-balance: slice mới chứa unit có dependency vào unit ở slice còn lại → `blocked_by` add slice đó.
   - **Merge slice:** union `units`, union `parent_epics`, union `blocked_by` trừ self-reference. Audit G7 (Thinness) phải re-pass — merge có thể vi phạm seam test.
   - **Re-order:** sửa `blocked_by` chain. Audit G3 (DAG no cycle) phải re-pass.
5. **Re-run audit Bước 3** trên toàn bộ slice (không chỉ slice bị sửa) — 7 invariant phải PASS. Fail → quay lại bước 4 (sửa thêm) hoặc rollback từ archive snapshot.
6. **Approval gate Bước 4** — trình diff (slices thêm / xóa / sửa) cho Senior Dev + SA. Highlight slice in-flight đã được respect (chỉ `enhanced_by` thay đổi).
7. **Emit** chỉ slice mới + slice bị sửa (không re-write slice không đổi để giảm noise git diff). Ghi commit message mention slice_id liên quan. **Preserve `demo_status`**: khi re-write một slice cũ, giữ nguyên giá trị `demo_status` hiện có — KHÔNG reset slice đã `passed` về `pending` (đó là as-built fact, không phải plan). Slice mới sinh ra → seed `pending`.

**Re-run rule:**
- WBS update (thêm unit mới ở Stage 2) → chạy Re-run mode tự động để incorporate unit mới vào slice plan. Không tự bịa slice mới — hỏi user assign vào slice nào.
- Slice plan **không** lock cứng như WBS. WBS lock = bất di bất dịch (hook lookup); slice plan flexible với constraint slice in-flight không đổi front-matter.
- Không re-run khi slice plan vẫn match WBS + chưa có ai phản hồi cần update. Re-run vô cớ = noise git diff, mất audit signal.
