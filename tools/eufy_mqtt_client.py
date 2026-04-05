#!/usr/bin/env python3
"""
Eufy X10 Pro Omni — Cloud MQTT client.

Authenticates with Eufy's cloud, obtains MQTT certificates, connects
to the vacuum's MQTT broker, and provides a simple interface to
monitor status and send commands.

Usage:
    python3 eufy_mqtt_client.py --email EMAIL --password PASSWORD

    # Capture mode — record all HTTP responses and MQTT messages to disk
    # for building test fixtures:
    python3 eufy_mqtt_client.py --email EMAIL --password PASSWORD \
        --capture-dir /tmp/eufy_capture --duration 120

Environment variables:
    EUFY_EMAIL      Eufy account email
    EUFY_PASSWORD   Eufy account password
"""

import argparse
import base64
import hashlib
import json
import os
import ssl
import sys
import tempfile
import time
import uuid
import types as _types

import requests

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("pip install paho-mqtt")
    sys.exit(1)


_PROTOS_AVAILABLE = False
StationResponse = None
UnisettingResponse = None
ErrorCode = None
try:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for _pkg, _path in [
        ('custom_components', f'{_root}/custom_components'),
        ('custom_components.robovac_mqtt', f'{_root}/custom_components/robovac_mqtt'),
        ('custom_components.robovac_mqtt.proto', f'{_root}/custom_components/robovac_mqtt/proto'),
        ('custom_components.robovac_mqtt.proto.cloud', f'{_root}/custom_components/robovac_mqtt/proto/cloud'),
    ]:
        if _pkg not in sys.modules:
            _m = _types.ModuleType(_pkg)
            _m.__path__ = [_path]
            _m.__package__ = _pkg
            sys.modules[_pkg] = _m
    from custom_components.robovac_mqtt.proto.cloud.station_pb2 import StationResponse
    from custom_components.robovac_mqtt.proto.cloud.unisetting_pb2 import UnisettingResponse
    from custom_components.robovac_mqtt.proto.cloud.error_code_pb2 import ErrorCode
    _PROTOS_AVAILABLE = True
except Exception:
    pass


DPS_MAP = {
    "152": "play_pause",
    "153": "work_status",
    "154": "cleaning_parameters",
    "155": "direction",
    "158": "clean_speed",
    "160": "find_robot",
    "163": "battery_level",
    "164": "map_edit",
    "167": "cleaning_statistics",
    "168": "accessories_status",
    "169": "device_info",
    "173": "station_status",
    "176": "unsetting",
    "177": "error_code",
    "178": "keepalive",
    "179": "telemetry",
    "180": "scene_info",
}

SPEED_NAMES = {0: "quiet", 1: "standard", 2: "turbo", 3: "max"}


def _try_decode_proto(proto_class, b64_value: str):
    try:
        raw = base64.b64decode(b64_value)
        i = 0
        while i < len(raw) and (raw[i] & 0x80):
            i += 1
        i += 1
        msg = proto_class()
        msg.ParseFromString(raw[i:])
        return msg
    except Exception:
        return None


