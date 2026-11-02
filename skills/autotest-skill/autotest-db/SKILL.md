---
name: autotest-db
description: Supporting skill for database operations in Robot Framework tests — connection, assertion, setup/teardown, state reset. Supports MariaDB/MySQL, PostgreSQL, MSSQL, SQLite. SSH tunnel for remote DBs.
user-invocable: false
---

# RF-DB Supporting Skill

Skill hỗ trợ — không có slash command riêng. Được đọc bởi `autotest-api`, `autotest-web`, `autotest-android`, `autotest-ios` khi TC cần DB operations.

> **Ngôn ngữ giao tiếp:** Mọi text hiển thị cho user trong lúc làm việc — tiến trình, câu hỏi, cảnh báo — viết bằng **tiếng Việt**. Giữ nguyên thuật ngữ kỹ thuật (DB, query, tunnel, transaction...) không dịch.

---

## Khi nào autotest-* skills dùng skill này

Scan TC file và domain docs tìm các tín hiệu sau:

| Tín hiệu trong TC | Hành động |
|---|---|
| "verify DB", "check bảng", "kiểm tra database", "query" | Cần **DB Assertion** |
| "tạo test data", "seed", "insert trước khi chạy", "precondition data" | Cần **DB Setup** |
| "xoá sau test", "cleanup", "reset state", "rollback" | Cần **DB Teardown/Reset** |
| "kết nối qua tunnel", "overseas", "nước ngoài", "SSH" | Cần **SSH Tunnel** |

Nếu phát hiện bất kỳ tín hiệu nào → **đọc skill này trước khi viết code** → scaffold các file DB nếu chưa có.

---

## Setup môi trường

### Cài packages

```python
import subprocess, sys

DB_TYPE = "<mariadb|mysql|postgresql|mssql|sqlite>"

packages = {
    "mariadb": ["pymysql"],
    "mysql":   ["pymysql"],
    "postgresql": ["psycopg2-binary"],
    "mssql":   ["pymssql"],
    "sqlite":  [],  # built-in
}

tunnel_needed = False  # set True nếu cần SSH tunnel
base = ["robotframework-databaselibrary>=2.0.0"]
db_pkgs = packages.get(DB_TYPE, [])
tunnel_pkgs = ["sshtunnel", "paramiko"] if tunnel_needed else []

all_pkgs = base + db_pkgs + tunnel_pkgs
if all_pkgs:
    subprocess.run([sys.executable, "-m", "pip", "install"] + all_pkgs, check=True)
print("OK")
```

### Thêm vào requirements.txt (nếu project có)

```
robotframework-databaselibrary>=2.0.0
pymysql==1.1.1          # MariaDB/MySQL
# psycopg2-binary==2.9.9  # PostgreSQL
# pymssql==2.3.1          # MSSQL
# sshtunnel==0.4.0        # SSH tunnel
# paramiko==3.4.0         # SSH tunnel
```

---

## Scaffold files

Tạo các file sau nếu chưa tồn tại — **không bao giờ ghi đè file đang có**.

### `automation_test/common/db_variables.resource`

```robotframework
*** Variables ***
# ── DB Connection ──────────────────────────────────────────────
${DB_TYPE}          mariadb
${DB_HOST}          127.0.0.1
${DB_PORT}          3306
${DB_NAME}          your_db_name
${DB_USER}          your_db_user
${DB_PASS}          your_db_pass
${DB_CHARSET}       utf8mb4

# ── SSH Tunnel (bỏ trống nếu không dùng) ───────────────────────
${DB_TUNNEL_SSH_HOST}       ${EMPTY}
${DB_TUNNEL_SSH_PORT}       22
${DB_TUNNEL_SSH_USER}       ${EMPTY}
${DB_TUNNEL_SSH_KEY}        ${EMPTY}
${DB_TUNNEL_LOCAL_PORT}     13306
```

### `automation_test/common/db_keywords.resource`

> **Requires:** `robotframework-databaselibrary>=2.0.0` (version 2.x — native alias support, no_transaction parameter)

