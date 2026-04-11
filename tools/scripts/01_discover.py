#!/usr/bin/env python3
"""
Phase 1: Network Reconnaissance — Discover your Eufy vacuum on the LAN.

Scans your local subnet for Tuya-based devices (port 6668) and performs
a full port scan on any discovered vacuum to map all open ports.

Usage:
    sudo python3 scripts/01_discover.py [--subnet 192.168.1.0/24]

Requires: nmap installed (sudo apt install nmap)
"""

import argparse
import json
import re
import socket
import subprocess
import sys
from pathlib import Path


def get_local_subnet() -> str:
    """Auto-detect the local subnet from default interface."""
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Example: "default via 192.168.1.1 dev eth0 ..."
        match = re.search(r"via\s+(\d+\.\d+\.\d+)\.\d+", result.stdout)
        if match:
            return f"{match.group(1)}.0/24"
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show"], capture_output=True, text=True, timeout=5
        )
        # Find non-loopback address
        for match in re.finditer(r"inet\s+(\d+\.\d+\.\d+)\.\d+/(\d+)", result.stdout):
            ip_prefix = match.group(1)
            cidr = match.group(2)
            if not ip_prefix.startswith("127."):
                return f"{ip_prefix}.0/{cidr}"
    except Exception:
        pass

    return "192.168.1.0/24"


def check_nmap() -> bool:
    """Check if nmap is installed."""
    try:
        subprocess.run(["nmap", "--version"], capture_output=True, timeout=5)
        return True
    except FileNotFoundError:
        return False


def scan_for_tuya_devices(subnet: str) -> list[dict]:
    """Scan subnet for devices with Tuya port 6668 open."""
    print(f"[*] Scanning {subnet} for Tuya devices (port 6668)...")
    print(f"    This may take 30-60 seconds...\n")

    result = subprocess.run(
        ["nmap", "-sS", "-p", "6668", "--open", "-oG", "-", subnet],
        capture_output=True,
        text=True,
        timeout=120,
    )

    devices = []
    for line in result.stdout.splitlines():
        if "6668/open" in line:
            match = re.search(r"Host:\s+(\d+\.\d+\.\d+\.\d+)", line)
            if match:
                ip = match.group(1)
                hostname = resolve_hostname(ip)
                devices.append({"ip": ip, "hostname": hostname})

    return devices


def resolve_hostname(ip: str) -> str:
    """Try reverse DNS lookup."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ""


def full_port_scan(ip: str) -> dict:
    """Full TCP + UDP port scan on a specific IP."""
    print(f"[*] Running full TCP port scan on {ip}...")
    tcp_result = subprocess.run(
        ["nmap", "-sS", "-p-", "--min-rate", "5000", "-oG", "-", ip],
        capture_output=True,
        text=True,
        timeout=300,
    )

    tcp_ports = []
    for line in tcp_result.stdout.splitlines():
        if "Ports:" in line:
            for port_match in re.finditer(r"(\d+)/open/tcp", line):
                tcp_ports.append(int(port_match.group(1)))

    print(f"[*] Running UDP port scan on {ip} (top 1000 ports)...")
    udp_result = subprocess.run(
        ["nmap", "-sU", "--top-ports", "1000", "--min-rate", "3000", "-oG", "-", ip],
        capture_output=True,
        text=True,
        timeout=300,
    )

    udp_ports = []
    for line in udp_result.stdout.splitlines():
        if "Ports:" in line:
            for port_match in re.finditer(r"(\d+)/open/udp", line):
                udp_ports.append(int(port_match.group(1)))

    return {"tcp": sorted(tcp_ports), "udp": sorted(udp_ports)}


def tinytuya_scan(subnet: str) -> list[dict]:
    """Use tinytuya's built-in device scanner as a secondary method."""
    print(f"[*] Running tinytuya broadcast scan...")
    try:
        import tinytuya

        devices = tinytuya.deviceScan(verbose=False, maxretry=3, byID=False)
        results = []
        for ip, info in devices.items():
            results.append(
                {
                    "ip": ip,
                    "gwId": info.get("gwId", ""),
                    "productKey": info.get("productKey", ""),
                    "version": info.get("version", ""),
                }
            )
        return results
    except ImportError:
        print("    tinytuya not installed — skipping broadcast scan")
        return []
    except Exception as e:
        print(f"    tinytuya scan failed: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Discover Eufy/Tuya vacuum on your local network"
    )
    parser.add_argument(
        "--subnet", type=str, default=None, help="Subnet to scan (default: auto-detect)"
    )
    parser.add_argument(
        "--skip-full-scan",
        action="store_true",
        help="Skip full port scan on discovered devices",
    )
    args = parser.parse_args()

    if not check_nmap():
        print("ERROR: nmap is not installed.")
        print("Install it: sudo apt install nmap")
        sys.exit(1)

    subnet = args.subnet or get_local_subnet()
    print(f"{'='*60}")
    print(f"  Eufy Vacuum Discovery Tool")
    print(f"{'='*60}")
    print(f"  Subnet: {subnet}\n")

    # Method 1: nmap scan for port 6668
    devices = scan_for_tuya_devices(subnet)

    # Method 2: tinytuya broadcast
    tuya_devices = tinytuya_scan(subnet)

    # Merge results
    known_ips = {d["ip"] for d in devices}
    for td in tuya_devices:
        if td["ip"] not in known_ips:
            devices.append(
                {
                    "ip": td["ip"],
                    "hostname": "",
                    "tuya_id": td.get("gwId", ""),
                    "tuya_version": td.get("version", ""),
                }
            )
            known_ips.add(td["ip"])

    if not devices:
        print("\n[!] No Tuya devices found on the network.")
        print("    Make sure your vacuum is powered on and connected to WiFi.")
        print("    Try specifying the subnet manually: --subnet 192.168.0.0/24")
        sys.exit(1)

    print(f"\n[+] Found {len(devices)} Tuya device(s):\n")
    for i, dev in enumerate(devices):
        hostname = f" ({dev['hostname']})" if dev.get("hostname") else ""
        print(f"  [{i+1}] {dev['ip']}{hostname}")
        if dev.get("tuya_id"):
            print(f"      Tuya ID: {dev['tuya_id']}")
        if dev.get("tuya_version"):
            print(f"      Protocol: v{dev['tuya_version']}")

    # Full port scan on each device
    if not args.skip_full_scan:
        for dev in devices:
            print(f"\n{'='*60}")
            ports = full_port_scan(dev["ip"])
            dev["ports"] = ports

            print(f"\n[+] Open ports on {dev['ip']}:")
            if ports["tcp"]:
                print(f"    TCP: {', '.join(str(p) for p in ports['tcp'])}")
            if ports["udp"]:
                print(f"    UDP: {', '.join(str(p) for p in ports['udp'])}")

            non_tuya = [p for p in ports["tcp"] if p != 6668]
            if non_tuya:
                print(f"\n    ⚡ Non-standard ports (potential map data):")
                for p in non_tuya:
                    print(f"       TCP {p}")

    # Save results
    output_path = Path("output/discovery_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(devices, f, indent=2)
    print(f"\n[+] Results saved to {output_path}")

    # Tuya info from broadcast
    for td in tuya_devices:
        print(f"\n    tinytuya broadcast data for {td['ip']}:")
        for k, v in td.items():
            if k != "ip" and v:
                print(f"      {k}: {v}")

    print(f"\n{'='*60}")
    print(f"  NEXT STEP:")
    print(f"  Run the traffic monitor with your vacuum IP:")
    print(f"    sudo python3 scripts/02_monitor.py VACUUM_IP")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
