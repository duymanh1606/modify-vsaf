#!/usr/bin/env python3
"""Helper Jira REST client cho skill jira-subtask-creator.

Chỉ dùng stdlib (urllib) — không cần cài thêm package.

Subcommands:
  find-parent        Tìm Story/Task cha theo summary (JQL).
  create-issue       Tạo issue (mặc định Task) làm parent.
  create-subtask     Tạo Sub-task dưới một parent.
  distribute-worklog Log work qua các task tới khi hết ET, trần giờ/ngày.
  sprint-dates       Suy ra Start/Due Date từ mã sprint (M.N.YY).
  close-issue        Chuyển issue sang trạng thái đóng (đa bước nếu cần).

Mọi lệnh cần --env trỏ tới file env.md (mặc định dò các vị trí quen thuộc).
In kết quả ra stdout dạng JSON để model đọc lại.
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
from datetime import datetime, timedelta

DEFAULT_BASE_URL = "http://jira.digital.vn"
JIRA_URL_HINT = "jira.digital.vn"

DEFAULT_ENV_PATHS = [
    os.path.join(os.getcwd(), "env.md"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "env.md"),
    os.path.join(os.path.expanduser("~"), "Documents", ".env", "env.md"),
    os.path.join(os.path.expanduser("~"), "env.md"),
]


def fail(msg):
    print(json.dumps({"ok": False, "error": str(msg)}, ensure_ascii=False))
    sys.exit(1)


def find_env_path(explicit):
    if explicit:
        if os.path.isfile(explicit):
            return explicit
        fail(f"Không tìm thấy env file: {explicit}")
    for p in DEFAULT_ENV_PATHS:
        if os.path.isfile(p):
            return p
    fail("Không tìm thấy env.md. Truyền --env <path>.")


def load_jira_credentials(env_path):
    """Parse env.md markdown linh hoạt, lấy block Jira (theo URL hint).

    Hỗ trợ:
      Username: xxx
      Pass: yyy   (hoặc Password:)
      token: zzz  (Personal Access Token -> Bearer)
      JIRA_URL=...  (override base url)
    """
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    base_url = DEFAULT_BASE_URL
    username = password = token = None
    in_jira_block = False

    def header(line):
        return line.lstrip().startswith("#")

    for line in lines:
        stripped = line.strip()
        low = stripped.lower()

        # Bắt đầu block Jira khi gặp header chứa URL hint.
        if header(line):
            in_jira_block = JIRA_URL_HINT in low
            continue

        if "jira_url" in low and "=" in stripped:
            base_url = stripped.split("=", 1)[1].strip().rstrip("/")
            continue

        if not in_jira_block:
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

    base_url = base_url.rstrip("/")
    if token:
        auth_header = "Bearer " + token
    elif username and password:
        raw = f"{username}:{password}".encode("utf-8")
        auth_header = "Basic " + base64.b64encode(raw).decode("ascii")
    else:
        fail(
            "Không đọc được credential Jira từ env.md (cần Username+Pass hoặc token "
            "trong block có URL chứa '%s')." % JIRA_URL_HINT
        )
    return base_url, auth_header, username


def current_user_name(base_url, auth, fallback=None):
    """Lấy username Jira hiện tại (cho assignee). Ưu tiên fallback từ env."""
    if fallback:
        return fallback
    me = api_request(base_url, auth, "GET", "/rest/api/2/myself")
    return me.get("name")


def api_request(base_url, auth_header, method, path, payload=None):
    url = base_url + path
    data = None
    headers = {"Authorization": auth_header, "Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        fail(f"HTTP {e.code} {method} {path}: {detail}")
    except urllib.error.URLError as e:
        fail(f"Lỗi kết nối {url}: {e.reason}")


def jql_escape(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


# Ký tự đặc biệt Lucene trong toán tử `~` (vd [ ] bị hiểu là range query -> HTTP 400).
_LUCENE_SPECIAL = set('+-&|!(){}[]^"~*?:\\/')


def lucene_sanitize(text):
    """Giữ lại chữ/số/khoảng trắng, bỏ ký tự đặc biệt Lucene -> chuỗi keyword an toàn."""
    cleaned = "".join(" " if ch in _LUCENE_SPECIAL else ch for ch in text)
    return " ".join(cleaned.split()).strip()


def cmd_find_parent(args, base_url, auth):
    search_text = lucene_sanitize(args.summary)
    if not search_text:
        fail("Summary rỗng sau khi làm sạch ký tự đặc biệt, không thể tìm parent.")
    summary = jql_escape(search_text)
    jql = f'summary ~ "{summary}"'
    if args.project:
        jql = f'project = "{args.project}" AND ' + jql
    jql += " ORDER BY updated DESC"
    payload = {
        "jql": jql,
        "maxResults": 20,
        "fields": ["summary", "issuetype", "project"],
    }
    res = api_request(base_url, auth, "POST", "/rest/api/2/search", payload)
    candidates = []
    for issue in res.get("issues", []):
        fields = issue.get("fields", {})
        candidates.append(
            {
                "key": issue.get("key"),
                "summary": fields.get("summary"),
                "issuetype": (fields.get("issuetype") or {}).get("name"),
                "project": (fields.get("project") or {}).get("key"),
            }
        )
    # Ưu tiên Story trước Task khi sắp xếp gợi ý.
    order = {"story": 0, "task": 1}
    candidates.sort(key=lambda c: order.get((c["issuetype"] or "").lower(), 9))
    print(json.dumps({"ok": True, "candidates": candidates}, ensure_ascii=False))


def build_labels(args):
    labels = []
    for chunk in args.labels or []:
        labels.extend([x for x in chunk.split(",") if x])
    return labels


def merge_extra_fields(fields, fields_json):
    """Gộp thêm field tuỳ ý (vd duedate, customfield cascading) từ JSON.

    Một số project bắt buộc field riêng (vd TTCNSPQT: duedate + customfield_15200
    'Vai trò - Công đoạn' cascading: {"value":"DEV APP","child":{"value":"Meeting"}}).
    """
    if not fields_json:
        return
    try:
        extra = json.loads(fields_json)
    except json.JSONDecodeError as e:
        fail(f"--fields-json không phải JSON hợp lệ: {e}")
    if not isinstance(extra, dict):
        fail("--fields-json phải là JSON object.")
    fields.update(extra)


def cmd_create_issue(args, base_url, auth):
    if not args.project:
        fail("create-issue cần --project <KEY>.")
    fields = {
        "project": {"key": args.project},
        "summary": args.summary,
        "issuetype": {"name": args.type},
    }
    labels = build_labels(args)
    if labels:
        fields["labels"] = labels
    merge_extra_fields(fields, args.fields_json)
    res = api_request(base_url, auth, "POST", "/rest/api/2/issue", {"fields": fields})
    print(json.dumps({"ok": True, "key": res.get("key")}, ensure_ascii=False))


def cmd_create_subtask(args, base_url, auth, env_username):
    # Lấy project key từ parent nếu không truyền.
    project_key = args.project
    if not project_key:
        pres = api_request(
            base_url, auth, "GET",
            f"/rest/api/2/issue/{urllib.parse.quote(args.parent)}?fields=project",
        )
        project_key = ((pres.get("fields") or {}).get("project") or {}).get("key")
    if not project_key:
        fail("Không xác định được project cho sub-task.")

    fields = {
        "project": {"key": project_key},
        "parent": {"key": args.parent},
        "summary": args.summary,
        "issuetype": {"name": args.subtask_type},
    }
    labels = build_labels(args)
    if labels:
        fields["labels"] = labels
    if args.et:
        fields["timetracking"] = {"originalEstimate": args.et}
    # Mặc định assignee = chính người dùng (env username hoặc /myself). Tắt bằng --no-assignee.
    if not args.no_assignee:
        assignee = args.assignee or current_user_name(base_url, auth, env_username)
        if assignee:
            fields["assignee"] = {"name": assignee}
    merge_extra_fields(fields, args.fields_json)
    res = api_request(base_url, auth, "POST", "/rest/api/2/issue", {"fields": fields})
    print(
        json.dumps(
            {
                "ok": True,
                "key": res.get("key"),
                "summary": args.summary,
                "et": args.et,
                "assignee": (fields.get("assignee") or {}).get("name"),
            },
            ensure_ascii=False,
        )
    )


def _hours_to_jira(hours):
    """0.5 -> '30m', 8 -> '8h', 1.5 -> '1h 30m'."""
    total_min = int(round(hours * 60))
    h, m = divmod(total_min, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    return " ".join(parts) or "0m"


def parse_days_off(days_off_json):
    """Trả dict {date: 'full'|'morning'|'afternoon'} từ JSON ngày nghỉ.

    Chấp nhận:
      [{"date":"2026-05-20"}]                      -> full (nghỉ cả ngày)
      [{"date":"2026-05-29","off":"morning"}]      -> nghỉ sáng
      ["2026-05-20"]                               -> full
    off nhận: full/cả ngày, morning/sáng, afternoon/chiều.
    """
    if not days_off_json:
        return {}
    try:
        items = json.loads(days_off_json)
    except json.JSONDecodeError as e:
        fail(f"--days-off-json không phải JSON hợp lệ: {e}")
    if not isinstance(items, list):
        fail("--days-off-json phải là JSON array.")

    norm = {
        "full": "full", "cả ngày": "full", "ca ngay": "full", "ngày": "full", "": "full",
        "morning": "morning", "sáng": "morning", "sang": "morning", "nghỉ sáng": "morning",
        "afternoon": "afternoon", "chiều": "afternoon", "chieu": "afternoon",
        "nghỉ chiều": "afternoon",
    }
    result = {}
    for it in items:
        if isinstance(it, str):
            date_s, off = it.strip(), "full"
        elif isinstance(it, dict):
            date_s = (it.get("date") or "").strip()
            off = (it.get("off") or "full").strip().lower()
        else:
            fail("Mỗi phần tử --days-off-json phải là string hoặc object.")
        date_s = _normalize_date(date_s)
        if off not in norm:
            fail(f"Giá trị off '{off}' không hợp lệ (full/morning/afternoon).")
        result[date_s] = norm[off]
    return result


def _normalize_date(date_s):
    """Chuẩn hoá ngày về YYYY-MM-DD. Chấp nhận YYYY-MM-DD hoặc D/M/YYYY (vd 1/7/2026)."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    fail(f"Ngày nghỉ '{date_s}' phải dạng YYYY-MM-DD hoặc D/M/YYYY.")