```robotframework
*** Settings ***
Library    DatabaseLibrary
Resource   db_variables.resource


*** Variables ***
${__DB_IN_TX}    ${EMPTY}


*** Keywords ***
# ── Connect ──────────────────────────────────────────────────────────────────

DB - Connect
    [Documentation]    Kết nối DB trực tiếp. alias cho phép kết nối nhiều DB cùng lúc.
    [Arguments]    ${alias}=default
    IF    '${DB_TYPE}' == 'mariadb' or '${DB_TYPE}' == 'mysql'
        ${conn_str}=    Set Variable
        ...    host='${DB_HOST}', port=${DB_PORT}, user='${DB_USER}', password='${DB_PASS}', database='${DB_NAME}', charset='${DB_CHARSET}', cursorclass=pymysql.cursors.DictCursor
        Connect To Database Using Custom Params    pymysql    ${conn_str}    alias=${alias}
    ELSE IF    '${DB_TYPE}' == 'postgresql'
        ${conn_str}=    Set Variable
        ...    host='${DB_HOST}', port=${DB_PORT}, user='${DB_USER}', password='${DB_PASS}', database='${DB_NAME}'
        Connect To Database Using Custom Params    psycopg2    ${conn_str}    alias=${alias}
    ELSE IF    '${DB_TYPE}' == 'mssql'
        ${conn_str}=    Set Variable
        ...    server='${DB_HOST}', port=${DB_PORT}, user='${DB_USER}', password='${DB_PASS}', database='${DB_NAME}'
        Connect To Database Using Custom Params    pymssql    ${conn_str}    alias=${alias}
    ELSE IF    '${DB_TYPE}' == 'sqlite'
        Connect To Database Using Custom Params    sqlite3    database='${DB_NAME}'    alias=${alias}
    ELSE
        Fail    DB_TYPE không được hỗ trợ: ${DB_TYPE}. Hỗ trợ: mariadb, mysql, postgresql, mssql, sqlite.
    END

DB - Connect Via Tunnel
    [Documentation]    SSH tunnel → local port → DB. Copy automation_test/python_lib/db_tunnel.py vào project trước khi dùng.
    [Arguments]    ${alias}=default
    Import Library    automation_test/python_lib/db_tunnel.py    WITH NAME    DBTunnel_${alias}
    Run Keyword    DBTunnel_${alias}.Open Tunnel
    ...    ssh_host=${DB_TUNNEL_SSH_HOST}    ssh_port=${DB_TUNNEL_SSH_PORT}
    ...    ssh_user=${DB_TUNNEL_SSH_USER}    ssh_key=${DB_TUNNEL_SSH_KEY}
    ...    remote_host=${DB_HOST}    remote_port=${DB_PORT}    local_port=${DB_TUNNEL_LOCAL_PORT}
    IF    '${DB_TYPE}' == 'mariadb' or '${DB_TYPE}' == 'mysql'
        ${conn_str}=    Set Variable
        ...    host='127.0.0.1', port=${DB_TUNNEL_LOCAL_PORT}, user='${DB_USER}', password='${DB_PASS}', database='${DB_NAME}', charset='${DB_CHARSET}', cursorclass=pymysql.cursors.DictCursor
        Connect To Database Using Custom Params    pymysql    ${conn_str}    alias=${alias}
    ELSE IF    '${DB_TYPE}' == 'postgresql'
        ${conn_str}=    Set Variable
        ...    host='127.0.0.1', port=${DB_TUNNEL_LOCAL_PORT}, user='${DB_USER}', password='${DB_PASS}', database='${DB_NAME}'
        Connect To Database Using Custom Params    psycopg2    ${conn_str}    alias=${alias}
    ELSE
        Fail    DB - Connect Via Tunnel chỉ hỗ trợ mariadb, mysql, postgresql.
    END

DB - Disconnect
    [Documentation]    Đóng kết nối DB. Gọi trong Suite Teardown.
    [Arguments]    ${alias}=default
    Disconnect From Database    alias=${alias}

DB - Close Tunnel
    [Documentation]    Đóng SSH tunnel. Gọi sau DB - Disconnect.
    [Arguments]    ${alias}=default
    Run Keyword    DBTunnel_${alias}.Close Tunnel

# ── Transaction ───────────────────────────────────────────────────────────────

DB - Begin Transaction
    [Documentation]    Bắt đầu transaction. Dùng DB - Rollback trong [Teardown] để cleanup tự động.
    ...                Sau khi gọi, mọi DB - Execute sẽ không auto-commit cho đến khi Rollback/Commit.
    [Arguments]    ${alias}=default
    IF    '${DB_TYPE}' == 'mariadb' or '${DB_TYPE}' == 'mysql'
        Execute Sql String    START TRANSACTION    no_transaction=${TRUE}    alias=${alias}
    ELSE IF    '${DB_TYPE}' == 'mssql'
        Execute Sql String    BEGIN TRANSACTION    no_transaction=${TRUE}    alias=${alias}
    ELSE
        Execute Sql String    BEGIN    no_transaction=${TRUE}    alias=${alias}
    END
    Set Suite Variable    ${__DB_IN_TX}    ${alias}

DB - Commit
    [Documentation]    Commit transaction và kết thúc chế độ transaction.
    [Arguments]    ${alias}=default
    Execute Sql String    COMMIT    no_transaction=${TRUE}    alias=${alias}
    Set Suite Variable    ${__DB_IN_TX}    ${EMPTY}

DB - Rollback
    [Documentation]    Rollback transaction — an toàn dù TC pass hay fail.
    [Arguments]    ${alias}=default
    Execute Sql String    ROLLBACK    no_transaction=${TRUE}    alias=${alias}
    Set Suite Variable    ${__DB_IN_TX}    ${EMPTY}

# ── Query (primary use case) ──────────────────────────────────────────────────

DB - Query Row
    [Documentation]    Trả về row đầu tiên dạng tuple (index 0-based). ${NONE} nếu không có kết quả.
    [Arguments]    ${sql}    ${alias}=default
    ${results}=    Query    ${sql}    no_transaction=${TRUE}    alias=${alias}
    IF    len($results) == 0    RETURN    ${NONE}
    RETURN    ${results}[0]

DB - Query Value
    [Documentation]    Trả về giá trị cột đầu tiên, row đầu tiên. ${NONE} nếu không có kết quả.
    [Arguments]    ${sql}    ${alias}=default
    ${results}=    Query    ${sql}    no_transaction=${TRUE}    alias=${alias}
    IF    len($results) == 0    RETURN    ${NONE}
    RETURN    ${results}[0][0]

DB - Query Rows
    [Documentation]    Trả về list tất cả rows dạng tuple.
    [Arguments]    ${sql}    ${alias}=default
    ${results}=    Query    ${sql}    no_transaction=${TRUE}    alias=${alias}
    RETURN    ${results}

# ── Assert ────────────────────────────────────────────────────────────────────

DB - Assert Row Exists
    [Documentation]    Fail nếu query không trả về row nào.
    [Arguments]    ${sql}    ${msg}=Row not found in DB    ${alias}=default
    ${results}=    Query    ${sql}    no_transaction=${TRUE}    alias=${alias}
    Should Not Be Empty    ${results}    ${msg}

DB - Assert Row Not Exists
    [Documentation]    Fail nếu query trả về row.
    [Arguments]    ${sql}    ${msg}=Row still exists in DB    ${alias}=default
    ${results}=    Query    ${sql}    no_transaction=${TRUE}    alias=${alias}
    Should Be Empty    ${results}    ${msg}

DB - Assert Row Count
    [Documentation]    Fail nếu số rows không khớp expected.
    [Arguments]    ${sql}    ${expected}    ${alias}=default
    ${results}=    Query    ${sql}    no_transaction=${TRUE}    alias=${alias}
    Length Should Be    ${results}    ${expected}
    ...    Expected ${expected} rows but got ${results.__len__()}

DB - Assert Field Value
    [Documentation]    Assert giá trị theo index cột (0-based). Dùng số nguyên cho col_index.
    [Arguments]    ${sql}    ${col_index}    ${expected}    ${alias}=default
    ${row}=    DB - Query Row    ${sql}    ${alias}
    Should Be True    $row is not None    No row found for: ${sql}
    ${actual}=    Set Variable    ${row}[${col_index}]
    Should Be Equal As Strings    ${actual}    ${expected}
    ...    Col[${col_index}]: expected '${expected}' but got '${actual}'

# ── Async wait ────────────────────────────────────────────────────────────────

DB - Wait Until Row Exists
    [Documentation]    Poll DB cho đến khi row xuất hiện hoặc hết timeout.
    ...                Dùng khi API gọi xong nhưng background job chưa ghi DB ngay.
    [Arguments]    ${sql}    ${timeout}=30s    ${interval}=2s    ${alias}=default
    Wait Until Keyword Succeeds    ${timeout}    ${interval}
    ...    DB - Assert Row Exists    ${sql}    Row not found within ${timeout}    ${alias}

# ── Execute ───────────────────────────────────────────────────────────────────

DB - Execute
    [Documentation]    Chạy bất kỳ SQL nào. Tự động dùng no_transaction=True nếu đang trong transaction.
    [Arguments]    ${sql}    ${alias}=default
    IF    '${__DB_IN_TX}' == '${alias}'
        Execute Sql String    ${sql}    no_transaction=${TRUE}    alias=${alias}
    ELSE
        Execute Sql String    ${sql}    alias=${alias}
    END

# ── Write (dùng hạn chế) ─────────────────────────────────────────────────────

DB - Insert Row
    [Documentation]    ⚠️ Dùng hạn chế — ưu tiên tạo data qua API.
    ...                Insert 1 row. ${data} là dict {column: value}.
    [Arguments]    ${table}    ${data}    ${alias}=default
    ${cols}=    Evaluate    ', '.join($data.keys())
    ${vals}=    Evaluate    ", ".join(["'" + str(v).replace("'", "''") + "'" for v in $data.values()])
    DB - Execute    INSERT INTO ${table} (${cols}) VALUES (${vals})    ${alias}

DB - Delete Rows
    [Documentation]    ⚠️ Dùng hạn chế — ưu tiên DB - Rollback để cleanup.
    ...                Xoá rows theo điều kiện WHERE.
    [Arguments]    ${table}    ${where}    ${alias}=default
    DB - Execute    DELETE FROM ${table} WHERE ${where}    ${alias}

DB - Truncate Table
    [Documentation]    ⚠️ Dùng hạn chế — chỉ khi không còn cách nào khác.
    ...                Xoá toàn bộ data trong bảng.
    [Arguments]    ${table}    ${alias}=default
    DB - Execute    DELETE FROM ${table}    ${alias}
```

