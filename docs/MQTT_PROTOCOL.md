# Eufy X10 Pro Omni (T2351) — Cloud MQTT Control

## Discovery Summary

Through extensive reverse engineering, we discovered that the Eufy X10 Pro Omni
does NOT use the standard Tuya cloud infrastructure. Instead, it uses **Anker's
own AWS IoT Core MQTT infrastructure** with mutual TLS (client certificate)
authentication.

This document describes how to authenticate and connect to your vacuum's MQTT
broker to receive status updates and send commands.

## Architecture

```
┌──────────────┐     TLS 1.3 (mTLS)      ┌─────────────────────────┐
│  Your Client ├─────────────────────────►│ aiot-mqtt-eu.anker.com  │
│  (Python)    │   Client cert + key      │ AWS IoT Core (port 8883)│
└──────────────┘                          └────────────┬────────────┘
                                                       │
                                          ┌────────────▼────────────┐
                                          │   Eufy X10 Pro Omni     │
                                          │   (T2351)               │
                                          │   192.168.1.XXX         │
                                          └─────────────────────────┘
```

## Authentication Flow

Three API calls are required to obtain MQTT credentials:

### Step 1 — Eufy Login

```
POST https://home-api.eufylife.com/v1/user/email/login
```

Returns `access_token` and `user_info.id`.

### Step 2 — Get User Center Token

```
GET https://api.eufylife.com/v1/user/user_center_info
Header: token: <access_token from step 1>
```

Returns `user_center_token` and `user_center_id`.
Compute `gtoken = MD5(user_center_id)`.

### Step 3 — Get MQTT Certificates

```
POST https://aiot-clean-api-pr.eufylife.com/app/devicemanage/get_user_mqtt_info
Headers:
  x-auth-token: <user_center_token from step 2>
  gtoken: <MD5 hash from step 2>
  app-name: eufy_home
```

Returns:
- `certificate_pem` — X.509 client certificate
- `private_key` — RSA private key
- `aws_root_ca1_pem` — AWS root CA certificate
- `endpoint_addr` — `aiot-mqtt-eu.anker.com`
- `thing_name` — MQTT client ID prefix

## MQTT Connection

| Parameter | Value |
|-----------|-------|
| **Broker** | `aiot-mqtt-eu.anker.com` |
| **Port** | `8883` |
| **Protocol** | MQTT 3.1.1 over TLS 1.2+ |
| **Auth** | Mutual TLS (client certificate) |
| **Client ID** | `{thing_name}_{random_5_digits}` |

## MQTT Topics

### Subscribe (receive data from vacuum)

| Topic | Purpose |
|-------|---------|
| `cmd/eufy_home/T2351/{device_sn}/res` | Command responses and device status |
| `smart/mb/in/{device_sn}` | Smart messages from device |

### Publish (send commands to vacuum)

| Topic | Purpose |
|-------|---------|
| `cmd/eufy_home/T2351/{device_sn}/req` | Send commands |
| `smart/mb/out/{device_sn}` | Smart messages to device |

## Message Format

### Outbound (commands)

```json
{
  "head": {
    "client_id": "android-eufy_home-eufy_android_{user_id}",
    "cmd": 65537,
    "cmd_status": 2,
    "msg_seq": 1,
    "timestamp": 1775083844,
    "version": "1.0.0.1"
  },
  "payload": "{\"account_id\":\"<user_id>\",\"device_sn\":\"<device_sn>\",\"protocol\":2,\"t\":1775083844000,\"data\":{\"152\":true}}"
}
```

Note: `payload` is a JSON-encoded string, not a nested object.

### Inbound (responses)

```json
{
  "head": {
    "version": "1.0.0.2",
    "client_id": "ANON_DEVICE_ID_001",
    "cmd": 65537,
    "cmd_status": 1,
    "msg_seq": 21593,
    "timestamp": 1775083815
  },
  "payload": {
    "protocol": 1,
    "t": 1775083815624,
    "account_id": "<user_id>",
    "device_sn": "ANON_DEVICE_ID_001",
    "data": {
      "163": 99,
      "179": "PRI7ggE4EjYKNPMH6QfaB88HxAe7B7QH..."
    }
  }
}
```

## DPS (Data Points)

| DPS | Name | Type | Description |
|-----|------|------|-------------|
| 152 | PLAY_PAUSE | bool | Start/pause cleaning |
| 153 | WORK_STATUS | int | Current work mode |
| 154 | CLEANING_PARAMETERS | base64 protobuf | Cleaning configuration |
| 155 | DIRECTION | int | Direction control |
| 158 | CLEAN_SPEED | int | 0=Quiet, 1=Standard, 2=Turbo, 3=Max |
| 160 | FIND_ROBOT | bool | Locate (beep) |
| 163 | BATTERY_LEVEL | int | Battery percentage (0-100) |
| 167 | CLEANING_STATISTICS | base64 protobuf | Cleaning history |
| 168 | ACCESSORIES_STATUS | base64 protobuf | Brush/filter wear |
| 173 | GO_HOME | bool | Return to dock |
| 179 | STATUS_REPORT | base64 protobuf | Periodic status update |

## Commands

| Action | DPS Payload |
|--------|-------------|
| Start auto clean | `{"152": true}` |
| Pause | `{"152": false}` |
| Return to dock | `{"173": true}` |
| Locate (beep) | `{"160": true}` |
| Fan speed: Quiet | `{"158": 0}` |
| Fan speed: Standard | `{"158": 1}` |
| Fan speed: Turbo | `{"158": 2}` |
| Fan speed: Max | `{"158": 3}` |

## Device Info (from API)

Endpoint: `POST https://aiot-clean-api-pr.eufylife.com/app/devicerelation/get_device_list`

Returns per device:
- `device_sn`, `device_name`, `device_model`
- `main_sw_version` (firmware)
- `wifi_ssid`, `wifi_mac`
- `device_status` (1=online)
- `mqtt_info.host`, `mqtt_info.port`

## Limitations

- **Map data** is not available via MQTT. It uses a separate P2P protocol
  defined in protobuf (`p2pdata.proto` in the `eufy-clean` library).
- **Real-time position** requires the P2P channel.
- **Cloud dependency**: the MQTT connection goes through `aiot-mqtt-eu.anker.com`.
  If Anker's servers go down, control is lost.

## References

- `martijnpoppen/eufy-clean` — TypeScript library implementing this protocol
- `thomluther/anker-solix-api` — Python library for Anker Solix (same MQTT infra)
- USENIX WOOT '24 — "Reverse Engineering the Eufy Ecosystem"