def _monday_of_week(d):
    """Thứ Hai của tuần chứa ngày d."""
    return d - timedelta(days=d.weekday())


def _last_friday_of_month(year, month):
    """Thứ Sáu cuối cùng của tháng."""
    if month == 12:
        first_next = datetime(year + 1, 1, 1)
    else:
        first_next = datetime(year, month + 1, 1)
    last_day = first_next - timedelta(days=1)
    offset = (last_day.weekday() - 4) % 7
    return last_day - timedelta(days=offset)


def _sprint1_range(year, month):
    """Sprint 1: thứ Hai của tuần chứa ngày 1 tới thứ Sáu tuần thứ hai (2 tuần)."""
    start = _monday_of_week(datetime(year, month, 1))
    end = start + timedelta(days=11)
    return start, end


def parse_sprint_code(code):
    """Tách mã sprint M.N.YY thành (tháng, số sprint, năm). Chấp nhận . - / làm dấu."""
    parts = re.split(r"[.\-/]", code.strip())
    if len(parts) != 3:
        fail(f"Mã sprint '{code}' phải dạng M.N.YY, vd 7.1.26.")
    try:
        month, sprint_no, year = (int(x) for x in parts)
    except ValueError:
        fail(f"Mã sprint '{code}' chứa phần không phải số.")
    if year < 100:
        year += 2000
    if not 1 <= month <= 12:
        fail(f"Tháng '{month}' trong mã sprint không hợp lệ.")
    if sprint_no not in (1, 2):
        fail(f"Số sprint '{sprint_no}' phải là 1 hoặc 2.")
    return month, sprint_no, year


