# Step 02 — Fix + pre-commit + verify + code-review

**Persona:** Dev sửa lỗi tối thiểu, đúng nguyên nhân đã chốt ở step-01.

**Mục tiêu:** Sửa code cho đúng root-cause, giữ đúng pre-commit tuỳ `commit_mode`, verify ở bậc cao nhất có sẵn, review theo `lane`.

---

## 1. Fix code (tối thiểu, đúng nguyên nhân)
- Sửa **tối thiểu, đúng nguyên nhân** (R4 — không refactor ngoài phạm vi bug). Fix đúng blast radius đã localize (R2).
- Chạm hot node → kiểm consumer trong `ripples` không vỡ (giữ signature/contract). Phát hiện phải chạm file NGOÀI blast radius → DỪNG, ghi ESCALATE, KHÔNG lan sang unit khác.
- **ATDD `mandatory`** (từ step-01): sửa đến khi regression test XANH (GREEN). Đây là test-first: RED (step-01) → GREEN (đây).
- Đa file/đa repo: một bug trải nhiều điểm → sửa hết các điểm liên quan trong đúng (các) repo sở hữu unit.

## 2. Pre-commit compliance (theo resolver)
Áp Rule liên quan của pre-commit 9-rule cho vùng code sửa (dù có commit hay không — để commit sau của user không vỡ):
- **Rule 1** — header `id: <unit> | dd_version: vN` trong 10 dòng đầu; `vN` khớp `dd_version` của DD SAU-FIX (reconstruct case: DD đã bump v2 ở step-01 → header code phải `dd_version: v2`).
- **Rule 4/6/9 (UI)** — không hardcode color hex/px/font-family (dùng design token); UI file có `ui_schema` tương ứng; KHÔNG emoji unicode (import icon từ `stack-profile.icon_library`).
- `commit_mode=branch-commit` → Rule 2/3 phải PASS hợp lệ (unit có trong WBS + DD có/đã reconstruct). `SKIP_PRECOMMIT=1` CHỈ cho diện escalate (Tier 3/4 không viết được DD, hoặc WBS gap phải đặt id mới) — commit trên branch để không mất công + gắn cờ rõ trong report.
- `commit_mode=in-place-nocommit` → không commit ở đây; chỉ đảm bảo header nhất quán để hook fire đúng khi user commit sau.

## 3. Verify (bậc cao nhất có sẵn — ghi trung thực)
Theo thứ tự ưu tiên, dừng ở bậc cao nhất khả thi:
1. **ATDD/test liên quan** → chạy runner lọc theo unit. Unit thuộc slice có `demoable` + AC trong story → chạy ATDD/demo slice đó (bao phủ hành vi tốt nhất). Pass = chắc nhất.
2. **Không test nhưng có đường chạy/build** → build + smoke; quan sát không còn lỗi bug gốc.
3. **UI-style thuần** (không có test tự động) → verify bằng đọc lại code so token + mô tả; ghi rõ **cần verify trực quan thủ công** (so ảnh bug). KHÔNG tự nhận đã verify visual khi chưa chạy app.
4. **Không chạy được test trong môi trường** → ghi "verify: static-only / chưa verify tự động" + nêu rủi ro.

**GATE:** ATDD `mandatory` mà không có regression test XANH kèm theo → **BLOCKER**: KHÔNG tính là fixed, ghi vào report, KHÔNG commit.

## 4. Code-review (INLINE self-review — theo resolver)
**KHÔNG gọi `/bmad-code-review`**: skill đó có chuỗi HALT "wait-for-human" + persist bám theo story file → trong headless/fanout sẽ treo hoặc ghi finding vào hư vô. Engine là fresh-context nên tự review trực tiếp, chắc chắn hơn.

Self-review diff của lần fix này theo rubric gọn:
1. **Correctness:** bug gốc thực sự được xử lý (không che triệu chứng); fix conform DD (step-01).
2. **Blast radius:** diff CHỈ chạm file đã localize; rò rỉ file ngoài blast radius = dấu hiệu localize/grouping sót → ESCALATE (không tự sửa lan).
3. **Contract/ripples:** chạm hot node → GIỮ signature/shape response; consumer trong `ripples` không vỡ.
4. **Regression:** không phá behavior lân cận; có ATDD/test liên quan (step-01) → đối chiếu.
5. **Rule 4/6/9** (khi chạm `.tsx/.jsx/.css/.scss`): không hardcode token màu/px/font, không emoji.

- `lane≠express` → self-review **đầy đủ** cả 5 mục. `lane=express` (trivial) → self-review **nhanh** (tập trung 1/5).
- Sửa NGAY finding tầm thường. Finding còn lại + ESCALATE → **LUÔN đưa vào fix-report** (step-03). Orchestration lo persist ra file (fanout) hay in report (interactive) — engine KHÔNG tự ghi file review.

---

**Next:** Read fully and follow `./steps/step-03-close.md`
