#!/usr/bin/env python3
"""Strip PII from captured Eufy fixture files while preserving protocol data."""

import argparse
import json
import os
import re
import sys


PII_RULES = {
    "email": lambda v, ctx: "test@example.com" if isinstance(v, str) else v,
    "username": lambda v, ctx: "test@example.com" if isinstance(v, str) else v,
    "device_sn": lambda v, ctx: _anon_device_sn(v, ctx) if isinstance(v, str) else v,
    "deviceId": lambda v, ctx: _anon_device_sn(v, ctx) if isinstance(v, str) else v,
    "device_id": lambda v, ctx: _anon_device_sn(v, ctx) if isinstance(v, str) else v,
    "user_center_id": lambda v, ctx: _anon_user(v, ctx) if isinstance(v, str) else v,
    "user_center_user_id": lambda v, ctx: "ANON_USER_HASH_001" if isinstance(v, str) else v,
    "admin_user_id": lambda v, ctx: "ANON_USER_HASH_001" if isinstance(v, str) else v,
    "member_user_id": lambda v, ctx: "ANON_USER_HASH_001" if isinstance(v, str) else v,
    "user_id": lambda v, ctx: _anon_user(v, ctx) if isinstance(v, str) else v,
    "userId": lambda v, ctx: _anon_user(v, ctx) if isinstance(v, str) else v,
    "account_id": lambda v, ctx: _anon_user(v, ctx) if isinstance(v, str) else v,
    "access_token": lambda v, ctx: "ANON_TOKEN_XXX" if isinstance(v, str) else v,
    "user_center_token": lambda v, ctx: "ANON_TOKEN_XXX" if isinstance(v, str) else v,
    "token": lambda v, ctx: "ANON_TOKEN_XXX" if isinstance(v, str) else v,
    "certificate_pem": lambda v, ctx: "ANON_CERT" if isinstance(v, str) else v,
    "private_key": lambda v, ctx: "ANON_KEY" if isinstance(v, str) else v,
    "client_id": lambda v, ctx: "android-anon-openudid-anon_user-0" if isinstance(v, str) else v,
    "sess_id": lambda v, ctx: "android-anon-openudid-anon_user-0" if isinstance(v, str) else v,
    "device_mac": lambda v, ctx: _anon_mac(v, ctx) if isinstance(v, str) else v,
    "mac": lambda v, ctx: _anon_mac(v, ctx) if isinstance(v, str) else v,
    "wifi_mac": lambda v, ctx: _anon_mac_compact(v, ctx) if isinstance(v, str) else v,
    "bt_mac": lambda v, ctx: _anon_mac(v, ctx) if isinstance(v, str) else v,
    "wifi_ssid": lambda v, ctx: "ANON_WIFI" if isinstance(v, str) else v,
    "wifi_ip": lambda v, ctx: "192.168.1.100" if isinstance(v, str) else v,
    "lan_ip_addr": lambda v, ctx: "" if isinstance(v, str) else v,
    "ip_addr": lambda v, ctx: "" if isinstance(v, str) else v,
    "local_ip": lambda v, ctx: "" if isinstance(v, str) else v,
    "home_id": lambda v, ctx: "ANON_HOME_ID_001" if isinstance(v, str) else v,
    "room_id": lambda v, ctx: "ANON_ROOM_ID_001" if isinstance(v, str) else v,
    "thing_name": lambda v, ctx: f"ANON_USER_HASH_001-eufy_home" if isinstance(v, str) else v,
}

TIMESTAMP_KEYS = {"timestamp", "t"}

MODEL_PREFIX_RE = re.compile(r"^(T\d{4})")


