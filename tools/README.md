# Eufy X10 Pro Omni — Local Map Extractor

Reverse-engineering toolkit for extracting and decoding vacuum map data from the Eufy X10 Pro Omni (T2351) over your local network. **Zero cloud dependency.**

## Prerequisites

```bash
pip install -r requirements.txt
sudo apt install nmap    # for network discovery
```

## Workflow

Run each phase in order. Each script tells you the next step.

### Phase 1 — Discover your vacuum

```bash
sudo python3 run.py discover
# or specify subnet:
sudo python3 run.py discover --subnet 192.168.1.0/24
```

Finds Tuya devices (port 6668) on your LAN. Records all open ports.

### Phase 2 — Monitor traffic

```bash
sudo python3 run.py monitor 192.168.1.XXX
```

Captures all traffic to/from the vacuum. **While running:** open the Eufy Clean app, view the map, start a cleaning session. Large packets on non-6668 ports are flagged as potential map data.

### Phase 3 — Extract payloads

```bash
python3 run.py extract output/pcaps/monitor_*.pcap \
    --vacuum-ip 192.168.1.XXX \
    --map-ports 8100,9000
```

Extracts binary payloads from the map-candidate ports identified in Phase 2.

### Phase 4 — Decode map data

```bash
python3 run.py decode output/map_payloads/port_XXXX_outgoing/
```

Brute-forces every combination of decompression method, header offset, and dimension detection. Renders successful decodes as PNG images in `output/map_renders/`.

### Phase 5 — Probe via Tuya protocol

```bash
python3 run.py probe \
    --ip 192.168.1.XXX \
    --device-id YOUR_DEVICE_ID \
    --local-key YOUR_LOCAL_KEY \
    --version 3.4 \
    --trigger-map
```

Connects directly to the vacuum's Tuya port (6668), dumps all DPS values, and optionally sends map request commands. Requires your device credentials from [eufy-clean-local-key-grabber](https://github.com/Rjevski/eufy-clean-local-key-grabber) or the damacus/robovac HA integration.

### Phase 6 — HA Integration

Once you've decoded the map format, the `ha_integration/camera.py` skeleton provides a camera entity. Update the decode parameters with your Phase 4 findings, then copy to `config/custom_components/eufy_vacuum_map/`.

## Project Structure

```
eufy-map-extractor/
├── run.py                          # CLI runner
├── requirements.txt
├── scripts/
│   ├── 01_discover.py              # Network recon
│   ├── 02_monitor.py               # Traffic capture
│   ├── 03_extract.py               # Payload extraction
│   ├── 04_decode.py                # Brute-force decoder
│   └── 05_tuya_probe.py            # Direct Tuya protocol probe
├── ha_integration/
│   └── camera.py                   # HA camera entity skeleton
└── output/
    ├── pcaps/                      # Captured traffic
    ├── map_payloads/               # Extracted binary data
    ├── map_renders/                # Decoded map images
    └── dps_payloads/               # DPS data from probe
```

## Getting Your Local Key

The Tuya local key is required for Phase 5 (direct protocol probe) and for the HA integration. Options:

1. **eufy-clean-local-key-grabber**: https://github.com/Rjevski/eufy-clean-local-key-grabber
2. **damacus/robovac HA integration**: extracts keys automatically during setup
3. **tinytuya wizard**: `python -m tinytuya wizard` (requires Tuya IoT developer account)

## Fixture Capture & Anonymization

Two-step workflow for recording live device data and turning it into safe, committed test fixtures.

### Step 1 — Capture raw data

Connect to your vacuum via cloud MQTT and save every HTTP response and MQTT message to disk:

```bash
python3 tools/eufy_mqtt_client.py \
    --email "$EUFY_EMAIL" --password "$EUFY_PASSWORD" \
    --capture-dir /tmp/eufy_capture \
    --duration 120
```

This creates `/tmp/eufy_capture/http/` (one JSON per API call) and `/tmp/eufy_capture/mqtt/` (one JSON per incoming message, named `{timestamp}_{dps_keys}.json`).

### Step 2 — Anonymize before committing

Strip emails, device serials, tokens, certificates, MAC addresses, and Wi-Fi details:

```bash
python3 tools/anonymize_fixtures.py \
    --input-dir /tmp/eufy_capture \
    --output-dir tests/fixtures
```

The anonymizer replaces PII with deterministic fakes (e.g. `T2351_ANON_001`) while preserving all protocol payloads, DPS values, model strings, and status codes verbatim. Timestamps are converted to zero-based relative offsets.
