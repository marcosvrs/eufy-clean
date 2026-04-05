#!/usr/bin/env python3
"""
Eufy Map Extractor — main CLI runner.

Orchestrates the full reverse-engineering pipeline:
  discover → monitor → extract → decode → probe

Usage:
    python3 run.py discover [--subnet 192.168.1.0/24]
    sudo python3 run.py monitor 192.168.1.XXX [--duration 120]
    python3 run.py extract pcap_file --vacuum-ip IP --map-ports 8100,9000
    python3 run.py decode output/map_payloads/
    python3 run.py probe --ip IP --device-id ID --local-key KEY
"""

import subprocess
import sys
import os

SCRIPTS = {
    "discover": "scripts/01_discover.py",
    "monitor": "scripts/02_monitor.py",
    "extract": "scripts/03_extract.py",
    "decode": "scripts/04_decode.py",
    "probe": "scripts/05_tuya_probe.py",
}

HELP_TEXT = """
Eufy X10 Pro Omni — Local Map Extractor Toolkit
================================================

Workflow:
  1. discover  — Find your vacuum on the network
  2. monitor   — Capture traffic while using the Eufy app
  3. extract   — Pull map data payloads from the capture
  4. decode    — Brute-force decode the binary map format
  5. probe     — Query the vacuum directly via Tuya local protocol

Commands:
  python3 run.py discover [--subnet 192.168.1.0/24]
  sudo python3 run.py monitor VACUUM_IP [--duration 120]
  python3 run.py extract PCAP_FILE --vacuum-ip IP --map-ports PORTS
  python3 run.py decode PATH_TO_BIN_FILES
  python3 run.py probe --ip IP --device-id ID --local-key KEY [--trigger-map]

Prerequisites:
  pip install -r requirements.txt
  sudo apt install nmap     (for discover)
  Root/sudo required        (for monitor)
"""


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(HELP_TEXT)
        sys.exit(0)

    command = sys.argv[1]

    if command not in SCRIPTS:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(SCRIPTS.keys())}")
        sys.exit(1)

    script = SCRIPTS[command]
    project_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(project_dir, script)

    remaining_args = sys.argv[2:]
    result = subprocess.run(
        [sys.executable, script_path] + remaining_args,
        cwd=project_dir
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