def compute_sprint_dates(code):
    """Suy ra Start/Due Date từ mã sprint.

    Sprint 1: thứ Hai của tuần chứa ngày 1 của tháng tới thứ Sáu tuần thứ hai.
    Sprint 2: thứ Hai kế tiếp sau Sprint 1 tới thứ Sáu cuối tháng (2 hoặc 3 tuần).
    """
    month, sprint_no, year = parse_sprint_code(code)
    if sprint_no == 1:
        start, end = _sprint1_range(year, month)
    else:
        _, s1_end = _sprint1_range(year, month)
        start = s1_end + timedelta(days=3)
        end = _last_friday_of_month(year, month)
    return {
        "ok": True,
        "sprint": code.strip(),
        "month": month,
        "sprint_no": sprint_no,
        "year": year,
        "start_date": start.strftime("%Y-%m-%d"),
        "due_date": end.strftime("%Y-%m-%d"),
        "weeks": (end - start).days // 7 + 1,
    }


def cmd_sprint_dates(args):
    print(json.dumps(compute_sprint_dates(args.sprint), ensure_ascii=False))


def logged_hours_on(base_url, auth, me_name, date_s):
    """Tổng giờ user hiện tại đã log trên mọi issue trong ngày date_s (YYYY-MM-DD).

    Dùng để không vượt trần giờ/ngày khi user đã tự log tay từ trước.
    """
    jql = f'worklogAuthor = currentUser() AND worklogDate = "{date_s}"'
    res = api_request(
        base_url, auth, "POST", "/rest/api/2/search",
        {"jql": jql, "maxResults": 200, "fields": ["summary"]},
    )
    total_sec = 0
    for issue in res.get("issues", []):
        key = issue.get("key")
        wl = api_request(
            base_url, auth, "GET",
            f"/rest/api/2/issue/{urllib.parse.quote(key)}/worklog",
        )
        for w in wl.get("worklogs", []):
            same_author = (w.get("author") or {}).get("name") == me_name
            same_day = (w.get("started") or "")[:10] == date_s
            if same_author and same_day:
                total_sec += w.get("timeSpentSeconds") or 0
    return total_sec / 3600.0


