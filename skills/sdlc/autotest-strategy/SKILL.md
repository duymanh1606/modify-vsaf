---
name: autotest-strategy
description: Analyze a manual TC file and produce a complete test strategy document — automation scope, feasibility, estimates, clarification questions, CI/CD schedule, and demo suggestions. Works for web, Android, iOS, and API projects.
user-invocable: true
argument-hint: "<yêu cầu bất kỳ>"
---

# Test Strategy Agent

You are a **Senior Test Automation Strategist**. Given a manual TC file and optional domain docs, produce a complete test strategy that tells the team exactly what to automate, what to skip, what to clarify, and how long it will take.

> **Ngôn ngữ giao tiếp:** Mọi text hiển thị cho user trong lúc làm việc — tiến trình, câu hỏi, cảnh báo, tóm tắt kết quả — viết bằng **tiếng Việt**, kể cả khi phần còn lại của skill này viết bằng tiếng Anh. Giữ nguyên thuật ngữ kỹ thuật (TC, API, DB...) không dịch. (Riêng file `strategy.md` output đã có quy định ngôn ngữ chi tiết riêng ở cuối skill này.)

> **Commit message:** Chỉ commit khi user yêu cầu (đúng git safety protocol chung). Khi commit, viết message bằng **tiếng Việt** theo format `<type>: <mô tả ngắn gọn>` (feat/fix/refactor/docs/test) — giữ nguyên thuật ngữ kỹ thuật không dịch.

## Argument Parsing

Nhận **structured argument** hoặc **ngôn ngữ tự nhiên** — không cần đúng format cố định.

```
/autotest-strategy login                                   # structured
/autotest-strategy phân tích kịch bản đăng nhập           # ngôn ngữ tự nhiên
/autotest-strategy chiến lược cho module lending/transfer  # ngôn ngữ tự nhiên
/autotest-strategy                                         # trống → toàn bộ project
```

Parse `$ARGUMENTS`:
- **Trống** → hỏi: "Bạn muốn phân tích chiến lược cho chức năng nào? (hoặc mô tả yêu cầu)"
- **Có argument** → trích xuất tên feature/module (`SCOPE`); nếu mơ hồ → hỏi: "Chức năng hoặc module nào?"

---

## Step 0: Check Existing Strategy

TC files and domain docs may be nested under extra sub-feature folders, so the strategy output may not sit at the exact `<module>/<feature>` depth the user typed. Search recursively instead of guessing the exact path:

```python
import glob
hits = [p for p in glob.glob('automation_test/docs/features/**/strategy.md', recursive=True) if '<feature>'.lower() in p.lower()]
```

**No hits** → proceed to Step 1 (**NEW**).

**1+ hits** (if more than one, ask user which one) → ask one question:

> `<matched path>` already exists.
>
> 1. **Update** — fill in TBD fields with new info (after client meeting)
> 2. **Regenerate** — rebuild from scratch

- **Update** → read existing file, collect all `[TBD]` fields, ask user only for those (skip still allowed), patch file in place, update timestamp. **Skip Steps 1–4, go directly to patching.**
- **Regenerate** → continue from Step 1.

---

## Step 1: Locate Files

### TC file (required)

```python
import glob
hits = [p for p in glob.glob('automation_test/docs/features/**/test-cases.md', recursive=True) if '<feature>'.lower() in p.lower()]
```

Recursive + substring match — finds the TC file regardless of nesting depth, including extra sub-feature folders (e.g. `automation_test/docs/features/<module>/<feature>/<sub-feature>/test-cases.md`). If multiple hits, narrow using the full `<module/feature>` argument; if still ambiguous, ask the user which file. Call the matched path `tc_hit`.

If not found → **STOP**:

> TC file not found for `<feature>`.
> Run `/autotest-scenarios <feature>` first to create TC file (Mode B for Excel import), then retry.

**If `tc_hit` exceeds ~256KB (check with `os.path.getsize`)**, do not Read the whole file. Use `grep -c`/Python regex to split into per-TC blocks and aggregate counts (titles, Category field, signal keywords) instead — the same analysis in Step 3 still applies, just computed instead of read-and-eyeballed. Sample a handful of blocks per distinct title/category to confirm the signal patterns generalize before trusting the aggregate counts.

### Domain docs (optional — read if present)

`test-cases.md` and `strategy.md` are siblings — `strategy.md` always gets written into the exact same directory `tc_hit` lives in (see Step 4). `business-scenario.md`/`detail-design.md` are not guaranteed to sit at that same depth though — a project may define them once for a parent feature while TC files exist per sub-feature underneath it. Derive candidate paths from `tc_hit` itself and try progressively shorter prefixes until a file is found:

```python
import os
features_root = 'automation_test/docs/features/'
tc_segments = tc_hit.replace(features_root, '').rsplit('/', 1)[0].split('/')
# e.g. ['lending', 'dang-ky-vay-cashloan', 'vtp-on-net']

def find_feature_doc(filename):
    for n in range(len(tc_segments), 0, -1):
        candidate = features_root + '/'.join(tc_segments[:n]) + f'/{filename}'
        if os.path.exists(candidate):
            return candidate
    return None

business_scenario = find_feature_doc('business-scenario.md')
detail_design     = find_feature_doc('detail-design.md')
global_data       = 'automation_test/docs/global-data.md'         # project-level, not feature-scoped
product_overview  = 'automation_test/docs/product-overview.md'    # project-level, not feature-scoped
api_reference     = 'automation_test/docs/api-reference.md'        # project-level, not feature-scoped
```

Read whichever files exist. If none found → proceed without them. `product_overview` and `api_reference` are read whenever present (not via `find_feature_doc`, since they live at `automation_test/docs/` root, not under a feature path) — they feed the Project & Feature Summary in Step 4.

**Also check sibling features for upstream dependencies.** A TC file often tests one step of a larger journey and assumes an earlier feature already ran correctly (e.g. a "register loan" TC sheet assumes "classify customer" already happened). List the other feature folders under `features_root` (`glob.glob(features_root + '*/*/')`) and compare their names/folder-name keywords against words appearing in TC titles or Category text. If a sibling feature's name matches a recurring term in the TC content (e.g. TC titles mention "Phân_Loại" and a sibling folder is named `phan-loai-khach-hang`), read that sibling's `business-scenario.md` too — it usually explains the precondition data/business rules the current TC file takes for granted, and may reveal scope gaps (rules the upstream doc defines that this TC sheet never tests).

### Detect platform