def _decode_dps_for_display(key: str, value) -> str:
    if key == "158":
        return SPEED_NAMES.get(value, str(value))
    if key == "163":
        return f"{value}%"
    if key == "160":
        return "ON" if value else "off"

    if not isinstance(value, str):
        return str(value)

    if len(value) <= 4:
        return value

    if not _PROTOS_AVAILABLE:
        return f"{value[:60]}..." if len(value) > 60 else value

    if key == "153":
        try:
            from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import WorkStatus
            msg = _try_decode_proto(WorkStatus, value)
            if msg is None:
                return value[:60]
            state_names = {0: "standby", 1: "sleep", 2: "fault", 3: "charging", 4: "positioning", 5: "cleaning", 7: "returning"}
            parts = [state_names.get(msg.state, f"state={msg.state}")]
            if msg.HasField("mode"):
                mode_names = {0: "auto", 1: "room", 2: "zone", 3: "spot"}
                parts.append(f"mode={mode_names.get(msg.mode.value, msg.mode.value)}")
            if msg.HasField("go_wash"):
                go_wash_names = {1: "WASHING", 2: "DRYING"}
                parts.append(f"go_wash={go_wash_names.get(msg.go_wash.mode, msg.go_wash.mode)}")
            if msg.HasField("trigger"):
                trigger_names = {1: "app", 2: "button", 3: "schedule", 4: "robot", 5: "remote"}
                parts.append(f"trigger={trigger_names.get(msg.trigger.source, msg.trigger.source)}")
            return " | ".join(parts)
        except Exception:
            return value[:60]

    if key == "173":
        msg = _try_decode_proto(StationResponse, value)
        if msg is None:
            return value[:60]
        parts = []
        if msg.HasField("status"):
            status_names = {0: "idle", 1: "WASHING", 2: "DRYING"}
            parts.append(f"dock={status_names.get(msg.status.state, f'state={msg.status.state}')}")
            if msg.status.clear_water_adding:
                parts.append("adding_water")
            if msg.status.waste_water_recycling:
                parts.append("recycling")
            if msg.status.collecting_dust:
                parts.append("emptying_dust")
        if msg.HasField("clean_water"):
            parts.append(f"water={msg.clean_water.value}%")
        return " | ".join(parts) if parts else "idle"

    if key == "176":
        msg = _try_decode_proto(UnisettingResponse, value)
        if msg is None:
            return value[:60]
        parts = []
        if msg.HasField("multi_map_sw"):
            parts.append(f"multi_map={'on' if msg.multi_map_sw.value else 'off'}")
        if msg.HasField("water_level_sw"):
            parts.append(f"water_level_sw={'on' if msg.water_level_sw.value else 'off'}")
        if msg.HasField("unistate") and msg.unistate.HasField("mop_state"):
            parts.append(f"mop={'attached' if msg.unistate.mop_state.value else 'detached'}")
        return " | ".join(parts) if parts else f"{value[:40]}..."

    if key == "177":
        msg = _try_decode_proto(ErrorCode, value)
        if msg is None:
            return value[:60]
        if msg.HasField("new_code"):
            errors = list(msg.new_code.error)
            warns = list(msg.new_code.warn)
            if errors:
                return f"ERROR codes={errors}"
            if warns:
                return f"WARN codes={warns}"
        return "no error"

    if key == "169":
        try:
            raw = base64.b64decode(value)
            i = 0
            while i < len(raw) and (raw[i] & 0x80):
                i += 1
            i += 1
            # Extract length-prefixed strings from the proto blob (field type 2 = LEN)
            # Walk proto fields manually to find readable strings
            import re as _re
            text = raw[i:].decode("utf-8", errors="replace")
            # Find runs of printable ASCII (device name, IP, MAC, firmware version)
            readable = _re.findall(r'[A-Za-z0-9][A-Za-z0-9 :.\-_/]{3,}', text)
            # Filter out noise (pure hex, single words that are proto garbage)
            meaningful = [s.strip() for s in readable if not _re.fullmatch(r'[0-9a-f]+', s.lower())]
            return " | ".join(meaningful[:5]) if meaningful else f"{value[:40]}..."
        except Exception:
            return f"{value[:40]}..."

    return f"{value[:60]}..." if len(value) > 60 else value