### `automation_test/python_lib/db_tunnel.py` (chỉ tạo khi có SSH tunnel)

Copy từ `.claude/skills/autotest-db/scripts/db_tunnel.py`.

### `automation_test/config/imports.resource` — thêm vào nếu chưa có

```robotframework
Resource    ../common/db_keywords.resource
```

### Format sau khi scaffold

```bash
python -m robotidy automation_test/common/db_keywords.resource automation_test/common/db_variables.resource
```

---

## Triết lý sử dụng DB trong automation

**DB chủ yếu dùng để đọc và verify — hạn chế tối đa việc ghi dữ liệu.**

| Mục đích | Cách ưu tiên | Dùng DB write khi |
|---|---|---|
| Tạo data cho test | Gọi API tạo data | API không có / môi trường không cho phép |
| Verify kết quả | `DB - Assert Row Exists` / `DB - Query Row` | — |
| Cleanup sau test | `DB - Rollback` (nếu dùng transaction) | Không dùng transaction |
| Reset state | Gọi API delete | Không có API |

**Thứ tự ưu tiên cleanup:** `DB - Rollback` > `DB - Delete Rows` > `DB - Truncate Table`

---

## Patterns tích hợp vào test suite

### Pattern 1 — Chỉ verify DB (phổ biến nhất)

