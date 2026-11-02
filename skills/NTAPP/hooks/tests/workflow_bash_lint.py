#!/usr/bin/env python3
"""Lint bash node trong VSAF workflow — chặn 4 lớp lỗi "hỏng mà không kêu".

Vì sao cần: cả 3 lỗi tìm được ngày 2026-08-14 (path-b input-gate không parse nổi args,
slice-shippable-gate không bao giờ nổ, express test-gate test nhầm repo) đều KHÔNG làm
workflow báo lỗi — nó chạy tiếp và báo xanh. Không có gì ngăn workflow thứ tư mắc lại,
nên chuyển hợp đồng engine thành test chạy được. Luật D thêm sau đó, khi bug-fix-batch
đúng là workflow thứ tư mắc phải một lỗi cùng họ (cổng HITL chết trên dash).

4 luật:
  A. Trong `bash:` node, $ARGUMENTS bị engine shell-escape sẵn (macOS/Linux bọc dấu ', Windows
     bọc dấu "). Chỉ được gán BARE (`var=$ARGUMENTS`) rồi dùng biến — dạng bare đúng trên cả hai
     nền tảng. Tự bọc quote hoặc ghép thẳng vào chuỗi → giá trị mang theo dấu nháy → so sánh/đường
     dẫn lệch âm thầm trên POSIX, và trên Windows thì biến rỗng + phần sau dấu | chạy như lệnh.
  B. Bash node không có biến WORKSPACE (engine chỉ truyền ARTIFACTS_DIR). `cd "$WORKSPACE"`
     không báo lỗi, chỉ lặng lẽ ở nguyên chỗ cũ.
  C. Node thiếu `workspace: false` chạy trong worktree fork của SPEC repo. Node đụng
     git/test/build mà thiếu cờ này là đang thao tác nhầm repo.
  D. Bash node chạy bằng /bin/sh (engine không truyền option `shell` trên macOS/Linux).
     macOS /bin/sh là bash nên `set -o pipefail` / `set -u` chạy được, nhưng Debian/Ubuntu
     /bin/sh là dash → "Illegal option -o pipefail", script chết ngay dòng 1. Với node cổng
     HITL thì nghĩa là cổng không bao giờ qua được, và thông báo lỗi chẳng chỉ về đâu.

Mẫu đúng để đối chiếu: staging-deploy/feature-integration-gate.
Thư mục tests/ được bỏ qua: fixture ở đó cố tình viết sai để chứng minh hành vi engine.

Chạy: python3 hooks/tests/workflow_bash_lint.py [workflow_root]
Exit 0 = sạch, 1 = có vi phạm.
"""
import glob
import os
import re
import sys

BARE_ASSIGN = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*=\$ARGUMENTS\s*$")
ARGS_ANY = re.compile(r"\$\{?ARGUMENTS\}?")
WORKSPACE_VAR = re.compile(r"\$\{?WORKSPACE\}?")
REPO_CMD = re.compile(r"(^|\s)(git|npm|yarn|pnpm|pytest|mvn|gradle|\./gradlew|cargo|dotnet)\s"
                      r"|(^|\s)go\s+test\b")
# `set` với option chỉ có ở bash/ksh. dash (= /bin/sh trên Debian/Ubuntu) bỏ cả `-o pipefail` lẫn `-u`.
# Bắt cả dạng gộp (`set -euo pipefail`) lẫn dạng tách (`set -o pipefail`, `set -u`).
DASH_UNSAFE = re.compile(r"^\s*set\s+(-[a-zA-Z]*[uo][a-zA-Z]*\b|-o\s+pipefail\b)")
ALLOW_PRAGMA = "workflow-bash-lint: allow"


def load_nodes(path):
    """Đọc node bằng parser thụt lề tối giản — không phụ thuộc pyyaml."""
    import yaml
    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh) or {}
    return doc.get("nodes") or []