class EufyCloudAuth:
    LOGIN_URL = "https://home-api.eufylife.com/v1/user/email/login"
    USER_CENTER_URL = "https://api.eufylife.com/v1/user/user_center_info"
    MQTT_INFO_URL = "https://aiot-clean-api-pr.eufylife.com/app/devicemanage/get_user_mqtt_info"
    DEVICE_LIST_URL = "https://aiot-clean-api-pr.eufylife.com/app/devicerelation/get_device_list"
    DEVICE_V2_URL = "https://api.eufylife.com/v1/device/v2"

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.openudid = uuid.uuid4().hex[:16]
        self.access_token = ""
        self.user_id = ""
        self.user_center_token = ""
        self.user_center_id = ""
        self.gtoken = ""

    def login(self) -> dict:
        resp = requests.post(self.LOGIN_URL, json={
            "email": self.email, "password": self.password,
            "client_id": "eufyhome-app", "client_secret": "GQCpr9dSp3uQpsOMgJ4xQ",
        }, headers=self._login_headers(), timeout=15).json()

        self.access_token = resp["access_token"]
        self.user_id = resp["user_info"]["id"]
        return resp

    def get_user_center(self) -> dict:
        resp = requests.get(self.USER_CENTER_URL, headers={
            **self._base_headers(),
            "token": self.access_token,
        }, timeout=15).json()

        self.user_center_token = resp["user_center_token"]
        self.user_center_id = resp["user_center_id"]
        self.gtoken = hashlib.md5(self.user_center_id.encode()).hexdigest()
        return resp

    def get_mqtt_certs(self) -> dict:
        resp = requests.post(self.MQTT_INFO_URL,
            headers=self._aiot_headers(), json={}, timeout=15).json()
        return resp.get("data", {})

    def get_devices(self) -> list:
        resp = requests.post(self.DEVICE_LIST_URL,
            headers=self._aiot_headers(), json={}, timeout=15).json()
        return resp.get("data", {}).get("devices", [])

    def get_cloud_device_list(self) -> list:
        resp = requests.get(self.DEVICE_V2_URL, headers={
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "user-agent": "EufyHome-Android-3.1.3-753",
            "category": "Home",
            "token": self.access_token,
            "openudid": self.openudid,
            "clienttype": "2",
        }, timeout=15).json()
        return resp.get("devices", [])

    def _login_headers(self) -> dict:
        return {**self._base_headers(), "clientType": "1"}

    def _base_headers(self) -> dict:
        return {
            "User-Agent": "EufyHome-Android-3.1.3-753",
            "category": "Home", "openudid": self.openudid,
            "clienttype": "2", "language": "en", "country": "IE",
            "timezone": "Europe/Dublin",
        }

    def _aiot_headers(self) -> dict:
        return {
            "content-type": "application/json",
            "User-Agent": "EufyHome-Android-3.1.3-753",
            "x-auth-token": self.user_center_token,
            "gtoken": self.gtoken,
            "openudid": self.openudid,
            "language": "en", "country": "IE", "timezone": "Europe/Dublin",
            "os-version": "Android", "model-type": "PHONE",
            "app-name": "eufy_home",
        }


