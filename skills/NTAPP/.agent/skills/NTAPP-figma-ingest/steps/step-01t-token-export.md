# Step 1t: Token Export (gated — chỉ mode `--tokens-only`)

## GOAL

Xuất Figma Variables / Styles ra **W3C token JSON** để DSO đưa vào `/ntapp-ds-bootstrap --external-tokens`. Đây là **pass 0** giải vòng phụ thuộc: `ds-bootstrap` cần file token từ Figma, còn full ingest cần `master_token.json` để snap.

## ENTRY CONDITION

Chỉ chạy khi step-01 kết luận `run_mode == "tokens-only"`. Invoke trực tiếp mà không qua step-01 → STOP: *"Chạy `/ntapp-figma-ingest --tokens-only` để step-01 resolve nguồn trước."*

**TERMINAL step** — không chạy tiếp step-02.

## 1. Persona

Procedural. Tuân thủ U1 (atomic), U4 (deterministic), U5 (no fabrication — KHÔNG bịa tier/semantic cho token không đọc được), U6, U7.

## 2. Inputs

- `figma-source.json` (step-01) — `file_key` + `version` pinned.
- `{family_root}/_shared/w3c-converter.md` — **SSoT format conversion**. KHÔNG restate luật convert ở đây.
- `{family_root}/_shared/token-format-schema.md` — tier/semantic của NTAPP v1.

## 3. Pipeline

### Stage 3.1: Thử Variables API (nguồn tốt nhất)

```bash
bash <skill_dir>/scripts/figma-fetch.sh variables --out "{output_root}/.work/variables.json"
```

- **200** → nguồn `variables`. Figma Variables map gần nhất với design token thật (có collection, mode light/dark, alias) → chất lượng cao nhất.
- **403** → endpoint này yêu cầu **Enterprise plan**. KHÔNG STOP — fallback Stage 3.2, ghi WARN.
- **404** → file không có variable nào → fallback Stage 3.2.

### Stage 3.2: Fallback Styles API

```bash
bash <skill_dir>/scripts/figma-fetch.sh styles --out "{output_root}/.work/styles.json"
```

Styles chỉ cho `FILL` / `TEXT` / `EFFECT` / `GRID` — **không có spacing, không có radius, không có mode**. Ghi rõ giới hạn này vào report để DSO không tưởng đã có bộ token đủ.

### Stage 3.3: Fallback manual (Tokens Studio)

Cả 3.1 và 3.2 fail (hoặc `source_mode: manual`) → đọc `inbox/tokens.json`. Không có → STOP: *"Không lấy được token qua API (403 = không phải Enterprise). Nhờ designer export bằng plugin **Tokens Studio** (Export → W3C DTCG JSON) rồi drop vào `{output_root}/inbox/tokens.json`, chạy lại."*

### Stage 3.4: Normalize → W3C

1. Nguồn `variables`: mỗi variable → token path theo tên collection/group (`color/brand/primary` → `color.brand.primary`). Mode → W3C `$extensions` (giữ light/dark, KHÔNG flatten mất mode).
2. Nguồn `styles`: tên style dạng `Brand/Primary` → path `brand.primary`. Style không có giá trị resolve (chỉ metadata) → cần thêm 1 call `nodes` lấy `fills`; không resolve được → **bỏ** + liệt kê ở report (U5: không bịa).
3. Convert sang W3C DTCG theo `_shared/w3c-converter.md`. Tier (`primitive`/`semantic`/`component`) suy từ độ sâu path + naming convention; **không chắc → để trống** `$extensions.ntapp.tier`, ghi `confidence: LOW`. `ds-bootstrap` step-05 sẽ 3-way diff và DSO quyết ở đó — đây không phải chỗ chốt tier.
4. Sort keys (U4).

### Stage 3.5: Emit + hand-off hint

Ghi (atomic) `{ds_root}/_reference/figma/exports/figma-tokens.w3c.json`.

In hint chạy tiếp — **lưu ý `ds-bootstrap` chạy từ CODE repo**, nên in path dạng relative-từ-code-repo (dùng `bmad.code_repo_root` để tính, chỉ để in, không đọc/ghi code repo — U3):

```
/ntapp-ds-bootstrap --external-tokens ../{spec_repo_folder}/{ds_root_rel}/_reference/figma/exports/figma-tokens.w3c.json
```

## 4. Decision Points

- **Variables 403** → WARN, fallback styles. Report ghi rõ: *"Không có Figma Enterprise → thiếu spacing/radius/mode token. Bổ sung bằng Tokens Studio export nếu cần bộ token đủ."*
- **Cả 3 nguồn fail** → STOP theo Stage 3.3.
- **Token count = 0** sau normalize → STOP: *"Export ra 0 token — kiểm file Figma có Variables/Styles published chưa (local style chưa publish không xuất hiện ở API `/styles`)."*
- **Style không resolve được giá trị** → bỏ token đó, liệt kê ở report. KHÔNG fabricate (U5).

## 5. Output

- `{ds_root}/_reference/figma/exports/figma-tokens.w3c.json`.
- `report_sections[]` += `[TOKEN EXPORT]` (nguồn thật đã dùng, số token/tier, giới hạn nếu fallback styles, danh sách token bị bỏ).
- `figma_ingest_report.md` (bản tokens-only, ghi luôn ở step này vì đây là TERMINAL).

**TERMINAL.** Không đọc step tiếp. Việc kế tiếp thuộc về người dùng: chạy `/ntapp-ds-bootstrap --external-tokens <path>` từ code repo, rồi sau khi WBS lock mới chạy `/ntapp-figma-ingest` (full).