def lint_file(path):
    problems = []
    for node in load_nodes(path):
        if not isinstance(node, dict) or "bash" not in node:
            continue
        body = node["bash"] or ""
        nid = node.get("id", "<no-id>")
        if ALLOW_PRAGMA in body:
            continue

        for lineno, line in enumerate(body.splitlines(), 1):
            code = line.split("#", 1)[0]
            if not ARGS_ANY.search(code):
                continue
            if BARE_ASSIGN.match(code):
                continue
            problems.append((
                nid, lineno,
                "$ARGUMENTS dùng trực tiếp trong bash node — engine đã shell-escape sẵn. "
                "Gán bare trước (vd `slice=$ARGUMENTS`) rồi dùng biến.",
                line.strip()))

        for lineno, line in enumerate(body.splitlines(), 1):
            code = line.split("#", 1)[0]
            if WORKSPACE_VAR.search(code):
                problems.append((
                    nid, lineno,
                    "$WORKSPACE không tồn tại trong bash node (engine chỉ truyền ARTIFACTS_DIR). "
                    "Đặt workspace:false rồi cd vào repo đọc từ state file.",
                    line.strip()))

        for lineno, line in enumerate(body.splitlines(), 1):
            if DASH_UNSAFE.match(line.split("#", 1)[0]):
                problems.append((
                    nid, lineno,
                    "`set -u` / `set -o pipefail` không chạy trên dash — mà /bin/sh trên Debian/Ubuntu "
                    "chính là dash, và engine không truyền option `shell`. Script chết ngay dòng này với "
                    "\"Illegal option -o pipefail\". Kiểm tra tường minh bằng if/exit thay thế.",
                    line.strip()))

        if node.get("workspace", True) and REPO_CMD.search(body):
            problems.append((
                nid, 0,
                "node chạy lệnh git/test/build nhưng thiếu `workspace: false` — nó sẽ chạy trong "
                "worktree fork của SPEC repo, không phải code repo.",
                ""))
    return problems


def main():
    # `--strict` → mọi workflow đều gate. Mặc định chỉ workflow NTAPP (thứ ta sở hữu) mới làm fail;
    # workflow scaffold bên thứ ba (sdlc/… do sdlc-init sinh) chỉ cảnh báo — cùng lỗi nhưng sửa nó là
    # sửa template của người khác, phải là quyết định riêng chứ không nên chặn suite của team.
    argv = [a for a in sys.argv[1:] if a != "--strict"]
    strict = "--strict" in sys.argv
    root = argv[0] if argv else ".vsaf/workflows"
    files = [f for f in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True))
             if f"{os.sep}tests{os.sep}" not in f]
    if not files:
        print(f"workflow-bash-lint: không thấy workflow nào dưới {root}")
        return 1

    errors = warnings = 0
    for path in files:
        owned = strict or f"{os.sep}NTAPP{os.sep}" in path
        try:
            problems = lint_file(path)
        except Exception as exc:                      # YAML hỏng cũng là lỗi cần biết
            print(f"  {path}: KHÔNG PARSE ĐƯỢC — {exc}")
            errors += 1
            continue
        for nid, lineno, msg, snippet in problems:
            tag = "LỖI " if owned else "cảnh báo"
            where = f"{path} :: {nid}" + (f" (dòng {lineno} của bash)" if lineno else "")
            print(f"  [{tag}] {where}\n      {msg}")
            if snippet:
                print(f"      > {snippet}")
            if owned:
                errors += 1
            else:
                warnings += 1

    if warnings:
        print(f"workflow-bash-lint: {warnings} cảnh báo ngoài NTAPP (workflow bên thứ ba — "
              f"cùng lỗi, dùng --strict để gate cả chúng)")
    if errors:
        print(f"workflow-bash-lint: {errors} vi phạm trong workflow NTAPP")
        return 1
    print(f"workflow-bash-lint: NTAPP sạch ({len(files)} workflow đã quét)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