```robotframework
*** Settings ***
Suite Setup     <Feature> Suite - Setup
Suite Teardown  <Feature> Suite - Teardown

*** Keywords ***
<Feature> Suite - Setup
    API - Create Session
    DB - Connect
    ${token}=    API - Login    ${API_USERNAME}    ${API_PASSWORD}
    Set Suite Variable    ${SUITE_TOKEN}    ${token}

<Feature> Suite - Teardown
    Delete All Sessions
    DB - Disconnect

# Trong feature keywords file
<Feature> - Create Order And Verify DB
    [Arguments]    ${test_data}
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    &{body}=    Create Dictionary    ...
    ${response}=    API - POST    ${EP_ORDER_CREATE}    ${body}    ${headers}
    ${order_id}=    Set Variable    ${response.json()}[id]
    DB - Assert Row Exists
    ...    SELECT * FROM orders WHERE id = '${order_id}' AND status = 'pending'
```

### Pattern 2 — Verify DB async (background job)

```robotframework
# API trả về ngay nhưng background job xử lý sau vài giây
<Feature> - Submit Payment And Wait DB
    [Arguments]    ${test_data}
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    ${response}=    API - POST    ${EP_PAYMENT}    ${test_data}    ${headers}
    ${payment_id}=    Set Variable    ${response.json()}[paymentId]
    # Chờ background job ghi DB — timeout 30s, check mỗi 2s
    DB - Wait Until Row Exists
    ...    SELECT * FROM payments WHERE id = '${payment_id}' AND status = 'COMPLETED'
    ...    timeout=30s    interval=2s
```

### Pattern 3 — Transaction để cleanup tự động

```robotframework
# Khi TC phải tạo data trực tiếp vào DB (không có API)
TC-101 Tạo đơn hàng khi có data seed
    [Tags]    order    db-setup    TC-101
    [Teardown]    DB - Rollback    # Tự động xoá sạch dù TC pass hay fail
    DB - Begin Transaction
    DB - Insert Row    orders    ${{ {'user_id': '99', 'status': 'draft', 'source': 'auto'} }}
    <Feature> - Trigger Order Processing    ...
    DB - Assert Row Exists    SELECT * FROM orders WHERE user_id = '99' AND status = 'processing'
```

