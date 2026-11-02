# -*- coding: utf-8 -*-
"""Tao pull request tren Bitbucket Server cho 1 hoac nhieu repo.

Nguyen tac: PR chi phan anh nhung gi DA PUSH len remote. Moi phep so sanh deu
dung origin/<source> va origin/<target>, khong bao gio dung HEAD local. Commit
chua push va thay doi chua commit se bi bo qua (co canh bao), khong tu push.

Credential doc tu env.md, block Bitbucket duoc xac dinh theo URL hint.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BITBUCKET_URL_HINT = "bitbucket.digital.vn"

DEFAULT_ENV_PATHS = [
    os.path.join(os.getcwd(), "env.md"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "env.md"),
    os.path.join(os.path.expanduser("~"), ".env", "env.md"),
    os.path.join(os.path.expanduser("~"), "Documents", ".env", "env.md"),
    os.path.join(os.path.expanduser("~"), "env.md"),
]

# Remote URL -> (host, project key, repo slug). Ho tro ca HTTP(S) va SSH.
RE_HTTP = re.compile(r"^https?://(?:[^@/]+@)?([^/]+)/scm/([^/]+)/(.+?)(?:\.git)?/?$", re.I)
RE_SSH = re.compile(r"^(?:ssh://)?git@([^:/]+)(?::\d+)?[:/](?:.*?/)?([^/]+)/(.+?)(?:\.git)?/?$", re.I)


def log(msg):
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def git(repo, *args, check=True):
    """Chay lenh git trong repo. Tra ve (exit_code, stdout)."""
    proc = subprocess.run(
        ["git", "-C", repo] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    out = proc.stdout.decode("utf-8", "replace").strip()
    if check and proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError("git " + " ".join(args) + " that bai: " + err[:300])
    return proc.returncode, out


# --------------------------------------------------------------------------
# Credential
# --------------------------------------------------------------------------

def find_env_path(explicit):
    if explicit:
        if os.path.isfile(explicit):
            return explicit
        raise SystemExit("Khong tim thay env file: " + explicit)
    for p in DEFAULT_ENV_PATHS:
        if os.path.isfile(p):
            return p
    raise SystemExit(
        "Khong tim thay env.md. Truyen --env <path>. Da thu: " + ", ".join(DEFAULT_ENV_PATHS)
    )


def load_credentials(env_path):
    """Lay credential trong block Bitbucket cua env.md.

    env.md thuong chua NHIEU block (Confluence, Jira, Grafana, Bitbucket) va moi
    block deu co dong 'token:'. Bat buoc phai gioi han theo header chua URL hint,
    neu khong se lay nham token cua he thong khac va nhan HTTP 401 luc POST.
    """
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    username = password = token = None
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            in_block = BITBUCKET_URL_HINT in stripped.lower()
            continue
        if not in_block:
            continue
        m = re.match(r"(?i)\s*username\s*[:=]\s*(.+)", stripped)
        if m:
            username = m.group(1).strip()
            continue
        m = re.match(r"(?i)\s*(?:pass(?:word)?)\s*[:=]\s*(.+)", stripped)
        if m:
            password = m.group(1).strip()
            continue
        m = re.match(r"(?i)\s*token\s*[:=]\s*(.+)", stripped)
        if m:
            token = m.group(1).strip()
            continue

    if token:
        return "Bearer " + token
    if username and password:
        raw = (username + ":" + password).encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")
    raise SystemExit(
        "Khong tim thay credential Bitbucket trong " + env_path
        + ". Can mot header chua '" + BITBUCKET_URL_HINT + "' kem 'token:' hoac 'Username:'/'Pass:'."
    )


# --------------------------------------------------------------------------
# REST API
# --------------------------------------------------------------------------

def api(auth, url, payload=None):
    data = None
    headers = {"Authorization": auth, "Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers)
    try:
        return json.loads(urlopen(req, timeout=60).read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            msgs = "; ".join(x.get("message", "") for x in json.loads(body).get("errors", []))
        except Exception:
            msgs = body[:300]
        raise RuntimeError("HTTP " + str(e.code) + ": " + (msgs or body[:300]))
    except URLError as e:
        raise RuntimeError("Khong ket noi duoc " + url + " (" + str(e.reason) + ")")


def parse_remote(url):
    for rx in (RE_HTTP, RE_SSH):
        m = rx.match(url.strip())
        if m:
            return m.group(1), m.group(2), m.group(3)
    return None, None, None


# --------------------------------------------------------------------------
# Phat hien repo
# --------------------------------------------------------------------------

def is_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))


def repo_root(path):
    code, out = git(path, "rev-parse", "--show-toplevel", check=False)
    return out if code == 0 else None


def discover_repos(start):
    """Tra ve danh sach repo trong workspace.

    Workspace = thu muc cha cua repo hien tai, neu no chua tu 2 git repo tro len.
    Nguoc lai chi tra ve chinh repo hien tai.
    """
    root = repo_root(start)
    if not root:
        raise SystemExit("Thu muc hien tai khong nam trong git repo: " + start)
    parent = os.path.dirname(root)
    siblings = []
    try:
        for name in sorted(os.listdir(parent)):
            p = os.path.join(parent, name)
            if os.path.isdir(p) and is_git_repo(p):
                siblings.append(os.path.abspath(p))
    except OSError:
        siblings = []
    if len(siblings) >= 2:
        return siblings
    return [os.path.abspath(root)]


# --------------------------------------------------------------------------
# Xu ly tung repo
# --------------------------------------------------------------------------

class Result:
    def __init__(self, repo, status, detail, url=None, warns=None,
                 commits=None, stat=None, path=None, pr_id=None, rng=None):
        self.repo = repo
        self.status = status          # CREATED | SKIP | DRYRUN | ERROR
        self.detail = detail
        self.url = url
        self.warns = warns or []
        self.commits = commits or []  # tieu de commit, nguyen lieu de tom tat
        self.stat = stat or []        # dong diffstat theo file
        self.path = path              # duong dan repo, de doc dien diff sau
        self.pr_id = pr_id
        self.rng = rng            # khoang diff de doc lai chi tiet


def remote_branch_exists(repo, branch):
    code, _ = git(repo, "rev-parse", "--verify", "--quiet", "refs/remotes/origin/" + branch, check=False)
    return code == 0


def process_repo(repo, args, auth):
    name = os.path.basename(repo)
    warns = []

    code, _ = git(repo, "remote", "get-url", "origin", check=False)
    if code != 0:
        return Result(name, "SKIP", "khong co remote origin")
    _, remote_url = git(repo, "remote", "get-url", "origin")
    host, project, slug = parse_remote(remote_url)
    if not host or BITBUCKET_URL_HINT not in host.lower():
        return Result(name, "SKIP", "remote khong phai Bitbucket (" + remote_url + ")")

    # Fetch co the that bai vi ten nhanh khong hop le tren Windows, nhung cac ref
    # khac van duoc cap nhat, nen chi canh bao roi di tiep.
    code, _ = git(repo, "fetch", "origin", "--prune", check=False)
    if code != 0:
        warns.append("git fetch bao loi (co the do ten nhanh remote khong hop le); van dung ref da co")

    source = args.source
    if not source:
        _, source = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        if source == "HEAD":
            return Result(name, "SKIP", "dang o detached HEAD, khong xac dinh duoc nhanh nguon")
    target = args.target

    if source == target:
        return Result(name, "SKIP", "nhanh nguon trung nhanh dich (" + source + ")")
    if not remote_branch_exists(repo, source):
        return Result(name, "SKIP", "nhanh nguon chua duoc push len remote: " + source)
    if not remote_branch_exists(repo, target):
        return Result(name, "SKIP", "remote khong co nhanh dich: " + target)

    # So sanh REMOTE voi REMOTE - PR chi chua nhung gi da push.
    _, ahead = git(repo, "rev-list", "--count", "origin/" + target + "..origin/" + source)
    if ahead == "0":
        return Result(name, "SKIP", "khong co commit moi so voi " + target + " (PR se rong)")

    # Canh bao phan KHONG nam trong PR.
    _, dirty = git(repo, "status", "--porcelain")
    if dirty:
        warns.append(str(len(dirty.splitlines())) + " file thay doi chua commit - KHONG nam trong PR")
    code, local_head = git(repo, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    if code == 0 and local_head == source:
        _, unpushed = git(repo, "rev-list", "--count", "origin/" + source + "..HEAD", check=False)
        if unpushed and unpushed != "0":
            warns.append(unpushed + " commit da commit nhung CHUA PUSH - KHONG nam trong PR")

    base = "http://" + host + "/rest/api/1.0/projects/" + project + "/repos/" + slug
    prs = base + "/pull-requests"

    # Chong tao trung. Luu y: tham so 'at' chi hoat dong khi di kem
    # direction=OUTGOING; thieu direction se tra ve rong va sinh PR trung.
    existing = api(auth, prs + "?state=OPEN&direction=OUTGOING&limit=50&at=refs/heads/" + source)
    for p in existing.get("values", []):
        if p["toRef"]["displayId"] == target:
            url = "http://" + host + "/projects/" + project + "/repos/" + slug + "/pull-requests/" + str(p["id"])
            return Result(name, "SKIP", "da co PR mo #" + str(p["id"]), url, warns)

    _, subjects = git(repo, "log", "--format=%s", "origin/" + target + ".." + "origin/" + source)
    commits = [s for s in subjects.splitlines() if s.strip()]
    title = args.title or (commits[0] if len(commits) == 1
                           else source + " -> " + target + " (" + ahead + " commit)")
    nl = chr(10)
    desc = ("## Noi dung" + nl + nl
            + nl.join("- " + c for c in commits) + nl + nl
            + "## Nhanh" + nl + nl + "`" + source + "` -> `" + target + "`" + nl)

    # Nguyen lieu de nguoi goi tom tat thay doi (script khong tu dien giai code).
    rng = "origin/" + target + "..." + "origin/" + source
    _, statout = git(repo, "diff", "--stat", rng, check=False)
    stat = [s.strip() for s in statout.splitlines() if s.strip()]

    if args.dry_run:
        return Result(name, "DRYRUN", ahead + " commit: " + source + " -> " + target,
                      None, warns, commits, stat, repo, None, rng)

    created = api(auth, prs, {
        "title": title,
        "description": desc,
        "fromRef": {"id": "refs/heads/" + source,
                    "repository": {"slug": slug, "project": {"key": project}}},
        "toRef": {"id": "refs/heads/" + target,
                  "repository": {"slug": slug, "project": {"key": project}}},
    })
    pid = created["id"]
    url = created["links"]["self"][0]["href"]

    try:
        merge = api(auth, prs + "/" + str(pid) + "/merge")
        if merge.get("conflicted"):
            warns.append("PR CO CONFLICT voi " + target + " - can giai quyet truoc khi merge")
        for v in merge.get("vetoes") or []:
            warns.append("veto: " + str(v.get("summaryMessage")))
    except RuntimeError:
        pass

    return Result(name, "CREATED", "#" + str(pid) + " (" + ahead + " commit)", url, warns,
                  commits, stat, repo, pid, rng)


def merge_pr(repo, pr_id, auth):
    """Merge DUNG MOT pull request. Khong co che do merge hang loat.

    Moi lan goi chi cham toi mot PR duoc chi dinh tuong minh bang --pr, de viec
    phe duyet luon la quyet dinh rieng cua tung repo.
    """
    _, remote_url = git(repo, "remote", "get-url", "origin")
    host, project, slug = parse_remote(remote_url)
    if not host:
        raise SystemExit("Khong doc duoc remote Bitbucket cua " + repo)
    base = "http://" + host + "/rest/api/1.0/projects/" + project + "/repos/" + slug
    prs = base + "/pull-requests/" + str(pr_id)

    pr = api(auth, prs)
    if pr.get("state") != "OPEN":
        raise SystemExit("PR #" + str(pr_id) + " dang o trang thai "
                         + str(pr.get("state")) + ", khong merge duoc.")

    check = api(auth, prs + "/merge")
    if check.get("conflicted"):
        raise SystemExit("PR #" + str(pr_id) + " dang CONFLICT voi nhanh dich. "
                         "Giai quyet conflict truoc, script nay khong tu merge nguoc.")
    if not check.get("canMerge"):
        reasons = "; ".join(str(v.get("summaryMessage")) for v in (check.get("vetoes") or []))
        raise SystemExit("PR #" + str(pr_id) + " chua duoc phep merge. " + (reasons or ""))

    merged = api(auth, prs + "/merge?version=" + str(pr["version"]), payload={})
    log("[MERGED] " + os.path.basename(repo) + " - PR #" + str(pr_id)
        + " -> " + merged.get("toRef", {}).get("displayId", "?"))
    return 0


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Tao pull request Bitbucket cho 1 hoac nhieu repo")
    ap.add_argument("--source", help="Nhanh nguon (mac dinh: nhanh hien tai cua tung repo)")
    ap.add_argument("--target", default="staging", help="Nhanh dich (mac dinh: staging)")
    ap.add_argument("--repo", action="append", help="Chi xu ly repo nay (lap lai duoc)")
    ap.add_argument("--cwd-only", action="store_true", help="Chi repo hien tai, khong quet workspace")
    ap.add_argument("--title", help="Tieu de PR (mac dinh sinh tu commit)")
    ap.add_argument("--env", help="Duong dan env.md")
    ap.add_argument("--dry-run", action="store_true", help="Chi bao cao, khong tao PR")
    ap.add_argument("--merge", action="store_true",
                    help="Merge DUNG MOT PR (bat buoc di kem --repo va --pr)")
    ap.add_argument("--pr", help="So hieu PR can merge")
    args = ap.parse_args()

    auth = load_credentials(find_env_path(args.env))

    if args.merge:
        if not args.pr or not args.repo or len(args.repo) != 1:
            raise SystemExit("Che do merge can dung mot --repo <duong dan> va mot --pr <so>. "
                             "Khong co che do merge nhieu PR cung luc.")
        try:
            return merge_pr(os.path.abspath(args.repo[0]), args.pr, auth)
        except RuntimeError as e:
            raise SystemExit("Merge that bai: " + str(e))

    if args.repo:
        repos = [os.path.abspath(r) for r in args.repo]
    elif args.cwd_only:
        root = repo_root(os.getcwd())
        if not root:
            raise SystemExit("Thu muc hien tai khong nam trong git repo")
        repos = [os.path.abspath(root)]
    else:
        repos = discover_repos(os.getcwd())

    log("Quet " + str(len(repos)) + " repo, nhanh dich: " + args.target
        + (" [DRY-RUN]" if args.dry_run else ""))
    log("")

    results = []
    for r in repos:
        try:
            results.append(process_repo(r, args, auth))
        except Exception as e:
            results.append(Result(os.path.basename(r), "ERROR", str(e)))

    order = {"CREATED": 0, "DRYRUN": 1, "ERROR": 2, "SKIP": 3}
    for res in sorted(results, key=lambda x: (order.get(x.status, 9), x.repo)):
        log("[" + res.status + "] " + res.repo + " - " + res.detail)
        if res.url:
            log("    " + res.url)
        for w in res.warns:
            log("    ! " + w)
        if res.commits:
            log("    commit:")
            for c in res.commits:
                log("      - " + c)
        if res.stat:
            log("    diffstat:")
            for s in res.stat:
                log("      " + s)
        if res.rng and res.status in ("CREATED", "DRYRUN"):
            log("    doc dien diff: git -C \"" + res.path + "\" diff " + res.rng)

    log("")
    n_created = sum(1 for r in results if r.status == "CREATED")
    n_err = sum(1 for r in results if r.status == "ERROR")
    log("Tong: " + str(n_created) + " PR tao moi, "
        + str(sum(1 for r in results if r.status == "SKIP")) + " bo qua, "
        + str(n_err) + " loi")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
