#!/usr/bin/env python3
# id: EVAL-HARVESTER | dd_version: v1
"""
Evaluation harvester for the NTAPP/BMAD AI-coding workflow.

Parses the structured sections that the Stage 1-5 skills already emit
(Change Log tables, Review Findings checkboxes, Completion Notes DEVIATIONs,
AC status tags, deferred-work.md bullets, archive/ versions) and produces a
per-SLICE baseline scorecard for the three evaluation axes:

  A. Hieu qua (Effectiveness)        -> First-Pass Yield, deviation density
  B. Hieu suat (Efficiency)          -> rework (archive versions), changelog depth
  C. Defer / CR / Change Log         -> defer backlog, avoidability index, AC churn

Outputs (single root, per CLAUDE.md):
  NTAPP-output/evaluation/metrics.json   (raw machine-readable)
  NTAPP-output/evaluation/scorecard.md   (human-readable baseline)

Pure stdlib. Run from spec-repo root:  python3 scripts/eval-harvester.py
The numbers are HARVESTED, not authoritative judgement -- parser heuristics
and their known blind spots are documented in scorecard.md section "Limits".

Token-burn engine (gop tu build_token_log.py): real token burn duoc tu gom tu
session JSONL cua Claude Code -> token-log.json. Khong con file rieng; chay
`python3 scripts/eval-harvester.py --refresh-burn` de re-harvest burn cache.
"""
import datetime
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

# Project "current date" for aging math (EFF-8). Bump when re-running on a real clock.
AS_OF = datetime.date(2026, 6, 11)
# G2 — ngưỡng độ phủ session-log: phiên phủ ≥ ngần này khoảng git → coi là 'đủ',
# dưới ngưỡng → burn đánh dấu 'một phần (cận dưới)'.
COVERAGE_FULL = 0.8
DEFER_CATEGORY_ORDER = ["contract-blocked", "arch-limit", "asset-gap", "scope-deferred",
                        "test-deferred", "cross-slice-dep", "deferred-bug", "security-hardening"]

ROOT = Path(__file__).resolve().parent.parent
# Output root: ưu tiên '_bmad-output' (tên cũ trước commit rename), fallback
# 'NTAPP-output' (tên mới) để đọc được cả cây dự án đã/chưa migrate. Default
# '_bmad-output' nếu chưa có thư mục nào (project chưa chạy).
BMAD_OUT = next((ROOT / n for n in ("_bmad-output", "NTAPP-output") if (ROOT / n).is_dir()),
                ROOT / "_bmad-output")
S5 = BMAD_OUT / "Stage_5_Build_Verify"
SLICES_DIR = BMAD_OUT / "Stage_2_Architecture" / "slices"
DESIGN_DIR = BMAD_OUT / "Stage_4_Design"
UI_SCHEMA_DIR = DESIGN_DIR / "ui_schema"           # drift_report_*.md sống ở đây (G8)
DD_DIR = DESIGN_DIR / "detailed_design"            # *_detailed_design.md (CR table + drift §1.2 — G10)
DD_ARCHIVE = DD_DIR / "archive"
OUT_DIR = BMAD_OUT / "evaluation"

# --- Cost lens (Bộ C) -------------------------------------------------------
# Token PROXY: deliverable weight, NOT real LLM burn. ~4 chars/token (rough,
# language-agnostic). Real burn (input+thinking+retries+re-reads) is typically
# 5-50x this. Burn nay AUTO-harvest tu session JSONL qua harvest_burn() (engine
# gop trong chinh file nay) khi token-log.json chua co (hoac --refresh-burn) --
# xem load_token_log() + section "Token-burn engine" o cuoi file.
CHARS_PER_TOKEN = 4
# Mở rộng cho cả FE (TS/JS/Vue/...) lẫn BE (Java/Kotlin/Go/Rust/C#/...) — multi-repo.
CODE_EXT = re.compile(
    r"\.(ts|tsx|js|jsx|mjs|cjs|css|scss|sass|less|vue|svelte|py"
    r"|java|kt|kts|go|rs|cs|rb|php|scala|swift|c|cc|cpp|cxx|h|hpp|hxx)$")
# Test-detection: pattern JS (.test./.spec./.cy.) + path/name convention BE.
TEST_FILE = re.compile(r"\.(test|spec|cy)\.|\.integration\.test\.")
TEST_NAME = re.compile(r"(Test|Tests|IT|Spec)\.[A-Za-z]+$|_test\.(go|py|rb)$|_spec\.rb$")
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|specs)/|/src/test/|(^|/)src/test/")
# Thư mục build/dep KHÔNG đo (khớp theo segment, kể cả khi lồng trong module con).
SKIP_DIRS = {"node_modules", "build", "dist", ".pnpm-store", "target", ".gradle",
             "out", "vendor", "__pycache__", ".venv", "venv", ".next", ".nuxt",
             "coverage", "obj"}
ID_HEADER = re.compile(r"id:\s*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)")
TOKEN_LOG = OUT_DIR / "token-log.json"  # real-burn cache (auto-harvested if missing)

# --- Claude API pricing (hard reference) ------------------------------------
# Nguon: Claude API pricing. USD / 1 TRIEU token. Quy uoc chung moi model:
#   cache_write = 1.25x input (5-min TTL); cache_read = 0.1x input.
# PRICE_PER_MTOK = default/fallback (Opus 4.8) cho model khong nam trong
# PRICE_BY_MODEL. Chi phi tinh THEO TUNG MODEL qua price_for_model() (session dung
# ca Opus lan Haiku cho sub-agent → dinh gia phang mot model se lech).
PRICING_MODEL = "claude-opus-4-8"
PRICE_PER_MTOK = {
    "input": 5.00,           # input_tokens (uncached)
    "cache_write": 6.25,     # cache_creation_input_tokens (1.25x, ephemeral 5-min)
    "cache_read": 0.50,      # cache_read_input_tokens (0.1x)
    "output": 25.00,         # output_tokens
}
# Bang gia per-model (input, output tra cuu; cache_write=1.25x, cache_read=0.1x input).
# Key = base model id (đã bỏ hậu tố [1m]/-YYYYMMDD qua _price_norm).
PRICE_BY_MODEL = {
    "claude-opus-4-8":   {"input": 5.00, "cache_write": 6.25, "cache_read": 0.50, "output": 25.00},
    "claude-opus-4-7":   {"input": 5.00, "cache_write": 6.25, "cache_read": 0.50, "output": 25.00},
    "claude-opus-4-6":   {"input": 5.00, "cache_write": 6.25, "cache_read": 0.50, "output": 25.00},
    "claude-sonnet-5":   {"input": 3.00, "cache_write": 3.75, "cache_read": 0.30, "output": 15.00},
    "claude-sonnet-4-6": {"input": 3.00, "cache_write": 3.75, "cache_read": 0.30, "output": 15.00},
    "claude-sonnet-4-5": {"input": 3.00, "cache_write": 3.75, "cache_read": 0.30, "output": 15.00},
    "claude-haiku-4-5":  {"input": 1.00, "cache_write": 1.25, "cache_read": 0.10, "output": 5.00},
    "claude-fable-5":    {"input": 10.00, "cache_write": 12.50, "cache_read": 1.00, "output": 50.00},
    "claude-mythos-5":   {"input": 10.00, "cache_write": 12.50, "cache_read": 1.00, "output": 50.00},
}


def _price_norm(mid):
    """Chuẩn hoá model_id thô → base id để tra PRICE_BY_MODEL (bỏ [1m]/-YYYYMMDD)."""
    base = re.sub(r"\[.*?\]$", "", mid or "")
    return re.sub(r"-\d{8}$", "", base)


def price_for_model(mid):
    """Bảng giá 4 thành phần cho 1 model; fallback Opus 4.8 nếu model lạ."""
    return PRICE_BY_MODEL.get(_price_norm(mid), PRICE_PER_MTOK)

# --- Model display names (model_id thô trong session JSONL → tên gọn) ----------
MODEL_NAMES = {
    "claude-opus-4-8": "Opus 4.8", "claude-opus-4-7": "Opus 4.7", "claude-opus-4-6": "Opus 4.6",
    "claude-sonnet-5": "Sonnet 5",
    "claude-sonnet-4-6": "Sonnet 4.6", "claude-sonnet-4-5": "Sonnet 4.5",
    "claude-haiku-4-5": "Haiku 4.5", "claude-fable-5": "Fable 5", "claude-mythos-5": "Mythos 5",
}


def model_label(mid):
    """Chuẩn hoá model_id (bỏ hậu tố [1m]/-YYYYMMDD) rồi map sang tên gọn."""
    if not mid:
        return "unknown"
    base = re.sub(r"\[.*?\]$", "", mid)              # bỏ '[1m]'
    base = re.sub(r"-\d{8}$", "", base)              # bỏ date-suffix
    return MODEL_NAMES.get(base, base)


def merge_models(dicts):
    """Gộp nhiều dict {model_id:{input,output}} lại (cộng token)."""
    out = {}
    for d in dicts:
        for mid, v in (d or {}).items():
            o = out.setdefault(mid, {"input": 0, "output": 0})
            o["input"] += v.get("input", 0)
            o["output"] += v.get("output", 0)
    return out


def model_share(by_model):
    """{model_id: {input, output}} → 'Opus 4.8 (15%), Sonnet 4.6 (85%)' theo token total."""
    if not by_model:
        return "n/a"
    tot = {}
    for mid, v in by_model.items():
        tot[model_label(mid)] = tot.get(model_label(mid), 0) + v.get("input", 0) + v.get("output", 0)
    grand = sum(tot.values())
    if not grand:
        return "n/a"
    items = sorted(tot.items(), key=lambda kv: -kv[1])
    return ", ".join(f"{name} ({round(100 * t / grand)}%)" for name, t in items if t)

