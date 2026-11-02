---
name: autotest-mcp-assist
description: Supporting skill — bắt buộc dùng RobotMCP (rf-mcp, manykarim/rf-mcp) để phát hiện/verify locator bằng live session khi viết/debug script Web/Android/iOS, thay vì đoán rồi chạy lại cả suite. Hỗ trợ Web (SeleniumLibrary), Android/iOS (AppiumLibrary).
user-invocable: false
---

# RF-MCP-Assist Supporting Skill

Skill hỗ trợ — không có slash command riêng. Được đọc bởi `autotest-web`, `autotest-android`, `autotest-ios` ở bước tìm locator và ở vòng lặp debug khi TC fail vì sai locator. **Bắt buộc** cho cả 3 skill này — không phải bước tuỳ chọn.

> **Ngôn ngữ giao tiếp:** Mọi text hiển thị cho user trong lúc làm việc — tiến trình, câu hỏi, cảnh báo — viết bằng **tiếng Việt**. Giữ nguyên thuật ngữ kỹ thuật (locator, session, keyword, MCP...) không dịch.

---

## Cài đặt trước khi dùng (khuyến nghị — làm 1 lần trước khi gọi `/autotest-web`/`/autotest-android`/`/autotest-ios`)

```bash
# Chọn extra theo platform sẽ làm — hoặc [all] nếu làm nhiều platform
uv tool install "rf-mcp[web]"      # autotest-web
uv tool install "rf-mcp[mobile]"   # autotest-android / autotest-ios
uv tool install "rf-mcp[all]"      # cả 3 + api + database

# Đăng ký MCP server cho đúng project hiện tại (KHÔNG phải template repo)
robotmcp install --agents all --scope project -C . --yes
```

Đăng ký cho **mọi agent** RobotMCP hỗ trợ (Claude Code, Codex, Gemini...), không riêng Claude Code — dùng chung 1 lần cài cho cả team dù ai dùng agent nào. Sau đó **mở phiên Claude Code mới** trong project rồi mới gọi `/autotest-web`/`/autotest-android`/`/autotest-ios` — MCP server mới đăng ký không nạp được vào phiên đang chạy dở.

Nếu `uv` chưa có: `pip install "rf-mcp[all]"` cũng cài được (executable `rf-mcp`/`robotmcp` vẫn có, chỉ khác cách quản lý venv).

**Bỏ qua bước này không sao** — nếu chưa cài mà đã gọi `/autotest-web`/`/autotest-android`/`/autotest-ios`, AI tự cài và tự đăng ký (xem Step 0 bên dưới), không cần làm gì thêm ngoài mở lại session khi được yêu cầu.

---

## Vấn đề skill này giải quyết

Cách cũ: viết `.robot` với locator đoán/suy từ đọc UI → chạy cả suite → fail ở 1 bước giữa chừng (sai locator) → phải chạy lại **từ đầu** để app quay lại đúng màn hình đó → sửa locator → chạy lại từ đầu lần nữa. Với mobile (Android/iOS), mỗi vòng lặp tốn cả việc mở lại app, login lại, điều hướng lại — rất mất thời gian.

RobotMCP giữ 1 session sống (browser/app không đóng) xuyên suốt nhiều lần gọi `execute_step`. Khi 1 step fail, session **không đóng** — app vẫn đứng nguyên tại màn hình đó. Gọi `get_session_state` lấy ngay DOM/UI-tree thật tại đúng thời điểm đó, sửa locator, gọi lại đúng step đó (không phải chạy lại từ đầu), rồi tiếp tục các step sau. Đã verify thật (không suy đoán) cho cả 3 nền tảng: Web (SeleniumLibrary + Chrome), Android (AppiumLibrary + UiAutomator2, emulator thật), iOS (AppiumLibrary + XCUITest, simulator thật) — session sống sót qua lỗi, `get_session_state(sections=['page_source'])` trả đúng element/locator thật của màn hình đang đứng, retry bằng locator đúng pass ngay không cần mở lại app.