### Pattern 4 — Kết nối 2 DB song song (multi-alias)

```robotframework
# Verify dữ liệu đồng bộ giữa main DB và audit DB
<Feature> Suite - Setup
    DB - Connect    alias=main
    DB - Connect Via Tunnel    alias=audit    # DB ở nước ngoài, qua SSH tunnel

<Feature> Suite - Teardown
    DB - Disconnect    alias=main
    DB - Disconnect    alias=audit
    DB - Close Tunnel    alias=audit

<Feature> - Verify Order Synced To Audit
    [Arguments]    ${order_id}
    DB - Assert Row Exists
    ...    SELECT * FROM orders WHERE id = '${order_id}'    alias=main
    DB - Wait Until Row Exists
    ...    SELECT * FROM audit_log WHERE order_id = '${order_id}'    alias=audit
    ...    timeout=60s
```

### Pattern 5 — SSH Tunnel (kết nối DB nước ngoài)

Khi `${DB_TUNNEL_SSH_HOST}` không rỗng → dùng `DB - Connect Via Tunnel`. Teardown theo đúng thứ tự:

```robotframework
<Feature> Suite - Teardown
    Delete All Sessions
    DB - Disconnect    alias=remote
    DB - Close Tunnel  alias=remote    # Luôn đóng tunnel SAU disconnect DB
```

---

## Khi TC cần ghi vào DB — phân tích và hỏi trước

TC chỉ **SELECT / assert** → viết code trực tiếp, không cần hỏi.

TC cần **INSERT / UPDATE / DELETE / DDL** (seed data, cleanup, reset state...) → **dừng lại, phân tích tác động, hỏi user confirm** trước khi viết bất kỳ dòng code nào.

**Nội dung cần phân tích và trình bày:**

> ⚠️ **TC này cần ghi vào DB**
>
> | | Chi tiết |
> |---|---|
> | **TC** | `<TC-NNN: tên TC>` |
> | **Mục đích ghi** | `<vd: seed order record trước khi chạy test>` |
> | **Bảng / dữ liệu bị ảnh hưởng** | `<vd: bảng orders — thêm 1 row với user_id = test_user>` |
> | **Rủi ro** | `<vd: nếu không cleanup, row tồn tại mãi trong DB test env>` |
> | **Kế hoạch cleanup** | `<vd: dùng DB - Rollback trong [Teardown] → tự xoá sau TC>` |
>
> Bạn có muốn tôi viết TC này với DB write không?

Chỉ tiếp tục sau khi user xác nhận. Nếu user không đồng ý → note lại TC đó là "cần xử lý thủ công" và bỏ qua.

**Sau khi được xác nhận — ưu tiên pattern transaction:**
- Wrap toàn bộ write trong `DB - Begin Transaction` + `[Teardown]    DB - Rollback`
- Mọi data tạo ra trong TC sẽ tự động bị xoá sau khi TC kết thúc, dù pass hay fail

---

## Hỏi user khi thiếu thông tin DB

Nếu `automation_test/common/db_variables.resource` chưa có hoặc còn placeholder → hỏi **một lần**, gộp tất cả:

> **Cần thông tin DB để kết nối:**
>
> 1. **DB type** — mariadb / mysql / postgresql / mssql / sqlite
> 2. **Host** — IP hoặc hostname (vd: `192.168.1.10`)
> 3. **Port** — mặc định MariaDB/MySQL: `3306`, PostgreSQL: `5432`, MSSQL: `1433`
> 4. **Database name**
> 5. **Username / Password**
> 6. **SSH tunnel?** — Nếu có: SSH host, SSH port, SSH user, đường dẫn SSH key

Sau khi user trả lời → cập nhật `automation_test/common/db_variables.resource` → tiếp tục.

---

## Rules

- **Không bao giờ hardcode credentials** trong keyword hay robot file — luôn dùng biến từ `db_variables.resource`
- **Chỉ dùng trong test environment** — `DB - Truncate Table` và `DB - Delete Rows` nguy hiểm nếu chạy nhầm production
- **SQL injection safe** — khi build SQL từ test data, wrap value trong quotes; không concat input user trực tiếp
- **Luôn Disconnect trong Suite Teardown** — tránh connection leak
- **Tunnel phải đóng sau Disconnect** — không được đóng tunnel trước DB connection
- **Tag TC có DB operation** thêm `db-assert` / `db-setup` / `db-teardown` để dễ filter