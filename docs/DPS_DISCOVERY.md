# Eufy X10 Pro Omni (T2351) — Cloud API DPS Discovery

## Date: 2026-04-20 (updated)

## Source

Official DPS catalog retrieved from Eufy Cloud API:
```
POST https://aiot-clean-api-pr.eufylife.com/app/things/get_product_data_point
{"product_code": "T2351", "code": "T2351"}
```

Auth headers: `x-auth-token` (user_center_token), `gtoken` (md5 of user_center_id), `user-agent: EufyHome-Android-3.1.3-753`

## Official T2351 DPS Catalog

| DPS | Cloud Code | Mode | Type | Description (translated) | Integration Status |
|-----|-----------|------|------|--------------------------|-------------------|
| 150 | proto | rw | String | Reserved. Not used. | Skipped ✅ |
| 151 | power | rw | Bool | Send: false=shutdown. Report: false=shutting down, true=just booted and connected | Parsed ✅ — Binary sensor (power) |
| 152 | mode_ctrl | rw | Raw | Send: ModeCtrlRequest. Report: ModeCtrlResponse | Parsed ✅ |
| 153 | work_status | rw | Raw | Send: None. Report: WorkStatus | Parsed ✅ |
| 154 | clean_params | rw | Raw | Send: CleanParamRequest. Report: CleanParamResponse | Parsed ✅ |
| 155 | remote_ctrl | rw | Enum | Remote control. App enters RC mode via ModeCtrlRequest | Logged (UNHANDLED — RC state derived from WorkStatus) |
| 156 | pause_job | rw | Bool | Pause current job | Logged (UNHANDLED — pause derived from WorkStatus) |
| 157 | dnd | rw | Raw | Send: UndisturbedRequest. Report: UndisturbedResponse | Parsed ✅ — DND switch + time entities |
| 158 | suction_level | rw | Enum | Suction level setting | Parsed ✅ |
| 159 | boost_iq | rw | Bool | Boost IQ (auto-boost on carpet) | Parsed ✅ — Switch entity |
| 160 | calling_robot | rw | Bool | Find robot / locate | Parsed ✅ |
| 161 | volume | rw | Value | Voice volume. Range: 0-100, step: 1 | Parsed ✅ — Number entity |
| 162 | user_language | rw | Raw | Send: LanguageRequest. Report: LanguageResponse | Skipped (low value — language config) |
| 163 | bat_level | ro | Value | Battery level percentage | Parsed ✅ — Sensor (SensorDeviceClass.BATTERY) |
| 164 | timing | rw | Raw | Send: TimerRequest. Report: TimerResponse | Parsed ✅ — Schedule calendar + switch entities |
| 165 | reserved2 | rw | Raw | Reserved (NOT map data for T2351!) — Room segments via RoomParams | Parsed ✅ — Room segments |
| 166 | log_debug | rw | Raw | Send: DebugRequest. Report: DebugResponse | Skipped (debug protocol, low value) |
| 167 | clean_statistics | rw | Raw | Send: None. Report: CleanStatistics | Parsed ✅ |
| 168 | consumables | w | Raw | Send: ConsumableRequest. Report: ConsumableRuntime | Parsed ✅ |
| 169 | app_dev_info | rw | Raw | Send: AppInfo. Report: DeviceInfo | Parsed ✅ — Device info, firmware, WiFi |
| 170 | map_edit | rw | Raw | Send: MapEditRequest. Report: MapEditResponse | Parsed ✅ — Map edit diagnostic sensor |
| 171 | multi_maps_ctrl | rw | Raw | Send: MultiMapsCtrlRequest. Report: MultiMapsCtrlResponse | Parsed ✅ — Multi-map diagnostic |
| 172 | multi_maps_mng | rw | Raw | Send: MultiMapsManageRequest. Report: MultiMapsManageResponse | Parsed ✅ — Multi-map management diagnostic |
| 173 | station | rw | Raw | Send: StationRequest. Report: StationResponse | Parsed ✅ |
| 174 | media_manager | rw | Raw | Send: MediaManagerRequest. Report: MediaManagerResponse | Parsed ✅ — Media capture, record, resolution |
| 175 | reserved3 | rw | String | Reserved | Skipped ✅ |
| 176 | unisetting | rw | Raw | Universal device settings | Parsed ✅ — Switches (AI, pet mode, child lock, etc.) |
| 177 | error_warning | rw | Raw | Send: ErrorCode (suppression list). Report: ErrorCode | Parsed ✅ — Error sensor + new_code parsing |
| 178 | toast | rw | Raw | Send: PromptCode (suppression list). Report: PromptCode | Parsed ✅ — Notification sensor (58 mapped codes) |
| 179 | analysis | rw | Raw | Send: AnalysisRequest. Report: AnalysisResponse | Parsed ✅ — Position, battery, clean records, go-home |
| 180 | scenes | w | Raw | Send: SceneRequest. Report: SceneResponse | Parsed ✅ |

