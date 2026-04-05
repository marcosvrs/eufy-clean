# Eufy P2P Protocol — Map Data & MITM Capture Guide

## Background

The Eufy Clean app displays a live map during cleaning that includes:
- Real-time robot position and cleaning path
- Room boundaries, obstacles, restricted zones
- Dock location and robot orientation

The MQTT channel (see [MQTT_PROTOCOL.md](./MQTT_PROTOCOL.md)) provides **commands and status** but only partial map data:
- **DPS 165** (`MAP_DATA`): Room names and IDs via `UniversalDataResponse`/`RoomParams` protobuf
- **DPS 179** (`STATUS_REPORT`): Real-time position telemetry every ~2s (see [DPS_179_TELEMETRY.md](./DPS_179_TELEMETRY.md))

Full pixel-level map rendering (the colorful floor plan in the app) is believed to use a **separate P2P data channel** defined in `p2pdata.proto`.

## What We Know

### P2P Protobuf Definitions (`proto/cloud/p2pdata.proto`)

The codebase includes a `p2pdata.proto` with detailed map data structures:

#### `MapChannelMsg` — Top-level P2P map envelope
- `MAP_INFO` (type 0): Real-time map data (pushed, no request needed)
- `MULTI_MAP_RESPONSE` (type 1): Multi-map management (requires DP request)

#### `MapInfo` — Single map frame
Contains `map_width`, `map_height`, `origin` (Point), `docks` (Pose list), plus a `msg_type` oneof:
| msg_type | Payload | Description |
|----------|---------|-------------|
| `MAP_REALTIME` (0) | `MapPixels` | Live SLAM pixel data |
| `MAP_ROOMOUTLINE` (1) | `MapPixels` | Room partition overlay |
| `OBSTACLE_INFO` (2) | `ObstacleInfo` | Detected obstacles |
| `RESTRICT_ZONES` (3) | `RestrictedZone` | No-go/no-mop zones |
| `ROOM_PARAMS` (4) | `RoomParams` | Per-room cleaning config |
| `CRUISE_DATA` (5) | `CruiseData` | Patrol/cruise data |
| `TEMPORARY_DATA` (6) | `TemporaryData` | Transient state |

#### `MapPixels` — Pixel data format
- `pixels` (bytes): **LZ4-compressed** pixel grid
- `pixel_size` (uint32): Decompressed size
- **Real-time map**: 1 byte = 4 pixels (2 bits each): `0x00`=unknown, `0x01`=obstacle, `0x02`=cleanable, `0x03`=carpet
- **Partition map**: 1 byte = 1 pixel: low 2 bits = pixel type, high 6 bits = room ID (0-31 valid, 60=no room, 61=gap, 62=obstacle, 63=unknown)

#### `CompletePath` — Robot path history
- `path` (bytes): LZ4-compressed path points
- Each point = 5 bytes: X (2 bytes signed), Y (2 bytes signed), flags byte
- Flags: bits 0-3 = type (0=sweep, 1=mop, 2=sweep+mop, 3=navigate, 4=go-home), bit 4 = new segment

### Camera P2P vs Vacuum P2P

The `eufy-security-client` library implements P2P for **cameras and doorbells only** using:
- Custom UDP-based protocol with STUN/TURN-like hole punching
- Device credentials from Eufy cloud API
- Both LAN (local) and WAN (remote) connectivity

**This does NOT apply to vacuums.** The vacuum's P2P channel appears to be a different mechanism, likely tunneled through the same AWS IoT infrastructure or via a direct LAN connection during active app usage.

### What the Eufy App Does (Hypothesis)

When viewing the live map in the Eufy Clean app:
1. App connects to the vacuum via cloud MQTT for commands/status
2. App may open a **separate data channel** for high-bandwidth map pixel data
3. This channel carries `MapChannelMsg` protobuf frames with LZ4-compressed pixel grids
4. The `smart/mb/in/{device_sn}` and `smart/mb/out/{device_sn}` MQTT topics may carry this data

---

## MITM Traffic Capture Procedure

### Goal

Intercept traffic between the Eufy Clean mobile app and the vacuum to identify:
1. Whether map pixel data flows through MQTT (smart/mb topics) or a separate channel
2. The exact transport (TCP/UDP, port, TLS) for map data
3. Sample payloads to decode with `p2pdata.proto`