def read(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def parse_slices():
    """slice_id -> [unit_id]; also unit_id -> slice_id, plus slice meta (type)."""
    slice_units, unit_slice, slice_meta = {}, {}, {}
    for f in sorted(SLICES_DIR.glob("SLICE-*.md")):
        txt = read(f)
        sid_m = re.search(r"SLICE-(\d+)", f.name)
        sid = f"SLICE-{int(sid_m.group(1))}" if sid_m else f.stem
        units = re.findall(r"-\s*\{\s*id:\s*([A-Z0-9-]+)", txt)
        slice_units[sid] = units
        for u in units:
            unit_slice[u] = sid
        stype = "HITL" if re.search(r"^type:\s*HITL", txt, re.M) else "AFK"
        demo = (re.search(r"demo_status:\s*(\w+)", txt) or [None, "?"])[1]
        slice_meta[sid] = {"type": stype, "demo_status": demo}
    return slice_units, unit_slice, slice_meta


def section(txt, start_pat, end_pat=r"\n##\s"):
    """Return text of the section starting at start_pat up to next end_pat."""
    m = re.search(start_pat, txt)
    if not m:
        return ""
    rest = txt[m.end():]
    e = re.search(end_pat, rest)
    return rest[: e.start()] if e else rest


def count_ac(txt):
    """AC total + method. Prefer bold headers (**AC-N); fall back qua nhiều style.

    Thứ tự ưu tiên: bold-header → numbered-bold (WGT) → referenced AC-id →
    plain-list (BE/prose). Nhánh plain-list bắt unit BE liệt kê tiêu chí bằng
    list thường (KHÔNG `**AC-N**`, KHÔNG AC-id) — nếu thiếu nhánh này, unit BE
    trả 0 AC, làm mẫu số FPY lệch nguồn so với tử số `[Review][Patch]` và đẩy
    FPY xuống âm (xem build(): guard `fpy_ac`)."""
    ac_sec = section(txt, r"##\s*Acceptance Criteria")
    bold = set(re.findall(r"\*\*AC-?(\d+)", ac_sec))            # **AC-N —** header style
    numbered = re.findall(r"^\d+\.\s+\*\*", ac_sec, re.M)        # N. **Title.** list style (WGT)
    if len(bold) > 1:
        return len(bold), "bold-header"
    if len(numbered) > 1:
        return len(numbered), "numbered-list"
    refs = set(re.findall(r"\bAC-?(\d+)\b", ac_sec))
    if len(refs) > 1:
        return len(refs), "referenced"
    # BE/prose: list thường top-level (không thụt đầu dòng → khỏi đếm sub-bullet
    # giải thích). Lấy max(numbered, bullet) để không cộng dồn 2 kiểu list.
    plain = max(len(re.findall(r"^\d+\.\s+\S", ac_sec, re.M)),
                len(re.findall(r"^[-*]\s+\S", ac_sec, re.M)))
    if plain > 1:
        return plain, "plain-list"
    return (len(refs), "referenced") if refs else (0, "none")


def count_ac_churn(txt):
    """AC status changes flagged in the AC callout: [vN] [cancelled] [defer] [vN-caveat].
    `vN` khớp MỌI số phiên ([v2]/[v3]/[v4]/...) — trước đây hardcode 'v3' nên AC
    đổi ở phiên khác bị sót im lặng, làm 'tỉ lệ yêu cầu đổi giữa chừng' hụt."""
    ac_sec = section(txt, r"##\s*Acceptance Criteria")
    tags = re.findall(r"\[(v\d+(?:-caveat)?|cancelled|defer)\]", ac_sec)
    by = defaultdict(int)
    for t in tags:
        by[t] += 1
    return len(tags), dict(by)


def count_deviations(txt):
    """Explicit 'DEVIATION N' tokens + numbered items under a 'Deviation' labelled
    bullet. DEDUP within-doc: 1 numbered child mang sẵn token `DEVIATION N` thì đã
    nằm trong `explicit` (set theo số) → KHÔNG cộng lần 2. Trước đây
    `len(explicit) + listed` chồng nhau khi story vừa đánh số `DEVIATION N` vừa liệt
    kê chính nó dưới header 'Deviations:' → phồng số lệch."""
    explicit = set(re.findall(r"DEVIATION ?(\d+)", txt, re.I))
    listed_extra = 0
    # find a bullet/line that introduces a deviation list, count its numbered children
    for m in re.finditer(r"Deviations?\b[^\n]*:[^\n]*\n", txt):
        block = txt[m.end():]
        stop = re.search(r"\n#{2,3}\s|\n- \*\*[^D]", block)  # next section or next top bullet
        block = block[: stop.start()] if stop else block
        for ln in re.findall(r"^\s+\d+\.\s+\*\*.*$", block, re.M):
            # child có token `DEVIATION N` → đã đếm ở `explicit`; chỉ child KHÔNG
            # mang token mới là deviation chưa được đếm.
            if not re.search(r"DEVIATION ?\d+", ln, re.I):
                listed_extra += 1
    return len(explicit) + listed_extra


def count_findings(txt):
    return (len(re.findall(r"\[Review\]\[Patch\]", txt)),
            len(re.findall(r"\[Review\]\[Defer\]", txt)))


# ── Phân loại patch cho F-FPY (Functional First-Pass Yield) ──────────────────
# Mục tiêu chỉ số: "tính năng chạy ĐÚNG SPEC sau lần code đầu từ spec+design".
# CHỈ lỗi chức năng (luồng chính / AC sai) mới trừ điểm. Lỗi bảo mật, edge-case,
# chất lượng/convention = feature VẪN chạy, chỉ cần gia cố → KHÔNG trừ F-FPY.
#
# Anchor: 3 layer review của `/bmad-code-review` map gần 1:1 với phân loại này —
#   Acceptance Auditor → đúng AC/chức năng    (TÍNH vào F-FPY)
#   Edge Case Hunter   → biên/hiếm            (loại)
#   Blind Hunter       → adversarial/bảo mật  (loại)
# Patch corpus tự gắn tag lăng kính `(auditor)` / `(blind+edge)` / ... ở cuối bullet.
_HUNTER_PAREN = re.compile(r"\(([^)]*\b(?:blind|edge|auditor|acceptance)\b[^)]*)\)", re.I)
# T2 fallback (story KHÔNG tag — 6/17 story HUB rơi vào đây): lexicon nội dung.
_AC_REF = re.compile(r"\bAC-?\d+\b")
_FUNC_VERB = re.compile(
    r"\b(sai|thiếu|lệch\s*DD|broken|wrong|incorrect|missing|mismatch|fails?\b|"
    r"does\s*n.?t|returns?\s+(?:wrong|null|sai))\b"
    r"|không\s+(?:trả|chạy|đúng|match|khớp|hoạt động)"
    r"|chưa\s+(?:đúng|implement|trả|chạy)", re.I)
_SEC = re.compile(
    r"\b(password|token|auth|inject|mask(?:ing|ed)?|vault|signature|secret|TLS|"
    r"SSRF|XSS|CSRF|leak|sanitiz|escap|defen[cs]e[- ]in[- ]depth|hardening|poison)\b", re.I)
_EDGE = re.compile(
    r"\b(edge|boundary|biên|race|concurren|overflow|null[- ]?check|empty|rỗng|"
    r"hiếm|rare|DLQ|retry|backoff|timeout|idempoten)\b", re.I)
_QUAL = re.compile(
    r"\b(convention|naming|lint|refactor|dead\s*code|log[- ]?level|style|"
    r"observability|gauge|metric|magic\s*number|đặt\s*tên)\b", re.I)


def _excl_class(text):
    """Lớp của 1 patch bị loại khỏi F-FPY, ưu tiên bảo mật > edge > chất lượng."""
    if _SEC.search(text):
        return "security"
    if _EDGE.search(text):
        return "edge"
    if _QUAL.search(text):
        return "quality"
    return None


def classify_patch(text):
    """Phân loại 1 patch review → (bucket, method, klass).

    bucket: 'functional'   = Acceptance Auditor / luồng AC hỏng → TÍNH vào F-FPY
            'excluded'     = bảo mật / edge / chất lượng → feature vẫn chạy, chỉ gia cố
            'unclassified' = không đủ tín hiệu → KHÔNG ngầm tính clean, report riêng
    method: 'tag' (lăng kính review — tin cao) > 'inferred' (lexicon) > 'unclassified'
    klass : với 'excluded' = 'security'|'edge'|'quality'; còn lại None."""
    tags = _HUNTER_PAREN.findall(text)
    if tags:
        joined = " ".join(tags).lower()
        if re.search(r"\b(auditor|acceptance)\b", joined):
            return "functional", "tag", None
        return "excluded", "tag", (_excl_class(text) or ("edge" if "edge" in joined else "security"))
    # T2 — không tag: dẫn AC-id + động từ hỏng chức năng ⇒ functional
    if _AC_REF.search(text) and _FUNC_VERB.search(text):
        return "functional", "inferred", None
    klass = _excl_class(text)
    if klass:
        return "excluded", "inferred", klass
    return "unclassified", "unclassified", None


def parse_patches(txt):
    """Trích từng bullet `[Review][Patch]` (gồm dòng wrap) để classify. Marker chỉ
    xuất hiện ở checklist Patch — Change Log narrative ghi 'N patch' nên không lẫn."""
    out = []
    for m in re.finditer(r"\[Review\]\[Patch\]", txt):
        seg = txt[m.end():]
        stop = re.search(r"\n\s*[-*]\s|\n#{1,6}\s|\n\s*\n", seg)  # bullet/heading/blank kế tiếp
        out.append(seg[: stop.start()] if stop else seg[:400])
    return out


def classify_unit_patches(txt):
    """Gộp classify mọi patch của 1 unit → dict đếm + method trội + breakdown lớp loại."""
    func = excl = uncl = 0
    excl_by = defaultdict(int)
    methods = set()
    for p in parse_patches(txt):
        bucket, method, klass = classify_patch(p)
        methods.add(method)
        if bucket == "functional":
            func += 1
        elif bucket == "excluded":
            excl += 1
            excl_by[klass] += 1
        else:
            uncl += 1
    # method trội phục vụ cờ độ tin: 'tag' (story có tag) > 'inferred' > 'none'
    pm = "tag" if "tag" in methods else ("inferred" if "inferred" in methods else "none")
    return {
        "functional_patch": func,
        "patch_excluded": excl,
        "patch_unclassified": uncl,
        "patch_excluded_by": dict(excl_by),
        "patch_class_method": pm,
    }


def count_changelog(txt):
    """Số lần CẬP NHẬT sau khi tạo unit = (số dòng Change Log có ngày) − 1.
    Dòng đầu tiên = dòng khai sinh (tạo story / scaffold), không tính là 'thay đổi'.
    Clamp max(0, …) để unit thiếu Change Log không ra số âm. Lưu ý heuristic: giả
    định dòng-1 luôn là dòng tạo; nếu Change Log bắt đầu giữa chừng sẽ hụt 1."""
    # end_pat chặn ở `##` HOẶC `###` kế tiếp: Change Log thường là `###`, mặc định
    # `\n##\s` không dừng ở `###` sau nó → đọc lố sang section khác có bảng `| 20xx-`.
    sec = section(txt, r"#{2,3}\s*Change Log", end_pat=r"\n#{2,3}\s")
    rows = len(re.findall(r"^\|\s*20\d{2}-", sec, re.M))
    return max(0, rows - 1)


def find_unit_story(unit_id):
    """Định vị file story Stage 5 của unit_id, KHOAN DUNG khi AI ảo giác và tự
    chèn tiền tố lạ vào tên file (vd `STORY-SCR-FOO.md`, `1.2-SCR-FOO.md`,
    `slice3_MPF-01.md`). Tìm theo unit_id trước, rồi mới nới regex:

      1. Khớp đúng: S5/{unit_id}.md            (canonical — skill emit chuẩn)
      2. Khớp đuôi: S5/*.md có stem KẾT THÚC bằng {unit_id} tại token boundary
         (AI thêm prefix nhưng giữ nguyên unit_id ở cuối)
      3. Khớp giữa: S5/*.md có stem CHỨA {unit_id} giữa 2 token boundary
         (unit_id bị kẹp giữa prefix lẫn suffix lạ)

    Trả về Path (kể cả khi không tồn tại) để caller vẫn read() bình thường."""
    exact = S5 / f"{unit_id}.md"
    if exact.exists() or not S5.is_dir():
        return exact
    uid = re.escape(unit_id)
    suffix_re = re.compile(rf"(?:^|[^A-Za-z0-9]){uid}$")            # ...-{uid}
    embed_re = re.compile(rf"(?:^|[^A-Za-z0-9]){uid}(?:[^A-Za-z0-9]|$)")  # ...{uid}...
    suffix_hits, embed_hits = [], []
    for f in sorted(S5.glob("*.md")):
        if f.stem == unit_id:        # phòng race với check exact ở trên
            return f
        if suffix_re.search(f.stem):
            suffix_hits.append(f)
        elif embed_re.search(f.stem):
            embed_hits.append(f)
    pool = suffix_hits or embed_hits
    if pool:
        # stem ngắn nhất = ít rác ảo giác bao quanh unit_id thật nhất
        best = min(pool, key=lambda p: len(p.stem))
        print(f"[eval-harvester] story '{unit_id}' khớp mờ qua tên file "
              f"'{best.name}' (đã khoan dung tiền tố ảo giác)")
        return best
    return exact


def parse_unit(unit_id):
    txt = read(find_unit_story(unit_id))
    if not txt:
        return None
    ac, ac_method = count_ac(txt)
    churn, churn_by = count_ac_churn(txt)
    patch, rdefer = count_findings(txt)
    rec = {
        "unit": unit_id,
        "ac_total": ac,
        "ac_count_method": ac_method,
        "ac_churn": churn,
        "ac_churn_by": churn_by,
        "deviations": count_deviations(txt),
        "review_patch": patch,
        "review_defer": rdefer,
        "changelog_rows": count_changelog(txt),
    }
    rec.update(classify_unit_patches(txt))   # F-FPY: tách patch chức năng vs gia cố
    return rec


def _parse_date(s):
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def parse_defers(unit_slice):
    """Parse the defer-ledger từ `deferred-work.md`. Đọc HAI format (G1 —
    xem NTAPP_Evaluation/harvester_upgrade.md):

      1. Block giàu trường `### DEF-<ID> — title` + opened/status/category/
         avoidable/... → record đầy đủ (`source='ledger'`). Chuẩn lý tưởng,
         hiện chưa skill nào phát.
      2. Bullet `- [x] [Review][Defer] <title> [file:line] — reason` dưới heading
         `## Deferred from: <nguồn> (<date>)` — ĐÂY là format `bmad-code-review`
         đang phát. Sinh record NHẸ (`source='bullet'`, avoidable=None vì thiếu
         trường) qua _parse_defer_bullets(). Trước G1 các bullet này bị bỏ qua
         hoàn toàn → defer_count=0 dù review sinh defer.

    Consumer-only: harvester đọc hiểu artifact skill phát, KHÔNG sửa skill."""
    txt = read(S5 / "deferred-work.md")
    defers = []
    for chunk in txt.split("\n### ")[1:]:
        first, _, body = chunk.partition("\n")
        h = re.match(r"(DEF-[A-Z0-9-]+)\s*[—-]+\s*(.*)", first)
        if not h:
            continue
        did, title = h.group(1), h.group(2).strip()

        def field(key, default=None):
            m = re.search(rf"\b{key}:\s*([^\n·]+)", body)
            return m.group(1).strip() if m else default

        opened = _parse_date(field("opened"))
        closed = _parse_date(field("closed"))
        status = (field("status", "open") or "open").lower()
        age_days = ((closed or AS_OF) - opened).days if opened else None
        defers.append({
            "id": did,
            "title": title,
            "slice": field("slice") or unit_slice.get((field("unit") or "").strip()),
            "unit": field("unit"),
            "owner": field("owner"),
            "category": field("category", "uncategorized"),
            "avoidable": (field("avoidable", "no") or "no").lower() == "yes",
            "severity": field("severity"),
            "status": status,
            "opened": opened.isoformat() if opened else None,
            "closed": closed.isoformat() if closed else None,
            "age_days": age_days,
            "blocking_condition": field("blocking-condition"),
            "target_reentry": field("target-reentry"),
            "excludable_by": _norm_excludable(field("excludable-by")),
            "source": "ledger",
        })
    defers.extend(_parse_defer_bullets(txt, unit_slice))
    return defers


def _parse_defer_bullets(txt, unit_slice):
    """Format bullet mà bmad-code-review phát (G1). Heading
    `## Deferred from: <nguồn> (<date>)` + bullet `[Review][Defer]`. Record NHẸ:
    thiếu category/avoidable nên để consumer ĐO ĐƯỢC capture-rate, nhưng KHÔNG
    đưa vào mẫu số avoidability (`avoidable=None`) — không suy diễn bừa."""
    records = []
    units = sorted((u for u in unit_slice if u), key=len, reverse=True)  # khớp dài trước
    for part in re.split(r"\n##\s+Deferred from:\s*", txt)[1:]:
        head, _, body = part.partition("\n")
        dm = re.search(r"\((\d{4}-\d{2}-\d{2})\)", head)
        opened = _parse_date(dm.group(1)) if dm else None
        unit = next((u for u in units if u in head), None)   # nguồn chứa unit_id đã biết?
        sid = unit_slice.get(unit) if unit else None
        seq = 0
        for line in body.splitlines():
            if line.startswith("## "):       # sang section khác cùng cấp → dừng
                break
            if "[Review][Defer]" not in line:
                continue
            seq += 1
            title = re.sub(r"^[\s>*-]*\[[ xX]\]\s*\[Review\]\[Defer\]\s*", "", line).strip()
            records.append({
                # 'rev' = phân biệt với DEF-<ID> block giàu, tránh trùng id.
                "id": f"DEF-{(unit or 'REVIEW')}-rev{seq}",
                "title": title[:120],
                "slice": sid,
                "unit": unit,
                "owner": None,
                "category": "uncategorized",
                "avoidable": None,           # unknown — loại khỏi mẫu số EFF-7
                "severity": None,
                "status": "open",            # defer = nợ đang mở
                "opened": opened.isoformat() if opened else None,
                "closed": None,
                "age_days": ((AS_OF - opened).days if opened else None),
                "blocking_condition": None,
                "target_reentry": None,
                "excludable_by": None,
                "source": "bullet",
            })
    return records


def _norm_excludable(v):
    """Normalise excludable-by; treat dash/empty as scattered (no single-action close)."""
    if not v or v.strip() in {"—", "-", "none", "n/a"}:
        return None
    return v.strip()


def cluster_defers(defers):
    """Group OPEN defers by excludable-by action. Returns sorted list of clusters."""
    by = defaultdict(lambda: {"count": 0, "avoidable": 0, "slices": set(), "ids": []})
    scattered = {"count": 0, "avoidable": 0, "slices": set(), "ids": []}
    for d in defers:
        if d["status"] == "closed":
            continue
        bucket = by[d["excludable_by"]] if d["excludable_by"] else scattered
        bucket["count"] += 1
        bucket["avoidable"] += 1 if d["avoidable"] else 0
        bucket["slices"].add(d["slice"])
        bucket["ids"].append(d["id"])
    out = [{"action": k, **v, "slices": sorted(v["slices"])} for k, v in by.items()]
    out.sort(key=lambda c: (-c["count"], c["action"]))
    scat = {"action": "— (rải rác)", **scattered, "slices": sorted(scattered["slices"])}
    return out, scat


# ============================================================================
# Drift gate L3↔L2 (G8) — đọc drift_report_*.md ở Stage_4_Design/ui_schema.
# Đo số lệch thiết-kế(L3) ↔ hợp-đồng-dữ-liệu(L2) BẮT ĐƯỢC ở cổng thiết kế trước
# khi vào code. Format thực tế biến thiên: item dạng `### Item N`, `### NB-N`,
# `- **Item N**`; section `## [BLOCKING]/[NON-BLOCKING]/[RECONCILED]` (có thể kèm
# hậu tố `— RECONCILED`); section rỗng ghi `(none …)`. Mỗi unit có thể có 2 file
# (flat `drift_report_<ID>.md` + nested `<ID>/drift_report.md`, re-run) → dedup
# theo ngày mới nhất. Đây là heuristic đếm — không phải phán xử.
# ============================================================================
DRIFT_ITEM_RE = re.compile(r"^[ \t]*(?:#{3,4}[ \t]+|[-*][ \t]+\*\*)(?:Item\b|NB-|N\d+\b)[^\n]*", re.M)
DRIFT_H2_RE = re.compile(r"^##\s+(.*)$", re.M)


def _drift_unit_from_path(p):
    if p.name == "drift_report.md":
        return p.parent.name
    m = re.match(r"drift_report_(.+)\.md$", p.name)
    return m.group(1) if m else p.stem


def _drift_date(txt):
    head = "\n".join(txt.splitlines()[:14])  # header blockquote
    m = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", head)
    return m.group(1) if m else None


def _drift_item_key(text):
    """ID phân biệt của 1 drift item từ dòng tiêu đề (`Item 3` / `NB-2` / `N4`).
    Giữ NGUYÊN loại (item/nb/n) để `NB-2` ≠ `Item 2`. None nếu không bắt được số →
    item không định danh, KHÔNG dedup được (đếm thô như cũ)."""
    m = re.search(r"\bItem\s*(\d+)\b|\bNB-?(\d+)\b|\bN(\d+)\b", text, re.I)
    if not m:
        return None
    if m.group(1):
        return "item" + m.group(1)
    if m.group(2):
        return "nb" + m.group(2)
    return "n" + m.group(3)


def _drift_section_items(body):
    """(active_ids, recon_ids, active_idless, recon_idless) của 1 section. `*_ids` =
    list ID drift item (để dedup xuyên section ở `_parse_one_drift`); `*_idless` = số
    item KHÔNG định danh (đếm thô). '(none' → rỗng, nhưng vớt được số trong câu
    '… N (historic) items reconciled' (prose-only re-run) để khỏi hụt im lặng."""
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith(">"):
            continue
        if s.lower().startswith("(none"):
            pm = re.search(r"(\d+)\s+(?:historic\s+)?items?\s+reconciled", body, re.I)
            return [], [], 0, (int(pm.group(1)) if pm else 0)
        break
    a_ids, r_ids, a_idless, r_idless = [], [], 0, 0
    for m in DRIFT_ITEM_RE.finditer(body):
        key = _drift_item_key(m.group(0))
        if "RECONCILED" in m.group(0).upper():
            r_ids.append(key) if key else None
            r_idless += 0 if key else 1
        else:
            a_ids.append(key) if key else None
            a_idless += 0 if key else 1
    return a_ids, r_ids, a_idless, r_idless


# Precedence khi 1 item-id xuất hiện ở nhiều section: trạng thái "mới/đã giải quyết
# hơn" thắng — reconciled > blocking > nonblocking. Tránh đếm 1 item cả ở BLOCKING
# lẫn RECONCILED (lifecycle move) thành 2.
_DRIFT_PREC = {"nonblocking": 0, "blocking": 1, "reconciled": 2}


def _parse_one_drift(txt, unit):
    rec = {"unit": unit, "date": _drift_date(txt),
           "blocking": 0, "reconciled": 0, "nonblocking": 0,
           "gate_outcome": None, "res_l2": 0, "res_l3": 0}
    item_bucket = {}                                  # id → bucket cuối (dedup xuyên section)
    idless = {"blocking": 0, "reconciled": 0, "nonblocking": 0}

    def assign(key, bucket):
        cur = item_bucket.get(key)
        if cur is None or _DRIFT_PREC[bucket] > _DRIFT_PREC[cur]:
            item_bucket[key] = bucket

    heads = list(DRIFT_H2_RE.finditer(txt))
    for i, m in enumerate(heads):
        tm = re.match(r"\[(BLOCKING|NON-BLOCKING|RECONCILED)\]", m.group(1))
        if not tm:
            continue
        tag = tm.group(1)
        sec_reconciled = "RECONCILED" in m.group(1).upper()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(txt)
        a_ids, r_ids, a_idless, r_idless = _drift_section_items(txt[m.end():end])
        if tag == "NON-BLOCKING":
            for k in a_ids + r_ids:
                assign(k, "nonblocking")
            idless["nonblocking"] += a_idless + r_idless
        elif tag == "RECONCILED":
            for k in a_ids + r_ids:
                assign(k, "reconciled")
            idless["reconciled"] += a_idless + r_idless
        else:  # BLOCKING (có thể đã reconciled qua hậu tố section hoặc per-item)
            if sec_reconciled:
                for k in a_ids + r_ids:
                    assign(k, "reconciled")
                idless["reconciled"] += a_idless + r_idless
            else:
                for k in a_ids:
                    assign(k, "blocking")
                for k in r_ids:
                    assign(k, "reconciled")
                idless["blocking"] += a_idless
                idless["reconciled"] += r_idless
    for b in item_bucket.values():                    # mỗi item-id chỉ tính 1 lần
        rec[b] += 1
    for b, n in idless.items():
        rec[b] += n
    rec["res_l2"] = len(re.findall(r"\[L2\]|update L2", txt, re.I))
    rec["res_l3"] = len(re.findall(r"\[L3\]|update L3", txt, re.I))
    # Cổng = đọc RIÊNG dòng Verdict/Outcome (fallback Status) — không quét cả doc,
    # vì 'HALT' hay xuất hiện khi mô tả lần chạy TRƯỚC → false positive.
    vm = re.search(r"(?im)^\s*>?\s*\*\*(?:Verdict|Outcome)\b[^\n]*", txt) \
        or re.search(r"(?im)^\s*>?\s*\*\*Status:[^\n]*", txt)
    vline = vm.group(0).upper() if vm else ""
    if "HALT" in vline:
        rec["gate_outcome"] = "halted"
    elif re.search(r"NO BLOCKING|PASS|PROCEED|RESOLVED|UNBLOCK", vline):
        rec["gate_outcome"] = "proceeded"
    else:
        rec["gate_outcome"] = "halted" if rec["blocking"] else "proceeded"
    return rec


def parse_drift_reports(ui_dir=None):
    """Đọc mọi drift_report ở Stage_4_Design/ui_schema → đếm BLOCKING/RECONCILED/
    NON-BLOCKING bắt ở cổng thiết kế (G8). Dedup 2 file/unit theo ngày mới nhất
    (tie → bản nested re-run thắng)."""
    d = ui_dir or UI_SCHEMA_DIR
    out = {"available": False, "reports": 0, "blocking": 0, "reconciled": 0,
           "nonblocking": 0, "halted": 0, "res_l2": 0, "res_l3": 0, "by_unit": {}}
    if not d.exists():
        return out
    files = sorted(d.glob("drift_report_*.md")) + sorted(d.glob("*/drift_report.md"))
    if not files:
        return out
    best = {}  # unit -> (sortkey, record)
    for f in files:
        txt = read(f)
        if not txt:
            continue
        unit = _drift_unit_from_path(f)
        rec = _parse_one_drift(txt, unit)
        key = (rec["date"] or "", 1 if f.name == "drift_report.md" else 0)
        if unit not in best or key > best[unit][0]:
            best[unit] = (key, rec)
    out["available"] = True
    out["reports"] = len(best)
    for unit, (_, rec) in sorted(best.items()):
        out["by_unit"][unit] = rec
        for k in ("blocking", "reconciled", "nonblocking", "res_l2", "res_l3"):
            out[k] += rec[k]
        out["halted"] += 1 if rec["gate_outcome"] == "halted" else 0
    return out


def parse_rework():
    """unit -> archived DD versions (current = archived + 1)."""
    rework = defaultdict(int)
    for f in DD_ARCHIVE.glob("*_detailed_design_v*.md"):
        m = re.match(r"(.+)_detailed_design_v(\d+)", f.name)
        if m:
            rework[m.group(1)] = max(rework[m.group(1)], int(m.group(2)))
    return dict(rework)


# ============================================================================
# CR & drift trong Detailed Design L3 (G10) — đọc detailed_design/*_detailed_design.md.
# DD chứa 3 khối tín hiệu mà trước đây harvester KHÔNG đọc (chỉ cân token-proxy):
#   1. `## BẢNG LỊCH SỬ THAY ĐỔI` — bảng CR/change-history (cột Link CR/Jira, A/M/D,
#      Phiên bản). count_changelog cũ khớp 'Change Log' tiếng Anh + chỉ chạy trên
#      story Stage-5 → bảng này vô hình.
#   2. `### 1.2 Drift resolution log` — bảng D1..Dn (L3↔TechSpec). Khác hẳn G8
#      (G8 = drift UI L3↔L2 schema ở ui_schema/drift_report). Với feature BE
#      (id_type=feature_id, không UI) KHÔNG có drift_report → §1.2 là NGUỒN DRIFT
#      DUY NHẤT. Bổ khuyết điểm mù drift BE.
#   3. `[TBD-confirm]` / `[TBD…]` — quyết định thiết kế treo (defer ở tầng thiết kế).
# Heuristic đếm theo cấu trúc bảng markdown — không phải phán xử. Bù trục C
# (Defer / CR / Change Log) vốn chỉ đọc từ Stage-5.
# ============================================================================
def _md_table(block):
    """(headers, rows) của bảng markdown đầu tiên trong block. headers = list cell
    dòng tiêu đề; rows = list[list cell] data. Bỏ separator (:---); dừng ở dòng
    đầu tiên KHÔNG bắt đầu '|' sau khi bảng đã mở."""
    cells_rows, started = [], False
    for ln in block.splitlines():
        s = ln.strip()
        if not s.startswith("|"):
            if started:
                break
            continue
        started = True
        if re.fullmatch(r"[:\-\s|]+", s):   # dòng separator
            continue
        cells_rows.append([c.strip() for c in s.strip("|").split("|")])
    if not cells_rows:
        return [], []
    return cells_rows[0], cells_rows[1:]


def _col_idx(headers, *keywords):
    """Index cột đầu tiên có header chứa 1 trong keywords (lower-case substring)."""
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(k in hl for k in keywords):
            return i
    return None


# Ticket CR/Jira THẬT: token `CR-123`/`CR 123`, hoặc URL Jira/Atlassian/`/browse/`.
# Cố ý KHÔNG nhận: `[TBD]`, story-ref ('E3 Story 3.2'), tên file, prose, URL bất kỳ
# (staging/schema URL lẫn trong mô tả), và KHÔNG nhận `[A-Z]{2,}-\d+` vì đụng chính
# WBS-ID (`HUB-12`/`PMT-EXT-01`). Tác giả DD điền cột "Link CR/Jira" rất tùy tiện nên
# 'có chữ' ≠ 'có CR ngoài' — pattern chặt để cr_ticketed không bị thổi. Vẫn portable:
# project thật sự dùng Jira (link `/browse/PROJ-123`) vẫn bắt được.
DD_TICKET_RE = re.compile(r"\bCR[-\s]?\d+\b|https?://\S*(?:jira|atlassian|/browse/)", re.I)


# G11 — tombstone (DD của feature bị XÓA theo CR): header `dd_version: v*-removed`
# hoặc banner `🚫 REMOVED` ở đầu file. Đây KHÔNG phải deliverable sống → tách khỏi
# mẫu số DD, drift/CR/TBD; surface riêng thành tín hiệu trục-C scope-removal. Quét
# 800 ký tự đầu (header + banner). Bắt kèm CR-id để quy nhóm. Consumer-only: harvester
# nhận diện format skill ĐÃ emit (`-removed` + `🚫 REMOVED`), không sửa skill gốc.
DD_REMOVED_RE = re.compile(
    r"dd_version:\s*v[\w.]*-removed|🚫\s*\*{0,2}\s*REMOVED\b|—\s*REMOVED\s*$", re.I | re.M)
DD_REMOVED_CR_RE = re.compile(r"\bCR-[A-Z0-9][A-Z0-9-]*\b")


def _dd_removed_info(txt):
    """Nếu DD là tombstone (feature bị xóa theo CR) → {removed: True, cr, date}; ngược
    lại {removed: False}. Chỉ soi 800 ký tự đầu (header + banner XÓA)."""
    head = txt[:800]
    if not DD_REMOVED_RE.search(head):
        return {"removed": False}
    crm = DD_REMOVED_CR_RE.search(head)
    dm = re.search(r"REMOVED\s+(\d{4}-\d{2}-\d{2})", head)
    return {"removed": True, "cr": crm.group(0) if crm else None,
            "date": dm.group(1) if dm else None}


def _dd_cr_table(txt):
    """Bảng `## BẢNG LỊCH SỬ THAY ĐỔI` → cr_total (= số lần sửa DD, tín hiệu chính),
    cr_ticketed (số dòng có link CR/Jira NGOÀI chính thức — strict), A/M/D, version,
    D-id tham chiếu. Map cột theo tên tiêu đề (chịu được DD đổi thứ tự cột)."""
    block = section(txt, r"##\s*BẢNG LỊCH SỬ THAY ĐỔI", end_pat=r"\n##\s")
    headers, rows = _md_table(block)
    if not rows:
        return None
    i_type = _col_idx(headers, "a*", "a, m", "m, d")   # cột A/M/D
    i_cr = _col_idx(headers, "cr", "jira")
    i_ver = _col_idx(headers, "phiên bản", "version")
    i_desc = _col_idx(headers, "mô tả")
    by_type, versions, drift_refs = defaultdict(int), set(), set()
    total = ticketed = 0
    for r in rows:
        total += 1
        if i_cr is not None and i_cr < len(r) and DD_TICKET_RE.search(r[i_cr]):
            ticketed += 1
        if i_type is not None and i_type < len(r):
            for t in re.findall(r"\b([AMD])\b", r[i_type]):
                by_type[t] += 1
        if i_ver is not None and i_ver < len(r):
            vm = re.search(r"v\d+(?:\.\d+)*", r[i_ver])
            if vm:
                versions.add(vm.group(0))
        if i_desc is not None and i_desc < len(r):
            for d in re.findall(r"\bD\d+\b", r[i_desc]):
                drift_refs.add(d)
    return {"cr_total": total, "cr_ticketed": ticketed,
            "by_type": dict(by_type), "versions": versions, "drift_refs": drift_refs}


# --- G10 drift: per-unit VERDICT, KHÔNG đếm per-item `Dn` ---------------------
# Validate trên 13 file có section drift cho thấy ID drift đa convention
# (`Dn` / `drift-N` / `D-DRIFT-N` / `DW-<unit>-N` / chỉ nêu prose) và status nằm ở
# cấp section/verdict CHỨ KHÔNG per-row → đếm `Dn` ra số sai (HUB-18 từng bị chấm
# 4/4-open trong khi file ghi "ĐÃ RESOLVED"; HUB-07 bị bỏ sót vì `D-DRIFT-1`≠`Dn`).
# Thay bằng phân 3 bucket: resolved (mọi finding đã LAND — kể cả fix tại
# L2/Module-0/WBS) / flags (≥1 finding còn treo: [TBD], 'cần upstream resolve',
# build trên mock, finding-row thiếu ✅) / none (section có nhưng không drift finding).
DRIFT_KEEP = re.compile(r"drift|inheritance\s+compliance|phát hiện (trước|cần)|đối soát l2", re.I)
DRIFT_SKIP = re.compile(r"đối soát (fe-be|logic|chất lượng|vết)|traceability", re.I)
DRIFT_DEDICATED = re.compile(r"drift\s+(resolution|notes|register|flags|&|và)", re.I)
FINDING_ID = re.compile(r"\b(?:drift[-\s]?\d+|D-DRIFT-\d+|DW-[A-Z0-9]+-\d+)\b", re.I)
BARE_DN = re.compile(r"\bD\d+\b")
RESOLVED_MARK = re.compile(
    r"✅|\bRESOLVED\b|đã đóng|đã chốt|\bDone\b|không còn blocked|zero (internal )?drift", re.I)
PENDING_MARK = re.compile(
    r"\[TBD|cần\s+upstream|cần[^\n]{0,12}resolve|chưa (resolve|fix|đóng|chốt)|"
    r"build[^\n]{0,6}mock|carried|logged[^\n]{0,8}non-?block|không block release|"
    r"ghi nhận[^\n]{0,14}không block|pass-?with-?flags|với mock", re.I)


def _dd_drift_status(txt):
    """Phân loại verdict drift L3↔TechSpec của 1 DD → {verdict, findings, open}.
    verdict ∈ {resolved, flags, none}. Anchor vào section drift/inheritance (loại
    P1-P4 QA-sync), đếm finding-row mang ID drift (bare `Dn` chỉ trong bảng drift
    chuyên dụng → tránh false-positive `Dn`=cột-DB), chấm resolved theo marker
    ✅/RESOLVED/Done ở row, fallback theo marker của heading section."""
    heads = [(m.start(), m.end(), m.group(1))
             for m in re.finditer(r"(?im)^#{2,4}\s+(.*)$", txt)]
    saw_section = saw_resolved_heading = False
    res_map, pend_map = {}, {}    # finding-id (lower) → đã-thấy-resolved / đã-thấy-pending
    for i, (s, e, title) in enumerate(heads):
        if not DRIFT_KEEP.search(title) or DRIFT_SKIP.search(title):
            continue
        saw_section = True
        nxt = heads[i + 1][0] if i + 1 < len(heads) else len(txt)
        body = txt[e:nxt]
        dedicated = bool(DRIFT_DEDICATED.search(title))
        h_res = bool(RESOLVED_MARK.search(title))
        h_pend = bool(PENDING_MARK.search(title))
        default_open = h_pend and not h_res
        if h_res:
            saw_resolved_heading = True
        for ln in body.splitlines():
            ls = ln.strip()
            is_bullet = bool(re.match(r"[-*]\s*\**\[?(?:drift|DW-|D-DRIFT)", ls, re.I)) \
                and FINDING_ID.search(ls)
            is_row = ls.startswith("|") and not re.fullmatch(r"[:\-\s|]+", ls)
            if not (is_bullet or is_row):
                continue
            fid = FINDING_ID.search(ls)
            if fid:
                key = re.sub(r"[\s-]", "", fid.group(0).lower())
            elif is_row and dedicated and BARE_DN.search(ls):
                key = BARE_DN.search(ls).group(0).lower()
            else:
                continue
            r = bool(RESOLVED_MARK.search(ls))
            # resolved-marker THẮNG pending cùng dòng: '✅ RESOLVED … không còn [TBD]'
            # là tác giả xác nhận đóng, không phải còn treo.
            p = bool(PENDING_MARK.search(ls)) and not r
            if not r and not p:        # row trung tính → kế thừa marker heading section
                r, p = h_res, default_open
            res_map[key] = res_map.get(key, False) or r
            pend_map[key] = pend_map.get(key, False) or p
    if not saw_section:
        return {"verdict": "none", "findings": 0, "open": 0}
    findings = [(res_map[k] and not pend_map[k]) for k in res_map]
    if not findings:
        return {"verdict": "resolved" if saw_resolved_heading else "none",
                "findings": 0, "open": 0}
    open_ = sum(1 for ok in findings if not ok)
    return {"verdict": "flags" if open_ else "resolved",
            "findings": len(findings), "open": open_}


def _dd_count_tbd(txt):
    """Đếm marker `[TBD…]` còn treo. BỎ mention bị phủ định — DD hay viết 'không
    còn [TBD]', '0 [TBD]', 'Gỡ toàn bộ [TBD]', 'Ghi nhận 3 [TBD]' (lịch sử đã đóng),
    hay tiêu đề 'Trạng thái [TBD]'; đếm thô thổi số quyết-định-treo (HUB-16 báo 12,
    thực tế 0). Quét cả prefix (phủ định trước) lẫn suffix gần (status sau)."""
    NEG = re.compile(
        r"không còn|đã gỡ|gỡ bỏ|gỡ toàn bộ|đã chốt|resolved|đã xử lý|"
        r"\b0\s*[`'\"]*$|ghi nhận\s+\d+\s*[`'\"]*$|trạng thái\s*[`'\"]*$", re.I)
    # DEDUP within-doc: cùng 1 quyết định treo CÓ payload phân biệt (vd
    # `[TBD-confirm: latency budget]`, `[TBD-PUSH-03]`) nhắc lại nhiều chỗ → đếm 1.
    # KHÔNG dedup marker generic (`[TBD]`, `[TBD-confirm]`) vì nhiều quyết định khác
    # nhau cùng viết generic → gộp lại sẽ HỤT số (over-dedup).
    GENERIC = {"[tbd]", "[tbd-confirm]", "[tbd confirm]"}
    seen = set()
    n = 0
    for m in re.finditer(r"\[TBD[^\]]*\]", txt):
        pre = txt[max(0, m.start() - 30):m.start()]
        post = txt[m.end():m.end() + 24].lower()
        if NEG.search(pre):
            continue
        if re.search(r"đã (chốt|đóng|resolve|xử lý)|resolved|→\s*\S", post):
            continue
        key = re.sub(r"\s+", "", m.group(0).lower())
        if key not in GENERIC:                  # có payload → lặp lại = cùng 1 TBD
            if key in seen:
                continue
            seen.add(key)
        n += 1
    return n


def parse_dd_reports(dd_dir=None):
    """Đọc mọi detailed_design/*_detailed_design.md (KHÔNG đệ quy → bỏ archive/ +
    feature_design_parts/) → CR + drift L3↔TechSpec + TBD (G10)."""
    d = dd_dir or DD_DIR
    out = {"available": False, "files": 0,
           "cr_total": 0, "cr_ticketed": 0, "by_type": {},
           "verdict_counts": {"resolved": 0, "flags": 0, "none": 0},
           "flagged_units": [], "findings_open": 0,
           "tbd_confirm": 0, "by_unit": {},
           "removed_units": [], "removed_by_cr": {}}
    if not d.exists():
        return out
    files = sorted(d.glob("*_detailed_design.md"))
    if not files:
        return out
    by_type = defaultdict(int)
    for f in files:
        txt = read(f)
        if not txt:
            continue
        um = re.match(r"(.+)_detailed_design\.md$", f.name)
        unit = um.group(1) if um else f.stem
        rmv = _dd_removed_info(txt)
        if rmv["removed"]:
            # Tombstone: KHÔNG vào mẫu số DD / drift / CR / TBD. Gom riêng trục-C.
            out["removed_units"].append(unit)
            cr_key = rmv["cr"] or "(CR không rõ)"
            out["removed_by_cr"].setdefault(cr_key, []).append(unit)
            out["by_unit"][unit] = {"version": "removed", "cr_total": 0,
                                    "cr_ticketed": 0, "drift_verdict": "removed",
                                    "drift_findings": 0, "drift_open": 0, "tbd": 0,
                                    "removed": True, "removed_cr": rmv["cr"],
                                    "removed_date": rmv["date"]}
            continue
        cr = _dd_cr_table(txt)
        dr = _dd_drift_status(txt)
        tbd = _dd_count_tbd(txt)
        rec = {"version": None, "cr_total": 0, "cr_ticketed": 0,
               "drift_verdict": dr["verdict"], "drift_findings": dr["findings"],
               "drift_open": dr["open"], "tbd": tbd}
        if cr:
            rec.update(cr_total=cr["cr_total"], cr_ticketed=cr["cr_ticketed"],
                       version=(sorted(cr["versions"])[-1] if cr["versions"] else None))
            out["cr_total"] += cr["cr_total"]
            out["cr_ticketed"] += cr["cr_ticketed"]
            for t, n in cr["by_type"].items():
                by_type[t] += n
        out["verdict_counts"][dr["verdict"]] += 1
        if dr["verdict"] == "flags":
            out["flagged_units"].append(unit)
        out["findings_open"] += dr["open"]
        out["tbd_confirm"] += tbd
        out["by_unit"][unit] = rec
    out["available"] = True
    # Mẫu số DD = chỉ deliverable sống (loại tombstone). by_unit vẫn giữ tombstone
    # (đánh dấu removed) để render bảng nhưng KHÔNG tính vào "files".
    out["files"] = len(out["by_unit"]) - len(out["removed_units"])
    out["by_type"] = dict(by_type)
    return out


def est_tokens(text):
    """Deliverable-weight proxy. NOT real LLM burn — see module header."""
    return len(text) / CHARS_PER_TOKEN


# Marker file nhận diện code repo — FE (package.json) + BE đa ngôn ngữ.
REPO_MARKERS = ("package.json", "pom.xml", "build.gradle", "build.gradle.kts",
                "settings.gradle", "settings.gradle.kts", "go.mod", "Cargo.toml",
                "build.sbt", "composer.json", "pyproject.toml", "requirements.txt",
                "*.csproj", "*.sln")


def _looks_like_code_repo(d):
    """True nếu d có marker của 1 code repo (FE hoặc BE). Bỏ qua spec/meta repo."""
    for marker in REPO_MARKERS:
        if "*" in marker:
            if any(d.glob(marker)):
                return True
        elif (d / marker).exists():
            return True
    return False


def resolve_code_roots():
    """Danh sách code repo. Override qua EVAL_CODE_ROOT (1 hoặc nhiều path, ngăn bằng
    os.pathsep ':' hoặc ','). Mặc định: quét sibling của spec repo, nhận mọi thư mục
    có marker (package.json / pom.xml / build.gradle / go.mod / Cargo.toml / ...) →
    hỗ trợ multi-repo + backend Java/Kotlin/Go trong cùng workspace."""
    env = os.environ.get("EVAL_CODE_ROOT")
    if env:
        roots = []
        for part in re.split(r"[%s,]" % re.escape(os.pathsep), env):
            part = part.strip()
            if not part:
                continue
            p = Path(part).expanduser()
            if p.is_dir():
                roots.append(p)
        return roots
    roots = []
    for d in sorted(ROOT.parent.iterdir()):
        if d.resolve() == ROOT or not d.is_dir():
            continue
        if _looks_like_code_repo(d):
            roots.append(d)
    return roots


def _classify_artifact(rel):
    """rel = posix path under NTAPP-output → (bucket, archived) or None to skip."""
    if rel.startswith("evaluation/"):
        return None  # don't measure our own outputs
    archived = "/archive/" in rel or "/_v" in rel
    head = rel.split("/", 1)[0]
    bucket = {
        "Stage_1_Discovery": "discovery",
        "Stage_2_Architecture": "architecture",
        "Stage_3_Specs": "spec",
        "Stage_4_Design": "design",
        "design-system": "design_system",
    }.get(head)
    if head == "Stage_5_Build_Verify":
        bucket = "test_audit" if ("/atdd/" in rel or "test-artifacts" in rel
                                  or "test-framework" in rel) else "build_review"
    return (bucket, archived) if bucket else None


def harvest_artifact_tokens():
    """Token-proxy weight per artifact bucket, split current vs archived (rework)."""
    buckets = defaultdict(lambda: {"files": 0, "tokens": 0.0,
                                   "arch_files": 0, "arch_tokens": 0.0})
    for f in BMAD_OUT.rglob("*"):
        if not f.is_file() or f.suffix not in (".md", ".json"):
            continue
        rel = f.relative_to(BMAD_OUT).as_posix()
        c = _classify_artifact(rel)
        if not c:
            continue
        bucket, archived = c
        tok = est_tokens(read(f))
        b = buckets[bucket]
        if archived:
            b["arch_files"] += 1
            b["arch_tokens"] += tok
        else:
            b["files"] += 1
            b["tokens"] += tok
    return {k: dict(v) for k, v in buckets.items()}


def _unit_for_name(name, units_by_len):
    """First (longest) workflow unit id appearing in a filename."""
    for u in units_by_len:
        if u in name:
            return u
    return None


def _skip_path(rel):
    """True nếu rel nằm trong thư mục build/dep (khớp segment, kể cả lồng module con)."""
    return any(seg in SKIP_DIRS for seg in rel.split("/")[:-1])


def _is_test(rel, name):
    """Test code? — pattern JS (.test/.spec/.cy) + convention BE (src/test/, *Test.java,
    *_test.go, tests/...)."""
    return bool(TEST_FILE.search(name) or TEST_NAME.search(name) or TEST_PATH.search(rel))


def harvest_code_tokens(unit_slice):
    """Walk các code repo; attribute tagged files (id: header) to prod/test + slice.

    Hỗ trợ multi-repo (FE + BE Java/Kotlin/Go/...): gộp số liệu qua mọi code root."""
    roots = resolve_code_roots()
    out = {"code_roots": [str(r) for r in roots],
           "prod": {"files": 0, "tokens": 0.0}, "test": {"files": 0, "tokens": 0.0},
           "by_slice": defaultdict(lambda: {"prod": 0.0, "test": 0.0}),
           "untagged_tests": {"files": 0, "tokens": 0.0}}
    if not roots:
        out["by_slice"] = {}
        return out
    for code_root in roots:
        for f in code_root.rglob("*"):
            if not f.is_file() or not CODE_EXT.search(f.name):
                continue
            rel = f.relative_to(code_root).as_posix()
            if _skip_path(rel):
                continue
            txt = read(f)
            m = ID_HEADER.search(txt[:600])
            is_test = _is_test(rel, f.name)
            if not m:
                # untagged test code (e.g. e2e, src/test) — counted separately, not attributed
                if is_test:
                    out["untagged_tests"]["files"] += 1
                    out["untagged_tests"]["tokens"] += est_tokens(txt)
                continue
            uid = m.group(1)
            tok = est_tokens(txt)
            kind = "test" if is_test else "prod"
            out[kind]["files"] += 1
            out[kind]["tokens"] += tok
            sid = unit_slice.get(uid, "(unmapped)")
            out["by_slice"][sid][kind] += tok
    out["by_slice"] = {k: dict(v) for k, v in out["by_slice"].items()}
    return out


def _loc(txt):
    """Dòng code (LOC) thô: đếm \\n, +1 nếu file không kết thúc bằng newline."""
    if not txt:
        return 0
    return txt.count("\n") + (0 if txt.endswith("\n") else 1)


def _current_code_index(code_root, unit_slice):
    """rel-path → {kind: prod|test, slice, loc} cho file code đang nằm trên đĩa.

    Dùng để (a) phân loại churn theo path và (b) lấy LOC sống-sót làm mẫu số
    EFFY-3b. Cùng quy ước attribution với harvest_code_tokens (header id:)."""
    idx = {}
    if not code_root:
        return idx
    for f in code_root.rglob("*"):
        if not f.is_file() or not CODE_EXT.search(f.name):
            continue
        rel = f.relative_to(code_root).as_posix()
        if _skip_path(rel):
            continue
        txt = read(f)
        m = ID_HEADER.search(txt[:600])
        is_test = _is_test(rel, f.name)
        loc = _loc(txt)
        if not m:
            if is_test:
                idx[rel] = {"kind": "test", "slice": None, "loc": loc}
            continue
        idx[rel] = {"kind": "test" if is_test else "prod",
                    "slice": unit_slice.get(m.group(1), "(unmapped)"), "loc": loc}
    return idx


def harvest_code_churn(unit_slice):
    """LOC committed (added/deleted) qua git history của code repo → EFFY-3b.

    Số TUYỆT ĐỐI added/deleted là base data; churn_ratio = Σ(added+deleted) prod
    ÷ LOC prod sống-sót (=net) là chỉ số phái sinh (1.0 = mọi dòng viết ra đều
    sống; >1 = viết-rồi-xoá-rồi-viết-lại, code thrash). KHÔNG phụ thuộc timestamp
    nên đo được ngay (🟢) dù mọi mốc Change Log đều giả."""
    import subprocess
    roots = resolve_code_roots()
    out = {"available": False, "code_roots": [str(r) for r in roots],
           "commits": 0,
           "prod": {"added": 0, "deleted": 0, "net_loc": 0, "churn_ratio": None},
           "test": {"added": 0, "deleted": 0},
           "other": {"added": 0, "deleted": 0},
           "by_slice": {}}
    if not roots:
        return out
    by_slice = defaultdict(lambda: {"added": 0, "deleted": 0})
    for code_root in roots:
        idx = _current_code_index(code_root, unit_slice)
        out["prod"]["net_loc"] += sum(v["loc"] for v in idx.values()
                                      if v["kind"] == "prod")
        try:
            res = subprocess.run(
                ["git", "-C", str(code_root), "log", "--numstat", "--format=tformat:__C__"],
                capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        if res.returncode != 0:
            continue  # repo này không phải git / git thiếu → bỏ qua, repo khác vẫn đo
        out["available"] = True
        for ln in res.stdout.splitlines():
            if ln.startswith("__C__"):
                out["commits"] += 1
                continue
            m = re.match(r"^(\d+|-)\t(\d+|-)\t(.+)$", ln)
            if not m:
                continue
            a, d, path = m.group(1), m.group(2), m.group(3)
            if a == "-" or d == "-":  # binary file → numstat cho "-"
                continue
            if not CODE_EXT.search(path) or _skip_path(path):
                continue
            added, deleted = int(a), int(d)
            info = idx.get(path)
            if info and info["kind"] == "prod":
                bucket = "prod"
                by_slice[info["slice"]]["added"] += added
                by_slice[info["slice"]]["deleted"] += deleted
            elif (info and info["kind"] == "test") or _is_test(path, path.rsplit("/", 1)[-1]):
                bucket = "test"
            else:
                bucket = "other"  # file đã xoá / không gắn id → không quy được prod
            out[bucket]["added"] += added
            out[bucket]["deleted"] += deleted
    pr = out["prod"]
    net = pr["net_loc"]
    pr["churn_ratio"] = ((pr["added"] + pr["deleted"]) / net) if net else None
    out["by_slice"] = {k: dict(v) for k, v in by_slice.items()}
    return out


# ============================================================================
# Token-burn engine — gộp từ build_token_log.py (file cũ đã xoá sau khi merge).
# ----------------------------------------------------------------------------
# Gom token THẬT (burn / ra tiền) từ session JSONL của Claude Code:
#   ~/.claude/projects/<project-slug>/*.jsonl (phiên chính) + transcript của
#   MỖI sub-agent do tool Agent/Task sinh ra ở <session-id>/subagents/*.jsonl.
#   Bản Claude Code hiện tại KHÔNG còn ghi sub-agent inline (isSidechain) mà tách
#   ra thư mục con → glob top-level `*.jsonl` bỏ sót toàn bộ burn sub-agent (có
#   phiên tới ~6% input + model Haiku phụ). Vì vậy đọc cả nested, nhóm theo phiên
#   cha (_burn_order_files) để burn sub-agent kế thừa slice/stage của cha, không
#   rơi _unattributed. Mỗi dòng assistant có message.usage {input_tokens,
#   cache_creation_input_tokens, cache_read_input_tokens, output_tokens} + message.model.
# Quy ước gộp (xấp xỉ cận-trên về token, không phải $ chính xác vì cache_read rẻ ~10×):
#   input  = input_tokens + cache_creation_input_tokens + cache_read_input_tokens
#   output = output_tokens
# Gán per-turn ra by_slice / by_stage / by_model theo resolve_context():
#   1. Explicit marker: lastPrompt = slash-command + arg (SLICE-N hoặc unit-id).
#   2. File-header: Edit/Write → id (tên artifact hoặc header `id:` code file) → slice.
#   3. Sticky: turn không tín hiệu kế thừa context gần nhất (reset mỗi phiên).
#   4. _unattributed: turn đầu phiên trước mọi tín hiệu.
# Đảm bảo Σ(by_slice) == total. Reuse CODE_EXT/ID_HEADER (định nghĩa ở trên, trùng hệt).
# ============================================================================
UNIT_ID = re.compile(r"\b([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)\b")
SLICE_RE = re.compile(r"\bSLICE-0*(\d+)\b", re.I)
TECHSPEC_DIR = BMAD_OUT / "Stage_3_Specs" / "techspec"

# slash-command (prefix, case-insensitive) → stage label
CMD_STAGE = [
    ("market-research", "Stage_1"), ("product-research", "Stage_1"),
    ("create-prd", "Stage_1"), ("create-epics", "Stage_1"), ("brainstorm", "Stage_1"),
    ("grill", "Stage_1"), ("feature-triage", "Stage_1"),
    ("architecture-design", "Stage_2"), ("system-overview", "Stage_2"),
    ("slice-planning", "Stage_2b"),
    ("technical-design", "Stage_3"), ("ux-design", "Stage_3"), ("ux-sketch", "Stage_3"),
    ("feature-design", "Stage_4"), ("ui-generation", "Stage_4"), ("ds-", "Stage_4"),
    ("dev-story", "Stage_5"), ("code-review", "Stage_5"), ("testarch", "Stage_5"),
    ("dev-this", "Stage_5"), ("feature-complete", "Stage_5"), ("quick-dev", "Stage_5"),
]


def _burn_norm_slice(n):
    return "SLICE-%d" % int(n)


def _burn_load_slice_map():
    """unit_id → SLICE-N, từ frontmatter `units[].id` của mỗi slice file."""
    m = {}
    if not SLICES_DIR.exists():
        return m
    for f in sorted(SLICES_DIR.glob("SLICE-*.md")):
        sm = SLICE_RE.search(f.stem)
        if not sm:
            continue
        slice_id = _burn_norm_slice(sm.group(1))
        txt = read(f)
        fm = txt.split("---", 2)
        body = fm[1] if len(fm) >= 3 else txt
        for uid in re.findall(r"id:\s*([A-Z][A-Z0-9-]+)", body):
            if not uid.startswith("SLICE-"):
                m[uid] = slice_id
    return m


def _burn_load_techspec_units():
    """{MODULE: [unit_id,...]} từ cột đầu bảng §2.1 'Đối soát kiến trúc' của mỗi
    {MODULE}_techspec.md. MODULE = stem bỏ hậu tố '_techspec'."""
    out = {}
    if not TECHSPEC_DIR.exists():
        return out
    for f in sorted(TECHSPEC_DIR.glob("*_techspec.md")):
        module = f.stem[:-len("_techspec")] if f.stem.endswith("_techspec") else f.stem
        lines = read(f).splitlines()
        units, in_audit = [], False
        for ln in lines:
            if re.search(r"2\.1.*[Đđ]ối\s*so[áa]t", ln):
                in_audit = True
                continue
            if in_audit:
                if re.match(r"^\s*#{1,4}\s", ln) or re.match(r"^\s*---\s*$", ln):
                    break  # sang section khác
                if ln.lstrip().startswith("|"):
                    cell = ln.split("|")[1].strip().strip("`")
                    mm = UNIT_ID.fullmatch(cell)
                    if mm:
                        units.append(cell)
        if units:
            out[module.upper()] = units
    return out


def _burn_default_sessions_dir():
    """~/.claude/projects/<slug> — slug = abs path, mọi ký tự non-alnum → '-'."""
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))
    d = Path.home() / ".claude" / "projects" / slug
    return d if d.exists() else None


