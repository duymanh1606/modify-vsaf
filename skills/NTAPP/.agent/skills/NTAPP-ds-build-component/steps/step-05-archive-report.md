# Step 5: Archive & Report

## GOAL
Dual-write `archive/_v{N+1}_{timestamp}/` snapshot + generate `build_report.md` với `proposal_checksum` (cho pre-commit Rule 7 detect outdated). Optional auto-commit.

## INSTRUCTIONS

1. **Reuse Persona:** Metadata Registrar đã handle archive logic trong `agents/metadata-registrar.md` mục 3.8. Step này validate + finalize report.

2. **Compose final `build_report.md`:**

   Concat-by-emit-order pattern — Step 5 KHÔNG hardcode section list. Mỗi sub-agent (Step 2-4) **append in-memory** một section vào `build_report_sections[]` array khi thực thi xong; Step 5 concat array theo apply_order với header + footer fixed:

   ```markdown
   # Build Report — {id}

   **Applied at:** {iso timestamp}
   **Proposal source:** {bmad-stage-4b | manual}
   **Proposal checksum:** sha256:{hash}      ← Pre-commit hook Rule 7 dùng

   {concat build_report_sections[] theo apply_order}

   ## [ARCHIVE]
   - Path: archive/_v{N+1}_{timestamp}/
   ```

   Section nào sub-agent emit ra (xem persona §4/§8/§11 Output) sẽ xuất hiện trong report. Thêm sub-agent mới sau này → tự append section, không cần update Step 5. Section thường thấy: `[TOKENS APPLIED]` (Step 3), `[RUNTIME TOKENS EXPORTED]` (Step 3b), `[COMPONENTS SCAFFOLDED]` + `[COMPONENTS PATCHED]` + `[METADATA REGISTERED]` (Step 4), `[DSO Override — Warnings skipped]` (Step 2 nếu có override), `[LAYOUT-PRIMITIVE SKIPPED]` (Step 4 lazy materialization).

3. **Verify archive completeness:**
   - `{design_system_root}/archive/_v{N+1}_{timestamp}/` chứa:
     - `master_token.json`
     - `components_metadata.json`
     - `stack-profile.json` (snapshot dù không thay đổi — coherent restore point)
     - `runtime_tokens/` — copy của runtime token file(s) từ Step 3b (file path bên code repo + checksum). Cho phép restore cross-repo nếu cần.
     - `build_report.md` (copy từ feature_deltas)
   - Thiếu file → log warning, không exit fail (archive best-effort).

4. **Write build report:**
   - Path: `{design_system_root}/feature_deltas/{id}/build_report.md`.
   - Atomic write: tempfile → rename.

5. **Optional auto-commit per repo (HITL prompt):**
   - Hỏi DSO: *"Tạo commit local cho 2 repo? **Spec repo** sẽ commit `master_token.json` + `components_metadata.json` + `feature_deltas/{id}/build_report.md` + archive snapshot. **Code repo** sẽ commit runtime token file (`{runtime_token_path}`) + scaffolded + patched component files. Y (cả 2 repo) / spec-only / code-only / N. Nếu Y, override commit message hay dùng default template?"*
   - DSO Y → tạo commit ở **cả 2 repo** với cùng `id` trong message để link traceability:
     - Spec repo template: `"ds-build({id}): apply {tokens_count} tokens, {components_count} components — Master DS update"`
     - Code repo template: `"ds-build({id}): export runtime tokens + scaffold/patch components per Master DS"`
   - DSO spec-only / code-only → chỉ commit repo tương ứng, repo còn lại để DSO commit thủ công sau.
   - DSO N → skip commit ở cả 2 repo (DSO tự commit sau).
   - KHÔNG push (chỉ local commit).

## OUTPUT

**Spec repo** (`{design_system_root}/...`):
- `feature_deltas/{id}/build_report.md` (final)
- `archive/_v{N+1}_{timestamp}/` (snapshot complete)
- (Optional) git commit local nếu DSO confirm

**Code repo** (`{code_repo_root}/...`):
- Runtime token file `{styling.runtime_token_path}` (đã ghi xong trong Step 3b)
- New / patched component files (đã ghi xong trong Step 4)
- (Optional) git commit local nếu DSO confirm

## CONSOLE SUMMARY
```
[BUILD] Step 5: Archive {design_system_root}/archive/_v{N+1}_{timestamp}/ created
[BUILD] Done. Build report: {design_system_root}/feature_deltas/{id}/build_report.md
[BUILD] Pre-commit Rule 7 (spec repo) will accept this commit (checksum match).
[BUILD] Cross-repo reminder: cần tạo 2 commit (spec repo + code repo). Đề xuất merge code repo PR trước, spec repo PR sau.
```

## CONSTRAINTS
- KHÔNG push git remote (commit local only nếu DSO confirm).
- Archive snapshot phải tạo trước khi báo done.
- `proposal_checksum` deterministic: sha256 của `proposed_ds_updates.md` raw bytes.
- Không commit cross-repo bằng 1 lệnh git duy nhất (không atomic được — xem [Manual mục 8.3](../../docs/Process/Manual_phase_1.md)).

---

> **[TERMINAL]** Đây là step cuối của pipeline — KHÔNG có `**Next:**`. Build-component hoàn tất sau khi `build_report.md` + archive snapshot ghi xong (+ optional commit local nếu DSO confirm).