# Từ khoá tên transition hoặc trạng thái đích, xếp theo độ ưu tiên từ cao xuống thấp.
CLOSE_TRANSITION_KEYWORDS = [
    "closed", "close", "done", "resolved", "resolve",
    "hoàn thành", "hoan thanh", "đóng", "dong",
]
# Transition trung gian để tiến tới trạng thái đóng khi chưa lộ transition đóng trực tiếp.
PROGRESS_TRANSITION_KEYWORDS = ["in progress", "progress", "start", "reopen", "đang"]


def _match_transition(transitions, keywords, hint=None):
    """Chọn transition khớp keyword sớm nhất; ưu tiên hint khớp đúng tên."""
    if hint:
        for tr in transitions:
            if hint.strip().lower() == (tr.get("name") or "").strip().lower():
                return tr
    best, best_rank = None, len(keywords)
    for tr in transitions:
        text = (
            (tr.get("name") or "") + " " + ((tr.get("to") or {}).get("name") or "")
        ).lower()
        for i, kw in enumerate(keywords):
            if kw in text and i < best_rank:
                best, best_rank = tr, i
                break
    return best


def close_issue(base_url, auth, key, hint=None, max_hops=4):
    """Chuyển issue sang trạng thái đóng.

    Workflow có thể nhiều bước (vd To Do -> In Progress -> Closed): nếu chưa lộ
    transition đóng, đi qua transition trung gian tiến tới rồi thử lại.
    """
    path = f"/rest/api/2/issue/{urllib.parse.quote(key)}/transitions"
    for _ in range(max_hops):
        transitions = api_request(base_url, auth, "GET", path).get("transitions", [])
        close_tr = _match_transition(transitions, CLOSE_TRANSITION_KEYWORDS, hint)
        if close_tr:
            api_request(base_url, auth, "POST", path,
                        {"transition": {"id": close_tr.get("id")}})
            return {
                "key": key, "closed": True,
                "transition": close_tr.get("name"),
                "status": (close_tr.get("to") or {}).get("name"),
            }
        inter = _match_transition(transitions, PROGRESS_TRANSITION_KEYWORDS)
        if not inter:
            return {
                "key": key, "closed": False,
                "error": "Không có transition đóng khả dụng",
                "available": [t.get("name") for t in transitions],
            }
        api_request(base_url, auth, "POST", path,
                    {"transition": {"id": inter.get("id")}})
    return {"key": key, "closed": False, "error": "Vượt số bước chuyển trạng thái cho phép"}


def cmd_close_issue(args, base_url, auth):
    result = close_issue(base_url, auth, args.key, args.transition)
    print(json.dumps({"ok": result.get("closed", False), **result}, ensure_ascii=False))