### Prerequisites

| Item | Notes |
|------|-------|
| Linux machine on same LAN | Needs root, two network paths recommended |
| Eufy X10 Pro Omni (T2351) | On same subnet, powered on and docked |
| Eufy Clean mobile app | On a phone also on the same subnet |
| `tcpdump` / `tshark` | Packet capture |
| `arpspoof` (dsniff) or `scapy` | ARP spoofing |
| `mitmproxy` (optional) | HTTP/HTTPS interception |
| `nmap` | Port scanning |

```bash
# Install tools (Debian/Ubuntu)
sudo apt install tcpdump tshark dsniff nmap
pip install scapy mitmproxy
```

### Step 1 — Identify Devices on Network

```bash
# Find vacuum IP (look for Anker/Eufy OUI or open port 6668)
sudo nmap -sn 192.168.1.0/24
sudo nmap -p 6668,8883,443,7000,9667,9668 192.168.1.0/24

# Note: vacuum IP, phone IP, gateway IP
```

### Step 2 — Baseline Traffic Capture (Passive)

Before any MITM, capture what the vacuum and phone send normally:

```bash
# Capture ALL traffic from vacuum
sudo tcpdump -i eth0 host <VACUUM_IP> -w /tmp/vacuum_baseline.pcap &

# Capture ALL traffic from phone
sudo tcpdump -i eth0 host <PHONE_IP> -w /tmp/phone_baseline.pcap &

# Now: open the Eufy Clean app, navigate to the map view
# Let it run for 60 seconds while viewing the live map
# Stop captures with Ctrl+C
```

Analyze the captures:
```bash
# What ports does the vacuum use?
tshark -r /tmp/vacuum_baseline.pcap -q -z conv,tcp
tshark -r /tmp/vacuum_baseline.pcap -q -z conv,udp

# What ports does the phone use?
tshark -r /tmp/phone_baseline.pcap -q -z conv,tcp
tshark -r /tmp/phone_baseline.pcap -q -z conv,udp

# Look for non-8883 connections (8883 = MQTT to Anker cloud)
tshark -r /tmp/vacuum_baseline.pcap -Y "tcp.port != 8883 && tcp.port != 443" -q -z conv,tcp
```

### Step 3 — Identify Map Data Channel

**What to look for in the passive capture:**

| Pattern | Interpretation |
|---------|---------------|
| Vacuum TCP/UDP to phone IP directly | **LAN P2P channel** — this is the map data |
| Phone TCP/UDP to vacuum IP directly | **LAN P2P channel** (phone-initiated) |
| Large packets (>1KB) on non-8883 ports | Likely LZ4-compressed map pixel frames |
| UDP traffic from vacuum to non-Anker IPs | Possible STUN/TURN for remote P2P |
| Traffic to `aiot-mqtt-eu.anker.com:8883` only | Map data may flow through smart/mb MQTT topics |

**Key ports to watch:**

| Port | Protocol | Expected Use |
|------|----------|-------------|
| 8883 | TCP/TLS | MQTT to `aiot-mqtt-eu.anker.com` (commands + status) |
| 443 | TCP/TLS | HTTPS API calls |
| 6668 | TCP | Legacy Tuya local protocol (may not be active on newer firmware) |
| 7000 | TCP | Potential P2P data channel |
| 9667-9668 | TCP/UDP | Potential P2P data channel |
| 32100-32200 | UDP | Eufy security P2P range (camera pattern, may apply) |
| Dynamic high ports | UDP | STUN/TURN hole punching |

### Step 4 — ARP Spoof for Deep Inspection

If map data flows through TLS connections that can't be passively read:

```bash
# Enable IP forwarding
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# ARP spoof: become the gateway for the vacuum
sudo arpspoof -i eth0 -t <VACUUM_IP> <GATEWAY_IP> &
sudo arpspoof -i eth0 -t <GATEWAY_IP> <VACUUM_IP> &

# Full packet capture with ARP spoof active
sudo tcpdump -i eth0 host <VACUUM_IP> -w /tmp/vacuum_mitm.pcap -s 0

# Trigger map activity: open app, view map, start a cleaning session
# Capture for 2-3 minutes

# Cleanup
sudo pkill arpspoof
echo 0 | sudo tee /proc/sys/net/ipv4/ip_forward
sudo arp -d <VACUUM_IP>
sudo arp -d <GATEWAY_IP>
```