**Đây là công cụ hỗ trợ khám phá/xác nhận locator — không thay quy trình viết file hiện có.** Sau khi verify xong 1 chuỗi step live-pass, Claude vẫn tự viết `_variables.resource`/`_keywords.resource`/`.robot` theo đúng FOM/AOM convention của `autotest-*-best-practices` (không dùng `build_test_suite` của RobotMCP để tự sinh file — output đó không theo tag/wrapper/robotidy convention của bộ skill này).

---

## Khi nào autotest-* skills dùng skill này

- **Web/Android/iOS** ở Step "Plan/Tìm locator" (trước khi ghi `_variables.resource`) — **luôn dùng**, không chỉ khi "chưa chắc": chạy thử từng step qua live session, xác nhận pass, rồi mới ghi vào file. Đây là cách chính để giảm thời gian viết script — không phải phương án dự phòng.
- Ở **vòng lặp debug** khi `robot` chạy fail vì locator sai/element không tìm thấy — dùng thay cho việc chạy lại cả suite.
- autotest-api **không dùng** skill này — API không có locator UI.

---

## Step 0 — Detect RobotMCP có sẵn không

```python
import shutil
has_cli = shutil.which("robotmcp") is not None
```

Kiểm tra tool `execute_step`/`get_session_state`/`manage_session` (thường xuất hiện dạng `mcp__robotmcp__...`) có nằm trong danh sách tool khả dụng của session hiện tại không.

- **Có tool + đã đăng ký MCP cho session hiện tại** → dùng theo hướng dẫn Step 1 trở xuống. Không hỏi lại, không cần xác nhận.
- **Chưa có tool** (dù CLI đã cài hay chưa) → **tự cài/đăng ký ngay, không hỏi xin phép** — xem Step Setup. Đây là hạ tầng bắt buộc của bộ skill, giống như Appium/adb/xcodebuild đã là prerequisite bắt buộc ở các bước khác.
  - Vẫn **thông báo rõ** cho user từng lệnh đang chạy (transparency), không âm thầm.
  - Sau khi cài/đăng ký xong → **dừng lại**, báo user:
    > Đã cài RobotMCP và đăng ký MCP server cho project. Mở phiên Claude Code mới rồi gọi lại lệnh này — MCP server mới đăng ký không nạp được vào phiên đang chạy.
    >
    > Lưu ý: lần đầu mở phiên mới, Claude Code có thể hỏi xác nhận "cho phép MCP server `robotmcp` trong `.mcp.json` của project này chạy không" (server mới trong `.mcp.json` ở trạng thái **chờ approve**, kiểm tra bằng `claude mcp list` nếu muốn) — bấm đồng ý 1 lần, không phải chỉ mở session mới là tự nhiên có tool.
  - Không tiếp tục viết code trong lượt này sau khi báo — chờ user mở session mới, approve nếu được hỏi, rồi gọi lại.
  - **Chạy headless/CI (không tương tác)**: prompt approve sẽ không hiện ra được — truyền rõ `--mcp-config .mcp.json --strict-mcp-config` khi gọi `claude -p ...` để tool nạp thẳng, không phụ thuộc trạng thái approve của `.mcp.json`.

---

## Step Setup — Tự cài đặt (khi Step 0 phát hiện thiếu)

Chạy được như nhau trên **Windows và macOS/Linux** — `uv`, `robotmcp`, Appium server đều là cross-platform. Chỉ khác nhau ở chỗ PATH được nạp lại như thế nào sau khi cài (xem cảnh báo PATH bên dưới).

```bash
# Chọn extra theo platform đang làm — hoặc [all] nếu làm nhiều platform
uv tool install "rf-mcp[web]"      # autotest-web
uv tool install "rf-mcp[mobile]"   # autotest-android / autotest-ios
uv tool install "rf-mcp[all]"      # cả 3 + api + database

# Đăng ký MCP server cho đúng project hiện tại (KHÔNG phải template repo)
robotmcp install --agents all --scope project -C . --yes
```

Đăng ký cho mọi agent RobotMCP hỗ trợ, không chỉ Claude Code. Lệnh trên ghi `.mcp.json` (và file cấu hình tương đương của các agent khác nếu có) vào project.