def cmd_distribute_worklog(args, base_url, auth):
    """Log work qua các task cho tới khi hết ET; mỗi ngày tổng tối đa hours-per-day.

    --tasks-json: '[{"key":"APP-1","hours":16},{"key":"APP-2","hours":8,"maxPerDay":2}]'
    Mỗi task có thể đặt "maxPerDay" (giờ/ngày riêng) — vd task họp = 2 để rải mỏng.
    --days-off-json: '[{"date":"2026-05-20","off":"full"},{"date":"2026-05-29","off":"morning"}]'
    off = full (nghỉ cả ngày, bỏ qua) | morning (nghỉ sáng → chỉ log chiều, ½ ngày)
        | afternoon (nghỉ chiều → chỉ log sáng, ½ ngày). Mặc định bỏ qua T7/CN.

    Mặc định kiểm tra worklog user đã tự log tay từ trước ở mỗi ngày, trừ vào trần
    giờ/ngày (vd ngày đã có 4h → chỉ log thêm 4h; đã đủ 8h → bỏ qua ngày đó).
    Tắt bằng --ignore-existing-worklog.
    """
    try:
        tasks = json.loads(args.tasks_json)
    except json.JSONDecodeError as e:
        fail(f"--tasks-json không phải JSON hợp lệ: {e}")
    if not isinstance(tasks, list):
        fail("--tasks-json phải là JSON array.")

    hpd = float(args.hours_per_day)
    if hpd <= 0:
        fail("--hours-per-day phải > 0.")
    try:
        cur = datetime.strptime(args.start_date, "%Y-%m-%d")
    except ValueError:
        fail("--start-date phải dạng YYYY-MM-DD.")
    try:
        base_h, base_m = (int(x) for x in args.start_time.split(":"))
    except Exception:
        fail("--start-time phải dạng HH:MM, vd 09:00.")
    try:
        aft_h, aft_m = (int(x) for x in args.afternoon_start.split(":"))
    except Exception:
        fail("--afternoon-start phải dạng HH:MM, vd 13:00.")

    skip_weekends = not args.include_weekends
    days_off = parse_days_off(args.days_off_json)

    # Kiểm tra giờ đã log tay từ trước để không vượt trần giờ/ngày.
    check_existing = not args.ignore_existing_worklog
    me_name = None
    if check_existing:
        me_name = api_request(base_url, auth, "GET", "/rest/api/2/myself").get("name")

    def day_info(d):
        """(cap_giờ, start_h, start_m) cho ngày làm việc; None nếu nghỉ cả ngày/cuối tuần."""
        if skip_weekends and d.weekday() >= 5:  # 5=T7, 6=CN
            return None
        off = days_off.get(d.strftime("%Y-%m-%d"))
        if off == "full":
            return None
        if off == "morning":   # nghỉ sáng -> chỉ log buổi chiều
            return (hpd / 2.0, aft_h, aft_m)
        if off == "afternoon":  # nghỉ chiều -> chỉ log buổi sáng
            return (hpd / 2.0, base_h, base_m)
        return (hpd, base_h, base_m)

    # Chuẩn hoá danh sách công việc. Mỗi task có thể có giới hạn giờ/ngày riêng
    # (maxPerDay) — vd task họp = 2h/ngày để không dồn vào một ngày.
    work = []
    for t in tasks:
        key = t.get("key")
        hours = float(t.get("hours", 0))
        if not key or hours <= 0:
            continue
        cap = float(t.get("maxPerDay", hpd) or hpd)
        if cap <= 0:
            cap = hpd
        work.append({"key": key, "remaining": hours, "cap": min(cap, hpd)})

    results = []
    safety = 0
    # Vòng lặp theo ngày: bỏ ngày nghỉ; mỗi ngày tổng ≤ cap của ngày (nửa ngày nghỉ = ½).
    while any(w["remaining"] > 1e-9 for w in work):
        safety += 1
        if safety > 2000:
            fail("Vượt 2000 ngày khi log work — kiểm tra lại dữ liệu đầu vào.")
        info = day_info(cur)
        if info is None:  # cuối tuần hoặc nghỉ cả ngày
            cur = cur + timedelta(days=1)
            continue
        day_cap, day_h, day_m = info
        # Giờ đã log tay từ trước làm offset: giảm quota còn lại và đẩy giờ bắt đầu.
        used_today = 0.0
        if check_existing:
            already = logged_hours_on(base_url, auth, me_name, cur.strftime("%Y-%m-%d"))
            used_today = min(already, day_cap)
        for w in work:
            if w["remaining"] <= 1e-9:
                continue
            avail = day_cap - used_today
            if avail <= 1e-9:
                break  # ngày đã đầy
            chunk = min(w["remaining"], avail, w["cap"])
            if chunk <= 1e-9:
                continue
            started_dt = cur.replace(hour=day_h, minute=day_m, second=0) + timedelta(
                hours=used_today
            )
            started = started_dt.strftime("%Y-%m-%dT%H:%M:%S.000") + args.tz_offset
            payload = {"timeSpent": _hours_to_jira(chunk), "started": started}
            r = api_request(
                base_url, auth, "POST",
                f"/rest/api/2/issue/{urllib.parse.quote(w['key'])}/worklog",
                payload,
            )
            results.append(
                {
                    "key": w["key"],
                    "date": started_dt.strftime("%Y-%m-%d"),
                    "timeSpent": payload["timeSpent"],
                    "worklogId": r.get("id"),
                }
            )
            w["remaining"] -= chunk
            used_today += chunk
        cur = cur + timedelta(days=1)

    out = {"ok": True, "worklogs": results}
    # Đóng những task đã log hết ET còn lại khi người dùng bật cờ đóng-khi-xong.
    if args.close_when_done:
        out["closed"] = [
            close_issue(base_url, auth, w["key"])
            for w in work if w["remaining"] <= 1e-9
        ]
    print(json.dumps(out, ensure_ascii=False))