def _burn_iter_records(jsonl_path):
    for ln in jsonl_path.read_text(errors="replace").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            yield json.loads(ln)
        except json.JSONDecodeError:
            continue


def _burn_stage_from_cmd(cmd):
    """Stage từ slash-command. Chỉ xét TÊN lệnh (token đầu sau '/'), KHÔNG quét arg
    — key ngắn như 'ds-' dễ trúng nhầm trong đường dẫn/arg (vd '/code-review
    cards-list.tsx' chứa 'ds-' ở 'cards-list' → Stage_4 sai). Vẫn để 'in' để khoan
    dung tiền tố wrapper ('ntapp-'/'bmad-' trong '/ntapp-architecture-design')."""
    m = re.match(r"\s*/(\S+)", cmd)
    name = m.group(1).lower() if m else cmd.lower()
    for key, stage in CMD_STAGE:
        if key in name:
            return stage
    return None


def _burn_id_from_path(path, slice_map):
    """Tên artifact (SCR-FOO.md) hoặc header `id:` của code file → unit id."""
    base = Path(path).stem
    if base in slice_map:
        return base
    for uid in UNIT_ID.findall(base):
        if uid in slice_map:
            return uid
    if CODE_EXT.search(path):
        p = Path(path)
        if p.exists():
            head = "\n".join(p.read_text(errors="replace").splitlines()[:10])
            hm = ID_HEADER.search(head)
            if hm:
                return hm.group(1)
    return None


