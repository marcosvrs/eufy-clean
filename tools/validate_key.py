#!/usr/bin/env python3
"""
Eufy X10 Pro Omni — Key Validator & HA Configurator

Once you have the 16-character local key, run this script to:
1. Validate the key against the vacuum
2. Dump all DPS values
3. Show the exact tuya-local configuration to use in HA

Usage:
    python3 validate_key.py YOUR_16_CHAR_LOCAL_KEY

The key can be extracted from:
- Rooted Android: adb shell su -c "grep -r 'localKey' /data/data/com.eufylife.clean/"
- mitmproxy + Frida: intercept Eufy Clean app traffic
- Tuya IoT developer account: if you can link the device
"""

import json
import sys

try:
    import tinytuya
except ImportError:
    print("ERROR: pip install tinytuya")
    sys.exit(1)

DEVICE_ID = "ANON_DEVICE_ID"
VACUUM_IP = "192.168.1.XXX"  # Replace with your vacuum's IP
VACUUM_PORT = 9668
PROTOCOL = 3.5


def validate_key(local_key: str):
    print(f"{'='*60}")
    print(f"  Eufy X10 Pro Omni — Key Validation")
    print(f"{'='*60}")
    print(f"  Device ID:  {DEVICE_ID}")
    print(f"  IP:         {VACUUM_IP}")
    print(f"  Port:       {VACUUM_PORT}")
    print(f"  Protocol:   {PROTOCOL}")
    print(f"  Local Key:  {local_key}")
    print(f"{'='*60}")
    print()

    if len(local_key) != 16:
        print(f"⚠️  Key is {len(local_key)} chars (expected 16). Trying anyway...")

    d = tinytuya.Device(DEVICE_ID, VACUUM_IP, local_key, version=PROTOCOL)
    d.port = VACUUM_PORT
    d.set_socketTimeout(15)

    print("[*] Connecting to vacuum...")
    status = d.status()

    err = status.get("Err", "")
    error = status.get("Error", "")
    dps = status.get("dps", {})

    if dps:
        print(f"\n✅ KEY IS CORRECT! Connected successfully!\n")
        print(f"DPS Values:")
        for dp_id, value in sorted(dps.items(), key=lambda x: int(x[0])):
            display = str(value)[:80]
            print(f"  DPS {dp_id:>4}: {display}")

        print(f"\n{'='*60}")
        print(f"  tuya-local Configuration for Home Assistant")
        print(f"{'='*60}")
        print(f"  Go to: Settings → Devices & Services → Add Integration → Tuya Local")
        print(f"  Choose: 'Add device using local key'")
        print(f"")
        print(f"    Device ID:         {DEVICE_ID}")
        print(f"    Host:              {VACUUM_IP}")
        print(f"    Local Key:         {local_key}")
        print(f"    Protocol Version:  3.5")
        print(f"    Port:              {VACUUM_PORT}")
        print(f"    Poll Only:         False")
        print(f"{'='*60}")

    elif err == "914":
        print(f"\n❌ WRONG KEY (error 914)")
        print(f"   The key '{local_key}' is incorrect.")
        print(f"   Transport works fine — you just need the right 16-char key.")

    elif err == "900":
        print(f"\n❌ TIMEOUT (error 900)")
        print(f"   Could not connect. Is the vacuum at {VACUUM_IP}?")

    else:
        print(f"\n❓ Unexpected response: {error} ({err})")
        print(f"   Full: {json.dumps(status)}")

    d.close()
    return bool(dps)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate_key.py YOUR_16_CHAR_LOCAL_KEY")
        print()
        print("Example: python3 validate_key.py ab12cd34ef56gh78")
        sys.exit(1)

    key = sys.argv[1]
    success = validate_key(key)
    sys.exit(0 if success else 1)