**Cảnh báo PATH (cả Windows và Mac/Linux):** `uv tool install` chỉ symlink/copy executable vào 1 thư mục (`~/.local/bin` trên Mac/Linux, `%USERPROFILE%\.local\bin` trên Windows) — **không tự thêm vào PATH**. Nếu `shutil.which("robotmcp")` vẫn trả `None` ngay sau khi cài trong cùng shell session:

```bash
uv tool update-shell
```

rồi kiểm tra lại `shutil.which("robotmcp")`. Nếu vẫn `None` (PATH chỉ áp dụng cho shell mới, không áp dụng cho process con hiện tại) → không chặn, coi CLI đã cài thành công (bước `robotmcp install` chỉ cần gọi được 1 lần từ đúng thư mục cài, không phải mọi lần); phần MCP tool (`execute_step`...) vẫn chỉ có hiệu lực sau khi user mở phiên Claude Code mới như đã báo ở Step 0 — lúc đó PATH của shell mới đã có `robotmcp`, không cần thao tác thêm.

> Extra `[web]` cài kèm cả `robotframework-browser` (Playwright) lẫn `robotframework-seleniumlibrary` — không có extra riêng chỉ Selenium. Không sao: bộ skill này không bao giờ gọi tới Browser, gói đó chỉ nằm đó không dùng tới (xem Step 1a).
>
> Nếu `uv` chưa có: thử `pip install "rf-mcp[all]"` (không cần `uv`). Nếu `pip` cũng không chạy được hoặc không có mạng — đây là lỗi môi trường thật, không phải điều skill có thể tự sửa: báo lỗi rõ cho user (đúng lệnh nào fail, thông báo lỗi gì) và yêu cầu user tự xử lý môi trường (mạng/quyền cài package) trước khi tiếp tục, tương tự cách xử lý khi thiếu Appium/adb/xcodebuild.

---

## Step 1 — Quy trình dùng RobotMCP (khi đã sẵn sàng)

### 1a. Luôn ép đúng library — không để RobotMCP tự chọn

Bộ skill này chỉ dùng **SeleniumLibrary** cho web (đúng convention của `autotest-web-best-practices`) — **không dùng Browser/Playwright**, không có ngoại lệ. `analyze_scenario`/`execute_step` tự động của RobotMCP có thể tự chọn Browser (Playwright) nếu không được ép rõ — luôn khởi tạo session tường minh bằng `manage_session` trước, đừng để tự chọn:

```
manage_session(action="init", session_id="<tc_id>", libraries=["SeleniumLibrary"])   # web — luôn dùng cái này, dùng Chrome hệ thống, Selenium Manager tự lo driver
manage_session(action="init", session_id="<tc_id>", libraries=["AppiumLibrary"])     # android / ios
```

Mọi `execute_step` sau đó dùng prefix `Library.Keyword` (vd `SeleniumLibrary.Click Element`, `AppiumLibrary.Click Element`) — không bao giờ gọi keyword không có prefix cho web (dễ bị RobotMCP tự route sang Browser).

### 1b. Chạy từng step, xem kết quả thật

```
execute_step(session_id="<tc_id>", keyword="SeleniumLibrary.Open Browser",
             arguments=["<url>", "headlesschrome"])
execute_step(session_id="<tc_id>", keyword="SeleniumLibrary.Input Text",
             arguments=["id=username", "demo"])
```

Web (headless mặc định `headlesschrome` — đủ để verify locator, không cần mở cửa sổ). Mobile cần capabilities đầy đủ trong `arguments`:

```
execute_step(session_id="<tc_id>", keyword="AppiumLibrary.Open Application", arguments=[
    "http://127.0.0.1:4723",
    "platformName=Android", "automationName=UiAutomator2",
    "deviceName=<device_or_emulator_id>",
    "appPackage=<package>", "appActivity=<activity>",
    "newCommandTimeout=120",
])
```

iOS tương tự nhưng `platformName=iOS`, `automationName=XCUITest`, `udid=<simulator_or_device_udid>`, `bundleId=<bundle_id>` thay cho `appPackage`/`appActivity`.