def _burn_resolve_context(rec, slice_map, techspec_units):
    """(slice, stage, is_cmd, techspec_module) của record này."""
    slice_hit = stage_hit = ts_module = None
    is_cmd = False
    lp = rec.get("lastPrompt")
    if isinstance(lp, str) and lp.strip().startswith("/"):
        is_cmd = True
        stage_hit = _burn_stage_from_cmd(lp)
        if "technical-design" in lp.lower():
            for mod in techspec_units:
                if re.search(r"\b" + re.escape(mod) + r"\b", lp, re.I):
                    ts_module = mod
                    break
        sm = SLICE_RE.search(lp)
        if sm:
            slice_hit = _burn_norm_slice(sm.group(1))
        else:  # unit-id arg → slice qua slice plan
            for uid in UNIT_ID.findall(lp):
                if uid in slice_map:
                    slice_hit = slice_map[uid]
                    break
    msg = rec.get("message")
    if slice_hit is None and ts_module is None and isinstance(msg, dict):
        c = msg.get("content")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_use" \
                        and b.get("name") in ("Edit", "Write", "NotebookEdit"):
                    fp = (b.get("input") or {}).get("file_path", "")
                    uid = _burn_id_from_path(fp, slice_map) if fp else None
                    if uid and uid in slice_map:
                        slice_hit = slice_map[uid]
                        break
    return slice_hit, stage_hit, is_cmd, ts_module


def _burn_finalize(buckets, total_in, total_out):
    """Làm tròn float → int, dồn residual vào bucket lớn nhất để Σ khớp."""
    rounded = {k: {"input": round(v["input"]), "output": round(v["output"])}
               for k, v in buckets.items()}
    for key, tot in (("input", total_in), ("output", total_out)):
        diff = tot - sum(b[key] for b in rounded.values())
        if diff and rounded:
            big = max(rounded, key=lambda k: rounded[k][key])
            rounded[big][key] += diff
    return rounded


def _burn_accumulate(ordered, slice_map, techspec_units):
    """`ordered` = list[(Path, is_group_start)] từ _burn_order_files: mỗi file
    phiên cha đứng ngay trước transcript sub-agent của nó. Sticky-context reset ở
    ranh giới NHÓM (is_group_start=True), KHÔNG reset giữa cha ↔ sub-agent → burn
    sub-agent kế thừa slice/stage của phiên cha thay vì rơi _unattributed."""
    inp = out = 0
    breakdown = {"input_tokens": 0, "cache_creation_input_tokens": 0,
                 "cache_read_input_tokens": 0, "output_tokens": 0}
    n_msgs = 0
    by_slice = defaultdict(lambda: {"input": 0.0, "output": 0.0})
    by_stage = defaultdict(lambda: {"input": 0.0, "output": 0.0})
    by_model = defaultdict(lambda: {"input": 0.0, "output": 0.0})
    # per-model 4-component breakdown → định giá chính xác theo bảng giá từng model
    by_model_breakdown = defaultdict(lambda: {"input_tokens": 0, "cache_creation_input_tokens": 0,
                                              "cache_read_input_tokens": 0, "output_tokens": 0})
    by_slice_model = defaultdict(lambda: defaultdict(lambda: {"input": 0.0, "output": 0.0}))
    by_stage_model = defaultdict(lambda: defaultdict(lambda: {"input": 0.0, "output": 0.0}))
    ts_min = ts_max = None  # G2 — khoảng ngày phiên (đo độ phủ session-log)
    cur_slice = cur_stage = cur_ts = None
    for f, group_start in ordered:
        if group_start:
            cur_slice = cur_stage = cur_ts = None  # reset mỗi NHÓM (phiên cha + sub-agent)
        else:
            cur_ts = None  # sub-agent: giữ slice/stage của cha, thoát techspec-split mode
        for rec in _burn_iter_records(f):
            rts = rec.get("timestamp")
            if isinstance(rts, str) and len(rts) >= 10:
                day = rts[:10]
                if ts_min is None or day < ts_min:
                    ts_min = day
                if ts_max is None or day > ts_max:
                    ts_max = day
            s, st, is_cmd, ts = _burn_resolve_context(rec, slice_map, techspec_units)
            if is_cmd:
                cur_ts = ts  # command mới: vào techspec mode, hoặc thoát nó
            if s:
                cur_slice = s
            if st:
                cur_stage = st
            msg = rec.get("message")
            if not (isinstance(msg, dict) and isinstance(msg.get("usage"), dict)):
                continue
            u = msg["usage"]
            it = u.get("input_tokens", 0) or 0
            cc = u.get("cache_creation_input_tokens", 0) or 0
            cr = u.get("cache_read_input_tokens", 0) or 0
            ot = u.get("output_tokens", 0) or 0
            ti, to = it + cc + cr, ot
            model = msg.get("model") or "unknown"
            n_msgs += 1
            breakdown["input_tokens"] += it
            breakdown["cache_creation_input_tokens"] += cc
            breakdown["cache_read_input_tokens"] += cr
            breakdown["output_tokens"] += ot
            inp += ti
            out += to
            by_model[model]["input"] += ti
            by_model[model]["output"] += to
            bmb = by_model_breakdown[model]
            bmb["input_tokens"] += it
            bmb["cache_creation_input_tokens"] += cc
            bmb["cache_read_input_tokens"] += cr
            bmb["output_tokens"] += ot
            # --- by_slice: techspec → chia đều cho unit của §2.1; ngược lại sticky
            if cur_ts:
                units = techspec_units[cur_ts]
                n = len(units)
                for uid in units:
                    tgt = slice_map.get(uid, "_unattributed")
                    by_slice[tgt]["input"] += ti / n
                    by_slice[tgt]["output"] += to / n
                    by_slice_model[tgt][model]["input"] += ti / n
                    by_slice_model[tgt][model]["output"] += to / n
            else:
                sk = cur_slice or "_unattributed"
                by_slice[sk]["input"] += ti
                by_slice[sk]["output"] += to
                by_slice_model[sk][model]["input"] += ti
                by_slice_model[sk][model]["output"] += to
            stk = cur_stage or "_unattributed"
            by_stage[stk]["input"] += ti
            by_stage[stk]["output"] += to
            by_stage_model[stk][model]["input"] += ti
            by_stage_model[stk][model]["output"] += to

    def round_nested(d):
        return {k: {m: {"input": round(v["input"]), "output": round(v["output"])}
                    for m, v in mv.items()} for k, mv in d.items()}

    return {
        "input": inp, "output": out, "breakdown": breakdown, "n_msgs": n_msgs,
        "ts_min": ts_min, "ts_max": ts_max,
        "by_slice": _burn_finalize(by_slice, inp, out),
        "by_stage": _burn_finalize(by_stage, inp, out),
        "by_model": _burn_finalize(by_model, inp, out),
        "by_model_breakdown": {m: dict(bd) for m, bd in by_model_breakdown.items()},
        "by_slice_model": round_nested(by_slice_model),
        "by_stage_model": round_nested(by_stage_model),
    }


def _burn_resolve_files(sessions_dir=None, session=None):
    """Danh sách file .jsonl cần đọc: phiên chính top-level + transcript sub-agent
    lồng trong <session-id>/subagents/*.jsonl (bản Claude Code mới tách sub-agent
    ra thư mục con, không còn inline isSidechain → glob non-recursive bỏ sót toàn
    bộ burn sub-agent). Trả [] nếu không tìm thấy."""
    if session:
        p = Path(session)
        # <session>.jsonl ↔ subagents của nó ở <session-dir>/<stem>/subagents/
        return [p] + sorted((p.parent / p.stem / "subagents").glob("*.jsonl"))
    d = Path(sessions_dir) if sessions_dir else _burn_default_sessions_dir()
    if not d or not d.exists():
        return []
    return sorted(d.glob("*.jsonl")) + sorted(d.glob("*/subagents/*.jsonl"))


def _burn_order_files(files):
    """Sắp `files` theo NHÓM: mỗi file phiên cha (top-level) đứng ngay trước các
    transcript sub-agent của nó (<session-id>/subagents/*.jsonl). Trả
    list[(path, is_group_start)] — is_group_start=True ở file cha (=False ở
    sub-agent) để _burn_accumulate reset sticky-context theo nhóm, cho sub-agent
    kế thừa slice/stage của phiên cha. Sub-agent mồ côi (không thấy file cha
    trong `files`) tự mở nhóm riêng — vẫn được đếm vào total."""
    subs_by_parent = defaultdict(list)
    tops = []
    for f in files:
        if f.parent.name == "subagents":
            subs_by_parent[f.parent.parent.name].append(f)
        else:
            tops.append(f)
    ordered, seen = [], set()
    for f in sorted(tops):
        ordered.append((f, True))
        seen.add(f.stem)
        for s in sorted(subs_by_parent.get(f.stem, [])):
            ordered.append((s, False))
    for parent, subs in sorted(subs_by_parent.items()):   # sub-agent mồ côi
        if parent not in seen:
            for i, s in enumerate(sorted(subs)):
                ordered.append((s, i == 0))
    return ordered


def _burn_build_log_dict(files, total_only=False):
    """Dựng dict token-log từ files (schema mà load_token_log đọc)."""
    slice_map = {} if total_only else _burn_load_slice_map()
    techspec_units = {} if total_only else _burn_load_techspec_units()
    r = _burn_accumulate(_burn_order_files(files), slice_map, techspec_units)
    inp, out, bd, n = r["input"], r["output"], r["breakdown"], r["n_msgs"]
    by_slice, by_stage = r["by_slice"], r["by_stage"]
    log = {
        "total": {"input": inp, "output": out},
        "_meta": {
            "source": "claude-code session jsonl",
            "files": len(files),
            "assistant_messages": n,
            "session_date_min": r.get("ts_min"),  # G2 — độ phủ session-log
            "session_date_max": r.get("ts_max"),
            "breakdown_raw": bd,
            "slice_plan_units": len(slice_map),
            "techspec_split": {m: techspec_units[m] for m in techspec_units},
            "by_model": r["by_model"],              # model_id → {input, output} (toàn cục)
            "by_model_breakdown": r["by_model_breakdown"],  # model_id → 4 thành phần (định giá per-model)
            "by_slice_model": r["by_slice_model"],  # slice → model_id → {input, output}
            "by_stage_model": r["by_stage_model"],  # stage → model_id → {input, output}
            "note": "input = input_tokens + cache_creation + cache_read; output = output_tokens",
        },
    }
    if not total_only:
        log["by_slice"] = by_slice
        log["by_stage"] = by_stage
        si = sum(v["input"] for v in by_slice.values())
        so = sum(v["output"] for v in by_slice.values())
        assert (si, so) == (inp, out), f"by_slice mismatch: {(si, so)} != {(inp, out)}"
    return log


def harvest_burn(sessions_dir=None, session=None, write=False, total_only=False):
    """High-level entry. Trả dict token-log, hoặc None nếu không có session.
    write=True → ghi TOKEN_LOG (token-log.json)."""
    files = _burn_resolve_files(sessions_dir, session)
    if not files:
        return None
    log = _burn_build_log_dict(files, total_only=total_only)
    if write:
        TOKEN_LOG.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    return log


def _burn_cache_stale():
    """True nếu có transcript phiên mới hơn cache burn (so theo thời gian sửa file).
    Nghĩa là cache đang bỏ sót burn của phiên vừa chạy. Thiếu cache hoặc thiếu
    phiên nào để đối chiếu → False, nhường quyết định cho nhánh gọi."""
    if not TOKEN_LOG.exists():
        return False
    try:
        cache_mtime = TOKEN_LOG.stat().st_mtime
    except OSError:
        return False
    for f in _burn_resolve_files():
        try:
            if f.stat().st_mtime > cache_mtime:
                return True
        except OSError:
            continue
    return False


