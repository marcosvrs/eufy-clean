#!/usr/bin/env python3
"""
Phase 2: Real-time traffic monitor.

Captures all traffic to/from the vacuum and categorizes it by port, protocol,
and packet size. Large packets on non-6668 ports are flagged as potential
map data streams.

Usage:
    sudo python3 scripts/02_monitor.py VACUUM_IP [--duration 120]
"""

import argparse
import signal
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    from scapy.all import IP, TCP, UDP, sniff, wrpcap
except ImportError:
    print("ERROR: scapy not installed. Run: pip install scapy")
    sys.exit(1)


MAP_DATA_THRESHOLD = 500  # bytes — packets above this are flagged
TUYA_COMMAND_PORT = 6668

streams: defaultdict[str, dict] = defaultdict(
    lambda: {
        "count": 0,
        "bytes": 0,
        "sizes": [],
        "first_seen": None,
        "last_seen": None,
        "sample_payloads": [],
    }
)
all_packets = []
large_packet_count = 0


def packet_handler(pkt):
    global large_packet_count

    if not pkt.haslayer(IP):
        return

    ip = pkt[IP]
    if ip.src != VACUUM_IP and ip.dst != VACUUM_IP:
        return

    all_packets.append(pkt)
    direction = "OUT" if ip.src == VACUUM_IP else " IN"
    size = len(pkt)
    now = datetime.now()
    payload = b""

    if pkt.haslayer(TCP):
        layer = pkt[TCP]
        port = layer.sport if ip.src == VACUUM_IP else layer.dport
        proto = "TCP"
        payload = bytes(layer.payload) if layer.payload else b""
    elif pkt.haslayer(UDP):
        layer = pkt[UDP]
        port = layer.sport if ip.src == VACUUM_IP else layer.dport
        proto = "UDP"
        payload = bytes(layer.payload) if layer.payload else b""
    else:
        return

    key = f"{proto}:{port}"
    s = streams[key]
    s["count"] += 1
    s["bytes"] += size
    s["sizes"].append(size)
    s["last_seen"] = now
    if s["first_seen"] is None:
        s["first_seen"] = now

    if len(payload) > MAP_DATA_THRESHOLD:
        large_packet_count += 1

        if len(s["sample_payloads"]) < 5:
            s["sample_payloads"].append(payload[:256])

        marker = "⚡ MAP?" if port != TUYA_COMMAND_PORT else "  DPS "
        print(
            f"  {marker} {direction} {proto}:{port:<6} "
            f"{size:>6} bytes  "
            f"hdr={payload[:16].hex()}"
        )


def print_summary():
    print(f"\n{'='*70}")
    print(f"  TRAFFIC SUMMARY — {VACUUM_IP}")
    print(f"{'='*70}")
    print(f"  Total packets: {len(all_packets)}")
    print(f"  Large packets (>{MAP_DATA_THRESHOLD}b): {large_packet_count}")
    print()
    print(
        f"  {'Stream':>12}  {'Packets':>8}  {'Total':>10}  {'Avg':>8}  {'Max':>6}  Note"
    )
    print(f"  {'-'*12}  {'-'*8}  {'-'*10}  {'-'*8}  {'-'*6}  ----")

    for key, info in sorted(streams.items(), key=lambda x: x[1]["bytes"], reverse=True):
        avg = info["bytes"] / max(info["count"], 1)
        mx = max(info["sizes"]) if info["sizes"] else 0
        note = ""
        port = int(key.split(":")[1])

        if port == TUYA_COMMAND_PORT:
            note = "← Tuya DPS commands"
        elif mx > MAP_DATA_THRESHOLD:
            note = "← ⚡ POTENTIAL MAP DATA"

        print(
            f"  {key:>12}  {info['count']:>8}  "
            f"{info['bytes']:>10}  {avg:>8.0f}  {mx:>6}  {note}"
        )

    map_streams = [
        (k, v)
        for k, v in streams.items()
        if max(v["sizes"], default=0) > MAP_DATA_THRESHOLD
        and int(k.split(":")[1]) != TUYA_COMMAND_PORT
    ]

    if map_streams:
        print(f"\n{'='*70}")
        print(f"  ⚡ CANDIDATE MAP STREAMS")
        print(f"{'='*70}")
        for key, info in map_streams:
            print(f"\n  {key}:")
            print(f"    Packets: {info['count']}, Total: {info['bytes']} bytes")
            print(f"    Active: {info['first_seen']} → {info['last_seen']}")
            for i, sample in enumerate(info["sample_payloads"][:3]):
                print(f"    Sample {i} first 64 bytes: {sample[:64].hex()}")

                sig = identify_signature(sample)
                if sig:
                    print(f"      → Detected: {sig}")

        print(f"\n  NEXT STEP:")
        ports = [k.split(":")[1] for k, _ in map_streams]
        print(f"    Use these ports in 03_extract.py:")
        print(f"      --map-ports {','.join(ports)}")
    else:
        print(f"\n  [!] No large-packet streams found on non-DPS ports.")
        print(f"      Try: open Eufy Clean app, view map, start a cleaning run.")
        print(f"      The map stream only activates when the app requests it.")