class EufyMqttClient:
    def __init__(self, mqtt_info: dict, device_sn: str, device_model: str,
                 user_id: str, on_status=None, capture_dir: str | None = None):
        self.mqtt_info = mqtt_info
        self.device_sn = device_sn
        self.device_model = device_model
        self.user_id = user_id
        self.on_status = on_status
        self._msg_seq = 0
        self._cert_dir = tempfile.mkdtemp(prefix="eufy_mqtt_")
        self._client = None
        self.last_dps = {}
        self._capture_dir = capture_dir
        self._mqtt_capture_count = 0

    def connect(self):
        ca_path = os.path.join(self._cert_dir, "ca.pem")
        cert_path = os.path.join(self._cert_dir, "cert.pem")
        key_path = os.path.join(self._cert_dir, "key.pem")

        with open(ca_path, "w") as f:
            f.write(self.mqtt_info["aws_root_ca1_pem"])
        with open(cert_path, "w") as f:
            f.write(self.mqtt_info["certificate_pem"])
        with open(key_path, "w") as f:
            f.write(self.mqtt_info["private_key"])

        thing = self.mqtt_info["thing_name"]
        client_id = f"{thing}_{int(time.time()) % 99999:05}"

        self._client = mqtt.Client(
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        self._client.tls_set(
            ca_certs=ca_path, certfile=cert_path, keyfile=key_path,
            cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS,
        )

        endpoint = self.mqtt_info["endpoint_addr"]
        self._client.connect(endpoint, 8883, keepalive=60)
        self._client.loop_start()

    def disconnect(self):
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()

    def send_command(self, dps_data: dict):
        self._msg_seq += 1
        payload_inner = json.dumps({
            "account_id": self.user_id,
            "device_sn": self.device_sn,
            "protocol": 2,
            "t": int(time.time() * 1000),
            "data": dps_data,
        })
        message = json.dumps({
            "head": {
                "client_id": f"android-eufy_home-eufy_android_{self.user_id}",
                "cmd": 65537, "cmd_status": 2,
                "msg_seq": self._msg_seq,
                "timestamp": int(time.time()),
                "version": "1.0.0.1",
            },
            "payload": payload_inner,
        })
        topic = f"cmd/eufy_home/{self.device_model}/{self.device_sn}/req"
        if self._client is not None:
            self._client.publish(topic, message)

    def start_clean(self):
        self.send_command({"152": True})

    def pause(self):
        self.send_command({"152": False})

    def go_home(self):
        self.send_command({"173": True})

    def locate(self):
        self.send_command({"160": True})

    def set_speed(self, speed: int):
        self.send_command({"158": speed})

    def _on_connect(self, client, userdata, flags, rc, *args):
        if rc != 0:
            print(f"Connection failed: rc={rc}")
            return

        print(f"Connected to {self.mqtt_info['endpoint_addr']}")
        client.subscribe(f"cmd/eufy_home/{self.device_model}/{self.device_sn}/res")
        client.subscribe(f"smart/mb/in/{self.device_sn}")

    def _on_message(self, client, userdata, msg):
        try:
            raw_payload = msg.payload.decode()
            data = json.loads(raw_payload)

            if self._capture_dir:
                self._save_mqtt_message(data)

            payload = data.get("payload", {})
            if isinstance(payload, str):
                payload = json.loads(payload)
            dps = payload.get("data", {})
            if dps:
                self.last_dps.update(dps)
                if self.on_status:
                    ts = time.strftime("%H:%M:%S")
                    print(f"\n[{ts}] ── DPS update ──────────────────────")
                    self.on_status(dps)
        except (json.JSONDecodeError, KeyError):
            pass

    def _save_mqtt_message(self, data: dict):
        assert self._capture_dir is not None
        mqtt_dir = os.path.join(self._capture_dir, "mqtt")
        os.makedirs(mqtt_dir, exist_ok=True)

        payload = data.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        dps = payload.get("data", {})
        dps_keys = "_".join(sorted(dps.keys(), key=lambda k: int(k))) if dps else "no_dps"
        ts = int(time.time() * 1000)
        filename = f"{ts}_{dps_keys}.json"
        filepath = os.path.join(mqtt_dir, filename)

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        self._mqtt_capture_count += 1

    def _on_disconnect(self, client, userdata, *args):
        rc = args[0] if args else 0
        if rc != 0:
            print(f"Unexpected disconnect: rc={rc}")


def print_status(dps: dict):
    for k, v in sorted(dps.items(), key=lambda x: int(x[0])):
        name = DPS_MAP.get(str(k), f"unknown_{k}")
        display = _decode_dps_for_display(str(k), v)
        print(f"  {name:25s} (DPS {k:>3s}): {display}")


def _save_http_response(capture_dir: str, method_name: str, data):
    http_dir = os.path.join(capture_dir, "http")
    os.makedirs(http_dir, exist_ok=True)
    filepath = os.path.join(http_dir, f"{method_name}.json")
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Eufy X10 Pro Omni MQTT client")
    parser.add_argument("--email", default=os.environ.get("EUFY_EMAIL"),
                        help="Eufy account email (or EUFY_EMAIL env)")
    parser.add_argument("--password", default=os.environ.get("EUFY_PASSWORD"),
                        help="Eufy account password (or EUFY_PASSWORD env)")
    parser.add_argument("--device", default=None, help="Device serial number")
    parser.add_argument("--command", choices=["status", "start", "pause", "dock",
                        "locate", "quiet", "standard", "turbo", "max"],
                        default="status", help="Command to execute")
    parser.add_argument("--listen", type=int, default=30,
                        help="Seconds to listen for status (0=forever)")
    parser.add_argument("--capture-dir", default=None,
                        help="Directory to save captured HTTP responses and MQTT messages "
                             "as JSON fixtures. Creates http/ and mqtt/ subdirectories. "
                             "Run anonymize_fixtures.py on the output before committing.")
    parser.add_argument("--duration", type=int, default=None,
                        help="Capture duration in seconds (overrides --listen in capture mode)")
    args = parser.parse_args()

    if not args.email or not args.password:
        print("Provide --email and --password (or set EUFY_EMAIL/EUFY_PASSWORD)")
        sys.exit(1)

    print("Authenticating with Eufy cloud...")
    auth = EufyCloudAuth(args.email, args.password)
    http_capture_count = 0

    login_resp = auth.login()
    if args.capture_dir:
        _save_http_response(args.capture_dir, "login", login_resp)
        http_capture_count += 1

    user_center_resp = auth.get_user_center()
    if args.capture_dir:
        _save_http_response(args.capture_dir, "get_user_center", user_center_resp)
        http_capture_count += 1

    mqtt_info = auth.get_mqtt_certs()
    if args.capture_dir:
        _save_http_response(args.capture_dir, "get_mqtt_certs", mqtt_info)
        http_capture_count += 1

    print("Fetching device list...")
    devices = auth.get_devices()
    if args.capture_dir:
        _save_http_response(args.capture_dir, "get_devices", devices)
        http_capture_count += 1

    cloud_devices = auth.get_cloud_device_list()
    if args.capture_dir:
        _save_http_response(args.capture_dir, "get_cloud_device_list", cloud_devices)
        http_capture_count += 1
    cleaning_devices = [d for d in devices if d.get("device", {}).get("device_model")]

    if not cleaning_devices:
        print("No vacuum devices found.")
        sys.exit(1)

    for d in cleaning_devices:
        dev = d["device"]
        print(f"  {dev['device_name']} ({dev['device_model']}) "
              f"SN={dev['device_sn']} FW={dev['main_sw_version']}")

    target = cleaning_devices[0]["device"]
    if args.device:
        for d in cleaning_devices:
            if d["device"]["device_sn"] == args.device:
                target = d["device"]
                break

    device_sn = target["device_sn"]
    device_model = target["device_model"]
    print(f"\nTarget: {target['device_name']} ({device_model}) [{device_sn}]")

    print("Connecting to MQTT...")
    client = EufyMqttClient(
        mqtt_info=mqtt_info,
        device_sn=device_sn,
        device_model=device_model,
        user_id=auth.user_id,
        on_status=print_status,
        capture_dir=args.capture_dir,
    )
    client.connect()
    time.sleep(3)

    speed_map = {"quiet": 0, "standard": 1, "turbo": 2, "max": 3}

    if args.command == "start":
        print("Starting clean...")
        client.start_clean()
    elif args.command == "pause":
        print("Pausing...")
        client.pause()
    elif args.command == "dock":
        print("Returning to dock...")
        client.go_home()
    elif args.command == "locate":
        print("Locating robot...")
        client.locate()
    elif args.command in speed_map:
        print(f"Setting speed: {args.command}")
        client.set_speed(speed_map[args.command])

    listen_seconds = args.duration if args.duration is not None else args.listen
    print(f"\nListening for {listen_seconds}s..." if listen_seconds else "\nListening (Ctrl+C to stop)...")
    try:
        if listen_seconds:
            time.sleep(listen_seconds)
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass

    print("\nFinal state:")
    print_status(client.last_dps)

    if args.capture_dir:
        mqtt_count = client._mqtt_capture_count
        print(f"\nCaptured {http_capture_count} HTTP responses, "
              f"{mqtt_count} MQTT messages to {args.capture_dir}")

    client.disconnect()


if __name__ == "__main__":
    main()