def load_token_log(refresh=False):
    """Real-burn input. Schema: {total:{input,output}, by_stage:{...}, by_slice:{...}}.

    Tự harvest từ session JSONL (harvest_burn — engine gộp ở trên) khi:
      - file token-log.json chưa tồn tại, hoặc
      - refresh=True (cờ --refresh-burn) — đọc lại session mới nhất, hoặc
      - cache cũ hơn transcript phiên mới (auto — chống bẫy dùng burn cũ).
    Có file + còn mới + không refresh → dùng cached. Không có session → None (hiển thị 🔴 n/a)."""
    stale = _burn_cache_stale()
    if TOKEN_LOG.exists() and not refresh and not stale:
        try:
            return json.loads(read(TOKEN_LOG))
        except (json.JSONDecodeError, ValueError):
            pass
    if stale and not refresh:
        print("[eval-harvester] cache burn cũ hơn phiên mới → tự re-harvest")
    try:
        log = harvest_burn(write=True)  # ghi luôn token-log.json
        if log:
            print(f"[eval-harvester] auto-harvested burn từ session JSONL "
                  f"({log['_meta']['files']} files, {log['_meta']['assistant_messages']} msgs)")
        return log
    except Exception as e:  # harvest lỗi → fallback file cũ nếu có, ngược lại None
        print(f"[eval-harvester] burn auto-harvest skip: {e}")
        if TOKEN_LOG.exists():
            try:
                return json.loads(read(TOKEN_LOG))
            except (json.JSONDecodeError, ValueError):
                return None
        return None