### Step 5 — Analyze Captured Payloads

```bash
# Extract TCP streams
tshark -r /tmp/vacuum_mitm.pcap -q -z follow,tcp,raw,0 > /tmp/stream_0.hex

# Look for LZ4 magic bytes (0x04224D18) in any stream
tshark -r /tmp/vacuum_mitm.pcap -Y "data.data contains 04:22:4d:18"

# Look for protobuf-like patterns (field tags starting with 0x08, 0x0a, 0x10, 0x12)
# MapChannelMsg starts with field 1 (type) = varint, so first byte would be 0x08
tshark -r /tmp/vacuum_mitm.pcap -Y "data.data[0:1] == 08"

# Export all payloads from suspicious ports
tshark -r /tmp/vacuum_mitm.pcap -Y "tcp.port == <SUSPECT_PORT>" \
    -T fields -e data.data > /tmp/suspect_payloads.hex
```

### Step 6 — Decode with p2pdata.proto

```python
#!/usr/bin/env python3
"""Attempt to decode captured payloads as MapChannelMsg."""

import sys
import lz4.block
sys.path.insert(0, "custom_components/robovac_mqtt")
from proto.cloud.p2pdata_pb2 import MapChannelMsg, MapInfo, MapPixels

def try_decode(payload: bytes) -> None:
    # Try direct parse
    for offset in range(min(8, len(payload))):
        try:
            msg = MapChannelMsg()
            msg.ParseFromString(payload[offset:])
            print(f"  MapChannelMsg (offset {offset}): type={msg.type}")
            if msg.HasField("map_info"):
                mi = msg.map_info
                print(f"    MapInfo: {mi.map_width}x{mi.map_height}, "
                      f"msg_type={MapInfo.MapMsgType.Name(mi.msg_type)}")
                if mi.HasField("pixels"):
                    raw = lz4.block.decompress(
                        mi.pixels.pixels,
                        uncompressed_size=mi.pixels.pixel_size
                    )
                    print(f"    Pixels: {len(raw)} bytes decompressed")
            return
        except Exception:
            continue
    print("  Failed to decode as MapChannelMsg")

# Usage: python decode_map.py <hex_payload>
if __name__ == "__main__":
    data = bytes.fromhex(sys.argv[1])
    try_decode(data)
```

---

## Existing Tool: `tools/mitm_attack.py`

> **WARNING**: The existing `mitm_attack.py` targets **Tuya cloud domains** (`a1.tuyaeu.com`, `mqtt.tuyaeu.com`, etc.). The Eufy X10 Pro Omni does **NOT** use Tuya cloud. It uses Anker's AWS IoT Core (`aiot-mqtt-eu.anker.com`).

### What `mitm_attack.py` does:
1. ARP spoof to intercept vacuum traffic
2. DNS redirect Tuya domains to a local fake server
3. TLS server on ports 443, 8883, 1883, 6668, 9668, 80
4. Captures raw bytes, analyzes for MQTT CONNECT, protobuf, Tuya headers, 16-char keys
5. Runs `tcpdump` for full pcap capture

### Why it won't capture map data as-is:
- **Wrong DNS targets**: Tuya domains are not used by this device
- **Assumes TLS intercept**: The vacuum uses **mutual TLS** with client certificates pinned to Anker's CA — a fake cert will be rejected
- **Missing smart/mb analysis**: Doesn't look for the `smart/mb/` MQTT topic pattern
- **Missing LZ4/protobuf map decoding**: `analyze_capture()` only checks for Tuya headers and generic patterns

### How to adapt for map data capture:

If adapting the tool, redirect these domains instead:
```python
ANKER_DOMAINS = [
    "aiot-mqtt-eu.anker.com",
    "aiot-clean-api-pr.eufylife.com",
    "home-api.eufylife.com",
    "api.eufylife.com",
]
```