def identify_signature(data: bytes) -> str:
    if data[:2] == b"\x1f\x8b":
        return "GZIP compressed"
    if data[:2] in (b"\x78\x9c", b"\x78\x01", b"\x78\xda"):
        return "ZLIB compressed"
    if data[:4] == b"\x89PNG":
        return "PNG image"
    if data[:2] == b"\xff\xd8":
        return "JPEG image"
    if data[:4] == b"RIFF":
        return "RIFF container"
    if data[:2] == b"\x00\x00" and len(data) > 20:
        return "Possible Tuya P2P frame (null header)"
    return ""


def save_pcap():
    if not all_packets:
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(f"output/pcaps/monitor_{ts}.pcap")
    path.parent.mkdir(parents=True, exist_ok=True)
    wrpcap(str(path), all_packets)
    print(f"\n  [+] Pcap saved to {path}")


def main():
    global VACUUM_IP

    parser = argparse.ArgumentParser(description="Monitor Eufy vacuum traffic")
    parser.add_argument("vacuum_ip", help="IP address of your Eufy vacuum")
    parser.add_argument(
        "--duration",
        type=int,
        default=0,
        help="Capture duration in seconds (0 = until Ctrl+C)",
    )
    args = parser.parse_args()
    VACUUM_IP = args.vacuum_ip

    print(f"{'='*70}")
    print(f"  Eufy Vacuum Traffic Monitor")
    print(f"{'='*70}")
    print(f"  Target:    {VACUUM_IP}")
    print(
        f"  Duration:  {'until Ctrl+C' if args.duration == 0 else f'{args.duration}s'}"
    )
    print(f"  Threshold: packets > {MAP_DATA_THRESHOLD} bytes flagged")
    print(f"{'='*70}")
    print()
    print("  ACTION REQUIRED:")
    print("    1. Open Eufy Clean app on your phone")
    print("    2. Navigate to your vacuum's page")
    print("    3. Open the map view")
    print("    4. Start a cleaning session")
    print("    5. Watch for ⚡ MAP? lines below")
    print()
    print("  Press Ctrl+C to stop and see summary.")
    print(f"{'='*70}\n")

    def on_signal(_sig, _frame):
        print("\n\n  Stopping capture...")
        print_summary()
        save_pcap()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_signal)

    bpf = f"host {VACUUM_IP}"
    timeout = args.duration if args.duration > 0 else None

    try:
        sniff(filter=bpf, prn=packet_handler, store=0, timeout=timeout)
    except PermissionError:
        print("ERROR: Must run as root. Use: sudo python3 scripts/02_monitor.py ...")
        sys.exit(1)

    print_summary()
    save_pcap()


if __name__ == "__main__":
    main()