def _git_commit_span():
    """(first_date, last_date, n_commits) theo author-date qua mọi code root.
    Trả (None, None, 0) nếu không repo nào đọc được git. Dùng cho G2 — đối
    chiếu khoảng hoạt động git với khoảng phiên Claude Code để bắt 'thiếu phiên'."""
    import subprocess
    dates = []
    for r in resolve_code_roots():
        try:
            res = subprocess.run(
                ["git", "-C", str(r), "log", "--format=%ad", "--date=short"],
                capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        if res.returncode != 0:
            continue
        dates += [l.strip() for l in res.stdout.splitlines() if l.strip()]
    if not dates:
        return None, None, 0
    return min(dates), max(dates), len(dates)


def _burn_coverage(meta):
    """G2 — tín hiệu độ phủ session-log. So khoảng ngày phiên (session_date_*)
    với khoảng author-date của commit git. Burn gom từ JSONL từng máy; nếu phiên
    chạy ở máy khác / đã xoá thì burn hụt trong im lặng. Phủ thấp → đánh dấu burn
    'một phần (cận dưới)' thay vì để số trần.

    Trả dict {level: full|partial|unknown, lower_bound: bool, ratio, ...}.
    'unknown' khi thiếu mốc git hoặc thiếu mốc phiên → không kết luận, không cảnh báo sai."""
    smin, smax = (meta or {}).get("session_date_min"), (meta or {}).get("session_date_max")
    gfirst, glast, gn = _git_commit_span()
    cov = {"session_min": smin, "session_max": smax,
           "git_first": gfirst, "git_last": glast, "git_commits": gn,
           "span_days": None, "covered_days": None, "ratio": None,
           "level": "unknown", "lower_bound": False}
    sd0, sd1 = _parse_date(smin), _parse_date(smax)
    gd0, gd1 = _parse_date(gfirst), _parse_date(glast)
    if not (sd0 and sd1 and gd0 and gd1):
        return cov  # thiếu một đầu mốc → unknown
    span = (gd1 - gd0).days + 1
    ov0, ov1 = max(sd0, gd0), min(sd1, gd1)
    covered = (ov1 - ov0).days + 1 if ov1 >= ov0 else 0
    ratio = covered / span if span else None
    cov.update(span_days=span, covered_days=covered, ratio=ratio)
    if ratio is not None:
        cov["level"] = "full" if ratio >= COVERAGE_FULL else "partial"
        cov["lower_bound"] = ratio < COVERAGE_FULL
    return cov


def build_cost(art, code, totals, token_log, units):
    """Assemble the Bộ C cost block: proxy ratios (🟢) + real-burn (🔴 if logged)."""
    def tok(bucket):
        return art.get(bucket, {}).get("tokens", 0.0)

    prod = code["prod"]["tokens"]
    spec_design = tok("spec") + tok("design")
    review_test = (tok("build_review") + tok("test_audit") + code["test"]["tokens"]
                   + code["untagged_tests"]["tokens"])
    governance = tok("discovery") + tok("architecture") + tok("design_system")
    all_artifact = sum(tok(b) for b in ("discovery", "architecture", "spec",
                                        "design", "build_review", "test_audit",
                                        "design_system"))
    # archive waste = superseded (archived) versions of the iterated design artifacts
    archived_arch = sum(art.get(b, {}).get("arch_tokens", 0.0)
                        for b in ("architecture", "design"))
    archived_curr = sum(art.get(b, {}).get("tokens", 0.0)
                        for b in ("architecture", "design"))

    def ratio(n, d):
        return (n / d) if d else None

    delivered = all_artifact + prod + code["test"]["tokens"]
    meta = (token_log.get("_meta") or {}) if token_log else {}
    burn = None
    if token_log and token_log.get("total"):
        t = token_log["total"]
        burn_total = (t.get("input", 0) + t.get("output", 0))
        ac = totals.get("ac_total") or 0
        # Phan ra 4 thanh phan input tu breakdown_raw (neu co); quy doi chi phi $.
        bd = (token_log.get("_meta") or {}).get("breakdown_raw") or {}
        comp = {
            "input": bd.get("input_tokens", 0),
            "cache_write": bd.get("cache_creation_input_tokens", 0),
            "cache_read": bd.get("cache_read_input_tokens", 0),
            "output": bd.get("output_tokens", t.get("output", 0)),
        }
        # Định giá THEO TỪNG MODEL (session dùng cả Opus lẫn Haiku cho sub-agent →
        # định giá phẳng một model sẽ lệch). Fallback định giá phẳng Opus nếu
        # token-log.json cũ chưa có by_model_breakdown.
        bmb = meta.get("by_model_breakdown") or {}
        cost_by_model = {}
        for mid, bd_m in bmb.items():
            comp_m = {
                "input": bd_m.get("input_tokens", 0),
                "cache_write": bd_m.get("cache_creation_input_tokens", 0),
                "cache_read": bd_m.get("cache_read_input_tokens", 0),
                "output": bd_m.get("output_tokens", 0),
            }
            if sum(comp_m.values()) == 0:   # model 0 token (vd '<synthetic>') → bỏ, khỏi rối bảng
                continue
            price = price_for_model(mid)
            cusd = {k: comp_m[k] / 1_000_000 * price[k] for k in comp_m}
            cost_by_model[mid] = {
                "label": model_label(mid), "components": comp_m, "cost_usd": cusd,
                "cost_total_usd": sum(cusd.values()), "tokens_total": sum(comp_m.values()),
            }
        if cost_by_model:  # per-component $ = tổng qua các model (giá khác nhau) → tổng đúng
            cost = {k: sum(c["cost_usd"][k] for c in cost_by_model.values())
                    for k in ("input", "cache_write", "cache_read", "output")}
        else:
            cost = {k: comp[k] / 1_000_000 * PRICE_PER_MTOK[k] for k in comp}
        burn = {
            "input": t.get("input"), "output": t.get("output"), "total": burn_total,
            "per_ac": ratio(burn_total, ac),
            "amplification": ratio(burn_total, delivered),  # burn ÷ delivered weight
            "by_stage": token_log.get("by_stage"),
            "by_slice": token_log.get("by_slice"),
            "components": comp if bd else None,   # 4-way input/output split (toàn cục)
            "cost_usd": cost if bd else None,     # per-component $ (blended per-model)
            "cost_total_usd": sum(cost.values()) if bd else None,
            # per-model, sắp theo chi phí giảm dần (list; label carries model id)
            "cost_by_model": sorted(cost_by_model.values(),
                                    key=lambda c: -c["cost_total_usd"]) or None,
            "cost_priced_per_model": bool(cost_by_model),
            "coverage": _burn_coverage(meta),     # G2 — độ phủ session-log
        }
    return {
        "unit": "token-proxy (~chars/%d)" % CHARS_PER_TOKEN,
        "buckets": {k: round(art[k].get("tokens", 0.0)) for k in sorted(art)},
        "buckets_archived": {k: round(art[k].get("arch_tokens", 0.0))
                             for k in sorted(art) if art[k].get("arch_tokens")},
        "code_prod_tokens": round(prod),
        "code_test_tokens": round(code["test"]["tokens"]),
        "code_untagged_test_tokens": round(code["untagged_tests"]["tokens"]),
        "code_roots": code["code_roots"],
        "ratios": {
            "spec_design_to_code": ratio(spec_design, prod),     # COST-2
            "review_test_to_code": ratio(review_test, prod),     # COST-3
            "all_artifact_to_code": ratio(all_artifact, prod),   # COST-4
            "governance_to_code": ratio(governance, prod),       # COST-5
            "archive_waste": ratio(archived_arch, archived_curr + archived_arch),  # COST-6
        },
        "delivered_tokens": round(delivered),
        "burn": burn,  # COST-1/7/8 — None unless token-log.json present
        "by_slice": code.get("by_slice", {}),
        "by_model": meta.get("by_model") or {},            # model_id → {input, output}
        "by_slice_model": meta.get("by_slice_model") or {},  # slice → model_id → {input, output}
        "by_stage_model": meta.get("by_stage_model") or {},  # stage → model_id → {input, output}
    }


def fmt_pct(x):
    return f"{round(100 * x):d}%" if x is not None else "n/a"


def fmt_ratio(x):
    return f"{x:.2f}×" if x is not None else "n/a"


def fmt_tok(x):
    """Token gọn theo bậc: ≥1 tỉ → B, ≥1 triệu → M, ≥1 nghìn → k."""
    if not x:
        return "0"
    if abs(x) >= 1_000_000_000:
        return f"{x/1_000_000_000:.2f}B"
    if abs(x) >= 1_000_000:
        return f"{x/1_000_000:.1f}M"
    return f"{round(x/1000, 1)}k"


def build(refresh_burn=False):
    slice_units, unit_slice, slice_meta = parse_slices()
    units = {u: parse_unit(u) for sl in slice_units.values() for u in sl}
    units = {u: v for u, v in units.items() if v}
    defers = parse_defers(unit_slice)
    drift = parse_drift_reports()   # G8 — lệch L3↔L2 (UI schema) bắt ở cổng thiết kế
    dd = parse_dd_reports()         # G10 — CR + drift L3↔TechSpec + TBD trong DD
    rework = parse_rework()

    # G11 — unit bị XÓA theo CR (tombstone DD `dd_version: v*-removed`). Loại khỏi
    # mọi chấm điểm FPY/AC/slice: chúng KHÔNG phải deliverable sống. Vẫn liệt kê
    # riêng (removed_slices / removed_in_slice) để surface trục-C scope-removal.
    removed = set(dd.get("removed_units") or [])
    removed_slices = []

    slices = {}
    for sid, ulist in slice_units.items():
        live_ulist = [u for u in ulist if u not in removed]
        rin_slice = [u for u in ulist if u in removed]
        us = [units[u] for u in live_ulist if u in units]
        if not us:
            # Slice rỗng SAU khi loại scope-removal = slice bị CR xóa hẳn → report
            # riêng thay vì nuốt im lặng (trước G11 bị `continue` bỏ qua vô hình).
            if rin_slice:
                removed_slices.append({"slice": sid, "units": rin_slice,
                                       "type": slice_meta.get(sid, {}).get("type"),
                                       "demo_status": slice_meta.get(sid, {}).get("demo_status")})
            continue
        ac_total = sum(u["ac_total"] for u in us)
        patch = sum(u["review_patch"] for u in us)
        # FPY chỉ tính trên unit CÓ AC đếm được (ac_total>0): tử & mẫu cùng nguồn.
        # Unit có patch nhưng AC=0 (parser trượt) bị loại khỏi tỉ lệ + gắn cờ,
        # tránh tử số `[Review][Patch]` ăn vào mẫu số 0 → FPY âm vô nghĩa.
        ac_bearing = [u for u in us if u["ac_total"] > 0]
        fpy_ac = sum(u["ac_total"] for u in ac_bearing)
        fpy_patch = sum(u["review_patch"] for u in ac_bearing)
        # F-FPY: tử số = CHỈ patch chức năng (Acceptance). Bảo mật/edge/quality loại.
        fpy_func = sum(u["functional_patch"] for u in ac_bearing)
        func_patch = sum(u["functional_patch"] for u in us)
        patch_excl = sum(u["patch_excluded"] for u in us)
        patch_uncl = sum(u["patch_unclassified"] for u in us)
        slice_excl_by = defaultdict(int)
        for u in us:
            for k, v in (u.get("patch_excluded_by") or {}).items():
                slice_excl_by[k] += v
        # Headline = unit-incidence: bao nhiêu unit chạy đúng luồng chính ngay lần đầu
        units_func_clean = sum(1 for u in ac_bearing if u["functional_patch"] == 0)
        # Cờ độ tin: story có tag lăng kính (tin cao) hay phải suy luận lexicon
        patch_inferred = any(u.get("patch_class_method") == "inferred" for u in ac_bearing)
        unscored_patch_units = [u["unit"] for u in us
                                if u["ac_total"] == 0 and u["review_patch"] > 0]
        rdefer = sum(u["review_defer"] for u in us)
        churn = sum(u["ac_churn"] for u in us)
        dev = sum(u["deviations"] for u in us)
        clog = sum(u["changelog_rows"] for u in us)
        sl_defers = [d for d in defers if d["slice"] == sid]
        # Avoidability chỉ tính trên record GIÀU trường (avoidable đã ghi rõ);
        # record bullet (avoidable=None) bị loại khỏi mẫu số — xem G1.
        sl_rich = [d for d in sl_defers if d["avoidable"] is not None]
        avoidable = sum(1 for d in sl_rich if d["avoidable"])
        closed = sum(1 for d in sl_defers if d["status"] == "closed")
        open_ages = [d["age_days"] for d in sl_defers if d["status"] != "closed" and d["age_days"] is not None]
        rework_versions = max([rework.get(u, 1) for u in live_ulist] + [1])
        slices[sid] = {
            "units": live_ulist,
            "removed_units_in_slice": rin_slice,
            "type": slice_meta.get(sid, {}).get("type"),
            "demo_status": slice_meta.get(sid, {}).get("demo_status"),
            "ac_total": ac_total,
            "review_patch": patch,
            "review_defer": rdefer,
            "fpy_ac": fpy_ac,
            "fpy_patch": fpy_patch,
            "fpy_func": fpy_func,
            # F-FPY headline = unit-incidence chức năng: % unit (feature) chạy đúng
            # luồng chính ngay lần đầu (functional_patch==0). Dễ "hình dung" hơn tỉ lệ.
            "fpy": (units_func_clean / len(ac_bearing)) if ac_bearing else None,
            "units_func_clean": units_func_clean,
            "units_ac_bearing": len(ac_bearing),
            # AC-normalized functional (phụ): 1 − lỗi-chức-năng/AC.
            "ffpy_acnorm": (max(0.0, 1 - fpy_func / fpy_ac) if fpy_ac else None),
            "func_density": (fpy_func / fpy_ac) if fpy_ac else None,
            # SFPY = yield GỒM CẢ hardening (số FPY cũ) — giữ để so sánh gánh nặng review.
            "sfpy": (max(0.0, 1 - fpy_patch / fpy_ac) if fpy_ac else None),
            "patch_density": (fpy_patch / fpy_ac) if fpy_ac else None,
            "functional_patch": func_patch,
            "patch_excluded": patch_excl,
            "patch_unclassified": patch_uncl,
            "patch_excluded_by": dict(slice_excl_by),
            "patch_inferred": patch_inferred,
            "unscored_patch_units": unscored_patch_units,
            "ac_churn": churn,
            "ac_churn_rate": (churn / ac_total) if ac_total else None,
            "deviations": dev,
            "changelog_rows": clog,
            "defer_count": len(sl_defers),
            "defer_avoidable": avoidable,
            "avoidability_index": (avoidable / len(sl_rich)) if sl_rich else None,
            # G1: defer ghi vào sổ ÷ defer review sinh ra. <1 = nợ mất dấu.
            "defer_capture_rate": (len(sl_defers) / rdefer) if rdefer else None,
            "defer_by_category": dict(_count_cat(sl_defers)),
            "defer_closed": closed,
            "defer_open": len(sl_defers) - closed,
            "closure_rate": (closed / len(sl_defers)) if sl_defers else None,
            "median_open_age_days": (statistics.median(open_ages) if open_ages else None),
            "rework_versions": rework_versions,
        }

    clusters, scattered = cluster_defers(defers)
    totals = _totals(slices, defers)
    art = harvest_artifact_tokens()
    code = harvest_code_tokens(unit_slice)
    churn = harvest_code_churn(unit_slice)
    # Gắn LOC committed (prod, đã gắn id) per-slice vào slice dict cho §1.
    for sid, sd in slices.items():
        cs = churn["by_slice"].get(sid)
        sd["code_added"] = cs["added"] if cs else 0
        sd["code_deleted"] = cs["deleted"] if cs else 0
    cost = build_cost(art, code, totals, load_token_log(refresh=refresh_burn), set(units))
    return {
        "slices": slices,
        "units": units,
        "defers": defers,
        "totals": totals,
        "clusters": clusters,
        "scattered": scattered,
        "cost": cost,
        "code_churn": churn,
        "drift": drift,
        "dd": dd,
        "removed_slices": removed_slices,
    }


def _count_cat(defers):
    c = defaultdict(int)
    for d in defers:
        c[d["category"]] += 1
    return c


def _totals(slices, defers):
    ac = sum(s["ac_total"] for s in slices.values())
    patch = sum(s["review_patch"] for s in slices.values())
    # FPY tổng: cùng nguồn AC-bearing như per-slice (xem build()), không phải
    # patch/ac thô — gộp tử/mẫu đã lọc rồi mới chia + clamp.
    fpy_ac = sum(s["fpy_ac"] for s in slices.values())
    fpy_patch = sum(s["fpy_patch"] for s in slices.values())
    fpy_func = sum(s["fpy_func"] for s in slices.values())
    units_clean = sum(s["units_func_clean"] for s in slices.values())
    units_ab = sum(s["units_ac_bearing"] for s in slices.values())
    func_patch = sum(s["functional_patch"] for s in slices.values())
    patch_excl = sum(s["patch_excluded"] for s in slices.values())
    patch_uncl = sum(s["patch_unclassified"] for s in slices.values())
    excl_by = defaultdict(int)
    for s in slices.values():
        for k, v in (s.get("patch_excluded_by") or {}).items():
            excl_by[k] += v
    closed = sum(1 for d in defers if d["status"] == "closed")
    rich = [d for d in defers if d["avoidable"] is not None]   # G1: chỉ record giàu
    rdefer = sum(s["review_defer"] for s in slices.values())
    return {
        "ac_total": ac,
        "review_patch": patch,
        "review_defer": rdefer,
        "defer_count": len(defers),
        "defer_avoidable": sum(1 for d in rich if d["avoidable"]),
        "defer_rich": len(rich),
        "defer_bullet": len(defers) - len(rich),
        # G1: tỉ lệ defer review-time được ghi vào sổ deferred-work.md.
        "defer_capture_rate": (len(defers) / rdefer) if rdefer else None,
        "defer_closed": closed,
        "closure_rate": (closed / len(defers)) if defers else None,
        # F-FPY headline = unit-incidence chức năng (xem build()).
        "fpy": (units_clean / units_ab) if units_ab else None,
        "units_func_clean": units_clean,
        "units_ac_bearing": units_ab,
        "ffpy_acnorm": (max(0.0, 1 - fpy_func / fpy_ac) if fpy_ac else None),
        "func_density": (fpy_func / fpy_ac) if fpy_ac else None,
        "sfpy": max(0.0, 1 - fpy_patch / fpy_ac) if fpy_ac else None,
        "patch_density": (fpy_patch / fpy_ac) if fpy_ac else None,
        "functional_patch": func_patch,
        "patch_excluded": patch_excl,
        "patch_unclassified": patch_uncl,
        "patch_excluded_by": dict(excl_by),
        "defer_by_category": dict(_count_cat(defers)),
    }


def render_scorecard(data, run_meta=None):
    s = data["slices"]
    order = sorted(s.keys(), key=lambda x: int(re.search(r"\d+", x).group()))
    L = []
    w = L.append
    w("# Báo cáo đánh giá quy trình code bằng AI (bản nền)\n")
    if run_meta:
        w(f"**Ngày đánh giá:** {run_meta['date']}  ·  **Lần đánh giá thứ:** {run_meta['round']}\n")
    bym = (data.get("cost") or {}).get("by_model") or {}
    if bym:
        w(f"**Model AI đã dùng:** {model_share(bym)}  *(tỉ lệ tính theo tổng token input+output)*\n")
    w("> Báo cáo này do `scripts/eval-harvester.py` **tự đọc các tài liệu Stage 1–5 rồi đếm ra số**, "
      "KHÔNG phải nhận xét chủ quan của con người. Mỗi con số chỉ phản ánh đúng những gì tài liệu ghi lại; "
      "muốn biết chỗ nào dễ sai, đọc mục **6. Giới hạn** trước khi kết luận.\n")
    w(f"**Phạm vi:** {len(order)} lát cắt (slice) — {', '.join(order)}.  "
      "*Lát cắt (slice) = một mảng tính năng làm trọn vẹn từ thiết kế đến code+test.*\n")
    dd0 = data.get("dd") or {}
    rmv_units = dd0.get("removed_units") or []
    rmv_slices = data.get("removed_slices") or []
    if rmv_units:
        by_cr = dd0.get("removed_by_cr") or {}
        crbits = "; ".join(f"**{cr}** xóa {', '.join(us)}" for cr, us in by_cr.items())
        emptied = ", ".join(f"{r['slice']} ({', '.join(r['units'])})" for r in rmv_slices)
        emptynote = (f" Trong đó **{len(rmv_slices)}** lát cắt không còn unit sống chấm điểm "
                     f"được sau khi loại scope-removal ({emptied}) → bỏ khỏi bảng tổng hợp "
                     "(trước đây các lát cắt này bị chấm FPY DỰA TRÊN unit đã xóa)."
                     if rmv_slices else "")
        w(f"> 🚫 **Phạm vi bị CR xóa (trục C — KHÔNG tính là sản phẩm):** {len(rmv_units)} feature "
          f"đã bị xóa hẳn — {crbits}. Các unit này đã **loại khỏi mọi chấm điểm FPY/AC/slice** "
          f"(tombstone DD `dd_version: v*-removed`).{emptynote} Effort thiết kế+story từng đổ vào "
          "scope này là **lãng phí trục-C**, không phải output — xem §3c.\n")

    w("\n## 1. Bảng tổng hợp từng lát cắt\n")
    w("> Mỗi cột là một lát cắt; mỗi dòng là một chỉ số. Các chỉ số được xếp theo **4 nhóm kể "
      "thành một mạch** — đọc từ trên xuống là đi hết vòng đời một lát cắt:\n"
      ">\n"
      "> **① Quy mô** (làm bao nhiêu) → **② Chất lượng ngay lần đầu** (code sạch tới đâu trước khi sửa) "
      "→ **③ Độ ổn định** (yêu cầu & thiết kế có phải làm đi làm lại không) → **④ Nợ để lại** "
      "(việc đã biết nhưng cố ý hoãn sang sau).\n"
      ">\n"
      "> Tên viết tắt (FPY, EFF-…) giữ để tra cứu, nhưng luôn kèm nghĩa tiếng Việt.\n")
    w("| Chỉ số | " + " | ".join(order) + " |")
    w("|---|" + "|".join(["---"] * len(order)) + "|")
    GROUP = object()  # dòng tiêu đề nhóm (label-only, các ô lát cắt để trống)
    rows = [
        (GROUP, "▸ ① QUY MÔ — lát cắt này gồm những gì"),
        ("Số đơn vị code (unit)", lambda x: str(len(x["units"]))),
        ("Kiểu chạy (AFK tự động / HITL có người duyệt)", lambda x: x["type"] or "?"),
        ("Số tiêu chí nghiệm thu (AC)", lambda x: str(x["ac_total"])),
        (GROUP, "▸ ② TÍNH NĂNG CHẠY ĐÚNG NGAY LẦN ĐẦU — đo đúng-spec, không tính gia cố"),
        ("Số lỗi review phải sửa (tổng Patch)", lambda x: str(x["review_patch"])),
        ("  ↳ lỗi CHỨC NĂNG (Acceptance) / gia cố (bảo mật·edge·chất lượng) / chưa rõ",
         lambda x: f"{x['functional_patch']}/{x['patch_excluded']}/{x['patch_unclassified']}"
                   + (" ⚠️suy luận" if x.get("patch_inferred") else "")),
        ("**Tính năng chạy đúng ngay lần đầu — F-FPY** (% feature KHÔNG lỗi chức năng; càng cao càng tốt)",
         lambda x: fmt_pct(x["fpy"])),
        ("  ↳ theo mật độ AC (1 − lỗi-chức-năng/AC; dịu hơn, không nhị phân hoá cả unit)",
         lambda x: fmt_pct(x["ffpy_acnorm"])),
        ("Yield gồm CẢ gia cố — SFPY (số FPY kiểu cũ; F-FPY≫SFPY = chạy được nhưng tốn công gia cố)",
         lambda x: fmt_pct(x["sfpy"])),
        (GROUP, "▸ ③ ĐỘ ỔN ĐỊNH — yêu cầu & thiết kế có phải làm lại không"),
        ("Số yêu cầu đổi giữa chừng (hủy/sửa/hoãn AC)", lambda x: str(x["ac_churn"])),
        ("Tỉ lệ yêu cầu đổi giữa chừng (càng thấp càng ổn định)", lambda x: fmt_pct(x["ac_churn_rate"])),
        ("Số lần làm khác thiết kế (Deviation)", lambda x: str(x["deviations"])),
        ("Dòng code thêm/xoá đã commit (LOC +/−, prod đã gắn id)", lambda x: f"+{x['code_added']}/−{x['code_deleted']}"),
        ("Số lần làm lại thiết kế (phiên bản DD)", lambda x: f"v{x['rework_versions']}"),
        ("Số lần cập nhật sau khi tạo (Change Log, đã trừ dòng khai sinh)", lambda x: str(x["changelog_rows"])),
        (GROUP, "▸ ④ NỢ ĐỂ LẠI — việc đã biết nhưng cố ý hoãn sang sau"),
        ("**Việc bị hoãn lại** (đang mở / đã đóng)", lambda x: f"{x['defer_count']} ({x['defer_open']}/{x['defer_closed']})"),
        ("**Defer review ghi vào sổ — G1** (sổ ÷ review-defer)", lambda x: fmt_pct(x["defer_capture_rate"])),
        ("Trong đó: lẽ ra tránh được", lambda x: str(x["defer_avoidable"])),
        ("**Tỉ lệ nợ lẽ-ra-tránh-được — EFF-7** (càng thấp càng tốt)", lambda x: fmt_pct(x["avoidability_index"])),
        ("**Tỉ lệ nợ đã xử lý xong — EFF-8** (càng cao càng tốt)", lambda x: fmt_pct(x["closure_rate"])),
        ("Số ngày trung bình nợ còn treo (EFF-8)", lambda x: ("—" if x["median_open_age_days"] is None else str(int(x["median_open_age_days"])))),
    ]
    blanks = " | ".join([""] * len(order))
    for entry in rows:
        if entry[0] is GROUP:
            w(f"| **{entry[1]}** | {blanks} |")
        else:
            label, fn = entry
            w(f"| {label} | " + " | ".join(fn(s[o]) for o in order) + " |")
    bsm = (data.get("cost") or {}).get("by_slice_model") or {}
    if bsm:
        def slice_models(sid):
            return model_share(bsm.get(sid) or {}) if bsm.get(sid) else "—"
        w("| Model AI dùng (% token) | " + " | ".join(slice_models(o) for o in order) + " |")
    w("\n*Cách đọc nhanh — lần theo đúng 4 nhóm:* "
      "**② F-FPY thấp** → tính năng KHÔNG chạy đúng spec ngay lần đầu (Acceptance Auditor phải sửa "
      "lỗi luồng chính/AC). *F-FPY chỉ đếm lỗi chức năng; lỗi bảo mật/edge/chất lượng nằm ở SFPY — "
      "F-FPY cao nhưng SFPY thấp = feature chạy được nhưng tốn nhiều công gia cố.* "
      "**③ Tỉ lệ đổi-giữa-chừng cao / Deviation nhiều / DD lên nhiều phiên bản** → yêu cầu & thiết kế "
      "chưa được chốt kỹ trước khi code. "
      "**④ Tỉ lệ nợ tránh-được cao** → phần lớn việc bị hoãn là do quy trình, không phải lý do khách quan.\n")

    w("\n## 2. Việc bị hoãn lại — phân theo lý do\n")
    w("> \"Việc bị hoãn\" (defer) = phần đã biết nhưng cố ý để làm sau. Chia 2 nhóm: "
      "**hợp lệ** (lý do khách quan, ngoài tầm kiểm soát) và **lẽ ra tránh được** (in đậm — nợ do quy trình). "
      "Mục tiêu là kéo nhóm tránh-được về 0.\n")
    # G1 — đối soát defer: review sinh bao nhiêu vs sổ deferred-work.md ghi bao nhiêu.
    t0 = data["totals"]
    trd, tdc, cap = t0["review_defer"], t0["defer_count"], t0.get("defer_capture_rate")
    if trd and (tdc == 0 or (cap is not None and cap < 0.5)):
        w(f"> ⚠️ **Lỗ hổng truy vết defer (G1):** review sinh **{trd}** defer "
          f"(`[Review][Defer]` trong story) nhưng sổ `deferred-work.md` chỉ đọc được **{tdc}** "
          f"(**{fmt_pct(cap)}** ghi sổ). Phần thiếu = nợ đã nhận diện nhưng **mất dấu** — "
          "không phân biệt được \"sạch nợ\" với \"không ghi sổ\". Xem `harvester_upgrade.md` G1.\n")
    elif trd:
        bullet = t0.get("defer_bullet", 0)
        w(f"> **Đối soát defer (G1):** {tdc}/{trd} defer review-time có trong sổ "
          f"(**{fmt_pct(cap)}** ghi sổ; {bullet} từ bullet `## Deferred from:`, "
          f"{t0.get('defer_rich', 0)} từ block `### DEF-`). "
          "*Capture-rate là tín hiệu định hướng — sổ có thể chứa defer ngoài review nên không phải 1:1.*\n")
    cats = DEFER_CATEGORY_ORDER + ["uncategorized"]
    w("| Lý do hoãn | " + " | ".join(order) + " | Tổng | Đánh giá bản chất |")
    w("|---|" + "|".join(["---"] * (len(order) + 2)) + "|")
    nature = {"contract-blocked": "chờ chốt hợp đồng API bên ngoài → hợp lệ",
              "arch-limit": "giới hạn kiến trúc đã biết, cố ý → hợp lệ",
              "asset-gap": "chờ tài nguyên/thiết kế bên ngoài → hợp lệ",
              "scope-deferred": "chủ động cắt bớt phạm vi → hợp lệ",
              "test-deferred": "**bỏ viết test → nợ quy trình (tránh được)**",
              "cross-slice-dep": "**chờ lát cắt khác xong → nợ điều phối (tránh được)**",
              "deferred-bug": "**bug/UX để lại làm sau → tránh được**",
              "security-hardening": "**gia cố bảo mật để sau → tránh được**",
              "uncategorized": "chưa ghi rõ lý do"}
    label_cat = {"contract-blocked": "Chờ hợp đồng API", "arch-limit": "Giới hạn kiến trúc",
                 "asset-gap": "Thiếu tài nguyên", "scope-deferred": "Cắt phạm vi",
                 "test-deferred": "Bỏ test", "cross-slice-dep": "Phụ thuộc lát cắt khác",
                 "deferred-bug": "Bug để sau", "security-hardening": "Bảo mật để sau",
                 "uncategorized": "Chưa phân loại"}
    tot = data["totals"]["defer_by_category"]
    for c in cats:
        if tot.get(c, 0) == 0:
            continue
        cells = [str(s[o]["defer_by_category"].get(c, 0)) for o in order]
        w(f"| {label_cat.get(c,c)} `{c}` | " + " | ".join(cells) + f" | {tot.get(c,0)} | {nature.get(c,'?')} |")
    t = data["totals"]
    if t["defer_count"]:
        rich = t.get("defer_rich", t["defer_count"])     # chỉ record có avoidable đã ghi
        bullet = t.get("defer_bullet", 0)
        if rich:
            avoid_pct = fmt_pct(t["defer_avoidable"] / rich)  # mẫu số = record đã phân loại
            w(f"\n**Tổng cộng {t['defer_count']} việc bị hoãn**, trong đó {rich} việc đã phân loại — "
              f"**{t['defer_avoidable']} ({avoid_pct}) lẽ ra tránh được** (nợ do quy trình, nên ưu tiên xử lý).")
        else:
            w(f"\n**Tổng cộng {t['defer_count']} việc bị hoãn.**")
        if bullet:
            w(f" Trong đó **{bullet}** việc từ review (bullet `## Deferred from:`) **chưa phân loại** "
              "avoidable/category — cần enrich → block `### DEF-` để chấm (G1).")
        w("\n")
    else:
        w("\n**Chưa có việc hoãn nào được ghi nhận** — không có nợ quy trình để xử lý ở thời điểm này.\n")

    w("\n## 2b. Gom nợ theo \"một hành động đóng được nhiều việc\"\n")
    w("> Nhiều việc bị hoãn thực ra cùng chờ MỘT điều kiện. Bảng này gom chúng lại: mỗi dòng là một hành động "
      "(hoặc sự kiện) mà khi xong sẽ đóng luôn nhiều việc cùng lúc — giúp biết nên ưu tiên làm gì. "
      "Dòng `— (rải rác)` = các việc không gom được, phải xử lý lẻ từng cái.\n")
    w("| Hành động đóng nợ | Số việc đóng được | Trong đó tránh-được | Thuộc lát cắt |")
    w("|---|--:|--:|---|")
    clusters = data["clusters"]
    for c in clusters:
        w(f"| `{c['action']}` | {c['count']} | {c['avoidable']} | {', '.join(c['slices'])} |")
    sc = data["scattered"]
    w(f"| **{sc['action']}** | {sc['count']} | {sc['avoidable']} | {', '.join(sc['slices'])} |")
    open_total = sum(c["count"] for c in clusters) + sc["count"]
    open_av = sum(c["avoidable"] for c in clusters) + sc["avoidable"]
    clustered_av = sum(c["avoidable"] for c in clusters)  # closeable by 1 action / dependency event
    w(f"\n**Đang mở {open_av} việc tránh-được**: **{clustered_av} việc gom cụm được** "
      f"(chỉ cần làm xong 1 hành động/sự kiện là đóng cả cụm) + **{sc['avoidable']} việc rải rác** "
      "(phải xử lý từng cái). "
      f"→ Phần rải-rác chiếm {fmt_pct(sc['avoidable']/open_total) if open_total else 'n/a'} — "
      "đây mới là phần khó giải quyết thật sự (không có đòn bẩy chung).\n")

    w("\n## 3. Lỗi sinh ra ở đâu, bắt được ở đâu (từng đơn vị code)\n")
    w("> Bảng truy ngược theo từng unit: nhiều lỗi review (Patch) + ít việc hoãn → lỗi bị dồn về cuối; "
      "ngược lại nhiều việc hoãn → vấn đề được nhận ra nhưng đẩy sang sau.\n")
    w("> Cột **Lỗi chức năng** = patch luồng chính/AC (trừ F-FPY); **Gia cố** = bảo mật·edge·chất lượng "
      "(không trừ F-FPY). `⚠️suy luận` = story không tag lăng kính review nên phải đoán từ nội dung.\n")
    w("| Đơn vị code | Lát cắt | Số AC | Lỗi chức năng | Gia cố | Tổng Patch | Việc hoãn | Làm khác thiết kế | Lần cập nhật sau tạo |")
    w("|---|---|--:|--:|--:|--:|--:|--:|--:|")
    for o in order:
        for u in s[o]["units"]:
            uu = data["units"].get(u)
            if not uu:
                continue
            note = " ⚠️(đếm gián tiếp)" if uu["ac_count_method"] in ("referenced", "plain-list") else ""
            fnote = " ⚠️suy luận" if uu.get("patch_class_method") == "inferred" else ""
            uncl = uu.get("patch_unclassified", 0)
            unote = f" (+{uncl}?)" if uncl else ""
            w(f"| {u} | {o} | {uu['ac_total']}{note} | {uu.get('functional_patch', 0)}{fnote} | "
              f"{uu.get('patch_excluded', 0)}{unote} | {uu['review_patch']} | "
              f"{uu['review_defer']} | {uu['deviations']} | {uu['changelog_rows']} |")

    render_drift(w, data)
    render_dd(w, data)
    render_crosslayer(w, data)

    w("\n## 4. Cảnh báo tự động — lát cắt nào cần chú ý\n")
    w("> Máy tự gắn cờ khi một chỉ số vượt ngưỡng đáng lo. Không có cờ = chỉ số trong vùng an toàn.\n")
    for o in order:
        x = s[o]
        flags = []
        if x["fpy"] is not None and x["fpy"] < 0.8:
            dens = x.get("func_density")
            extra = (f" — mật độ {fmt_ratio(dens)} lỗi-chức-năng/AC" if dens else "")
            inf = " *(suy luận — story không tag review)*" if x.get("patch_inferred") else ""
            flags.append(f"Tính-năng-chạy-đúng-lần-đầu chỉ {fmt_pct(x['fpy'])} (<80%){extra}{inf} → "
                         "Acceptance Auditor phải sửa lỗi luồng chính/AC mà lẽ ra spec+design Stage 3–4 "
                         "phải làm rõ trước")
        if x.get("patch_unclassified", 0) >= 3:
            flags.append(f"{x['patch_unclassified']} patch chưa phân loại được (không tag, không khớp lexicon) "
                         "→ F-FPY của lát cắt này kém chắc; soi tay mục *Patch* để xác nhận chức năng hay gia cố")
        if x.get("unscored_patch_units"):
            flags.append(f"{len(x['unscored_patch_units'])} unit có lỗi review nhưng parser không đếm được AC "
                         f"({', '.join(x['unscored_patch_units'])}) → đã loại khỏi F-FPY; kiểm tra mục "
                         "*Acceptance Criteria* của các unit này có viết đúng style không")
        if x["ac_churn_rate"] and x["ac_churn_rate"] >= 0.15:
            flags.append(f"Yêu cầu đổi giữa chừng {fmt_pct(x['ac_churn_rate'])} (cao) → yêu cầu chưa chốt kỹ "
                         "trước khi bắt tay code")
        if x["avoidability_index"] and x["avoidability_index"] >= 0.4:
            flags.append(f"{fmt_pct(x['avoidability_index'])} việc hoãn là loại tránh-được → phần lớn nợ do quy trình")
        if x["rework_versions"] >= 3:
            flags.append(f"Thiết kế đã làm lại tới phiên bản v{x['rework_versions']} → tốn nhiều vòng sửa thiết kế")
        if x["code_added"] and x["code_deleted"] / x["code_added"] >= 0.5:
            flags.append(f"Code viết-rồi-xoá nhiều (+{x['code_added']}/−{x['code_deleted']} dòng, "
                         f"xoá ≈ {fmt_pct(x['code_deleted']/x['code_added'])} số dòng thêm) → thrash ở tầng code (EFFY-3b)")
        w(f"- **{o}**: " + ("; ".join(flags) if flags else "không có cảnh báo nào — ổn ✓"))

    render_cost(w, data)

    w("\n## 6. Giới hạn của báo cáo — đọc trước khi kết luận\n")
    w("> Báo cáo do máy đọc văn bản đếm ra, nên có những chỗ dễ lệch. Biết trước các giới hạn này để "
      "không hiểu sai con số.\n")
    w("- **Cách đếm số tiêu chí nghiệm thu (AC)**: máy thử 3 cách theo thứ tự ưu tiên — (1) đề mục đậm "
      "`**AC-N**`, (2) danh sách đánh số `N. **…**`. Cả hai đều đáng tin. Chỉ khi cả hai đều trượt mới rơi "
      "xuống (3) *đếm gián tiếp* (`⚠️`): gom mọi chuỗi `AC-N` xuất hiện trong phần AC rồi đếm số khác nhau — "
      "cách này dễ lệch (không nở dải `AC7–AC14`, đếm nhầm cả tham chiếu chéo) nên FPY của unit đó kém tin cậy. "
      "*Hiện chưa unit nào rơi vào cách (3); nếu thấy `⚠️` ở §3 thì mới cần dè chừng.*")
    w("- **F-FPY chỉ đo lỗi CHỨC NĂNG, không đo gia cố**: tử số chỉ gồm patch khiến *tính năng chạy "
      "sai spec/luồng chính* — bám theo lăng kính **Acceptance Auditor** của `/bmad-code-review`. Lỗi "
      "bảo mật, edge-case, chất lượng/convention **cố ý loại** (feature vẫn chạy, chỉ cần gia cố) → "
      "xem ở **SFPY** và cột *Gia cố* §3. Cách phân loại 3 tầng: (1) **tag lăng kính** `(auditor)`/`(blind+edge)` "
      "ở cuối bullet patch — tin cao; (2) story không tag → *suy luận* (`⚠️`): dẫn `AC-N` + động từ hỏng "
      "⇒ chức năng, còn lexicon bảo mật/edge/quality ⇒ gia cố; (3) không đủ tín hiệu → **chưa phân loại** "
      "(cột Gia cố ghi `(+N?)`), KHÔNG ngầm tính sạch. *6/17 story HUB không tag lăng kính → rơi tầng (2), "
      "F-FPY của chúng kém chắc hơn — đã gắn `⚠️suy luận`.* Ngưỡng severity (Critical/High) hiện CHƯA dùng "
      "để lọc; một AC-nit nhỏ vẫn tính như một lỗi chức năng.")
    w("- **Chưa đo được tốc độ làm việc**: mọi mốc thời gian trong Change Log đều ghi cùng một ngày, "
      "nên không tính được mất bao lâu cho mỗi bước. Muốn đo cần ghi mốc bắt đầu/kết thúc cho từng stage.")
    w("- **\"Số lần cập nhật sau khi tạo\"**: đếm số dòng Change Log có ngày rồi **trừ 1 dòng khai sinh** "
      "(dòng \"tạo story / scaffold\" đầu tiên) — để unit tạo-xong-là-done tính 0 lần sửa, không phải 1. "
      "Giả định dòng đầu luôn là dòng tạo; nếu một unit ghi Change Log bắt đầu giữa chừng (thiếu dòng tạo) "
      "thì con số sẽ bị hụt 1.")
    w("- **Có thể sót \"làm khác thiết kế\"**: máy chỉ bắt được khi ghi rõ là deviation; nếu viết lẫn trong "
      "đoạn văn dài thì có thể bỏ lọt.")
    w(f"- **Phân loại việc-hoãn do người ghi**: lý do/đánh-giá-tránh-được/trạng-thái lấy thẳng từ sổ "
      f"`deferred-work.md` (do người điền), không phải máy đoán. Tuổi nợ tính tới ngày mốc {AS_OF.isoformat()}.")
    w("- **Số liệu do AI tự khai**: số lần làm-khác-thiết-kế và việc-hoãn là do agent tự ghi, nên phụ thuộc "
      "mức độ trung thực khi ghi chép.")
    w("- **Dòng code thêm/xoá (LOC committed, §5.3b)**: đếm từ `git log --numstat` của **mọi code repo** phát "
      "hiện được (multi-repo FE+BE: gộp qua từng repo, mỗi repo chạy git log riêng). Churn của "
      "file đã **bị xoá hẳn** không quy được về prod/lát cắt (không còn header `id:`) → gom vào dòng \"Khác\". "
      "Repo brownfield **chưa gắn `id:` header** (code cũ Java/FE) sẽ rơi hết vào \"Khác\" và prod=0 — đó là theo "
      "thiết kế (attribution dựa header), không phải lỗi đọc. "
      "Đổi-tên file (nếu git không nhận diện được rename) bị tính thành xoá+thêm → có thể thổi nhẹ tỉ lệ thrash. "
      "Commit đầu của dự án brownfield dồn codebase cũ vào một lần làm cột \"thêm\" rất lớn (nhưng không thổi tỉ lệ "
      "vì gần như không có dòng xoá). LOC chỉ là **mẫu số chuẩn-hoá**, KHÔNG phải thước đo năng suất — nhiều dòng "
      "≠ nhiều giá trị.")
    w("- **Mẫu còn nhỏ** (3 lát cắt): chỉ nên xem là xu hướng, chưa đủ để kết luận chắc; dự án dựng lại từ "
      "code cũ (brownfield) thường có nhiều việc-hoãn/tái-sử-dụng hơn do nền tảng cũ.")
    w(f"- **Hai loại token khác nhau, đừng nhầm**: §5 có cả *token-proxy* (cân theo độ dài văn bản, ~{CHARS_PER_TOKEN} "
      "ký tự/token — KHÔNG phải tiền) và *token thật* (LLM thực sự xử lý, gồm cả đọc-lại ngữ cảnh + suy luận + "
      "thử lại, mới ra chi phí $). Token thật được tự gom từ nhật ký phiên Claude Code; nếu không có sẽ hiện `n/a`. "
      "Token code đếm theo file có dòng `id:` trong code repo; test `tests/` không gắn id thì đếm riêng, "
      "không quy về lát cắt nào.")
    return "\n".join(L) + "\n"


def render_drift(w, data):
    """§3b — Drift gate L3↔L2 (G8): lệch thiết kế ↔ hợp đồng bắt TRƯỚC khi vào code."""
    dr = data.get("drift") or {}
    w("\n## 3b. Lệch thiết kế ↔ hợp đồng bắt ở cổng thiết kế (drift L3↔L2 — G8)\n")
    if not dr.get("available") or not dr.get("reports"):
        w("> 🔴 Chưa đọc được drift report nào (`Stage_4_Design/ui_schema/drift_report_*.md`). "
          "Khi có, phần này đếm số lệch L3↔L2 chặn được ở cổng thiết kế trước khi code.\n")
        return
    w("> Mỗi unit UI sinh **drift report** đối chiếu thiết kế chi tiết (L3) ↔ hợp đồng dữ liệu (L2). "
      "**BLOCKING** = lệch chặn sinh schema (phải sửa trước khi code) · **RECONCILED** = blocking đã hoà giải "
      "tại cổng · **NON-BLOCKING** = lệch nhỏ ghi nhận. Bắt ở đây = chặn lỗi **trước** Stage 5 (code). "
      "*Heuristic đếm theo cấu trúc văn bản, dedup re-run theo ngày mới nhất.*\n")
    b, r, nb = dr["blocking"], dr["reconciled"], dr["nonblocking"]
    w(f"- **{dr['reports']}** unit có drift report; **{dr['halted']}** unit bị HALT Phase B vì còn blocking.")
    w(f"- **Tổng lệch bắt ở cổng thiết kế: {b + r + nb}** — "
      f"**{b}** blocking đang mở · **{r}** blocking đã hoà giải · **{nb}** non-blocking.")
    if dr["res_l2"] + dr["res_l3"]:
        w(f"- Hướng hoà giải (ai là chuẩn): **L2 hợp đồng thắng {dr['res_l2']}** lần · "
          f"**L3 thiết kế phải sửa {dr['res_l3']}** lần" +
          (" — L2 thắng nhiều hơn ⇒ phần lớn là thiết kế lệch khỏi hợp đồng dữ liệu."
           if dr["res_l3"] >= dr["res_l2"] else "."))
    w("")
    w("| Unit | Ngày | Blocking (mở) | Đã hoà giải | Non-blocking | Cổng thiết kế |")
    w("|---|---|--:|--:|--:|---|")
    for unit, rec in dr["by_unit"].items():
        gate = "⛔ HALT" if rec["gate_outcome"] == "halted" else "✅ qua"
        w(f"| {unit} | {rec['date'] or '—'} | {rec['blocking']} | {rec['reconciled']} | "
          f"{rec['nonblocking']} | {gate} |")
    w("\n*Cách đọc: blocking-đang-mở cao = thiết kế còn lệch hợp đồng chưa chốt; đã-hoà-giải cao = cổng "
      "đang làm đúng việc (bắt & ép sửa trước khi code); non-blocking = nợ nhỏ ghi vào `_drift_notes` schema.*\n")


def render_dd(w, data):
    """§3c — CR & drift trong Detailed Design L3 (G10): bù trục C từ tầng thiết kế."""
    dd = data.get("dd") or {}
    w("\n## 3c. CR & lệch thiết kế trong Đặc tả chi tiết (L3 — G10)\n")
    if not dd.get("available") or not dd.get("files"):
        w("> 🔴 Chưa đọc được file `detailed_design/*_detailed_design.md` nào. Khi có, phần này đếm "
          "CR (bảng lịch sử thay đổi), lệch thiết kế L3↔TechSpec (§1.2) và quyết định treo `[TBD]`.\n")
        return
    w("> Mỗi DD chứa **bảng lịch sử thay đổi** (số lần sửa thiết kế) + (với feature có lệch) "
      "**section drift/inheritance-audit §1.x**. Tín hiệu **bổ sung** cho §3b: §3b đo drift **UI** (L3↔L2 "
      "schema, file `drift_report`); §3c đo drift **L3↔TechSpec** + lịch sử sửa DD — nguồn drift DUY NHẤT cho "
      "feature **BE** (không có UI schema). *Drift chấm theo **verdict per-unit** (resolved / flags / none) — "
      "KHÔNG đếm per-item `Dn` vì ID drift đa convention & status nằm ở cấp section, đếm thô ra số sai.*\n")
    ct, tk = dd["cr_total"], dd["cr_ticketed"]
    bt = dd.get("by_type") or {}
    amd = " · ".join(f"{k}={bt[k]}" for k in ("A", "M", "D") if bt.get(k)) or "—"
    ticknote = (f"; trong đó **{tk}** có link CR/Jira ngoài chính thức" if tk else
                "; **không dòng nào** link CR/Jira ngoài chính thức → mọi lần sửa là vòng lặp thiết kế nội bộ")
    rmv = dd.get("removed_units") or []
    rmv_note = (f" (+ **{len(rmv)}** tombstone bị XÓA theo CR — tách riêng bên dưới, "
                "KHÔNG tính vào mẫu số)" if rmv else "")
    w(f"- **{dd['files']}** DD sống đọc được{rmv_note}; tổng **{ct}** lần sửa thiết kế "
      f"(dòng change-history){ticknote}. Loại thay đổi: {amd} *(A=tạo mới, M=sửa, D=xoá)*.")
    if rmv:
        by_cr = dd.get("removed_by_cr") or {}
        crbits = " · ".join(f"**{cr}**: {', '.join(us)}" for cr, us in by_cr.items())
        w(f"- 🚫 **Scope-removal (trục C):** **{len(rmv)}** feature bị XÓA hẳn theo CR — "
          f"{crbits}. DD đã gut thành tombstone (`dd_version: v*-removed`). Các unit này đã "
          "**loại khỏi mẫu số §3c VÀ khỏi mọi chấm điểm FPY/AC/slice** (§1/§A) — không tính "
          "là deliverable sống. Effort thiết kế+story từng đổ vào scope sắp xóa là **lãng phí "
          "trục-C**, không phải output.")
    vc = dd.get("verdict_counts") or {}
    nres, nflag, nnone = vc.get("resolved", 0), vc.get("flags", 0), vc.get("none", 0)
    flagged = dd.get("flagged_units") or []
    if nres or nflag:
        flagnote = (f" — **{', '.join(flagged)}**" if flagged else "")
        w(f"- **Drift L3↔TechSpec (verdict per-unit):** **{nres}** unit resolved (mọi finding đã land, "
          f"kể cả fix tại L2/Module-0/WBS) · **{nflag}** unit còn **flags** (≥1 finding treo){flagnote} · "
          f"{nnone} unit có section nhưng không drift finding." +
          (" Không unit nào còn flag ⇒ cổng thiết kế L3 đang ép hoà giải trước khi code."
           if nflag == 0 else " Các unit flags cần review nợ thiết kế trước khi đóng."))
    else:
        w("- Không DD nào surface section drift/inheritance-audit (feature đơn giản, không lệch).")
    if dd["tbd_confirm"]:
        w(f"- **{dd['tbd_confirm']}** quyết định thiết kế còn treo (`[TBD]`/`[TBD-confirm]`) — defer ở tầng thiết kế, "
          "cần chốt trước khi đóng feature.")
    w("")
    w("| Unit | Bản DD | Lần sửa DD | có ticket | Drift verdict | finding treo/tổng | TBD |")
    w("|---|---|--:|--:|:--|--:|--:|")
    VMARK = {"resolved": "✅ resolved", "flags": "⚠️ flags", "none": "—",
             "removed": "🚫 XÓA (CR)"}
    for unit, rec in dd["by_unit"].items():
        ver = rec.get("version") or "—"
        vt = VMARK.get(rec.get("drift_verdict"), "—")
        fc = f"{rec['drift_open']}/{rec['drift_findings']}" if rec["drift_findings"] else "—"
        tb = rec["tbd"] or "—"
        tk = rec["cr_ticketed"] or "—"
        w(f"| {unit} | {ver} | {rec['cr_total']} | {tk} | {vt} | {fc} | {tb} |")
    w("\n*Cách đọc: lần-sửa-DD cao = thiết kế churn nhiều sau khi tạo (yêu cầu/thiết kế chưa ổn định); "
      "verdict **flags** = ≥1 finding drift còn treo (TBD / cần upstream / build trên mock) — nợ thiết kế "
      "cần đóng; **resolved** = mọi finding đã land (sửa L3 hoặc L2 đều tính); TBD = quyết định thiết kế đang "
      "hoãn. Cột 'có ticket' = số lần sửa truy được CR/Jira ngoài (— = sửa nội bộ, không ticket).*\n")


def render_crosslayer(w, data):
    """§3d — Drift & điều chỉnh tài liệu XUYÊN TẦNG L2 → L3 → Story. Tổng hợp lại 3
    nguồn đã có (G8 drift_report UI, G10 DD inheritance/TechSpec audit, deviation +
    change-log story) thành 2 bảng: (A) tỉ lệ drift xuôi dòng, (B) chiều điều chỉnh
    tài liệu 2 chiều. Consumer-only — không thêm parser, chỉ chiếu lại số đã đếm."""
    dd = data.get("dd") or {}
    dr = data.get("drift") or {}
    removed = set(dd.get("removed_units") or [])
    units = {u: v for u, v in (data.get("units") or {}).items() if u not in removed}
    N = len(units)
    w("\n## 3d. Drift & điều chỉnh tài liệu xuyên tầng (L2 → L3 → Story)\n")
    if not N:
        w("> Chưa đủ dữ liệu unit để tính drift xuyên tầng.\n")
        return
    w("> Gộp 3 nguồn đã đo ở §3b/§3c/§1 theo **ranh giới tầng tài liệu**: "
      "**L2** = thượng nguồn của thiết kế (HLD / Module-0 / TechSpec) · **L3** = Đặc tả chi "
      "tiết (DD) · **Story** = story build Stage-5. *Drift = tầng dưới lệch khỏi tầng trên; "
      "điều chỉnh 2 chiều = khi phát hiện lệch thì sửa tầng dưới (xuôi) hay đẩy ngược sửa tầng "
      "trên (escalate).* Mẫu số = **%d** unit sống (đã loại tombstone scope-removal).\n" % N)

    # --- Bảng A: drift xuôi dòng (unit-incidence, KHÔNG đếm per-item) ---
    g8u = {u for u, r in (dr.get("by_unit") or {}).items()
           if u not in removed and (r["blocking"] + r["reconciled"] + r["nonblocking"]) > 0}
    g10u = {u for u, r in (dd.get("by_unit") or {}).items()
            if u not in removed and r.get("drift_findings", 0) > 0}
    l2l3 = g8u | g10u
    devu = {u for u, v in units.items() if v["deviations"] > 0}
    w("\n**A. Tỉ lệ drift xuôi dòng** — **đơn vị đo: SỐ UNIT** *(1 unit có nhiều drift vẫn "
      "tính 1; đo theo unit chứ không theo per-item vì ID drift đa convention, xem §3c)*\n")
    w("| Ranh giới tầng | Đơn vị lệch / tổng (số unit) | Tỉ lệ drift (% unit) | Tín hiệu nguồn |")
    w("|---|--:|--:|:--|")
    w(f"| **L2 → L3** (Kiến trúc → Thiết kế chi tiết) | {len(l2l3)}/{N} | "
      f"**{fmt_pct(len(l2l3)/N)}** | drift_report UI ({len(g8u)} unit, G8) ∪ "
      f"inheritance/TechSpec audit DD ({len(g10u)} unit, G10) |")
    devnote = (f"{len(devu)}/{N}", fmt_pct(len(devu) / N)) if devu else ("0/%d" % N, "0%")
    w(f"| **L3 → Story** (Thiết kế chi tiết → Story build) | {devnote[0]} | "
      f"**{devnote[1]}** | Deviation \"làm khác thiết kế\" trong story |")
    if not devu:
        w("\n> ⚠️ *L3→Story = 0 vì story KHÔNG ghi token `DEVIATION` nào (format chưa được skill "
          "phát) — KHÔNG kết luận \"story bám sát thiết kế tuyệt đối\". Đọc kèm **AC đổi giữa "
          "chừng** (§1, ac_churn) và **lỗi review phải sửa** (§1, patch) làm tín hiệu thay thế cho "
          "độ lệch story↔thiết kế.*")

    # --- Bảng B: chiều điều chỉnh tài liệu 2 chiều ---
    rl2, rl3 = dr.get("res_l2", 0), dr.get("res_l3", 0)
    tot_res = rl2 + rl3
    esc = fmt_pct(rl2 / tot_res) if tot_res else "—"
    l3_rev = dd.get("cr_total", 0)
    story_rev = sum(v["changelog_rows"] for v in units.values())
    w("\n**B. Điều chỉnh tài liệu 2 chiều** — **đơn vị đo: SỐ LẦN** *(khi có lệch: sửa tầng dưới "
      "cho khớp = xuôi; sửa ngược tầng trên = escalate). ⚠️ 2 hàng dùng 2 counter khác nhau: "
      "L2↔L3 đếm **lần marker** `[L2]`/`[L3]`, L3↔Story đếm **dòng change-log** → KHÔNG so chéo "
      "giữa 2 hàng, chỉ đọc chiều xuôi/ngược trong cùng 1 hàng.*\n")
    w("| Ranh giới | Sửa tầng DƯỚI — xuôi (số lần) | Đẩy ngược sửa TRÊN (số lần) | "
      "Tỉ lệ escalate ngược (lần/lần) | Đơn vị đếm + nguồn |")
    w("|---|--:|--:|--:|:--|")
    w(f"| **L2 ↔ L3** | {rl3} | {rl2} | **{esc}** | "
      "số lần marker `[L3]`/`[L2]` trong drift_report (G8) |")
    w(f"| **L3 ↔ Story** | {story_rev} | {l3_rev} | — | "
      "số dòng change-log story vs change-log DD |")
    w("\n*Cách đọc: **L2↔L3** tách được chiều nhờ marker `[L2]`/`[L3]` ghi rõ trong drift_report "
      f"— escalate ngược **{esc}** nghĩa là gần ngần ấy lượt hoà giải phải sửa LÊN kiến trúc "
      "(L2 chưa chốt kỹ trước khi xuống L3), không chỉ sửa xuống L3. **L3↔Story** chỉ đếm được "
      "TỔNG số lần sửa mỗi tầng (change-log), **KHÔNG** tách được lần sửa nào do phản hồi ngược "
      "từ tầng kia (thiếu ticket liên kết) → cột escalate để `—`. Số lần sửa L3 cao so với Story "
      "= phần lớn churn tài liệu nằm ở tầng thiết kế.*\n")


def render_cost(w, data):
    c = data.get("cost")
    w("\n## 5. Chi phí token\n")
    if not c:
        w("> Không có dữ liệu chi phí.\n")
        return
    w("> **Đọc kỹ phần này có 2 loại token, đừng nhầm:**\n"
      f">  - **Token-proxy** = cân độ dài tài liệu/code (~{CHARS_PER_TOKEN} ký tự = 1 token). Đây CHỈ là thước "
      "đo \"khối lượng sản phẩm làm ra\", **không phải tiền**. Dùng để so tỉ lệ tài-liệu/code.\n"
      ">  - **Token thật (burn)** = số token LLM thực sự xử lý (gồm đọc-lại ngữ cảnh, suy luận, thử lại). "
      "Đây mới là cái **ra tiền $** — xem §5.4.\n")
    roots = c.get("code_roots") or []
    if not roots:
        w("> ⚠️ Không tìm thấy code repo nào (sibling của spec repo phải có marker "
          "`package.json` / `pom.xml` / `build.gradle` / `go.mod` / `Cargo.toml`... — "
          "hoặc chỉ định thủ công qua `EVAL_CODE_ROOT`, nhiều path ngăn bằng `:` hoặc `,`) "
          "→ các tỉ lệ \"so với code\" sẽ là n/a.\n")
    elif len(roots) > 1:
        w("> 📦 Đo gộp **%d code repo** (multi-repo FE+BE): %s\n"
          % (len(roots), ", ".join("`%s`" % r.rsplit("/", 1)[-1] for r in roots)))

    w("\n**5.1 Khối lượng theo từng bước (stage)**\n")
    w("> Cột **Token-proxy** = độ dài tài liệu sinh ra ở mỗi bước (không phải tiền). "
      "Cột **Token thật** = token LLM đã burn ở bước đó (ra tiền). Đặt cạnh nhau để thấy bước nào "
      "\"nhẹ giấy tờ nhưng tốn AI\" và ngược lại.\n")
    bk = c["buckets"]
    art_total = sum(v for k, v in bk.items())
    label = {"discovery": "Stage 1 Discovery", "architecture": "Stage 2 Architecture",
             "spec": "Stage 3 Specs", "design": "Stage 4 Design",
             "build_review": "Stage 5 Story+Review", "test_audit": "Stage 5 Test/ATDD",
             "design_system": "Design System"}
    bsm = c.get("by_stage_model") or {}
    bystage = (c.get("burn") or {}).get("by_stage") or {}
    bucket_stages = {"discovery": ["Stage_1"], "architecture": ["Stage_2", "Stage_2b"],
                     "spec": ["Stage_3"], "design": ["Stage_4"],
                     "build_review": ["Stage_5"], "test_audit": ["Stage_5"], "design_system": []}
    mcol = bool(bsm)  # chỉ thêm cột burn/Model khi có burn-log

    def bucket_models(k):
        merged = merge_models(bsm.get(st) for st in bucket_stages.get(k, []))
        return model_share(merged) if merged else "—"

    def bucket_burn(k):
        if k == "test_audit":   # burn của Stage_5 đã gộp ở dòng Story+Review → tránh đếm đôi
            return None
        stages = bucket_stages.get(k, [])
        if not stages:
            return None
        return sum((bystage.get(st) or {}).get("input", 0) + (bystage.get(st) or {}).get("output", 0)
                   for st in stages)

    def burn_cell(k):
        b = bucket_burn(k)
        return fmt_tok(b) if b is not None else "—"

    w("| Bước (stage) | Token-proxy (giấy tờ) | % giấy tờ |"
      + (" Token thật (ra tiền) | Model AI |" if mcol else ""))
    w("|---|--:|--:|" + ("--:|--:|" if mcol else ""))
    for k in ["discovery", "architecture", "spec", "design", "build_review", "test_audit", "design_system"]:
        if k not in bk:
            continue
        row = f"| {label.get(k,k)} | {fmt_tok(bk[k])} | {fmt_pct(bk[k]/art_total) if art_total else 'n/a'} |"
        w(row + (f" {burn_cell(k)} | {bucket_models(k)} |" if mcol else ""))
    tot_burn = (c.get("burn") or {}).get("total")
    tot_extra = (f" {fmt_tok(tot_burn) if tot_burn else '—'} | {model_share(c.get('by_model') or {})} |"
                 if mcol else "")
    w(f"| **Tổng tài liệu** | **{fmt_tok(art_total)}** | 100% |" + tot_extra)
    w(f"| _Code chạy thật (đã gắn id)_ | {fmt_tok(c['code_prod_tokens'])} | — |" + (" — | — |" if mcol else ""))
    w(f"| _Code test (đã gắn id)_ | {fmt_tok(c['code_test_tokens'])} | — |" + (" — | — |" if mcol else ""))
    if c["code_untagged_test_tokens"]:
        w(f"| _Code test (chưa gắn id, thư mục `tests/`)_ | {fmt_tok(c['code_untagged_test_tokens'])} | — |" + (" — | — |" if mcol else ""))
    if mcol:
        w("\n> *Vài lưu ý khi đọc bảng:*\n"
          "> - *Cột **Token thật** là tiền thật; cột **Token-proxy** chỉ là độ dài văn bản. Hai cột lệch nhau "
          "nhiều là bình thường — bước ít giấy tờ vẫn có thể tốn nhiều AI (đọc lại ngữ cảnh, thử nhiều lần).*\n"
          "> - *Dòng `Stage 5 Test/ATDD` để token-thật `—` vì phần burn đó đã gộp chung trong `Stage 5 Story+Review` "
          "(cùng một bước), ghi lại sẽ thành đếm hai lần.*\n"
          "> - *Các dòng code để `—` vì việc viết code do AI làm ngay trong bước Stage 5 rồi — không có \"bước viết code\" "
          "riêng để gán token.*\n"
          "> - ***Tổng token thật** lớn hơn tổng các dòng phía trên, vì có cả những lượt làm việc đầu phiên chưa kịp gán "
          "vào bước nào.*\n"
          "> - *`Design System` để model `—` vì không nhận diện được bước riêng cho nó.*")

    w("\n**5.2 Đầu tư bao nhiêu \"giấy tờ\" cho mỗi phần code? (token-proxy)**\n")
    w("> Mỗi tỉ lệ trả lời: cứ 1 phần code chạy thật thì kèm theo bao nhiêu phần tài liệu. **Số càng nhỏ càng gọn.** "
      "(Đây là token-proxy — đo công sức, không phải tiền.)\n")
    r = c["ratios"]
    w("| Mã | So sánh | Cách tính | Kết quả |")
    w("|---|---|---|--:|")
    w(f"| COST-2 | Thiết kế (spec+design) so với code | (Stage 3 + Stage 4) ÷ code chạy thật | **{fmt_ratio(r['spec_design_to_code'])}** |")
    w(f"| COST-3 | Kiểm thử + review so với code | (story/review + test/ATDD + code test) ÷ code chạy thật | **{fmt_ratio(r['review_test_to_code'])}** |")
    w(f"| COST-4 | Toàn bộ tài liệu so với code | tổng tài liệu ÷ code chạy thật | **{fmt_ratio(r['all_artifact_to_code'])}** |")
    w(f"| COST-5 | Quản trị/định hướng so với code | (discovery + kiến trúc + design-system) ÷ code chạy thật | {fmt_ratio(r['governance_to_code'])} |")
    w(f"| COST-6 | Tỉ lệ \"phí phạm\" do làm lại | phần tài liệu bản cũ đã thay ÷ tổng (cũ+mới) của kiến trúc & thiết kế | {fmt_pct(r['archive_waste'])} |")

    bys = c.get("by_slice") or {}
    if bys:
        w("\n**5.3 Khối lượng code theo từng lát cắt (token-proxy)**\n")
        w("> \"Code chạy thật\" so với \"code test\" của từng lát cắt; tỉ lệ test/code cao = phủ test nhiều hơn.\n")
        w("| Lát cắt | Code chạy thật | Code test | Test so với code |")
        w("|---|--:|--:|--:|")
        for sid in sorted(bys, key=lambda x: (x == "(unmapped)", x)):
            v = bys[sid]
            p, t = v.get("prod", 0), v.get("test", 0)
            name = "(chưa gán lát cắt)" if sid == "(unmapped)" else sid
            w(f"| {name} | {fmt_tok(p)} | {fmt_tok(t)} | {fmt_ratio(t/p) if p else 'n/a'} |")

    render_churn(w, data)

    w("\n**5.4 Chi phí tiền thật (token LLM đã burn)**\n")
    burn = c.get("burn")
    if not burn:
        w("> 🔴 Chưa gom được token thật (chưa có file `NTAPP-output/evaluation/token-log.json` và "
          "không đọc được nhật ký phiên Claude Code). Khi có, phần này sẽ tự tính tổng chi phí $, "
          "chi phí cho mỗi tiêu chí nghiệm thu, và hệ số \"khuếch đại\".")
    else:
        cov = burn.get("coverage") or {}
        lvl = cov.get("level")
        if lvl == "partial":
            w(f"> ⚠️ **Độ phủ nhật ký phiên thấp (G2) — burn dưới đây là CẬN DƯỚI, không phải con số đủ.** "
              f"Phiên Claude Code chỉ trải **{cov.get('session_min')} → {cov.get('session_max')}**, "
              f"trong khi commit git của code repo trải **{cov.get('git_first')} → {cov.get('git_last')}** "
              f"({cov.get('git_commits')} commit). Phủ ~{fmt_pct(cov.get('ratio'))} khoảng hoạt động → "
              "nhiều phiên (chạy máy khác / đã xoá / không gom đủ) **thiếu**. Mọi con số $/token bên dưới "
              "là **một phần**, KHÔNG dùng để so sánh giữa dự án.\n")
        elif lvl == "full":
            w(f"> ✅ Độ phủ nhật ký phiên đủ (G2): phiên **{cov.get('session_min')} → {cov.get('session_max')}** "
              f"phủ ~{fmt_pct(cov.get('ratio'))} khoảng commit git "
              f"(**{cov.get('git_first')} → {cov.get('git_last')}**, {cov.get('git_commits')} commit).\n")
        elif cov:  # unknown — thiếu mốc git hoặc mốc phiên → nói rõ chưa kiểm chứng được
            w("> ℹ️ Chưa kiểm chứng được độ phủ nhật ký phiên (G2): thiếu mốc git của code repo hoặc "
              "thiếu mốc thời gian phiên → không khẳng định burn đã gom **đủ**. Hãy coi là cận dưới cho tới khi đối chiếu được.\n")
        comp, cost = burn.get("components"), burn.get("cost_usd")
        cbm = burn.get("cost_by_model")
        priced_pm = burn.get("cost_priced_per_model")
        if comp and cost:
            tot_tok = sum(comp.values())
            tot_usd = burn["cost_total_usd"]
            if priced_pm:
                w("> Token thật chia làm 4 loại; **đơn giá theo TỪNG model** (Opus/Sonnet/Haiku khác nhau — "
                  "chi tiết ở bảng 5.4b). Quy ước cache giống nhau mọi model: **ghi cache = 1.25× input** "
                  "(lưu ngữ cảnh, TTL 5 phút), **đọc cache = 0.1× input** (rẻ bằng 1/10), **output** đắt nhất "
                  "(= 5× input). Cột \"Đơn giá TB\" bên dưới là bình quân gia quyền theo cơ cấu model.\n")
            else:
                w("> Token thật chia làm 4 loại, đơn giá khác nhau (theo bảng giá Claude API, model "
                  f"**{PRICING_MODEL}**, tính trên 1 triệu token):\n"
                  f">  - **Input mới**: ${PRICE_PER_MTOK['input']:.2f} — phần ngữ cảnh gửi lần đầu.\n"
                  f">  - **Ghi cache**: ${PRICE_PER_MTOK['cache_write']:.2f} — lưu ngữ cảnh để tái dùng (đắt hơn input 1.25×).\n"
                  f">  - **Đọc cache**: ${PRICE_PER_MTOK['cache_read']:.2f} — đọc lại ngữ cảnh đã lưu (rẻ, bằng 1/10 input).\n"
                  f">  - **Output**: ${PRICE_PER_MTOK['output']:.2f} — phần AI sinh ra (đắt nhất).\n")
            unit_hdr = "Đơn giá TB ($/1M)" if priced_pm else "Đơn giá ($/1 triệu)"
            w(f"| Loại token | Số token | {unit_hdr} | Thành tiền | % chi phí |")
            w("|---|--:|--:|--:|--:|")
            rows = [
                ("Input mới (chưa cache)", "input"),
                ("Ghi cache", "cache_write"),
                ("Đọc cache", "cache_read"),
                ("Output (AI sinh ra)", "output"),
            ]
            for label, key in rows:
                pct = (cost[key] / tot_usd) if tot_usd else 0
                # per-model: đơn giá là bình quân hiệu dụng (tiền ÷ token); phẳng: giá cứng
                unit = (cost[key] / comp[key] * 1_000_000) if (priced_pm and comp[key]) \
                    else PRICE_PER_MTOK[key]
                w(f"| {label} | {fmt_tok(comp[key])} | {unit:.2f} | "
                  f"${cost[key]:,.2f} | {round(100*pct)}% |")
            w(f"| **Tổng cộng** | **{fmt_tok(tot_tok)}** | — | **${tot_usd:,.2f}** | 100% |")
            w("")
            if cbm:
                w("\n**5.4b Chi phí theo model AI**\n")
                w("> Mỗi model một đơn giá (Opus 4.8 $5/$25, Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5 — "
                  "input/output trên 1 triệu token). Sub-agent thường chạy model rẻ (Haiku) → tách ra để "
                  "thấy đúng cơ cấu tiền, không quy hết về Opus.\n")
                w("| Model | Input mới | Ghi cache | Đọc cache | Output | Tổng token | Thành tiền | % chi phí |")
                w("|---|--:|--:|--:|--:|--:|--:|--:|")
                for m in cbm:
                    cm = m["components"]
                    pct = (m["cost_total_usd"] / tot_usd) if tot_usd else 0
                    w(f"| {m['label']} | {fmt_tok(cm['input'])} | {fmt_tok(cm['cache_write'])} | "
                      f"{fmt_tok(cm['cache_read'])} | {fmt_tok(cm['output'])} | {fmt_tok(m['tokens_total'])} | "
                      f"${m['cost_total_usd']:,.2f} | {round(100*pct)}% |")
                w(f"| **Tổng** | | | | | **{fmt_tok(sum(m['tokens_total'] for m in cbm))}** | "
                  f"**${tot_usd:,.2f}** | 100% |")
                w("")
        lb = " **(một phần — cận dưới)**" if (burn.get("coverage") or {}).get("lower_bound") else ""
        w(f"- **Tổng token thật đã burn**: {fmt_tok(burn['total'])} token{lb} "
          f"(gồm input {fmt_tok(burn.get('input') or 0)} + output {fmt_tok(burn.get('output') or 0)})")
        if burn.get("cost_total_usd") is not None:
            _basis = "định giá theo từng model" if burn.get("cost_priced_per_model") \
                else f"đơn giá {PRICING_MODEL}"
            w(f"- **Tổng chi phí tiền thật: ${burn['cost_total_usd']:,.2f}** ({_basis})")
        w(f"- **Chi phí cho mỗi tiêu chí nghiệm thu (AC)**: "
          f"{fmt_tok(burn['per_ac']) if burn['per_ac'] else 'n/a'} token/AC")
        w(f"- **Hệ số khuếch đại**: {fmt_ratio(burn['amplification'])} — cứ mỗi 1 token \"sản phẩm cuối\" "
          f"({fmt_tok(c['delivered_tokens'])} token-proxy) thì AI thực sự xử lý chừng đó token. "
          "Phần lớn là đọc lại ngữ cảnh và thử lại — bình thường với quy trình nhiều bước.")


def render_churn(w, data):
    """§5.3b — LOC committed (added/deleted) + tỉ lệ sửa-đi-sửa-lại tầng code (EFFY-3b)."""
    ch = data.get("code_churn") or {}
    w("\n**5.3b Sửa đi sửa lại ở tầng code — LOC đã commit (EFFY-3b)**\n")
    if not ch.get("available"):
        w("> 🔴 Chưa đọc được lịch sử git của code repo (không tìm thấy repo, hoặc `git` không chạy được). "
          "Khi có, phần này tự tính số dòng code đã thêm/xoá và tỉ lệ \"viết rồi xoá\".\n")
        return
    pr, te, ot = ch["prod"], ch["test"], ch["other"]
    w("> Đếm trực tiếp từ `git log --numstat` của code repo (đo **dòng chảy commit**, khác với token-proxy ở "
      "trên đo **trạng thái file cuối**). Cột **+/−** là số dòng tuyệt đối đã thêm/xoá qua toàn bộ lịch sử. "
      "**Tỉ lệ thrash** = (thêm+xoá) ÷ số dòng prod còn sống = bao nhiêu dòng phải viết để giữ lại 1 dòng "
      "(**1.0 = không phí**; càng cao càng viết-rồi-xoá nhiều).\n")
    w(f"> Quét **{ch['commits']}** commit.\n")
    w("| Loại code | Dòng thêm (+) | Dòng xoá (−) | Dòng còn sống | Tỉ lệ thrash |")
    w("|---|--:|--:|--:|--:|")
    w(f"| **Code chạy thật (prod, đã gắn id)** | +{pr['added']:,} | −{pr['deleted']:,} | "
      f"{pr['net_loc']:,} | **{fmt_ratio(pr['churn_ratio'])}** |")
    w(f"| Code test | +{te['added']:,} | −{te['deleted']:,} | — | — |")
    w(f"| Khác (đã xoá / chưa gắn id) | +{ot['added']:,} | −{ot['deleted']:,} | — | — |")
    bys = ch.get("by_slice") or {}
    if bys:
        w("\n*Phân theo lát cắt (chỉ file prod đã gắn id còn trên đĩa):*\n")
        w("| Lát cắt | Dòng thêm (+) | Dòng xoá (−) |")
        w("|---|--:|--:|")
        for sid in sorted(bys, key=lambda x: (x == "(unmapped)", x)):
            v = bys[sid]
            name = "(chưa gán lát cắt)" if sid == "(unmapped)" else sid
            w(f"| {name} | +{v['added']:,} | −{v['deleted']:,} |")
    w("\n> *Lưu ý:* commit ĐẦU TIÊN của dự án dựng-lại (brownfield) dồn cả codebase cũ vào một lần → cột "
      "**+** phình to nhưng **−**≈0 nên tỉ lệ thrash vẫn ~1.0 (không bị thổi). Dòng \"Khác\" gom churn của file "
      "đã bị xoá hẳn (không còn header để quy về prod/slice) — đây là giới hạn attribution, không phải lỗi.\n")


def next_round(archive_dir):
    """Lần đánh giá kế tiếp = max version đã archive + 1 (snapshot history)."""
    vs = []
    if archive_dir.exists():
        for f in archive_dir.glob("scorecard-v*.md"):
            m = re.match(r"scorecard-v(\d+)\.md$", f.name)
            if m:
                vs.append(int(m.group(1)))
    return max(vs, default=0) + 1


def main():
    import argparse
    ap = argparse.ArgumentParser(description="NTAPP eval harvester (gồm token-burn từ session JSONL)")
    ap.add_argument("--refresh-burn", action="store_true",
                    help="re-harvest token-log.json từ session JSONL (mặc định: auto-harvest nếu chưa có, "
                         "dùng cached nếu đã có)")
    args = ap.parse_args()
    data = build(refresh_burn=args.refresh_burn)

    archive_dir = OUT_DIR / "archive"
    run_meta = {"date": datetime.date.today().isoformat(), "round": next_round(archive_dir)}
    data["_run_meta"] = run_meta

    metrics_json = json.dumps(data, ensure_ascii=False, indent=2)
    scorecard_md = render_scorecard(data, run_meta)

    # Dual-write: canonical (latest, overwrite) + archive (snapshot version mới mỗi run)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "metrics.json").write_text(metrics_json, encoding="utf-8")
    (OUT_DIR / "scorecard.md").write_text(scorecard_md, encoding="utf-8")
    archive_dir.mkdir(parents=True, exist_ok=True)
    v = run_meta["round"]
    (archive_dir / f"metrics-v{v}.json").write_text(metrics_json, encoding="utf-8")
    (archive_dir / f"scorecard-v{v}.md").write_text(scorecard_md, encoding="utf-8")

    t = data["totals"]
    print(f"[eval-harvester] slices={len(data['slices'])} units={len(data['units'])} "
          f"defers={t['defer_count']} (avoidable={t['defer_avoidable']}) "
          f"F-FPY={fmt_pct(t['fpy'])} (func-patch={t['functional_patch']}/excl={t['patch_excluded']}"
          f"/uncl={t['patch_unclassified']}; SFPY={fmt_pct(t['sfpy'])})")
    c = data["cost"]
    print(f"[eval-harvester] cost-proxy: code-prod={fmt_tok(c['code_prod_tokens'])}tok "
          f"spec+design:code={fmt_ratio(c['ratios']['spec_design_to_code'])} "
          f"test+review:code={fmt_ratio(c['ratios']['review_test_to_code'])} "
          f"all-artifact:code={fmt_ratio(c['ratios']['all_artifact_to_code'])} "
          f"(burn={'logged' if c['burn'] else 'n/a'})")
    bym = c.get("by_model") or {}
    if bym:
        print(f"[eval-harvester] models: {model_share(bym)}")
    print(f"[eval-harvester] đánh giá #{run_meta['round']} ({run_meta['date']})")
    print(f"[eval-harvester] canonical → {OUT_DIR/'scorecard.md'} + metrics.json")
    print(f"[eval-harvester] archive   → {archive_dir}/scorecard-v{v}.md + metrics-v{v}.json")


if __name__ == "__main__":
    sys.exit(main())