## Critical DPS Naming Discrepancies

The integration's `const.py` DPS_MAP was built from older Eufy models. For the T2351, several DPS keys have DIFFERENT meanings:

| DPS | const.py Label | T2351 Actual | Impact |
|-----|---------------|-------------|--------|
| 155 | DIRECTION | remote_ctrl | Low — both unused |
| 156 | MULTI_MAP_SW | pause_job | Medium — could expose pause toggle |
| 164 | MAP_EDIT | timing | **HIGH** — timer/schedule, NOT map editing |
| 165 | MAP_DATA | reserved2 | **HIGH** — map data was NEVER on this DPS for T2351 |
| 166 | MAP_STREAM | log_debug | **HIGH** — debug logging, NOT map streaming |
| 178 | keepalive | toast | Medium — prompt/notification messages, not keepalive |

**Implication**: The map data investigation was searching for data on DPS 165/166 that never existed on the T2351. Map data for this device model uses a completely different mechanism (MEGA API + S3).

## New Feature Opportunities

### Tier 1: Remaining Unparsed DPS Keys

Only 3 DPS keys remain unprocessed (all low value):

| DPS | Cloud Code | Reason |
|-----|-----------|--------|
| 150 | proto | Reserved, always None |
| 162 | user_language | Language config — not useful for HA |
| 166 | log_debug | Debug protocol — not useful for HA |

DPS 155 (remote_ctrl) and 156 (pause_job) are logged as UNHANDLED because their state is already derived from WorkStatus (DPS 153).

### Tier 2: Remaining Investigation Targets

| Feature | Notes |
|---------|-------|
| Map data (MEGA API) | Requires `X-Encryption-Info` header — needs app traffic capture |
| S3 map storage | Requires different auth — `get_oss_config` returns 401 |

## Cloud API Endpoints Discovered

### Working (authenticated with uc_token + gtoken)
| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `POST /app/devicerelation/get_device_list` | Device list | Full device info including tuya_pid, WiFi, firmware |
| `POST /app/things/get_product_data_point` | DPS catalog | Official DPS definitions per product model |

### Exist But Need Different Auth/Params
| Endpoint | Purpose | Status |
|----------|---------|--------|
| `/app/devicemanage/get_oss_config` | S3/OSS config | 401 without proper auth |
| `/app/devicemanage/get_s3_config` | S3 config | 401 without proper auth |
| `/app/devicemanage/get_storage_config` | Storage config | 401 without proper auth |
| `/app/devicemanage/get_file_url` | File download URL | 401 without proper auth |
| `/app/clean/get_map` | Map data | 401 without proper auth |
| `/app/clean/map_list` | Map list | 401 without proper auth |
| `/app/clean/realtime_map` | Realtime map | 401 without proper auth |
| `/app/devicerelation/get_map` | Map data | 401 without proper auth |

Note: These return 401 with bad auth but 404 with valid auth — meaning the PATH exists on the server but may require a different API version prefix or additional headers.

### MEGA API (mega-eu-pr.eufy.com)
| Endpoint | Purpose | Status |
|----------|---------|--------|
| `/v1/map` | Map data | 403 — requires `X-Encryption-Info` header |
| `/map/realtime` | Realtime map | 403 — requires `X-Encryption-Info` header |

## Device Details

- **Model**: Eufy X10 Pro Omni (T2351)
- **SN**: `<redacted>`
- **FW**: v3.4.85
- **IP**: `<redacted>`
- **MAC**: `<redacted>`
- **MQTT Thing**: `<redacted>`
- **Tuya PID**: `<redacted>`
- **S3 Bucket**: eufy-data-frankfurt (eu-central-1)
- **MEGA API**: mega-eu-pr.eufy.com

## Authentication Flow

```
1. POST https://home-api.eufylife.com/v1/user/email/login
   → access_token

2. GET https://api.eufylife.com/v1/user/user_center_info
   Headers: token={access_token}, clienttype=2, category=Home
   → user_center_token, user_center_id

3. AIOT API calls to https://aiot-clean-api-pr.eufylife.com/app/...
   Headers: x-auth-token={user_center_token}, gtoken={md5(user_center_id)},
            user-agent=EufyHome-Android-3.1.3-753, app-name=eufy_home
```
