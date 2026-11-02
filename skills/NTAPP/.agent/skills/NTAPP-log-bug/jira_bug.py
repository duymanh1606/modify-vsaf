#!/usr/bin/env python3
"""Helper Jira dung chung cho NTAPP-log-bug (tao bug) va NTAPP-fix-bug (dong bug).

Chi dung stdlib (urllib) nen khong can pip install.

Subcommand ghi bug (NTAPP-log-bug):
  probe      --project KEY              -> issue type kha dung trong project + field bat buoc
  create     --project KEY --type Bug   -> tao issue (+ attach anh) -> tra key + url
  find-user  --query dinhtq             -> tra cuu username cho Assignee

Subcommand dong bug (NTAPP-fix-bug):
  get-issue     --key K                 -> mo ta + reporter + attachment + transition kha dung
  update-issue  --key K                 -> sua field (Nguyen nhan/Anh huong/Giai phap) + assignee
  transition    --key K --to Resolved   -> chuyen trang thai

CANH BAO: update-issue va transition GHI THAT len Jira (state dung chung, khong undo tu dong).
Luon chay kem --dry-run truoc de validate; chi bo --dry-run sau khi nguoi dung da duyet.

Credential doc tu env.md (KHONG hardcode path may nao — xem PORTABILITY trong SKILL.md):
  ./env.md -> <skill-dir>/env.md -> ~/Documents/.env/env.md -> ~/env.md
Override: --env <path> hoac bien moi truong NTAPP_JIRA_ENV.

Base URL lay theo thu tu: --url > dong "JIRA_URL=" trong env.md > URL nam trong header
cua block Jira (vd "# http://jira.example.com/:").

Moi output la MOT dong JSON: {"ok": true, ...} hoac {"ok": false, "error": "..."}.
Exit code 0 khi ok, 1 khi loi.
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

API = "/rest/api/2"
TIMEOUT = 60

# Field khong can hoi user vi skill luon tu dien (hoac Jira tu set).
SKIP_REQUIRED = {
    "project", "issuetype", "summary", "description",
    "reporter", "attachment", "labels", "assignee", "issuelinks",
}

try:  # Windows: tranh UnicodeEncodeError cp1252 khi in tieng Viet
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def out(payload):
    print(json.dumps(payload, ensure_ascii=False))


def fail(msg):
    out({"ok": False, "error": str(msg)})
    sys.exit(1)


# ---------------------------------------------------------------- credential
def env_candidates(explicit):
    if explicit:
        return [explicit]
    cands = []
    if os.environ.get("NTAPP_JIRA_ENV"):
        cands.append(os.environ["NTAPP_JIRA_ENV"])
    home = os.path.expanduser("~")
    cands += [
        os.path.join(os.getcwd(), "env.md"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "env.md"),
        os.path.join(home, "Documents", ".env", "env.md"),
        os.path.join(home, "env.md"),
    ]
    return cands


def find_env_path(explicit):
    cands = env_candidates(explicit)
    for p in cands:
        if p and os.path.isfile(p):
            return p
    fail(
        "Khong tim thay env.md. Da thu: " + " | ".join(cands)
        + ". Tao env.md theo mau env.example.md trong thu muc skill, hoac truyen --env <path>."
    )


def _clean_url(raw):
    return raw.rstrip("/:,;)>\"'").rstrip("/")


def load_credentials(env_path, url_override):
    """Parse env.md: block Jira = block co header (dong bat dau '#') chua chu 'jira'."""
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    base_url = header_url = username = password = token = None
    in_block = False

    for line in lines:
        s = line.strip()
        if s.startswith("#"):
            # Chi dong comment co URL moi duoc coi la header mo/dong block, nen dong
            # comment phu ben trong block (vd token da comment lai) khong lam mat block.
            m = re.search(r"https?://[^\s]+", s)
            if m:
                in_block = "jira" in s.lower()
                if in_block and header_url is None:
                    header_url = _clean_url(m.group(0))
            elif "jira" in s.lower():
                in_block = True
            continue
        m = re.match(r"(?i)\s*jira_url\s*[:=]\s*(.+)", s)
        if m:
            base_url = _clean_url(m.group(1).strip())
            continue
        if not in_block:
            continue
        m = re.match(r"(?i)\s*username\s*[:=]\s*(.+)", s)
        if m:
            username = m.group(1).strip()
            continue
        m = re.match(r"(?i)\s*pass(?:word)?\s*[:=]\s*(.+)", s)
        if m:
            password = m.group(1).strip()
            continue
        m = re.match(r"(?i)\s*token\s*[:=]\s*(.+)", s)
        if m:
            token = m.group(1).strip()
            continue

    final_url = _clean_url(url_override) if url_override else (base_url or header_url)
    if not final_url:
        fail("Khong xac dinh duoc base URL Jira. Them dong 'JIRA_URL=https://...' vao env.md hoac truyen --url.")

    if token:
        auth = "Bearer " + token
    elif username and password:
        auth = "Basic " + base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    else:
        fail("Khong doc duoc credential Jira trong env.md (can Username + Pass, hoac token) o block co header chua 'jira'.")
    return final_url, auth, username


# ---------------------------------------------------------------- http
def api(base_url, auth, method, path, payload=None):
    headers = {"Authorization": auth, "Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        fail(f"HTTP {e.code} {method} {path}: {e.read().decode('utf-8', 'replace')[:800]}")
    except urllib.error.URLError as e:
        fail(f"Loi ket noi {base_url}{path}: {e.reason}")


def download_file(auth, url, out_path):
    """Tai 1 attachment ve local. Tra None neu ok, chuoi loi neu that bai."""
    req = urllib.request.Request(url, headers={"Authorization": auth}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            blob = resp.read()
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(blob)
        return None
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return str(e.reason)


def fetch_transitions(base_url, auth, key):
    """Transition kha dung + field bat buoc cua tung transition screen.

    KHONG dung SKIP_REQUIRED o day: filter do danh cho createmeta (field skill luon tu
    dien khi TAO issue). Transition screen thi field nao bat buoc cung phai bao ra, ke ca
    assignee/labels — neu che di thi guard khong canh bao va Jira tra 400.
    """
    data = api(base_url, auth, "GET",
               f"{API}/issue/{key}/transitions?expand=transitions.fields")
    result = []
    for t in data.get("transitions") or []:
        required = []
        for fid, f in (t.get("fields") or {}).items():
            if not f.get("required"):
                continue
            entry = {"id": fid, "name": f.get("name")}
            allowed = f.get("allowedValues")
            if allowed:
                entry["allowedValues"] = [a.get("value") or a.get("name") for a in allowed[:15]]
            required.append(entry)
        result.append({"id": t.get("id"), "name": t.get("name"),
                       "to": (t.get("to") or {}).get("name"), "required_fields": required})
    return result


def upload_attachment(base_url, auth, key, path):
    """POST multipart len /issue/{key}/attachments. Tra None neu ok, chuoi loi neu that bai."""
    if not os.path.isfile(path):
        return "khong ton tai file"
    boundary = "----NTAPPLogBug" + uuid.uuid4().hex
    fname = os.path.basename(path)
    with open(path, "rb") as f:
        blob = f.read()
    body = b"".join([
        f"--{boundary}\r\n".encode("utf-8"),
        f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'.encode("utf-8"),
        b"Content-Type: application/octet-stream\r\n\r\n",
        blob,
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ])
    headers = {
        "Authorization": auth,
        "Accept": "application/json",
        "X-Atlassian-Token": "no-check",  # Jira bat buoc header nay cho upload
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    req = urllib.request.Request(
        f"{base_url}{API}/issue/{key}/attachments", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            resp.read()
        return None
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"
    except urllib.error.URLError as e:
        return str(e.reason)


# ---------------------------------------------------------------- commands
def cmd_probe(args, base_url, auth, me):
    path = (f"{API}/issue/createmeta?projectKeys={urllib.parse.quote(args.project)}"
            "&expand=projects.issuetypes.fields")
    meta = api(base_url, auth, "GET", path)
    projects = meta.get("projects") or []
    if not projects:
        fail(f"Project '{args.project}' khong ton tai hoac user khong co quyen tao issue trong project nay.")

    types = []
    for it in projects[0].get("issuetypes") or []:
        if it.get("subtask"):
            continue
        required = []
        for fid, f in (it.get("fields") or {}).items():
            if fid in SKIP_REQUIRED or not f.get("required"):
                continue
            entry = {"id": fid, "name": f.get("name")}
            allowed = f.get("allowedValues")
            if allowed:
                entry["allowedValues"] = [
                    a.get("value") or a.get("name") for a in allowed[:15]
                ]
            required.append(entry)
        types.append({"name": it.get("name"), "required_fields": required})

    out({
        "ok": True, "base_url": base_url, "me": me,
        "project": projects[0].get("key"),
        "types": types,
        "type_names": [t["name"] for t in types],
    })


def cmd_find_user(args, base_url, auth, me):
    q = urllib.parse.quote(args.query)
    users = api(base_url, auth, "GET", f"{API}/user/search?username={q}&maxResults=20")
    out({"ok": True, "users": [
        {"name": u.get("name"), "displayName": u.get("displayName"),
         "email": u.get("emailAddress"), "active": u.get("active")}
        for u in users
    ]})


def cmd_create(args, base_url, auth, me):
    with open(args.description_file, "r", encoding="utf-8") as f:
        description = f.read()

    fields = {
        "project": {"key": args.project},
        "issuetype": {"name": args.type},
        "summary": args.summary,
        "description": description,
    }
    if args.labels:
        fields["labels"] = args.labels
    if args.assignee:
        fields["assignee"] = {"name": args.assignee}
    if args.fields_json:
        try:
            extra = json.loads(args.fields_json)
        except json.JSONDecodeError as e:
            fail(f"--fields-json khong phai JSON hop le: {e}")
        if not isinstance(extra, dict):
            fail("--fields-json phai la JSON object.")
        fields.update(extra)

    created = api(base_url, auth, "POST", f"{API}/issue", {"fields": fields})
    key = created.get("key")
    if not key:
        fail(f"Jira khong tra ve issue key: {created}")

    attached, attach_errors = [], []
    for p in args.attach or []:
        err = upload_attachment(base_url, auth, key, p)
        (attach_errors.append({"file": p, "error": err}) if err
         else attached.append(os.path.basename(p)))

    out({
        "ok": True, "key": key, "url": f"{base_url}/browse/{key}",
        "type": args.type, "assignee": args.assignee or None,
        "attached": attached, "attach_errors": attach_errors,
    })


BASE_FIELDS = ("summary,description,issuetype,status,resolution,reporter,assignee,"
               "labels,priority,attachment,created,updated")


def _user(u):
    return {"name": u.get("name"), "displayName": u.get("displayName"),
            "email": u.get("emailAddress")} if u else None


def cmd_get_issue(args, base_url, auth, me):
    want = BASE_FIELDS
    if args.extra_fields:
        want += "," + args.extra_fields.replace(" ", "")
    issue = api(base_url, auth, "GET",
                f"{API}/issue/{args.key}?fields={urllib.parse.quote(want, safe=',')}")
    f = issue.get("fields") or {}

    attachments = []
    for att in f.get("attachment") or []:
        item = {"filename": att.get("filename"), "size": att.get("size"),
                "mimeType": att.get("mimeType"), "saved": None, "error": None}
        if args.download_dir and (att.get("mimeType") or "").startswith("image/"):
            dest = os.path.join(args.download_dir, f"{args.key}-{att.get('filename')}")
            err = download_file(auth, att.get("content"), dest)
            item["saved"] = None if err else dest
            item["error"] = err
        attachments.append(item)

    extra = {}
    for fid in (args.extra_fields or "").replace(" ", "").split(","):
        if fid:
            extra[fid] = f.get(fid)

    out({
        "ok": True, "key": issue.get("key"), "url": f"{base_url}/browse/{issue.get('key')}",
        "type": (f.get("issuetype") or {}).get("name"),
        "status": (f.get("status") or {}).get("name"),
        "resolution": (f.get("resolution") or {}).get("name"),
        "summary": f.get("summary"), "description": f.get("description"),
        "reporter": _user(f.get("reporter")), "assignee": _user(f.get("assignee")),
        "labels": f.get("labels") or [], "priority": (f.get("priority") or {}).get("name"),
        "extra": extra, "attachments": attachments,
        "transitions": fetch_transitions(base_url, auth, args.key),
    })


def _load_fields_json(raw):
    if not raw:
        return {}
    try:
        extra = json.loads(raw)
    except json.JSONDecodeError as e:
        fail(f"--fields-json khong phai JSON hop le: {e}")
    if not isinstance(extra, dict):
        fail("--fields-json phai la JSON object.")
    return extra


def cmd_update_issue(args, base_url, auth, me):
    fields = _load_fields_json(args.fields_json)
    if args.assignee:
        fields["assignee"] = {"name": args.assignee}
    if not fields:
        fail("Khong co field nao de update (can --fields-json va/hoac --assignee).")
    if args.dry_run:
        out({"ok": True, "dry_run": True, "key": args.key, "would_update": sorted(fields)})
        return
    api(base_url, auth, "PUT", f"{API}/issue/{args.key}", {"fields": fields})
    out({"ok": True, "key": args.key, "updated": sorted(fields)})


def cmd_transition(args, base_url, auth, me):
    trs = fetch_transitions(base_url, auth, args.key)
    target = args.to.strip().lower()
    match = next((t for t in trs
                  if (t["to"] or "").lower() == target or (t["name"] or "").lower() == target), None)
    if not match:
        fail("Khong tim thay transition '%s'. Kha dung: %s" % (
            args.to, ", ".join(f"{t['name']} -> {t['to']}" for t in trs)))

    payload_fields = _load_fields_json(args.fields_json)
    missing = [r for r in match["required_fields"] if r["id"] not in payload_fields]
    if missing:
        fail("Transition '%s' bat buoc field chua truyen: %s" % (
            match["name"], json.dumps(missing, ensure_ascii=False)))

    body = {"transition": {"id": match["id"]}}
    if payload_fields:
        body["fields"] = payload_fields
    if args.dry_run:
        out({"ok": True, "dry_run": True, "key": args.key, "transition": match["name"],
             "to": match["to"], "would_send": payload_fields})
        return
    api(base_url, auth, "POST", f"{API}/issue/{args.key}/transitions", body)

    after = api(base_url, auth, "GET", f"{API}/issue/{args.key}?fields=status,assignee")
    af = after.get("fields") or {}
    out({"ok": True, "key": args.key, "transition": match["name"],
         "status": (af.get("status") or {}).get("name"),
         "assignee": _user(af.get("assignee")),
         "url": f"{base_url}/browse/{args.key}"})


def main():
    ap = argparse.ArgumentParser(description="Jira helper cho NTAPP-log-bug / NTAPP-fix-bug")
    ap.add_argument("--env", help="Duong dan env.md (mac dinh tu dong do)")
    ap.add_argument("--url", help="Base URL Jira, override env.md")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe", help="Liet ke issue type + field bat buoc cua project")
    p.add_argument("--project", required=True)

    p = sub.add_parser("find-user", help="Tra cuu username cho Assignee")
    p.add_argument("--query", required=True)

    p = sub.add_parser("create", help="Tao issue + attach anh")
    p.add_argument("--project", required=True)
    p.add_argument("--type", required=True, help="Bug | Issue | ...")
    p.add_argument("--summary", required=True)
    p.add_argument("--description-file", required=True,
                   help="File .txt chua description (wiki markup) — tranh loi quoting multi-line")
    p.add_argument("--assignee", help="Username Jira; bo qua = khong gan")
    p.add_argument("--labels", action="append", help="Lap lai nhieu lan")
    p.add_argument("--attach", action="append", help="Duong dan anh, lap lai nhieu lan")
    p.add_argument("--fields-json", help="JSON object field bat buoc them (vd duedate, customfield_*)")

    p = sub.add_parser("get-issue", help="Doc issue: mo ta, reporter, attachment, transition")
    p.add_argument("--key", required=True, help="Issue key, vd TTCNSPQT-5067")
    p.add_argument("--extra-fields", help="Danh sach customfield can doc, cach nhau bang dau phay")
    p.add_argument("--download-dir", help="Neu co: tai attachment anh ve thu muc nay")

    p = sub.add_parser("update-issue", help="Sua field + assignee cua issue")
    p.add_argument("--key", required=True)
    p.add_argument("--assignee", help="Username nhan lai issue (vd reporter)")
    p.add_argument("--fields-json", help="JSON object field can set (vd Nguyen nhan/Anh huong/Giai phap)")
    p.add_argument("--dry-run", action="store_true", help="Chi validate, KHONG ghi len Jira")

    p = sub.add_parser("transition", help="Chuyen trang thai issue")
    p.add_argument("--key", required=True)
    p.add_argument("--to", required=True, help="Ten trang thai dich (vd Resolved) hoac ten transition")
    p.add_argument("--fields-json", help="JSON object field bat buoc cua transition screen")
    p.add_argument("--dry-run", action="store_true",
                   help="Chi validate (transition co ton tai + du field bat buoc), KHONG ghi len Jira")

    args = ap.parse_args()
    base_url, auth, me = load_credentials(find_env_path(args.env), args.url)
    {
        "probe": cmd_probe, "find-user": cmd_find_user, "create": cmd_create,
        "get-issue": cmd_get_issue, "update-issue": cmd_update_issue,
        "transition": cmd_transition,
    }[args.cmd](args, base_url, auth, me)


if __name__ == "__main__":
    main()
