#!/usr/bin/env python3
"""
Phase 3: Extract map data payloads from a pcap file.

Reads a pcap captured by 02_monitor.py (or tcpdump/Wireshark) and extracts
payload data from the map-candidate ports you identified. Saves individual
frame payloads and a concatenated stream for analysis.

Usage:
    python3 scripts/03_extract.py output/pcaps/monitor_*.pcap \
        --vacuum-ip 192.168.1.XXX --map-ports 8100,9000
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from scapy.all import IP, TCP, UDP, rdpcap
except ImportError:
    print("ERROR: scapy not installed. Run: pip install scapy")
    sys.exit(1)


def extract_streams(pcap_path: str, vacuum_ip: str, map_ports: list[int]) -> dict:
    print(f"[*] Reading {pcap_path}...")
    packets = rdpcap(pcap_path)
    print(f"    Total packets: {len(packets)}")

    streams: dict[int, dict] = {}
    for port in map_ports:
        streams[port] = {
            "outgoing": [],  # vacuum → phone
            "incoming": [],  # phone → vacuum
        }

    for i, pkt in enumerate(packets):
        if not pkt.haslayer(IP):
            continue

        ip = pkt[IP]
        is_from_vacuum = ip.src == vacuum_ip
        is_to_vacuum = ip.dst == vacuum_ip

        if not (is_from_vacuum or is_to_vacuum):
            continue

        payload = b""
        port = 0

        if pkt.haslayer(TCP):
            layer = pkt[TCP]
            port = layer.sport if is_from_vacuum else layer.dport
            payload = bytes(layer.payload) if layer.payload else b""
        elif pkt.haslayer(UDP):
            layer = pkt[UDP]
            port = layer.sport if is_from_vacuum else layer.dport
            payload = bytes(layer.payload) if layer.payload else b""

        if port not in streams or not payload:
            continue

        direction = "outgoing" if is_from_vacuum else "incoming"
        streams[port][direction].append(
            {
                "pkt_index": i,
                "size": len(payload),
                "data": payload,
            }
        )

    return streams


def save_payloads(streams: dict, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    for port, directions in streams.items():
        for direction, payloads in directions.items():
            if not payloads:
                continue

            port_dir = output_dir / f"port_{port}_{direction}"
            port_dir.mkdir(parents=True, exist_ok=True)

            total_bytes = 0
            for idx, p in enumerate(payloads):
                frame_path = port_dir / f"frame_{idx:05d}_pkt{p['pkt_index']}.bin"
                frame_path.write_bytes(p["data"])
                total_bytes += len(p["data"])

            concat_path = port_dir / "all_concatenated.bin"
            with open(concat_path, "wb") as f:
                for p in payloads:
                    f.write(p["data"])

            print(
                f"  [+] Port {port} {direction}: {len(payloads)} frames, "
                f"{total_bytes} bytes → {port_dir}/"
            )

            if payloads:
                first = payloads[0]["data"]
                print(f"      First frame ({len(first)} bytes): {first[:32].hex()}")


def analyze_frame_patterns(streams: dict):
    print(f"\n{'='*60}")
    print(f"  FRAME ANALYSIS")
    print(f"{'='*60}")

    for port, directions in streams.items():
        for direction, payloads in directions.items():
            if not payloads:
                continue

            sizes = [p["size"] for p in payloads]
            print(f"\n  Port {port} ({direction}):")
            print(f"    Frames: {len(payloads)}")
            print(f"    Size range: {min(sizes)} — {max(sizes)} bytes")
            print(f"    Total: {sum(sizes)} bytes")

            if len(set(sizes)) == 1:
                print(f"    Pattern: FIXED frame size ({sizes[0]} bytes)")
            elif max(sizes) / max(min(sizes), 1) < 1.5:
                print(f"    Pattern: UNIFORM sizes (likely chunked stream)")
            else:
                print(f"    Pattern: VARIABLE sizes (likely framed protocol)")

            unique_headers = set()
            for p in payloads[:20]:
                unique_headers.add(p["data"][:4])

            if len(unique_headers) <= 3:
                print(f"    Header patterns ({len(unique_headers)} unique):")
                for hdr in sorted(unique_headers):
                    print(f"      {hdr.hex()}")
            else:
                print(
                    f"    Headers vary widely ({len(unique_headers)} unique in first 20)"
                )

            for p in payloads[:1]:
                d = p["data"]
                if d[:2] == b"\x1f\x8b":
                    print(f"    ✅ GZIP signature detected!")
                elif d[:2] in (b"\x78\x9c", b"\x78\x01", b"\x78\xda"):
                    print(f"    ✅ ZLIB signature detected!")
                elif d[:4] == b"\x89PNG":
                    print(f"    ✅ PNG signature detected!")


def main():
    parser = argparse.ArgumentParser(description="Extract map payloads from pcap")
    parser.add_argument("pcap", help="Path to pcap file")
    parser.add_argument("--vacuum-ip", required=True, help="Vacuum IP address")
    parser.add_argument(
        "--map-ports",
        required=True,
        help="Comma-separated list of candidate map ports (from 02_monitor.py output)",
    )
    parser.add_argument(
        "--output", default="output/map_payloads", help="Output directory"
    )
    args = parser.parse_args()

    ports = [int(p.strip()) for p in args.map_ports.split(",")]

    print(f"{'='*60}")
    print(f"  Eufy Map Payload Extractor")
    print(f"{'='*60}")
    print(f"  Pcap:      {args.pcap}")
    print(f"  Vacuum:    {args.vacuum_ip}")
    print(f"  Ports:     {ports}")
    print(f"{'='*60}\n")

    streams = extract_streams(args.pcap, args.vacuum_ip, ports)
    save_payloads(streams, Path(args.output))
    analyze_frame_patterns(streams)

    print(f"\n{'='*60}")
    print(f"  NEXT STEP:")
    print(f"  Run the decoder on extracted payloads:")
    print(f"    python3 scripts/04_decode.py {args.output}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
