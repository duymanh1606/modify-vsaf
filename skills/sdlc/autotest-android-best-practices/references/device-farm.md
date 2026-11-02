# MCloud Device Farm Reference

## Connection Details

| Field | Value |
|---|---|
| Type | Local device farm / Appium Grid |
| Host | `10.207.247.201` |
| Path | `/mcloud/wd/hub` |
| Auth | HTTP Basic Auth embedded in URL |
| URL pattern | `http://<username>:<access_key>@10.207.247.201/mcloud/wd/hub` |

Credentials come from environment variables — **never hardcode** in any file.

---

## Setup: Environment Variables

Set before running tests. Add to your shell profile for convenience:

```bash
export FARM_USERNAME=your_username
export FARM_ACCESS_KEY=your_access_key
```

Verify they are set:

```bash
echo "User: $FARM_USERNAME"
echo "Key: ${FARM_ACCESS_KEY:0:4}****"    # show only first 4 chars
```

---

## Running on Device Farm

### Single test case

```bash
export FARM_USERNAME=xxx && export FARM_ACCESS_KEY=yyy

robot --loglevel TRACE -d results/ \
  -v EXECUTION_TARGET:device_farm \
  -v DEVICE_UDID:ABC123SERIALXXX \
  -t "User_Can_Login_With_Valid_Credentials" \
  tests/login.robot
```

### Full suite on device farm

```bash
robot --loglevel TRACE -d results/ \
  -v EXECUTION_TARGET:device_farm \
  -v DEVICE_UDID:ABC123SERIALXXX \
  tests/login.robot
```

### Local (default — no extra flags needed)

```bash
robot --loglevel TRACE -d results/ tests/login.robot
```

---

## Finding Device UDID

**From MCloud web UI:**
1. Open `http://10.207.247.201/mcloud/` in a browser (use VPN if needed)
2. Log in with your MCloud credentials
3. Go to **Devices** list
4. Find your target device — the UDID / serial is shown in the device card

**From adb (if device is also connected locally):**

```bash
adb devices
# Output example:
# ABC123SERIALXXX    device
```

---

## `common_variables.resource` Template (device farm enabled)

```robotframework
*** Variables ***
${TIMEOUT_MIN}          5s
${TIMEOUT_DEFAULT}      15s
${TIMEOUT_MAX}          30s

# --- Execution target: local | device_farm ---
${EXECUTION_TARGET}     local

# --- Local device ---
${APPIUM_URL}           http://127.0.0.1:4723
${DEVICE_NAME}          emulator-5554
${PLATFORM_VERSION}     13
${APP_PACKAGE}          com.example.app
${APP_ACTIVITY}         com.example.app.MainActivity
${NO_RESET}             ${TRUE}

# --- Shared ---
${DEVICE_UDID}          ${EMPTY}

# --- MCloud Device Farm ---
${FARM_HOST}            10.207.247.201
${FARM_PATH}            /mcloud/wd/hub
# Credentials: set FARM_USERNAME and FARM_ACCESS_KEY as environment variables
```

---

## `Common - Open App Device Farm` Implementation

```robotframework
Common - Open App Device Farm
    [Arguments]    ${no_reset}
    ${username}=    Get Environment Variable    FARM_USERNAME
    ${access_key}=  Get Environment Variable    FARM_ACCESS_KEY
    ${farm_url}=    Set Variable    http://${username}:${access_key}@${FARM_HOST}${FARM_PATH}
    ${caps}=    Create Dictionary
    ...    platformName=Android
    ...    platformVersion=${PLATFORM_VERSION}
    ...    deviceName=${DEVICE_NAME}
    ...    automationName=UiAutomator2
    ...    appPackage=${APP_PACKAGE}
    ...    appActivity=${APP_ACTIVITY}
    ...    autoGrantPermissions=${TRUE}
    ...    noReset=${no_reset}
    ...    newCommandTimeout=300
    IF    '${DEVICE_UDID}' != '${EMPTY}'
        Set To Dictionary    ${caps}    udid=${DEVICE_UDID}
    END
    Open Application    ${farm_url}    &{caps}
```

---

## Parallel Execution on Device Farm

To run multiple suites in parallel (different devices simultaneously):

```bash
# Terminal 1 — device A
export FARM_USERNAME=xxx FARM_ACCESS_KEY=yyy
robot -d results/device-a/ \
  -v EXECUTION_TARGET:device_farm \
  -v DEVICE_UDID:DEVICE_A_SERIAL \
  tests/login.robot &

# Terminal 2 — device B
robot -d results/device-b/ \
  -v EXECUTION_TARGET:device_farm \
  -v DEVICE_UDID:DEVICE_B_SERIAL \
  tests/transfer.robot &

wait
```

Each process must use a **different `DEVICE_UDID`** and a **separate `-d` output directory** to avoid collisions.

For CI (e.g., GitHub Actions / Jenkins), set `FARM_USERNAME` and `FARM_ACCESS_KEY` as **CI secrets**, not in plain-text files.

---

## Troubleshooting Device Farm Errors

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Wrong credentials | Re-check `FARM_USERNAME` and `FARM_ACCESS_KEY` env vars |
| `No device with udid <id>` | Wrong or stale UDID | Get fresh UDID from MCloud web UI |
| Device busy / session already active | Another session holds the device | Pick a different `DEVICE_UDID` from available pool |
| Connection refused / timeout | VPN not connected | Connect to company VPN and retry |
| `ENV_MISSING: FARM_USERNAME` | Env vars not set in current shell | `export FARM_USERNAME=xxx` before running robot |
| Session starts but app doesn't launch | Wrong `APP_PACKAGE` or `APP_ACTIVITY` | Verify package/activity for the device farm build variant |
| Test runs locally but fails on farm | Device farm uses different Android version | Check `PLATFORM_VERSION` matches farm device, adjust locators if needed |
