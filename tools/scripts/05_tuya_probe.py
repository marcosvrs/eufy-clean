#!/usr/bin/env python3
"""
Phase 5: Probe the vacuum directly via Tuya local protocol.

Connects to the vacuum on port 6668 using tinytuya and dumps all DPS values,
including any map-related data points (path_data, command_trans, request).
Also attempts to trigger map data by sending 'get_map' commands.

Usage:
    python3 scripts/05_tuya_probe.py \
        --ip 192.168.1.XXX \
        --device-id DEVICE_ID \
        --local-key LOCAL_KEY \
        --version 3.3

To get your device_id and local_key, run:
    https://github.com/Rjevski/eufy-clean-local-key-grabber
or use the damacus/robovac HA integration (it extracts keys during setup).
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import tinytuya
except ImportError:
    print("ERROR: tinytuya not installed. Run: pip install tinytuya")
    sys.exit(1)


KNOWN_VACUUM_DPS = {
    "1": "switch_go (start/stop)",
    "2": "pause",
    "3": "switch_charge (return to dock)",
    "4": "mode",
    "5": "status",
    "6": "clean_time",
    "7": "clean_area",
    "8": "battery (electricity_left)",
    "9": "suction",
    "10": "cistern (water level)",
    "12": "seek (find robot)",
    "13": "direction_control",
    "14": "reset_map",
    "15": "path_data ⚡",
    "16": "command_trans ⚡",
    "17": "request ⚡",
    "18": "break_clean",
    "19": "fault",
    "20": "device_timer",
    "26": "map_data ⚡",
    "28": "clean_record ⚡",
    "101": "return_home_custom",
    "102": "map_data_v2 ⚡",
    "103": "path_data_v2 ⚡",
    "104": "clean_area_map ⚡",
}

MAP_RELATED_DPS = ["15", "16", "17", "26", "28", "102", "103", "104"]


def connect(ip: str, device_id: str, local_key: str, version: str) -> tinytuya.Device:
    d = tinytuya.Device(device_id, ip, local_key)
    d.set_version(float(version))
    d.set_socketPersistent(True)
    return d


def dump_all_dps(device: tinytuya.Device):
    print(f"\n[*] Querying all DPS values...")
    status = device.status()

    if "Error" in status:
        print(f"    ERROR: {status['Error']}")
        print(f"    Code: {status.get('Err', 'unknown')}")
        print(f"\n    Troubleshooting:")
        print(f"    - Wrong local_key? Re-extract from eufy-clean-local-key-grabber")
        print(f"    - Wrong version? Try 3.3, 3.4, or 3.5")
        print(f"    - Device offline? Check vacuum WiFi connection")
        return {}

    dps = status.get("dps", {})
    print(f"    Found {len(dps)} DPS values:\n")

    for dp_id, value in sorted(dps.items(), key=lambda x: int(x[0])):
        label = KNOWN_VACUUM_DPS.get(str(dp_id), "unknown")
        is_map = str(dp_id) in MAP_RELATED_DPS
        marker = "⚡" if is_map else "  "

        display_value = value
        if isinstance(value, str) and len(value) > 80:
            display_value = f"{value[:80]}... ({len(value)} chars)"

        print(f"    {marker} DPS {dp_id:>4}: {display_value}")
        print(f"           → {label}")

        if is_map and value:
            save_dps_payload(dp_id, value)

    return dps


def save_dps_payload(dp_id: str, value):
    output_dir = Path("output/dps_payloads")
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"dps_{dp_id}_{ts}.txt"
    path.write_text(str(value))

    if isinstance(value, str):
        try:
            import base64
            decoded = base64.b64decode(value)
            bin_path = output_dir / f"dps_{dp_id}_{ts}.bin"
            bin_path.write_bytes(decoded)
            print(f"           → Saved base64-decoded to {bin_path} ({len(decoded)} bytes)")
            print(f"             Header: {decoded[:32].hex()}")
        except Exception:
            pass


def trigger_map_request(device: tinytuya.Device):
    print(f"\n[*] Sending map request commands...")

    commands = [
        ("get_map", {"17": "get_map"}),
        ("get_both", {"17": "get_both"}),
        ("get_path", {"17": "get_path"}),
    ]

    for label, dps_payload in commands:
        print(f"\n    Sending request='{label}'...")
        try:
            device.set_multiple_values(dps_payload)
            time.sleep(2)

            status = device.status()
            dps = status.get("dps", {})

            for dp_id in MAP_RELATED_DPS:
                if dp_id in dps and dps[dp_id]:
                    value = dps[dp_id]
                    if isinstance(value, str) and len(value) > 0:
                        print(f"    ✅ DPS {dp_id} responded: {str(value)[:80]}...")
                        save_dps_payload(dp_id, value)
                    elif value:
                        print(f"    ✅ DPS {dp_id} responded: {value}")
        except Exception as e:
            print(f"    ❌ Failed: {e}")


def listen_for_updates(device: tinytuya.Device, duration: int):
    print(f"\n[*] Listening for async DPS updates ({duration}s)...")
    print(f"    Open the Eufy Clean app map view now!\n")

    start = time.time()
    update_count = 0

    while time.time() - start < duration:
        data = device.receive()
        if data and "dps" in data:
            update_count += 1
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            dps = data["dps"]
            for dp_id, value in dps.items():
                is_map = str(dp_id) in MAP_RELATED_DPS
                marker = "⚡" if is_map else "  "
                display = str(value)[:80] + "..." if len(str(value)) > 80 else str(value)
                print(f"  {marker} [{ts}] DPS {dp_id}: {display}")

                if is_map and value:
                    save_dps_payload(str(dp_id), value)

    print(f"\n    Received {update_count} update(s) in {duration}s")


def main():
    parser = argparse.ArgumentParser(description="Probe Eufy vacuum via Tuya local protocol")
    parser.add_argument("--ip", required=True, help="Vacuum IP address")
    parser.add_argument("--device-id", required=True, help="Tuya device ID")
    parser.add_argument("--local-key", required=True, help="Tuya local key")
    parser.add_argument(
        "--version", default="3.4",
        help="Tuya protocol version (try 3.3, 3.4, or 3.5)"
    )
    parser.add_argument(
        "--listen", type=int, default=60,
        help="Duration to listen for async updates (seconds)"
    )
    parser.add_argument(
        "--trigger-map", action="store_true",
        help="Send map request commands to the vacuum"
    )
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"  Eufy Vacuum Tuya Protocol Probe")
    print(f"{'='*60}")
    print(f"  IP:       {args.ip}")
    print(f"  Device:   {args.device_id}")
    print(f"  Version:  {args.version}")
    print(f"{'='*60}")

    device = connect(args.ip, args.device_id, args.local_key, args.version)

    dps = dump_all_dps(device)
    if not dps:
        print("\n[!] Could not read DPS. Check credentials and try a different --version.")
        sys.exit(1)

    if args.trigger_map:
        trigger_map_request(device)

    if args.listen > 0:
        listen_for_updates(device, args.listen)

    print(f"\n{'='*60}")
    print(f"  NEXT STEPS")
    print(f"{'='*60}")
    print(f"  If map DPS data was captured:")
    print(f"    python3 scripts/04_decode.py output/dps_payloads/")
    print(f"  If no map data appeared:")
    print(f"    Run 02_monitor.py while using the Eufy Clean app to")
    print(f"    identify the map data port (it may use a separate channel).")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