### 1c. Khi 1 step fail — đừng chạy lại từ đầu

```
execute_step(..., raise_on_failure=False)   # không throw, trả lỗi trong payload để đọc tiếp
```

**Luôn dùng timeout ngắn (≤10s)** cho keyword đang verify (vd `Wait Until Element Is Visible    <locator>    5`) — không để trống/không truyền timeout rất lớn. Từng lệnh `execute_step` đã tự có timeout mặc định hợp lý (không treo), nhưng nếu tự tay truyền timeout hàng trăm/nghìn giây, nó sẽ tôn trọng đúng con số đó thật — đã tự verify: 1 lệnh với timeout ép rất lớn không trả về sau 20s dù đợi thêm. Timeout ngắn giữ mỗi lần thử nhanh, phù hợp với đúng tinh thần "verify sống" của skill này.

Session **vẫn sống** — app/browser vẫn đứng nguyên màn hình lúc fail. Lấy locator/element thật tại đúng chỗ đó:

```
get_session_state(session_id="<tc_id>", sections=["page_source"])
```

- Web: trả `context.forms/buttons/inputs/links` đã bóc tách sẵn id/name/text — không cần tự đọc raw HTML.
- Mobile: trả nguyên UI hierarchy XML (`resource-id`, `class`, `bounds`...) của màn hình hiện tại.

Nếu cần gợi ý thêm: `get_locator_guidance(library="SeleniumLibrary"|"AppiumLibrary", error_message="<lỗi vừa gặp>")`.

Sửa locator xong → gọi lại **đúng `execute_step` đó** với locator mới — không cần mở lại app, không cần login/điều hướng lại. Tiếp tục các step còn lại trong TC.

**Giới hạn 3 lần thử live cho cùng 1 step.** Mỗi lần fail đều nhanh (không treo — xem trên), nhưng nếu phần tử thật sự không có trên màn hình đó (sai màn hình, feature chưa làm, quyền bị ẩn...) thì cứ `get_session_state` → đoán locator khác → fail → lặp lại sẽ không có điểm dừng. Dựa trên quan sát thật: locator sai nhưng phần tử vẫn tồn tại luôn tìm ra fix đúng ngay ở lần inspect đầu; fail 3 lần liên tiếp với 3 locator khác nhau là tín hiệu mạnh cho thấy vấn đề không phải ở locator.

Sau lần fail thứ 3 cho cùng 1 step → **dừng vòng lặp tự đoán, không dừng session.** Cụ thể:
- **Không đóng/mở lại app** — session vẫn đứng nguyên đúng màn hình đang fail, đây chính là giá trị cốt lõi của skill này, kể cả lúc phải dừng lại hỏi user.
- Báo user nguyên văn những gì `get_session_state`/screenshot thấy thật ở màn hình hiện tại (không suy đoán thêm).
- Áp dụng đúng nguyên tắc "Stop if UI contradicts TC" (CLAUDE.md gốc) — hỏi user: TC sai bước, UI đã đổi khác TC, hay user biết locator đúng.
- Chỉ đóng/mở lại app nếu **user chủ động** yêu cầu điều hướng lại từ đầu — không phải hành vi tự động mặc định.

### 1d. Dọn session

```
execute_step(session_id="<tc_id>", keyword="SeleniumLibrary.Close Browser", arguments=[])
# hoặc AppiumLibrary.Close Application
```

---

## Step 2 — Ghi lại vào FOM/AOM sau khi verify xong

Sau khi toàn bộ chuỗi step của 1 TC đã live-pass qua RobotMCP, **Claude tự viết** — không copy nguyên `build_test_suite` của RobotMCP:

- Locator đã verify → `<feature>_variables.resource` (đúng naming convention của `autotest-*-best-practices`, không phải tên biến RobotMCP tự đặt).
- Chuỗi step → `<feature>_keywords.resource`, theo đúng quy tắc common wrapper (`Common - Click Element`, không gọi raw `SeleniumLibrary.Click Element` trong file cuối).
- Test case → `.robot` theo cấu trúc TC-NNN như bình thường.