def main():
    # Ép stdout UTF-8 để in được tiếng Việt trên console Windows (cp1252).
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Jira sub-task helper")
    parser.add_argument("--env", help="Đường dẫn env.md")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("find-parent")
    p.add_argument("--summary", required=True)
    p.add_argument("--project")

    p = sub.add_parser("create-issue")
    p.add_argument("--type", default="Task")
    p.add_argument("--summary", required=True)
    p.add_argument("--project")
    p.add_argument("--labels", action="append")
    p.add_argument("--fields-json", help="JSON object field bổ sung (vd duedate, customfield)")

    p = sub.add_parser("create-subtask")
    p.add_argument("--parent", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--project")
    p.add_argument("--labels", action="append")
    p.add_argument("--et", help="Original estimate dạng Jira, vd 16h, 8h, 4h")
    p.add_argument("--subtask-type", default="Sub-task")
    p.add_argument("--fields-json", help="JSON object field bổ sung (vd duedate, customfield)")
    p.add_argument("--assignee", help="Username assignee (mặc định = chính bạn từ env.md)")
    p.add_argument("--no-assignee", action="store_true", help="Không gán assignee")

    p = sub.add_parser("distribute-worklog")
    p.add_argument("--start-date", required=True, help="Ngày bắt đầu log, YYYY-MM-DD")
    p.add_argument(
        "--tasks-json", required=True,
        help='JSON array, mỗi item {"key","hours"[,"maxPerDay"]}. '
             'maxPerDay = giờ/ngày riêng cho task (vd họp = 2).',
    )
    p.add_argument("--hours-per-day", default="8", help="Giờ tối đa/ngày (mặc định 8)")
    p.add_argument("--start-time", default="09:00", help="Giờ bắt đầu mỗi ngày HH:MM")
    p.add_argument("--afternoon-start", default="13:00", help="Giờ bắt đầu buổi chiều (khi nghỉ sáng)")
    p.add_argument("--tz-offset", default="+0700", help="Timezone offset, mặc định +0700")
    p.add_argument("--include-weekends", action="store_true", help="Log cả T7/CN")
    p.add_argument(
        "--days-off-json",
        help='Ngày nghỉ: [{"date":"2026-05-20","off":"full|morning|afternoon"}]',
    )
    p.add_argument(
        "--ignore-existing-worklog", action="store_true",
        help="Bỏ qua việc kiểm tra worklog đã tự log tay từ trước (mặc định có kiểm tra)",
    )
    p.add_argument(
        "--close-when-done", action="store_true",
        help="Close task đã log đủ ET sau khi log work xong",
    )

    p = sub.add_parser("sprint-dates")
    p.add_argument("--sprint", required=True, help="Mã sprint dạng M.N.YY, vd 7.1.26")

    p = sub.add_parser("close-issue")
    p.add_argument("--key", required=True, help="Issue key cần đóng, vd TTCNSPQT-4994")
    p.add_argument("--transition", help="Tên transition đóng (mặc định tự dò close/done/resolve)")

    args = parser.parse_args()

    # sprint-dates thuần tính toán, không cần credential Jira.
    if args.command == "sprint-dates":
        cmd_sprint_dates(args)
        return

    env_path = find_env_path(args.env)
    base_url, auth, env_username = load_jira_credentials(env_path)

    if args.command == "find-parent":
        cmd_find_parent(args, base_url, auth)
    elif args.command == "create-issue":
        cmd_create_issue(args, base_url, auth)
    elif args.command == "create-subtask":
        cmd_create_subtask(args, base_url, auth, env_username)
    elif args.command == "distribute-worklog":
        cmd_distribute_worklog(args, base_url, auth)
    elif args.command == "close-issue":
        cmd_close_issue(args, base_url, auth)


if __name__ == "__main__":
    main()