And add map-specific payload analysis:
```python
def analyze_map_payload(data: bytes) -> None:
    """Look for MapChannelMsg protobuf patterns."""
    # LZ4 frame magic
    if b'\x04\x22\x4d\x18' in data:
        print("LZ4 compressed frame detected")
    # MapChannelMsg field 1 (type) = varint
    if data[0:1] == b'\x08' and data[1:2] in (b'\x00', b'\x01'):
        print("Possible MapChannelMsg envelope")
    # MapPixels: field 1 (pixels) = length-delimited
    if data[0:1] == b'\x0a':
        print("Possible length-delimited protobuf (MapPixels?)")
```

---

## Smart/mb MQTT Topics

The `smart/mb/` topics are an alternative MQTT channel that may carry map data:

| Topic | Direction | Description |
|-------|-----------|-------------|
| `smart/mb/in/{device_sn}` | Device to cloud | Messages from vacuum |
| `smart/mb/out/{device_sn}` | Cloud to device | Messages to vacuum |

### Capturing smart/mb traffic

The `tools/eufy_mqtt_client.py` tool already supports capturing these topics:

```bash
# Capture all MQTT traffic including smart/mb topics
python3 tools/eufy_mqtt_client.py \
    --email "$EUFY_EMAIL" --password "$EUFY_PASSWORD" \
    --capture-dir /tmp/eufy_capture \
    --duration 120

# During capture: open the Eufy Clean app and view the live map
```

Smart/mb captures are saved under `{capture_dir}/smart_mb/` with hex dumps for binary payloads.

### What to look for in smart/mb captures:
- **Large payloads** (>1KB): Likely LZ4-compressed map pixel data
- **Frequent small payloads**: Position updates (compare with DPS 179)
- **Protobuf field tag 0x08 followed by 0x00 or 0x01**: `MapChannelMsg.type` enum
- **Binary blobs with LZ4 magic** (`04 22 4d 18`): Compressed map frames

---

## What to Save from a Capture Session

When performing any capture, save these artifacts for later analysis:

| Artifact | Location | Purpose |
|----------|----------|---------|
| Full pcap | `vacuum_capture.pcap` | Complete packet trace for replay |
| Connection summary | `connections.txt` | `tshark -q -z conv,tcp` output |
| Port scan results | `portscan.txt` | Which ports the vacuum listens on |
| smart/mb payloads | `smart_mb/*.json` | MQTT payloads from smart/mb topics |
| Non-MQTT TCP streams | `streams/*.bin` | Raw TCP payload data from non-8883 ports |
| DPS 179 payloads | `telemetry/*.json` | Position telemetry for correlation |
| Phone-to-vacuum flows | `p2p_candidates/*.bin` | Direct LAN traffic between phone and vacuum |
| App-triggered map data | `map_trigger/*.bin` | Payloads captured while app shows live map |

### File naming convention:
```
{timestamp}_{port}_{direction}_{size}bytes.bin
# Example: 20260405_143022_7000_outgoing_4096bytes.bin
```

---

## Summary of Research Status

| Question | Status | Notes |
|----------|--------|-------|
| Does the vacuum use P2P for maps? | **Likely yes** | `p2pdata.proto` exists with detailed map structures |
| Is it the same P2P as cameras? | **No** | Camera P2P is UDP with custom encryption; vacuum likely different |
| Does map data flow through MQTT? | **Partially** | DPS 165 has room names; DPS 179 has position. Full pixels unknown. |
| Do smart/mb topics carry map pixels? | **Unknown** | Needs capture while app views live map |
| What transport does the pixel data use? | **Unknown** | Needs passive capture (Step 2) to identify |
| Can we decode the pixel format? | **Yes** | `p2pdata.proto` fully documents the format |
| Can we render the map? | **Possible** | LZ4 decompress + 2-bit or 8-bit pixel grid + PIL rendering |

### Next Steps (requires physical device access)

1. **Passive capture** (Step 2): Identify what connections appear when the app shows the live map
2. **smart/mb capture**: Run `eufy_mqtt_client.py` with `--capture-dir` while viewing the map in the app
3. **Decode payloads**: Try parsing captured data as `MapChannelMsg` using the decode script in Step 6
4. **If LAN P2P found**: Document the port, handshake, and framing for direct connection
5. **If smart/mb carries map data**: Implement a parser in `api/parser.py` for the new topic