RobotMCP chỉ có nhiệm vụ giúp **xác nhận locator đúng trước khi ghi**, không phải nguồn sinh code cuối cùng.

---

## Giới hạn đã biết

- Session MCP **không** tự nạp vào phiên Claude Code đang chạy — chỉ có hiệu lực từ lần khởi động lại sau khi đăng ký. Không có cách nào bỏ qua giới hạn này — mọi lần đăng ký MCP server lần đầu cho một project đều cần 1 lần restart.
- **Restart chưa đủ — còn cần approve.** Đã tự verify thật: sau khi đăng ký `.mcp.json` và mở phiên mới, server vẫn ở trạng thái **chờ approve** (`claude mcp list` báo "⏸ Pending approval") — tool chỉ nạp sau khi user đồng ý 1 lần (tương tác) hoặc khi gọi với `--mcp-config .mcp.json --strict-mcp-config` (headless/CI). Chỉ "mở session mới rồi gọi lại" không tự động có tool nếu chưa qua bước approve/flag này.
- Web: RobotMCP tự động có thể chọn Browser/Playwright nếu không ép rõ library — bộ skill này quy định chỉ dùng SeleniumLibrary, luôn ép tường minh theo Step 1a, không phụ thuộc việc máy có cài được Playwright browser hay không.
- Tài liệu gốc của RobotMCP mô tả sơ sài phần Appium/device farm — đã tự verify thật cơ chế session-persist cho Android (UiAutomator2) và iOS (XCUITest) hoạt động đúng như Web, nhưng chưa verify riêng với remote device farm (MCloud) — nếu `remote_url`/capabilities trỏ device farm mà lỗi, báo user và xử lý như lỗi môi trường thật (xem Step Setup), không tự âm thầm quay lại quy trình cũ.
- **Windows và macOS/Linux đều dùng được** cho Web (SeleniumLibrary) và Android (AppiumLibrary/UiAutomator2) — `uv`/`robotmcp`/Appium server cross-platform. Riêng **iOS chỉ chạy trên macOS** — không phải giới hạn riêng của RobotMCP, mà vì `autotest-ios` bản thân đã yêu cầu macOS + Xcode (XCUITest/simulator không chạy trên Windows/Linux); trên Windows/Linux, `autotest-mcp-assist` chỉ có tác dụng với Web và Android.
- **`execute_step` không tự giới hạn timeout nếu bạn tự ép một con số lớn.** Mỗi lệnh đã có timeout mặc định hợp lý theo loại keyword (không cần lo treo ở điều kiện thường), nhưng đã tự verify thật: nếu tự truyền timeout hàng trăm/nghìn giây cho keyword (vd `Wait Until Element Is Visible <locator> 9999`), nó **tôn trọng đúng con số đó** — 1 lệnh như vậy không trả về sau 20s dù đợi thêm. Luôn dùng timeout ngắn (≤10s) khi verify locator qua live session (xem Step 1c).
- **"Verify được" ≠ "verify đúng".** `get_session_state`/`execute_step` xác nhận locator **resolve ra được 1 element sống** — không xác nhận element đó có đúng là cái TC đang cần hay không. Đã tự bắt được false positive thật: locator `contains(@label,'Wi-Fi')` trên iOS Settings search match trúng **icon Wi-Fi ở status bar** (luôn hiển thị trên mọi màn hình) thay vì kết quả search thật — RobotMCP báo live-pass, `robot` chạy PASS, nhưng test không verify đúng cái cần verify. Locator dùng `contains()` trên attribute rộng (`label`, `text`, `content-desc`, `class`) **luôn phải tự kiểm tra thêm**: element match có nằm trong đúng container kết quả/nội dung không, hay nằm ở vùng UI hệ thống (status bar, nav bar, keyboard) luôn hiện diện bất kể hành động test. Xem quy tắc chi tiết ở `autotest-web-best-practices` / `autotest-android-best-practices` / `autotest-ios-best-practices` (mục "Danger of Matching System Chrome" / "Verify Locators Before Using").