---
name: autotest-results
description: Load when the user wants to check, analyze, or understand Robot Framework test results or failures — e.g. "check results", "view test results", "test is failing", "why is the test failing", "how many tests pass", "read output.xml".
user-invocable: true
argument-hint: [path/to/output.xml | blank to use automation_test/results/output.xml]
---

# Robot Framework Results Analyzer

Parse `output.xml` and report structured results. Do not read `output.xml` manually — use the bundled script to get structured JSON, then synthesize a clear summary.

> **Ngôn ngữ giao tiếp:** Mọi text hiển thị cho user — tiến trình, tóm tắt kết quả, chẩn đoán lỗi — viết bằng **tiếng Việt**, kể cả khi phần còn lại của skill này viết bằng tiếng Anh. Giữ nguyên thuật ngữ kỹ thuật (TC, keyword, locator, timeout...) không dịch.

## Setup

```bash
pip install robotframework    # required once
```

## Process

### Step 1: Parse output.xml

Default location is `automation_test/results/output.xml`. Use `$ARGUMENTS` if the user specified a different path.

```bash
# Summary only (default)
python .claude/skills/autotest-results/scripts/rf_results.py \
  --output automation_test/results/output.xml \
  --sections summary \
  --pretty

# Full report: summary + failures + timing
python .claude/skills/autotest-results/scripts/rf_results.py \
  --output automation_test/results/output.xml \
  --sections summary,details,errors,timing \
  --pretty

# Multiple output files, merged
python .claude/skills/autotest-results/scripts/rf_results.py \
  --outputs automation_test/results/out1.xml automation_test/results/out2.xml \
  --merge \
  --sections summary,details \
  --pretty
```

### Step 2: Synthesize and Report

After parsing, always produce a human-readable summary in Vietnamese — never just dump raw JSON. Format:

```
## Kết quả test

Tổng: X passed / Y failed / Z skipped (N total)
Trạng thái chung: PASS | FAIL

### Test fail
- [Suite] TestName — nội dung lỗi
  Keyword fail: đường dẫn keyword

### Test chạy chậm nhất (nếu có yêu cầu timing)
- TestName — Xs
```

### Step 3: Diagnose Failures and Suggest Fixes

After identifying the failing keyword from the JSON, **read the screenshot PNG directly** — it shows the browser state at the exact moment of failure and is usually more diagnostic than the error message alone:

```bash
python -c "import glob; [print(f) for f in sorted(glob.glob('automation_test/results/selenium-screenshot-*.png'))]"
```

Use the Read tool on each PNG. Screenshots are captured automatically by `SeleniumLibrary run_on_failure` — no teardown code needed.

Then match error to fix:

| Error pattern | Likely cause | Fix |
|---|---|---|
| `Element not found` / timeout | Wrong locator, page not loaded, or 404 | Read screenshot PNG — does it show 404? wrong page? update URL or locator |
| `Expected X but got Y` | Assertion mismatch | Check test data (`automation_test/data/*.yaml`) or app behavior |
| `No keyword with name` | Missing import or typo | Check `automation_test/config/imports.resource` and spelling |
| `Timeout after Ns` | Element too slow | Increase `timeout=` on that step or fix wait strategy |
| `ElementClickInterceptedException` | Overlapping element | Read screenshot — scroll into view or wait for overlay to dismiss |
| Assertion passes but navigation didn't happen | `Wait Until Location Contains` trivially true (starting URL already has the fragment) | Use negative URL wait pattern — see `autotest-web-best-practices` Section 11 |
| `Element not visible after Xs` but screenshot shows element in page | Element is CSS-hidden (exists in DOM, `visible=False`) — common for PrimeNG dialog close buttons | Use `Wait Until Page Contains Element` + JS click; see `autotest-web-best-practices` Section 11 |
| `ElementClickInterceptedException` from an overlay that won't close | Dismiss element is CSS-hidden — standard click never reached it | `Wait Until Page Contains Element    css=button.p-dialog-close-button` then `Execute JavaScript    document.querySelector('...').click()` |

### Step 4: Confirm Fix

After applying a fix, re-run the failing test and confirm it passes before reporting done.

```bash
robot --loglevel TRACE -d automation_test/results/ -t "Failed_Test_Name" automation_test/tests/<feature>.robot
```

## Output Sections Reference

| Section | What it contains |
|---|---|
| `summary` | Pass/fail/skip totals, suite/test counts, overall status |
| `details` | Per-suite breakdown, tag stats, criticality stats, failed test list |
| `errors` | Execution errors, failed test messages, keyword-level errors |
| `timing` | Total elapsed, slowest tests; add `--include-keyword-timing` for keyword breakdown |

## Notes

- JSON output goes to stdout. Use `--pretty` for readable output.
- For multiple `output.xml` files: `--merge` mirrors `rebot --merge` (later result wins when tests overlap). Without `--merge`, outputs are combined under a new top-level suite (`--name` sets its name).
- Criticality grouping inferred from tags: `critical`, `noncritical`, `non-critical`. Tests without these tags are grouped as `unspecified`.
