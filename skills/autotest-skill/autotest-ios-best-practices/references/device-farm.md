# MCloud Device Farm Reference — iOS

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

```bash
export FARM_USERNAME=your_username
export FARM_ACCESS_KEY=your_access_key

# Verify
echo "User: $FARM_USERNAME"
echo "Key: ${FARM_ACCESS_KEY:0:4}****"
```

---

## Running on Device Farm

### Single test case

```bash
export FARM_USERNAME=xxx && export FARM_ACCESS_KEY=yyy

robot --loglevel TRACE -d results/ \
  -v EXECUTION_TARGET:device_farm \
  -v DEVICE_UDID:00008030-001234567890002E \
  -t "User_Can_Login_With_Valid_Credentials" \
  tests/login.robot
```

### Full suite on device farm

```bash
robot --loglevel TRACE -d results/ \
  -v EXECUTION_TARGET:device_farm \
  -v DEVICE_UDID:00008030-001234567890002E \
  tests/login.robot
```

### Local simulator (default — no extra flags)

```bash
robot --loglevel TRACE -d results/ tests/login.robot
```

---

## Finding iOS Device UDID

**From MCloud web UI:**
1. Open `http://10.207.247.201/mcloud/` in a browser (VPN if needed)
2. Log in with MCloud credentials
3. Go to **Devices** → filter by iOS
4. The UDID is shown in the device card

**For simulator (local only):**
```bash
xcrun simctl list devices | grep "iPhone 15"
# Output: iPhone 15 (XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX) (Booted)
```

**For real device connected locally:**
```bash
xcrun xctrace list devices
# Or: Finder → select device → click device name to reveal UDID
```

---

## `common_variables.resource` Template (iOS + device farm)

```robotframework
*** Variables ***
${TIMEOUT_MIN}          5s
${TIMEOUT_DEFAULT}      15s
${TIMEOUT_MAX}          30s

# --- Execution target: local | device_farm ---
${EXECUTION_TARGET}     local

# --- Local simulator/device ---
${APPIUM_URL}           http://127.0.0.1:4723
${DEVICE_NAME}          iPhone 15
${PLATFORM_VERSION}     17.0
${BUNDLE_ID}            com.example.app
${APP_PATH}             ${EMPTY}
${NO_RESET}             ${TRUE}

# --- Shared ---
${DEVICE_UDID}          ${EMPTY}

# --- MCloud Device Farm ---
${FARM_HOST}            10.207.247.201
${FARM_PATH}            /mcloud/wd/hub
# Credentials: FARM_USERNAME and FARM_ACCESS_KEY env vars only
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
    ...    platformName=iOS
    ...    platformVersion=${PLATFORM_VERSION}
    ...    deviceName=${DEVICE_NAME}
    ...    automationName=XCUITest
    ...    bundleId=${BUNDLE_ID}
    ...    autoAcceptAlerts=${FALSE}
    ...    noReset=${no_reset}
    ...    newCommandTimeout=300
    ...    wdaLaunchTimeout=120000
    ...    wdaConnectionTimeout=240000
    IF    '${DEVICE_UDID}' != '${EMPTY}'
        Set To Dictionary    ${caps}    udid=${DEVICE_UDID}
    END
    IF    '${APP_PATH}' != '${EMPTY}'
        Set To Dictionary    ${caps}    app=${APP_PATH}
        Remove From Dictionary    ${caps}    bundleId
    END
    Open Application    ${farm_url}    &{caps}
```

---

## Parallel Execution on Device Farm

```bash
# Terminal 1 — iOS device A
export FARM_USERNAME=xxx FARM_ACCESS_KEY=yyy
robot -d results/device-a/ \
  -v EXECUTION_TARGET:device_farm \
  -v DEVICE_UDID:00008030-AAAA \
  tests/login.robot &

# Terminal 2 — iOS device B
robot -d results/device-b/ \
  -v EXECUTION_TARGET:device_farm \
  -v DEVICE_UDID:00008030-BBBB \
  tests/profile.robot &

wait
```

Each process must use a **different `DEVICE_UDID`** and a **separate `-d` output directory**.

For CI: set `FARM_USERNAME` and `FARM_ACCESS_KEY` as **CI secrets**, not in plain-text files.

---

## Troubleshooting Device Farm — iOS

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Wrong credentials | Re-check env vars: `echo $FARM_USERNAME` |
| `No device with udid <id>` | Wrong or unavailable UDID | Get fresh UDID from MCloud web UI |
| Device busy | Another session holds the device | Pick a different UDID from available pool |
| Connection refused / timeout | VPN not connected | Connect to company VPN |
| `ENV_MISSING: FARM_USERNAME` | Env vars not set | `export FARM_USERNAME=xxx` before robot |
| WDA fails on farm | Farm device has stale WDA | Contact MCloud admin to restart device |
| App not found on farm device | App not installed on farm device | Check with admin — may need re-provisioning |
| Test passes locally fails on farm | iOS version mismatch | Check `PLATFORM_VERSION` matches farm device |