class AnonymizeContext:
    def __init__(self):
        self._device_serials: dict[str, str] = {}
        self._device_counter = 0
        self._user_ids: dict[str, str] = {}
        self._user_counter = 0
        self._mac_addrs: dict[str, str] = {}
        self._mac_counter = 0
        self.min_timestamp: int | None = None
        self.pii_count = 0

    def get_device_anon(self, serial: str) -> str:
        if serial not in self._device_serials:
            self._device_counter += 1
            match = MODEL_PREFIX_RE.match(serial)
            prefix = match.group(1) if match else "TXXX"
            self._device_serials[serial] = f"{prefix}_ANON_{self._device_counter:03d}"
        return self._device_serials[serial]

    def get_user_anon(self, user_id: str) -> str:
        if user_id not in self._user_ids:
            self._user_counter += 1
            self._user_ids[user_id] = f"ANON_USER_{self._user_counter:03d}"
        return self._user_ids[user_id]

    def get_mac_anon(self, mac: str) -> str:
        if mac not in self._mac_addrs:
            self._mac_counter += 1
            self._mac_addrs[mac] = f"00:00:00:00:00:{self._mac_counter:02d}"
        return self._mac_addrs[mac]


def _anon_device_sn(value: str, ctx: AnonymizeContext) -> str:
    return ctx.get_device_anon(value)


def _anon_user(value: str, ctx: AnonymizeContext) -> str:
    return ctx.get_user_anon(value)


def _anon_mac(value: str, ctx: AnonymizeContext) -> str:
    return ctx.get_mac_anon(value)


def _anon_mac_compact(value: str, ctx: AnonymizeContext) -> str:
    anon = ctx.get_mac_anon(value)
    return anon.replace(":", "").upper()


def _find_min_timestamp(data, current_min: int | None) -> int | None:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in TIMESTAMP_KEYS and isinstance(value, int) and value > 1_000_000_000:
                if current_min is None or value < current_min:
                    current_min = value
            current_min = _find_min_timestamp(value, current_min)
    elif isinstance(data, list):
        for item in data:
            current_min = _find_min_timestamp(item, current_min)
    return current_min


def _anonymize_value(data, ctx: AnonymizeContext):
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if key in PII_RULES:
                new_value = PII_RULES[key](value, ctx)
                if new_value != value:
                    ctx.pii_count += 1
                result[key] = new_value
            elif key in TIMESTAMP_KEYS and isinstance(value, int) and value > 1_000_000_000:
                result[key] = value - (ctx.min_timestamp or 0)
                ctx.pii_count += 1
            else:
                result[key] = _anonymize_value(value, ctx)
        return result
    elif isinstance(data, list):
        return [_anonymize_value(item, ctx) for item in data]
    return data


def anonymize_directory(input_dir: str, output_dir: str) -> tuple[int, int]:
    ctx = AnonymizeContext()
    json_files: list[tuple[str, str]] = []

    for root, _dirs, files in os.walk(input_dir):
        for fname in files:
            if not fname.endswith(".json"):
                continue
            src = os.path.join(root, fname)
            rel = os.path.relpath(src, input_dir)
            dst = os.path.join(output_dir, rel)
            json_files.append((src, dst))

    all_data = []
    for src, _dst in json_files:
        with open(src) as f:
            data = json.load(f)
        all_data.append(data)
        ctx.min_timestamp = _find_min_timestamp(data, ctx.min_timestamp)

    for (src, dst), data in zip(json_files, all_data):
        anonymized = _anonymize_value(data, ctx)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w") as f:
            json.dump(anonymized, f, indent=2)

    return len(json_files), ctx.pii_count


def main():
    parser = argparse.ArgumentParser(
        description="Anonymize PII in captured Eufy fixture files"
    )
    parser.add_argument("--input-dir", required=True,
                        help="Directory containing captured JSON fixtures")
    parser.add_argument("--output-dir", default="tests/fixtures",
                        help="Output directory for anonymized fixtures (default: tests/fixtures)")
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"Error: input directory does not exist: {args.input_dir}")
        sys.exit(1)

    file_count, pii_count = anonymize_directory(args.input_dir, args.output_dir)
    print(f"Replaced {pii_count} PII fields across {file_count} files → {args.output_dir}")


if __name__ == "__main__":
    main()