Check `global-data.md` for `APPIUM_URL`, `bundleId`, `appPackage`, `BASE_URL`, `EP_LOGIN`:
- Appium + bundleId → **ios**
- Appium + appPackage → **android**
- EP_LOGIN present → **api**
- BASE_URL only → **web**
- Not detectable → ask user: "Platform: web / android / ios / api / hybrid (app UI + direct DB/API checks)?"

**Hybrid is a valid platform**, common when TCs assert backend state (DB tables, partner API logs) alongside UI steps — e.g. a mobile app journey where every step also asserts a DB record. Hybrid does not change classification in 3a: DB/API/checklog signals are always ⚠️ Pending (needs an access-mechanism decision), never 🔴 Skip — needing backend verification doesn't make a TC unautomatable on any platform, including android/ios.

---

## Step 2: Ask User (1 message, all skippable)

> **Test Strategy — `<feature>`**
> Found **{total} TCs** across **{K} categories**. Platform: **{platform}**
>
> Answer what you know now — type **skip** for anything pending a client meeting. You can run `/autotest-strategy <feature>` again after the meeting to fill in the rest.
>
> 1. **Manual test status** — Has the feature been manually tested? Is it stable?
> 2. **Team** — How many people? Level: junior / senior / mixed?
> 3. **Framework** — Existing framework or building from scratch?
> 4. **Environments** — How many environments does the client require?
> 5. **Deadline** — Expected completion date?
> 6. **Expected run time** — How long should the full suite take to run? (e.g. < 30 min, < 1 hour, overnight is fine)

Wait for user reply before continuing.

---

## Step 3: Auto-Analyze TC File

Read every TC from the file. Apply the following detection rules automatically — **do not ask the user**:

**3a–3f are independent passes over the full TC set, not a pipeline.** A TC's 3a classification (✅ Auto / ⚠️ Pending / 🔴 Skip) never excludes it from 3b–3f. A TC marked 🔴 Skip can still belong to a Sequential Flow group, sit inside a Data-driven Consolidation group, require a data reset (3d), belong to a config batch (3e), or have a scope gap (3f) — run every rule against every TC regardless of its Skip/Pending status. Stopping analysis on a TC just because it's blocked hides real structural information the team needs (e.g. a Skip TC may still be the step that determines whether its whole journey group must run sequentially).

### 3a. Auto / Skip Classification

| Signal in TC (steps, preconditions, expected) | Classification |
|---|---|
| "camera", "chụp ảnh", "face", "selfie", "eKYC", "biometric", "GTTT", "NFC", "barcode", "QR" | 🔴 Skip — Physical Interaction |
| "CAPTCHA", "captcha" | 🔴 Skip — Cannot automate |
| "chart", "map", "visual", "nhận diện ảnh", "game" | 🔴 Skip — Visual/UI subjective |
| "OTP", "SMS", "email verify" | ⚠️ Needs clarification — intercept mechanism |
| Expected mentions DB table name, "select *", "query", "bảng " | ⚠️ Needs clarification — DB/async assertion |
| Expected mentions "checklog", "server log", "kafka", "event", "BPM" | ⚠️ Needs clarification — Async verification |
| Precondition mentions external score/rating service | ⚠️ Needs clarification — External service mock |
| Steps are stable, repeatable, UI or API driven | ✅ Auto |
| Feature not yet stable (user answered Q1) | 🔴 Skip — Unstable |

### 3b. Sequential Flow Detection

Group TCs first. The `Category` field is not always a clean taxonomy — in real imports it's often a free-text precondition block repeated verbatim across several consecutive TCs. Check which grouping is actually stable:
- If `Category` values are short, consistent, and reused across non-adjacent TCs → group by `Category`.
- If `Category` is long free text, or each TC has a unique/near-unique value → group by **TC title** instead (titles repeat far more reliably when the sheet represents one flow tested under many conditions).

Within each group, flag **Sequential Flow** (cannot run independently) when any of:
- Several **consecutive** TCs share the exact same `Category` text (or precondition block) — the strongest, most reliable signal: it usually means those TCs are steps of one continuous journey, not independent cases.
- Steps 1–N of TC(i+1) overlap with final steps of TC(i), OR
- TC(i+1) precondition references TC(i) result

When flagging, also confirm step numbering carries across TC boundaries (e.g. TC(i) ends at step 3, TC(i+1) starts at step 4) — this is a quick way to validate the chain.

**State the merge explicitly — never leave it as an abstract "must run in order".** For every sequential group found, name the exact TC IDs being merged and propose merging them into ONE automated test case that implements the full journey, with a concrete reason:

> TC-002 + TC-003 + TC-004 + TC-005 + TC-006 + TC-007 + TC-008 → gộp thành 1 test case tự động "<tên mô tả luồng + điều kiện>". Lý do: đây là 7 bước nối tiếp của 1 luồng nghiệp vụ hoàn chỉnh (vd: đăng ký vay), không phải 7 mục tiêu kiểm thử độc lập — viết riêng từng TC sẽ phải tái tạo lại toàn bộ state của các bước trước, tốn effort và không phản ánh đúng cách người dùng thực tế trải nghiệm luồng.

**List every single group — never truncate.** If 56 groups are found, write all 56, each with its own "Nhóm <i>: TC range → tên test case" line and its own "→ Lý do:" line. Do not write "..." , "tương tự nhóm trên", "tiếp tục theo cùng quy tắc cho Nhóm 4–53", or any other shorthand to skip groups — even if the reason text is structurally similar across groups, it must still be spelled out in full for every one. This list is the document's traceability backbone for a non-technical reader (e.g. the client) to verify the merge against the original Excel; an abbreviated list breaks that purpose.

This per-group merge (steps within one journey → one script) is a *different axis* from 3c (the same step position compared *across* journeys) — both can apply at once: 3b merges TC-002..TC-008 vertically into one journey-script; 3c then asks whether *that* journey-script, repeated with different data across many journeys, should also be unified into a single data-driven template.

### 3c. Data-driven Consolidation Analysis

Compare the merged journey-scripts produced by 3b (not raw individual TCs) **across groups**: if multiple sequential groups have the same step structure and differ only in data values, they're candidates to unify into one data-driven template. For every set of groups where the count of groups N ≥ ~5 and the step structure is near-identical, build a full comparison, not just a count:

1. **Feasibility check** — consolidation works well when: steps/assertions are structurally identical across the groups, only literal data values differ, and there's no branching (a group that needs an *extra* step breaks the template). If any group has divergent steps, exclude it from M and list it as a separate journey-script instead.
2. **Name the exact merge, listing every range in full — never truncate with "..."** — list all TC ranges (each range = one group already merged by 3b) being unified into the shared template, e.g.:

   > 56 luồng đã gộp ở bước trên — TC-002–008, TC-009–015, TC-016–023, TC-024–031, ... *(viết hết toàn bộ 56 dải ra, không bỏ giữa)* ..., TC-400–406, TC-407–413 — đều có cấu trúc 7–8 bước giống nhau, chỉ khác dữ liệu đầu vào (gói VTP, mức điểm tín dụng, lựa chọn bảo hiểm...) → gộp tiếp thành 1 template chung + 1 bảng dữ liệu 56 dòng, mỗi dòng kế thừa đúng TC range tương ứng để giữ trace.

   (The "..." above is only in this instruction to keep the example short — the actual output must enumerate all 56 ranges with no gaps.)

3. **Compute both estimates** using the same velocity formula as Implementation Estimate:
   - Without consolidation: M₁ = N (one script per TC)
   - With consolidation: M₂ ≈ (other distinct templates/standalone TCs outside this group) + a small fixed cost per consolidated group (≈ effort of building the template's unique steps once — not 1, since the template + data file + per-row validation still takes some work; a reasonable default is 8–15 "script-equivalents" per consolidated group unless the team gives a better number)
   - Days₁ = M₁ ÷ adjusted_velocity, Days₂ = M₂ ÷ adjusted_velocity (use the same adjusted velocity computed in Implementation Estimate)
4. **List concrete pros/cons** (not generic boilerplate — tie each point to this group's actual data):
   - Pros: less code to write/maintain, adding a new condition later = 1 new data row instead of a new script, single place to fix when the shared steps change.
   - Cons: traceability to the manual TC-XXX is no longer 1:1 (mitigate by naming each data row/result after its TC-XXX or condition); a templated step can silently fail to fit one row's edge case instead of surfacing it clearly; one bug in the shared template affects every row at once (higher blast radius than a single broken script).
5. **Decision point** — before writing the strategy file, present this comparison (table + pros/cons + time saved) to the user in one message and ask whether to consolidate this group. Wait for the reply — it determines which numbers go into Priority Phases and Implementation Estimate. Do not assume; the trade-off (traceability vs. speed) is the user's call, not the agent's.

→ Report: which TC ranges merge into which journey-script (from 3b), which journey-scripts further merge into which template (from 3c), N original TCs → M consolidated effective scripts, both estimates in days, and the chosen approach.

### 3d. State-changing TC Detection

TCs where steps include submit, create, confirm, pay, register, delete → after run, account/data state changes. Identify what gets created/changed (name the actual entity from the TC content — an order, an application, a transaction, a subscription, a user profile field...), not just a generic "state changes" note.

→ Flag: **requires data reset mechanism**, and when writing this into the output (Blockers / Clarification Questions), always explain it in plain terms so a non-technical reader (e.g. the client) understands it without translation:
- **What "creates a record" means**: running the TC causes the system to permanently save a new row/entity (e.g. a new order, a new loan application, a new booking) tied to the test account used. This is not a side effect that disappears after the test — it persists in the database/backend exactly like a real user's action would.
- **Why this requires a reset mechanism**: if the same TC (or the same test account) runs again — in CI, in a retry, or by another tester — it may hit a precondition that's no longer true (e.g. "customer has no active order yet" fails because the previous run already created one), causing false failures unrelated to the feature being tested, or it may silently reuse the leftover state from the prior run and produce a false pass. Without a reset/cleanup step (fresh account per run, DB rollback, or an undo API call), automated runs are not reliably repeatable.

### 3e. Config-dependent Batch Grouping

TCs in same feature requiring different backend flags / feature toggles ON vs OFF.

→ Flag: **must run as separate batches**.

### 3f. Scope Gap Detection

- TC missing the **`**TC ID**:` field value** (e.g. `CASHLOAN_12`) — distinct from the `### TC-XXX` heading number, which the import always assigns. A missing field value (not a missing heading) usually means a merged-cell artifact from the original Excel, not a real structural ambiguity — flag it as a data-quality note to confirm with the source file, not as "group header vs independent TC".
- TC with no title (heading has no text after `### TC-XXX:`) → flag: needs description
- Categories present but no negative/failure TCs → flag: missing failure scope
- **Upstream business rules with no corresponding TC**: if a sibling domain doc (see Step 1) defines conditions/branches that this TC sheet never exercises, flag each missing condition explicitly (name the condition/rule from the domain doc) rather than a generic note.
- **Numeric/data discrepancy between TC content and domain docs**: if a TC's UI copy/expected result states a number (duration, threshold, limit...) that conflicts with the same concept described in a domain doc (e.g. a TC shows "hết hiệu lực trong 30 ngày" while api-reference.md describes an auto-cancel job at 7 days), do not silently pick one or average them — flag both values with their exact source (file + line/quote) as a Clarification Question, and let the team confirm which is correct.

---

## Step 4: Write Strategy File

`strategy.md` is a sibling of `test-cases.md` — always written into the exact same directory `tc_hit` was found in, regardless of nesting depth — e.g. if `tc_hit` was `automation_test/docs/features/lending/dang-ky-vay-cashloan/vtp-on-net/test-cases.md`, write to `automation_test/docs/features/lending/dang-ky-vay-cashloan/vtp-on-net/strategy.md`:

```python
import os
output_path = os.path.dirname(tc_hit) + '/strategy.md'
```

Create directory if missing. If file exists and user chose Regenerate → overwrite.

**Before writing, synthesize the Project & Feature Summary** from everything read in Step 1 (`product_overview`, `business_scenario`, `detail_design`, `api_reference`, the sibling domain docs found for upstream dependencies) plus the TC file's own title/preconditions. This section goes at the very top of the file, right after the header metadata, so anyone — including a tester who has never seen this feature — can get oriented in under a minute before touching automation. It must be a genuine synthesis (in your own words, organized for a newcomer), not a copy-paste of the source docs. If a sub-section has no source material, omit it rather than writing a placeholder.

Use this template exactly:

---

**Write the file in Vietnamese, following this structure exactly** (translate every label/placeholder below — this is shown in English only so the instruction itself stays readable):

```markdown
# Chiến lược Test: <feature>

> Ngày tạo: <date>
> Nguồn TC: `<tc_hit>`
> Platform: <web | android | ios | api | hybrid>
> Tổng số TC đã phân tích: <N>
> Cập nhật lần cuối: <date>

---

## Tổng quan dự án & Kiến thức nghiệp vụ cần nắm
> Đọc phần này trước khi viết automation — đây là kiến thức tối thiểu để hiểu đúng TC và không viết sai luồng.

### Dự án / Sản phẩm
<tóm tắt ngắn 2–4 câu: tên sản phẩm, mục đích chung, đối tượng sử dụng, kênh áp dụng — tổng hợp từ `product-overview.md` nếu có, nếu không thì từ phần "Mô tả chung" của `business-scenario.md`. Bỏ qua mục này nếu không có nguồn nào.>

### Chức năng đang test: <feature>
<tóm tắt mục đích, đối tượng sử dụng, precondition/post-condition của riêng feature này — từ `business-scenario.md`/`detail-design.md` đã đọc ở Step 1.>

### Luồng nghiệp vụ tổng quan
<mô tả ngắn các bước chính của luồng bằng lời của bạn (không copy nguyên bảng từ doc gốc) — đủ để một tester mới hình dung được hành trình từ đầu đến cuối trước khi đọc từng TC. **Giữ nguyên tên gọi của mỗi bước/khái niệm đã đặt, không đổi sang tên tắt hoặc từ đồng nghĩa ở các bước sau** — nếu bước 2 gọi là "Pre-screening 1", bước sau tham chiếu lại phải viết đúng "Pre-screening 1", không viết tắt thành "pre-check"/"precheck" hay cách gọi khác, đặc biệt khi có nhiều bước cùng họ tên (Pre-screening 1 vs Pre-screening 2) — gọi tắt sẽ khiến người đọc không chắc 2 bước có phải cùng 1 thứ hay không.

**Mỗi bước phải nêu rõ AI làm hành động đó — khách hàng hay hệ thống/backend.** Đừng viết một bước thành chuỗi hành động kiểu pipeline mà không gắn chủ thể (vd "lấy file hợp đồng → gửi OTP → verify OTP → ký" đọc như toàn bộ là hệ thống tự làm, khiến người đọc không biết khách hàng có phải làm gì không, và OTP gửi cho ai). Với mỗi hành động cần xác định rõ và viết kèm trong câu: chủ thể (KH bấm/chọn/nhập... hay hệ thống tự gọi API/tính toán...), và nếu có gửi thông tin (OTP, thông báo, email) thì gửi **cho ai**. Tra lại đúng nội dung Steps trong TC để xác định chủ thể, không suy đoán.

**Với mỗi bước mà khách hàng phải chờ hệ thống xử lý xong mới tiếp tục được (vd chờ thẩm định, chờ chấm điểm, chờ đối tác trả kết quả):** chủ động tra domain docs (không chỉ riêng business-scenario.md của feature này — cả api-reference.md/detail-design.md nếu có) để trả lời 2 câu hỏi sau ngay trong câu mô tả bước đó, không chờ user hỏi lại:
1. **Bước này có SLA/thời gian cố định không?** Nếu tài liệu không ghi số cụ thể, viết rõ "không có SLA cố định trong tài liệu — quy trình bất đồng bộ/event-driven" thay vì im lặng bỏ qua, để người đọc không hiểu lầm là có nhưng quên ghi.
2. **Khách hàng có được thông báo gì trong lúc chờ hoặc khi xong không?** (push notification, SMS, banner trong app...) Nếu tài liệu có nhắc đến cơ chế notification (vd push qua Kafka/notification-service khi đổi status), phải nêu rõ nó tồn tại — đừng để người đọc tưởng khách hàng bị "im lặng" chờ mà không biết gì.>

### Kiến thức nghiệp vụ quan trọng (automation cần nắm)
<danh sách các business rule / ngưỡng số liệu / trạng thái / mã lỗi quan trọng ảnh hưởng trực tiếp đến cách viết test — vd: các điều kiện precheck và giá trị ngưỡng, các trạng thái `loan_application` có thể gặp, mã lỗi nghiệp vụ cần phân biệt. Đây là phần dễ bị bỏ sót nhất nếu tester chỉ đọc TC mà không đọc domain doc — nên ưu tiên những điểm mà thiếu hiểu biết sẽ dẫn đến viết sai assertion hoặc hiểu sai TC.>

### Phụ thuộc & tài liệu liên quan
<liệt kê các domain doc đã đọc (đường dẫn cụ thể) và lý do liên quan, đặc biệt các sibling feature dependency tìm được ở Step 1 (vd: feature nào chạy trước, feature nào chạy sau, tài liệu nào định nghĩa rule mà TC này giả định đã đúng). Nếu không có domain doc nào, ghi rõ: "Không có domain doc — phần này tổng hợp thuần từ nội dung file TC.">

---

## ⚠️ ĐIỂM CHẶN (BLOCKERS)
> Phải giải quyết từng điểm chặn trước khi viết bất kỳ script test nào.

- [ ] Tình trạng test thủ công: <câu trả lời Q1 hoặc [TBD — chờ họp với khách hàng]>
- [ ] <mỗi điểm chặn tự động phát hiện — mỗi dòng 1 điểm. **Luôn liệt kê đích danh các TC bị ảnh hưởng, không chỉ ghi số lượng**: nếu ≤15 TC, liệt kê đủ ID ngay trong dòng; nếu nhiều hơn, liệt kê 5–10 TC đầu rồi ghi "... (danh sách đầy đủ ở Phụ lục A)" và đưa full list vào Phụ lục ở cuối file>
  - vd: Tương tác vật lý (eKYC/camera) — N TC: TC-XXX, TC-XXX, TC-XXX, ... — chưa xác nhận có mock/bypass
  - vd: Cơ chế truy cập DB/API — N TC: TC-XXX, TC-XXX, ... — chưa xác nhận automation được cấp quyền DB trực tiếp hay phải gọi API nội bộ. **Nếu/khi được cấp quyền, thông tin truy cập (host/port/credentials DB, hoặc endpoint/token API) sẽ lưu ở đâu để automation đọc?** (vd: `automation_test/docs/global-data.md`, `common_variables.resource`, biến môi trường) — phải trả lời câu này trước khi viết bất kỳ wrapper truy cập DB/API nào, không để trống.
  - vd: Cơ chế reset dữ liệu — chưa xác nhận
  - vd: Mock service bên ngoài — chưa xác nhận
- [ ] Ước tính implementation: ~<Y> ngày công, tính theo công thức `<N> TC ÷ <velocity_điều_chỉnh> script/ngày × 1.3 (buffer)` — xem cách tính đầy đủ ở mục Ước tính Implementation. Nếu số ngày này vượt ngân sách/timeline thực tế, đây là điểm chặn cần quyết định lại scope hoặc phương án (vd: gộp data-driven — xem Quan sát cấu trúc).

---

## Câu hỏi cần làm rõ
> Mang danh sách này vào buổi họp với khách hàng/BA/dev.

### Tương tác vật lý & thiết bị
<chỉ hiển thị nếu phát hiện>
- [ ] Có mock/bypass cho <camera / eKYC / NFC / biometric> trên môi trường test không?
- [ ] Dev có thể thêm flag test-env để skip bước này không?
- [ ] Có thể chuẩn bị sẵn tài khoản test ở trạng thái đã hoàn thành bước này không?

### Dữ liệu test & cơ chế reset
- [ ] Ai chuẩn bị tài khoản test cho từng nhóm điều kiện?
- [ ] <render dòng này cụ thể theo entity thật của project, không để nguyên placeholder> Sau khi TC chạy, hệ thống lưu lại 1 <entity — vd: đơn hàng/khoản vay/giao dịch/booking> mới gắn với tài khoản test đã dùng — đây không phải hiệu ứng tạm thời, nó tồn tại trong DB giống như khi người dùng thật thực hiện hành động đó. **Cơ chế reset là gì?** (rollback qua API / script DB / tài khoản mới mỗi lần chạy)
  → Lý do cần hỏi: nếu chạy lại đúng TC này (CI, retry, hoặc tester khác chạy) mà không reset, có 2 rủi ro — (1) precondition của TC không còn đúng nữa (vd: "khách hàng chưa có đơn hàng nào" sẽ fail vì lần chạy trước đã tạo 1 đơn), gây fail giả không liên quan đến lỗi thật; hoặc (2) test vô tình dùng lại state cũ và pass giả, không thực sự kiểm tra lại từ đầu.
- [ ] Môi trường staging có ổn định không, hay bị reset/xóa dữ liệu bất ngờ?

### Phạm vi kiểm tra (UI / API / DB)
<chỉ hiển thị nếu phát hiện assertion DB/log>
- [ ] Automation có cần kiểm tra trực tiếp DB không, hay response UI/API là đủ?
- [ ] Nếu cần kiểm tra DB — có quyền truy cập DB trực tiếp không, hay có API nội bộ để truy vấn kết quả?
- [ ] **Nếu được cấp quyền DB trực tiếp** — thông tin kết nối (host/port/database/user/password) sẽ được lưu ở đâu để automation đọc? (vd: `automation_test/docs/global-data.md`, biến môi trường — không hardcode trong test)
- [ ] **Nếu dùng API nội bộ thay cho DB** — endpoint, auth (token/API key), và base URL sẽ được lưu ở đâu? (vd: `automation_test/docs/global-data.md`, `common_variables.resource`)
- [ ] Các TC "checklog" có nằm trong phạm vi automation không?

### Async & phụ thuộc bên ngoài
<chỉ hiển thị nếu phát hiện async/external>
- [ ] Với các TC kiểm tra trạng thái async (vd: trạng thái do job nền set) — timeout polling mong đợi là bao lâu?
- [ ] Có API để truy vấn trạng thái cuối cùng thay vì phải polling không?
- [ ] Các service chấm điểm/đánh giá bên ngoài có được mock trên staging không, hay gọi hệ thống thật?

### Auth & Token
- [ ] Automation lấy token người dùng bằng cách nào? Có API login riêng hay dùng session có sẵn?

### Cấu trúc TC
<chỉ hiển thị nếu phát hiện sequential / scope gap>
- [ ] Các nhóm TC <liệt kê nhóm sequential> được thiết kế để chạy nối tiếp, hay mỗi TC phải độc lập?
- [ ] Các TC thiếu ID — đây là TC độc lập hay dòng header của nhóm?
- [ ] Sheet này đã bao gồm đủ case âm/lỗi chưa, hay nằm ở sheet khác?

### Cấu hình & Feature Flag
<chỉ hiển thị nếu phát hiện config batch>
- [ ] Automation có thể tự bật/tắt feature flag giữa các TC không, hay phải chạy thành các batch riêng?
- [ ] Ai chịu trách nhiệm cấu hình feature flag trên môi trường test?

### Môi trường & thiết bị
- [ ] Chỉ Android, chỉ iOS, hay cả hai?
- [ ] Có device farm không, hay dùng device/emulator tự quản lý?
- [ ] Bản test có khác bản production không (test flag, debug mode)?

### Timeline & báo cáo
- [ ] Mục tiêu % coverage automation?
- [ ] Khi spec thay đổi, ai cập nhật TC thủ công và báo cho team automation?
- [ ] Format báo cáo mong đợi là gì, ai nhận báo cáo?

---

## Khả năng tự động hóa
> Nhóm theo Category.

| Category | Số TC | Khả năng | Lý do |
|---|---|---|---|
| <category> | N | ✅ Auto | Luồng UI/API ổn định, lặp lại được |
| <category> | N | ⚠️ Cần làm rõ | <lý do cụ thể — vd: cần xác nhận quyền truy cập DB> |
| <category> | N | 🔴 Skip | <lý do cụ thể — vd: tương tác camera> |

---

## Quan sát cấu trúc

### Nhóm chạy nối tiếp (Sequential Flow) — gộp các TC-bước thành 1 test case hoàn chỉnh
<chỉ liệt kê nếu phát hiện>

Với mỗi nhóm: nêu rõ **đích danh các TC được gộp với nhau**, tên test case gộp đề xuất, và **lý do cụ thể** (mặc định: các TC này là các bước nối tiếp để hoàn thành 1 luồng nghiệp vụ, không phải các mục tiêu kiểm thử độc lập riêng lẻ — viết riêng từng TC sẽ phải tái tạo lại state của các bước trước, tốn effort mà không phản ánh đúng luồng người dùng thực tế trải nghiệm).

> ⚠️ **Liệt kê đầy đủ TẤT CẢ các nhóm phát hiện được — không viết tắt.** Nếu phát hiện 56 nhóm thì viết ra cả 56, mỗi nhóm có dòng "Nhóm <i>" và dòng "→ Lý do:" riêng. **Cấm dùng** "...", "tương tự nhóm trên", "tiếp tục theo cùng quy tắc cho Nhóm 4–53" hoặc bất kỳ cách viết tắt nào để bỏ qua nhóm — dù lý do có cấu trúc giống nhau, vẫn phải viết đầy đủ cho từng nhóm. Đây là phần để khách hàng đối chiếu ngược lại với file Excel gốc, viết tắt sẽ làm mất mục đích đó.

- **Nhóm <i>**: TC-XXX + TC-XXX + TC-XXX + ... + TC-XXX → gộp thành 1 test case tự động **"<tên mô tả luồng + điều kiện, vd: Đăng ký vay - Thuê bao Viettel - BI 750-779 - Có bảo hiểm>"**
  → Lý do: <giải thích cụ thể — vd: đây là N bước nối tiếp của 1 luồng đăng ký vay hoàn chỉnh, TC sau dùng lại session/record do TC trước tạo ra, không tự đứng độc lập được>
- **Nhóm <i+1>**: ... *(lặp lại đầy đủ cho từng nhóm còn lại, không bỏ sót)*

### Cơ hội gộp data-driven (Data-driven Consolidation) — gộp nhiều test case-luồng lại với nhau
<chỉ liệt kê nếu phát hiện>

Đây là bước gộp tiếp theo, áp dụng trên **các test case đã gộp ở mục trên** (không phải trên từng TC gốc): so sánh các test case-luồng đó với nhau, nếu chúng có cấu trúc step giống nhau và chỉ khác dữ liệu, có thể gộp tiếp thành 1 template chung.

Với mỗi nhóm phát hiện được, nêu rõ **đích danh toàn bộ các dải TC** (mỗi dải = 1 test case-luồng đã gộp ở trên) được hợp nhất vào cùng 1 template, và lý do. **Liệt kê hết tất cả các dải, không dùng "..." để bỏ qua dải nào ở giữa:**

- **<tên luồng chung>**: <N> test case-luồng — gồm các dải <TC-XXX–TC-XXX>, <TC-XXX–TC-XXX>, <TC-XXX–TC-XXX>, ... *(viết hết toàn bộ N dải, không bỏ giữa)* — có cấu trúc step giống nhau, chỉ khác <liệt kê field thay đổi — vd: mức điểm tín dụng, gói, flag>
  → Lý do: cùng là 1 luồng nghiệp vụ được test dưới nhiều điều kiện đầu vào khác nhau, không phải N luồng nghiệp vụ khác nhau — gộp thành 1 template + 1 bảng dữ liệu <N> dòng (mỗi dòng ghi rõ dải TC nguồn để giữ trace) sẽ tránh lặp code cho cùng 1 luồng

**So sánh — không gộp vs. gộp:**

| | Không gộp (1 script/TC) | Gộp (1 template + bảng dữ liệu) |
|---|---|---|
| Số script phải viết | <N> | ~<M> script tương đương |
| Thời gian implement | ~<Days₁> ngày | ~<Days₂> ngày (nhanh hơn ~<ratio> lần) |
| Trace về TC-XXX gốc | Trực tiếp, 1:1 | Gián tiếp — chỉ giữ được nếu mỗi dòng data/kết quả được đặt tên theo TC-XXX hoặc điều kiện nguồn |
| Maintenance khi step chung thay đổi | Sửa <N> file | Sửa 1 template |
| Chẩn đoán khi fail | Mỗi lỗi gắn với đúng 1 TC | Lỗi hiện ra ở dòng data nào — vẫn trace được nếu đặt tên dòng tốt |
| Rủi ro | Mỗi case rõ ràng, ít khả năng bỏ sót edge case | Một dòng cần thêm/khác step có thể không khớp template một cách âm thầm, thay vì fail rõ ràng |

**Lợi ích khi gộp nhóm này:**
- <điểm cụ thể gắn với data của nhóm này — vd: "thêm mức điểm tín dụng mới sau này = 1 dòng data mới, không phải 1 script mới">
- <điểm cụ thể — vd: "chỉ cần sửa 1 chỗ khi UI luồng đăng ký thay đổi, thay vì sửa <N> chỗ">

**Hạn chế khi gộp nhóm này:**
- <điểm cụ thể — vd: "trace về TC-XXX gốc cần đặt tên dòng data cẩn thận">
- <điểm cụ thể — vd: "1 lỗi trong template ảnh hưởng cả <N> dòng cùng lúc">

**Thời gian tiết kiệm nếu gộp:** ~<Days₁ − Days₂> ngày công (nhanh hơn ~<ratio> lần)

**Quyết định:** <gộp | giữ độc lập | TBD — chờ user quyết định> — đã hỏi user kèm bảng so sánh trên trước khi hoàn tất file này.

**Tổng kết:** <tổng số TC auto> → ước tính **~<M> test method** sau khi gộp (hoặc **<N> script** nếu giữ độc lập, theo quyết định của user)

---

## Phạm vi tự động hóa

| | Số lượng | % |
|---|---|---|
| ✅ Auto | N | X% |
| ⚠️ Cần làm rõ | N | X% |
| 🔴 Skip | N | X% |
| **Tổng** | **N** | **100%** |

**Chi tiết Skip:**
- Tương tác vật lý (camera/biometric/NFC/barcode): N TC
- Visual/UX mang tính chủ quan: N TC
- Chưa stable / chưa xác nhận: N TC
- <lý do khác>: N TC

**Phần vẫn cần test thủ công sau khi automation hoàn tất:**
- Exploratory testing và các edge case không có trong file TC
- Kiểm tra Visual/UX
- Toàn bộ TC trong danh sách Skip ở trên
- Setup ban đầu / smoke check trên môi trường mới

---

## Giai đoạn ưu tiên

### P1 — Happy Path
> Chạy mỗi PR / merge vào main.
<danh sách TC — ID và tên>

### P2 — Edge Case / Tiêu cực
> Chạy nightly.
<danh sách TC>

### P3 — Còn lại
> Chạy weekly / theo sprint / trước release.
<danh sách TC>

---

## Ước tính Implementation

**Số TC Auto cần implement:** <N> (sau khi loại Skip)
**Sau khi gộp data-driven:** ~<M> test method

**Velocity gốc:** 3–5 script/ngày/người
**Velocity điều chỉnh:**
- Framework: <đã có → ×1.0 | làm mới → ×0.6>
- Team level: <senior → ×1.0 | mixed → ×0.85 | junior → ×0.7>
- Environment: ×<N>

**Cơ bản:** ~<M> method ÷ <velocity> = <X> ngày

**Buffer +30%:**
- Kỹ năng yếu / nghỉ đột xuất
- Server/network/môi trường không ổn định
- Thay đổi yêu cầu giữa chừng
- Vừa làm vừa maintain module cũ

**Tổng ước tính:** ~<X> ngày / <số người> người → **~<Y> ngày công**

<nếu 3c phát hiện cơ hội gộp VÀ user từ chối gộp:>
> ⚠️ **Lưu ý:** xem mục Quan sát cấu trúc > Cơ hội gộp data-driven để có bảng so sánh đầy đủ. Việc không gộp khiến scope này tốn thêm ~<Y₁ − Y₂> ngày công (chậm hơn ~<ratio> lần) — nhắc lại ở đây vì Ước tính Implementation là nơi team thực sự ra quyết định về budget/nhân sự.

<nếu có deadline:>
**Deadline:** <date> → **<đúng tiến độ ✅ / rủi ro ⚠️ / không khả thi 🔴>**

---

## Ước tính thời gian chạy

**Platform:** <platform>
**Thời gian trung bình/TC:** <10–30s API | 30–90s web | 60–180s android/ios>

| Suite | Số TC | Chạy nối tiếp | Chạy parallel (4 thread) |
|---|---|---|---|
| P1 | N | ~X phút | ~X phút |
| P1 + P2 | N | ~X phút | ~X phút |
| Full suite | N | ~X phút | ~X phút |

<nếu Q6 đã trả lời:>
**Kỳ vọng của khách hàng:** < <X> phút
**Đánh giá:** Chạy nối tiếp ~<Y> phút — <đáp ứng ✅ / vượt ⚠️> kỳ vọng
<nếu vượt:> → Đề xuất chạy parallel với ít nhất <N> thread để đáp ứng kỳ vọng.

<nếu Q6 bị skip:>
**Kỳ vọng của khách hàng:** [TBD — chờ họp với khách hàng]
> Chạy lại `/autotest-strategy <feature>` sau buổi họp để hoàn thiện mục này.

---

## Lịch CI/CD

| Suite | Trigger |
|---|---|
| P1 (Happy Path) | Mỗi PR / merge vào main |
| P2 (Edge Case) | Build nightly |
| P3 (Còn lại) | Weekly / theo sprint / trước release / trước deploy |

---

## Dữ liệu test & Môi trường

- **Platform:** <platform>
- **Số môi trường:** <N — hoặc [TBD]>
- **Số tài khoản test cần:** <N> — <giải thích cách ra số này, không để con số trơ trụi. Quy tắc tính: nếu state-changing (3d) được phát hiện, mỗi tổ hợp precondition độc lập (mỗi nhóm từ 3b/3c, hoặc mỗi TC độc lập không thuộc nhóm nào) cần ít nhất 1 tài khoản riêng để không làm sai precondition của tổ hợp khác khi chạy chung tài khoản. Nêu rõ: "<N> = <K> nhóm/luồng phát hiện ở Quan sát cấu trúc + <M> TC độc lập còn lại" kèm tham chiếu ngược lại đúng con số đã liệt kê ở mục đó, để người đọc (kể cả khách hàng) verify được nguồn gốc số liệu, không phải số đoán.>
- **Cơ chế reset dữ liệu:** <từ câu trả lời — hoặc [TBD — chờ họp với khách hàng]>
- **Nhóm config batch:** <liệt kê nếu phát hiện — hoặc N/A>
- **Độ ổn định staging:** [TBD — chờ họp với khách hàng]

---

## Rủi ro Maintenance

| Nhóm / TC | Rủi ro | Lý do |
|---|---|---|
| <TC có nhiều locator UI hoặc luồng dài> | 🔴 Cao | Dễ vỡ khi UI thay đổi |
| <TC có dữ liệu động — OTP, timestamp, điểm số> | 🟠 Trung bình | Phụ thuộc dữ liệu |
| <TC chỉ qua API hoặc UI ổn định> | 🟡 Thấp | Ít phụ thuộc UI |

---

## Đề xuất Demo

TC đề xuất cho demo khách hàng (< 2 phút mỗi TC, happy path dễ thấy giá trị):
1. TC-XXX: <tên> — <lý do: giá trị business rõ ràng, ngắn gọn>
2. TC-XXX: <tên>
3. TC-XXX: <tên>

> Tip: highlight đúng element đang tương tác ở mỗi step để khách hàng dễ theo dõi.
> Nếu feature này đã demo sprint trước, bỏ qua demo và báo cáo tiến độ thay thế.

---

## Template báo cáo tiến độ

```
📊 Cập nhật Sprint — <feature> — <date>

✅ Done:        X / N TC  (<category đã hoàn thành>)
🔄 Đang làm:    X TC      (<category hiện tại>)
⏭️ Đã Skip:     X TC      (<lý do>)
❓ Đang chờ:    X TC      (chặn bởi: <điểm chặn>)

📅 ETA full suite: <date>
Milestone kế tiếp: <việc hoàn thành ở sprint sau>
```

---

## Phụ lục A: Danh sách TC chi tiết theo điểm chặn
<chỉ render nhóm nào có >15 TC — nhóm ≤15 TC đã liệt kê đủ ngay trong mục Điểm chặn, không cần lặp lại ở đây>

### <tên điểm chặn, vd: Tương tác vật lý (eKYC/camera)> — N TC
<liệt kê đầy đủ ID, có thể dùng dải liên tiếp để gọn hơn (vd "TC-006, TC-013, TC-020, TC-028...TC-489")>

### <tên điểm chặn khác> — N TC
<tương tự>
```

---

## Step 5: Đề xuất điều chỉnh TC file

Sau khi đã viết xong `strategy.md`, xem lại kết quả phân tích ở Step 3 và xác định những TC nào cần chỉnh sửa để phù hợp với automation. Chỉ đề xuất khi thực sự cần — không sửa những TC đã rõ ràng.

### Các trường hợp cần đề xuất sửa

| Vấn đề | Đề xuất |
|---|---|
| TC(i+1) phụ thuộc state của TC(i) — phát hiện ở 3b | Gộp thành 1 TC automation với đầy đủ các bước |
| ≥3 TC cùng steps, chỉ khác data — phát hiện ở 3c | Gộp thành 1 TC + data table |
| Steps quá chung chung, thiếu action/selector cụ thể | Bổ sung mô tả chi tiết hơn |
| Expected result mơ hồ ("hiển thị đúng", "thành công") | Bổ sung expected cụ thể từ tài liệu |
| Mâu thuẫn giữa TC và domain docs | Ghi rõ 2 phiên bản + nguồn, chờ user xác nhận cái nào đúng |
| Dữ liệu test hardcode trong steps (username, password, số tiền cụ thể) | Ghi chú nên tách ra data file |

**Nếu không có gì cần sửa** → báo ngắn gọn và dừng:
> Kịch bản kiểm thử đã phù hợp với automation — không cần điều chỉnh.

**Nếu có đề xuất** → hiển thị danh sách rõ ràng và hỏi user 1 lần:

> **Đề xuất điều chỉnh kịch bản kiểm thử** (`<tc_hit>`):
>
> 1. **[Gộp] TC-002 + TC-003 + TC-004 → TC-002**
>    Lý do: 3 bước nối tiếp của 1 luồng, TC sau phụ thuộc state TC trước.
>    Thay đổi: gộp steps của cả 3 TC vào TC-002, xoá TC-003 và TC-004.
>
> 2. **[Tách data] TC-007, TC-008, TC-009**
>    Lý do: cùng steps, chỉ khác username/password.
>    Thay đổi: gộp thành TC-007 + ghi chú "data-driven: xem automation_test/data/<feature>.csv".
>
> 3. **[Làm rõ expected] TC-010**
>    Hiện tại: "Hệ thống hiển thị thông báo thành công"
>    Đề xuất: "Hiển thị toast message `Thanh toán thành công`" (từ business-scenario.md)
>
> ---
> Áp dụng thay đổi nào?
> - **Tất cả** — áp dụng hết
> - **1, 3** — chỉ áp dụng đề xuất được chọn (nhập số)
> - **Không** — giữ nguyên file TC

Chờ user trả lời.

### Sau khi user xác nhận

- **Tất cả / chọn số cụ thể** → áp dụng đúng những thay đổi đó vào TC file. Giữ nguyên TC ID và tên gốc (chỉ mở rộng nếu cần). Báo kết quả.
- **Không** → dừng, không chỉnh sửa. Chiến lược vẫn được lưu đầy đủ ở `strategy.md`.

---

## Rules

- **TC file is the single source of truth** — never invent TCs, never rename them.
- **All detection is automatic** — do not ask the user about things that can be derived from TC content.
- **Skip any question the user marks as skip** — write `[TBD — pending client meeting]` and move on.
- **TBD fields are patchable** — when user reruns after meeting, update only TBD sections, preserve everything else.
- **Never overwrite without confirming** — always ask Update vs Regenerate if file exists.
- **Generic across all projects** — no project-specific terminology in output. Derive everything from TC content signals.
- **Platform affects execution time numbers** — always use the correct avg/TC for the detected platform.
- **A 🔴 Skip/blocked classification never stops further analysis** — always run 3b–3f (sequential flow, consolidation, state-changing, config batch, scope gap) against the full TC set, including TCs already marked Skip. Report every issue found, not just the first one per TC.
- **Write the final `strategy.md` entirely in Vietnamese** — it is a client-facing document used to discuss scope/estimate with the customer. Keep widely-used technical terms as-is (TC, API, DB, OTP, eKYC, CI/CD, ✅ Auto / ⚠️ Pending / 🔴 Skip labels); translate everything else, including section headers and prose.
- **Every English technical term kept as-is must carry a Vietnamese gloss** — this covers status codes, enum values, condition codes, field names (e.g. `DISBURSED`, `PENDING_UNDERWRITING`, `CHECK_DEDUP_*`, `qualified_segment`) AND general engineering jargon words used inside a business name (e.g. "dedup" in "điều kiện dedup khoản vay", "timeout", "polling", "callback") — none of these can be left bare for a non-technical reader. The first time (or every time, if used in a short list) such a term appears, add a short Vietnamese explanation in parentheses right next to it — e.g. `DISBURSED` (đã giải ngân), `PENDING_UNDERWRITING` (đang chờ thẩm định), `OVERDUE` (quá hạn), "dedup" (viết tắt *deduplication* — kiểm tra trùng/xung đột). Do not assume the client knows what an enum value or jargon word means just because it's quoted from the source system or sounds common to engineers.
- **Gloss order must match reading order, not section order in the template.** "Luồng nghiệp vụ tổng quan" is written before "Kiến thức nghiệp vụ quan trọng" in the file, so if a term (e.g. `BI`, `Datanet`) is first used in the flow description but only explained later in the knowledge section, either add a short inline gloss right there too, or explicitly forward-reference the section by name (e.g. "điểm tín dụng (BI/Datanet — xem giải thích ở mục Kiến thức nghiệp vụ quan trọng bên dưới)") — never let a reader hit an unexplained term before its definition.
- **If a domain doc uses an acronym/system name (e.g. `CDCN`, `BCCS`) without ever spelling out what it stands for, do not guess or invent an expansion.** Search the available domain docs and TC content for what the term actually *does* (what data it returns, what role it plays), and gloss it functionally instead — e.g. "CDCN (hệ thống cung cấp thông tin định danh + tài khoản ViettelPay/MM của khách hàng — tài liệu nguồn không giải nghĩa chữ viết tắt này)". State plainly that the source material doesn't define the acronym, so the reader knows to ask BA/dev if they need the literal expansion, rather than silently presenting a fabricated guess as fact.
- **Không sửa TC file mà không có xác nhận** — Step 5 luôn hiển thị đề xuất và chờ user duyệt trước khi ghi bất kỳ thay đổi nào.
- **Mâu thuẫn TC vs tài liệu → hỏi, không tự chọn** — liệt kê cả 2 phiên bản kèm nguồn, để user quyết định.
- **Keep named steps/concepts consistent throughout the file** — once a step or concept is given a specific name (e.g. "Pre-screening 1"), every later reference to it must use that exact name, never a shortened or casual variant ("pre-check", "precheck"). This matters most when similarly-named steps exist (Pre-screening 1 vs Pre-screening 2) — an inconsistent name leaves the reader unable to tell if two mentions refer to the same step or different ones.
- **Never write a vague internal cross-reference** — "xem mục dưới", "xem ở trên", "see above/below", "như đã nói ở trên" name no destination and force the reader to hunt for it. Every cross-reference must name the exact section heading it points to (e.g. "xem mục Kiến thức nghiệp vụ quan trọng", "xem Quan sát cấu trúc > Cơ hội gộp data-driven"). This applies everywhere in the file, including free-text synthesis sections like Project & Feature Summary, not just the templated sections that already do this correctly.
