from __future__ import annotations
import re
from pathlib import Path

# Marker máy-đọc (tùy chọn, do bước SDLC/SRS stamp nếu áp dụng) → auto APPROVED.
_MARKER = re.compile(r"vsaf[:-]gate\s*[=:]\s*(?:APPROVED|GO)\b", re.IGNORECASE)
# Dòng có dấu hiệu gate/verdict — TRÍCH cho NGƯỜI xác nhận (KHÔNG tự quyết định).
_GATE_HINT = re.compile(
    r"(?im)^.*\b(?:gate|verdict|kết luận|ket luan|trạng thái|trang thai|"
    r"mức độ|muc do|readiness|approved|no[\s-]*go|go|reject(?:ed)?|not\s+approved|draft)\b.*$"
)


def is_template_repo(cwd: Path) -> bool:
    """True nếu đang chạy trong template repo rf-agentskills (guard)."""
    return (Path(cwd) / "IS_TEMPLATE_REPO").exists()


def resolve_srs(feature: str, srs_root: Path) -> Path:
    """Trả path <srs_root>/<feature>/05-srs.md; raise FileNotFoundError nếu thiếu."""
    p = Path(srs_root) / feature / "05-srs.md"
    if not p.is_file():
        raise FileNotFoundError(f"SRS không tồn tại cho feature '{feature}': {p}")
    return p


def _read_with_report(srs_path: Path) -> str:
    text = Path(srs_path).read_text(encoding="utf-8")
    report = Path(srs_path).with_name("05-srs-validation-report.md")
    if report.is_file():
        text += "\n" + report.read_text(encoding="utf-8")
    return text


def extract_gate_context(srs_path: Path, max_lines: int = 12) -> str:
    """Trả các dòng có dấu hiệu gate/verdict (unique, giữ thứ tự) để NGƯỜI xác nhận. '' nếu không thấy."""
    text = _read_with_report(srs_path)
    seen: set[str] = set()
    out: list[str] = []
    for m in _GATE_HINT.finditer(text):
        ln = m.group(0).strip()
        if ln and ln not in seen:
            seen.add(ln)
            out.append(ln)
        if len(out) >= max_lines:
            break
    return "\n".join(out)


def gate_status(srs_path: Path) -> tuple[str, str]:
    """('APPROVED_MARKER','') nếu có marker máy-đọc; ('NEEDS_CONFIRM', <context>) nếu không.
    KHÔNG tự accept/reject theo prose — SRS thật không có field gate đáng tin (over-accept / false-reject)."""
    if _MARKER.search(_read_with_report(srs_path)):
        return ("APPROVED_MARKER", "")
    return ("NEEDS_CONFIRM", extract_gate_context(srs_path))


def write_traceability(feature: str, vsaf_root: Path, tc_paths: list[str],
                       suite_paths: list[str], jenkins_job: str | None = None) -> Path:
    """Ghi con trỏ traceability .vsaf/docs/features/<feature>/e2e/README.md. Trả path đã ghi."""
    out_dir = Path(vsaf_root) / ".vsaf" / "docs" / "features" / feature / "e2e"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "README.md"
    lines = [f"# E2E traceability — {feature}", "",
             "> Sinh bởi stage `sdlc-e2e` (không commit). SRS → E2E TC → suite → CI.", "",
             "## Test cases", *[f"- `{p}`" for p in tc_paths],
             "", "## Robot suites", *[f"- `{p}`" for p in suite_paths]]
    if jenkins_job:
        lines += ["", "## CI", f"- Jenkins job: `{jenkins_job}`"]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="vsaf-e2e-bridge")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("feature"); c.add_argument("--srs-root", required=True); c.add_argument("--cwd", default=".")
    t = sub.add_parser("trace")
    t.add_argument("feature"); t.add_argument("--vsaf-root", required=True)
    t.add_argument("--tc", action="append", default=[]); t.add_argument("--suite", action="append", default=[])
    t.add_argument("--jenkins", default=None)
    ns = ap.parse_args(argv)
    if ns.cmd == "check":
        try:
            if is_template_repo(Path(ns.cwd)):
                print("STOP: đang ở trong template repo"); return 2
            srs = resolve_srs(ns.feature, Path(ns.srs_root))
        except FileNotFoundError as e:
            print(f"STOP: {e}"); return 2
        status, ctx = gate_status(srs)
        print(f"GATE: {status}")
        print(f"SRS: {srs}")
        if status == "NEEDS_CONFIRM":
            print("--- gate context (cần người xác nhận) ---")
            print(ctx or "(không thấy dòng gate/verdict — SRS có thể chưa ghi gate)")
        return 0
    if ns.cmd == "trace":
        out = write_traceability(ns.feature, Path(ns.vsaf_root), ns.tc, ns.suite, ns.jenkins)
        print(f"WROTE: {out}"); return 0
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(_main())
