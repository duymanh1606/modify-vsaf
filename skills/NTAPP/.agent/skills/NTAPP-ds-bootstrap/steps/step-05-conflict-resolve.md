# Step 5: Conflict Resolution (External Tokens, gated)

## GOAL

Khi DSO cung cấp external tokens (designer / Figma AI), 3-way diff giữa code (Step 2 raw extracted), external (input file), best-practice baseline (Step 4 normalized) → propose merged result.

## ENTRY CONDITION

Chỉ chạy nếu DSO đã cung cấp external tokens path tại INITIALIZATION. Workflow.md đã gate `Skip if`; step file không re-check. Nếu invoke trực tiếp step-05 mà không có external path → STOP với hint *"External tokens path không cung cấp tại INITIALIZATION. Skip Step 5 hoặc chạy lại `/ntapp-ds-bootstrap` với path."*

## 1. Load Persona

Adopt role của **Conflict Resolver** sub-agent tại `../agents/conflict-resolver.md`. Persona declare: role + decision policies (§4.1 format detection, §4.2 3-way diff matrix, §4.3 auto-apply policy) + output spec (§5a JSON, §5b markdown section) + edge cases (§6) + constraints (§7).

## 2. Inputs

- `{design_system_root}/master_token_parts/01_raw_extracted.json` (Step 2 output).
- `{design_system_root}/master_token_parts/02_normalized.json` (Step 4 baseline + proposals).
- External token file (DSO cung cấp tại INITIALIZATION).
- `_shared/w3c-converter.md` (nếu external là W3C).

## 3. Pipeline

### Stage 3.1: Format detection + (optional) W3C convert

Per `conflict-resolver.md` §4.1:
- NTAPP v1 → load trực tiếp.
- W3C → convert sang NTAPP v1 qua `_shared/w3c-converter.md` (lossless, preserve `$extensions.ntapp.tier`).
- Khác → STOP per persona §4.1 message.

### Stage 3.2: 3-way diff per path

Per `conflict-resolver.md` §4.2 matrix. Build decision per token path (union of 3 sources).

### Stage 3.3: Auto-apply policy

Per `conflict-resolver.md` §4.3:
- MATCH / USE_CODE(external missing) / USE_EXTERNAL(code missing) → `auto_applied: true`.
- Khác → `needs_dso_review: true`.

### Stage 3.4: Atomic write + section emission

Theo U1 + U2: write `{design_system_root}/master_token_parts/03_conflict_resolved.json`.

Append `[CONFLICT RESOLUTION]` vào `report_sections[]` theo persona §5b template (summary + DSO Decision Required checklist).

## 4. Decision Points

- **External format không nhận diện được** (không phải NTAPP v1 / W3C) → STOP với hint check schema hoặc convert.
- **External parse fail** → STOP với hint DSO sửa file/format.
- **W3C có gradient/animation** không support NTAPP v1 → skip với `summary.skipped`.

## 5. Output

- `{design_system_root}/master_token_parts/03_conflict_resolved.json`.
- Append `[CONFLICT RESOLUTION]` vào `report_sections[]`.

**Next:** Read fully and follow `./step-06-human-approval.md`
