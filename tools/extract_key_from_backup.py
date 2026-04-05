#!/usr/bin/env python3
"""
Extract Tuya local key from an encrypted iPhone backup.

The Tuya SDK on iOS stores device credentials in the keychain and in
the app's local storage. Encrypted iPhone backups include keychain data.

Usage:
    python3 extract_key_from_backup.py /path/to/backup --password "your_backup_password"

Creating the backup:
    macOS:  Open Finder → select iPhone → Back Up (enable "Encrypt local backup")
    Linux:  idevicebackup2 encryption on && idevicebackup2 backup /path/to/backup
    Windows: iTunes → Summary → Back Up Now (enable "Encrypt local backup")
"""

import argparse
import json
import os
import plistlib
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

try:
    from iphone_backup_decrypt import EncryptedBackup, RelativePath
except ImportError:
    print("ERROR: pip install iphone_backup_decrypt")
    sys.exit(1)


EUFY_BUNDLE_IDS = [
    "com.eufylife.clean",
    "com.eufylife.smarthome",
    "com.oceanwing.eufylife.clean",
]

TUYA_KEY_PATTERNS = [
    re.compile(rb'localKey["\s:=]+([a-zA-Z0-9]{16})', re.IGNORECASE),
    re.compile(rb'local_key["\s:=]+([a-zA-Z0-9]{16})', re.IGNORECASE),
    re.compile(rb'"localKey"\s*:\s*"([a-zA-Z0-9]{16})"'),
    re.compile(rb'"key"\s*:\s*"([a-zA-Z0-9]{16})"'),
]

DEVICE_ID = "ANON_DEVICE_ID"
DEVICE_ID_BYTES = DEVICE_ID.encode()


def search_binary(data: bytes, filename: str = "") -> list[dict]:
    found = []

    if DEVICE_ID_BYTES in data:
        print(f"  🎯 Device ID '{DEVICE_ID}' found in {filename}!")

    for pattern in TUYA_KEY_PATTERNS:
        for match in pattern.finditer(data):
            key = match.group(1).decode("ascii", errors="replace")
            start = max(0, match.start() - 50)
            end = min(len(data), match.end() + 50)
            context = data[start:end]
            found.append({
                "key": key,
                "file": filename,
                "context": context.decode("ascii", errors="replace"),
            })
            print(f"  🔑 Potential key: {key} in {filename}")

    return found


def extract_from_encrypted_backup(backup_path: str, password: str) -> list[dict]:
    print(f"Opening encrypted backup: {backup_path}")
    print(f"Password: {'*' * len(password)}")
    print()

    backup = EncryptedBackup(backup_directory=backup_path, passphrase=password)
    all_keys = []

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Extract keychain
        print("[1/4] Extracting keychain...")
        try:
            keychain_path = os.path.join(tmpdir, "keychain.plist")
            backup.extract_file(
                relative_path=RelativePath.KEYCHAIN,
                output_filename=keychain_path,
            )
            keys = search_keychain(keychain_path)
            all_keys.extend(keys)
        except Exception as e:
            print(f"  Keychain extraction failed: {e}")

        # 2. Search all Eufy app files
        print("\n[2/4] Searching Eufy app data...")
        for bundle_id in EUFY_BUNDLE_IDS:
            print(f"  Checking {bundle_id}...")
            try:
                app_files = list_app_files(backup, bundle_id)
                for rel_path in app_files:
                    try:
                        out = os.path.join(tmpdir, rel_path.replace("/", "_"))
                        backup.extract_file(
                            relative_path=rel_path,
                            output_filename=out,
                        )
                        with open(out, "rb") as f:
                            data = f.read()
                        keys = search_binary(data, rel_path)
                        all_keys.extend(keys)
                    except Exception:
                        pass
            except Exception as e:
                print(f"  Bundle {bundle_id} not found: {e}")

        # 3. Search ALL plist and db files
        print("\n[3/4] Searching all plists and databases...")
        try:
            for domain, rel_path in backup._iter_files():
                lower = rel_path.lower() if rel_path else ""
                if any(kw in lower for kw in ["tuya", "eufy", "clean", "robo", "vacuum", "device"]):
                    try:
                        out = os.path.join(tmpdir, f"match_{hash(rel_path)}")
                        backup.extract_file(
                            relative_path=rel_path,
                            output_filename=out,
                        )
                        with open(out, "rb") as f:
                            data = f.read()
                        keys = search_binary(data, f"{domain}/{rel_path}")
                        all_keys.extend(keys)
                    except Exception:
                        pass
        except Exception as e:
            print(f"  File iteration failed: {e}")

        # 4. Brute search all files for device ID
        print("\n[4/4] Brute-force scanning all backup files for device ID...")
        try:
            count = 0
            for domain, rel_path in backup._iter_files():
                try:
                    out = os.path.join(tmpdir, f"brute_{count}")
                    backup.extract_file(
                        relative_path=rel_path,
                        output_filename=out,
                    )
                    with open(out, "rb") as f:
                        data = f.read()
                    if DEVICE_ID_BYTES in data or b"localKey" in data or b"local_key" in data:
                        print(f"  🎯 HIT in {domain}/{rel_path}")
                        keys = search_binary(data, f"{domain}/{rel_path}")
                        all_keys.extend(keys)
                    count += 1
                except Exception:
                    pass
        except Exception as e:
            print(f"  Brute scan failed: {e}")

    return all_keys


def search_keychain(keychain_path: str) -> list[dict]:
    found = []
    try:
        with open(keychain_path, "rb") as f:
            data = f.read()

        # Search raw bytes
        keys = search_binary(data, "keychain.plist")
        found.extend(keys)

        # Try plist parse
        try:
            plist = plistlib.loads(data)
            search_plist(plist, "keychain", found)
        except Exception:
            pass

    except Exception as e:
        print(f"  Keychain parse error: {e}")
    return found


def search_plist(obj, path: str, found: list):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (str, bytes)):
                s = v if isinstance(v, str) else v.decode("ascii", errors="replace")
                if DEVICE_ID in s or "localKey" in s.lower() or "local_key" in s.lower():
                    print(f"  🎯 Plist hit: {path}.{k} = {s[:100]}")
                    for pattern in TUYA_KEY_PATTERNS:
                        for m in pattern.finditer(v if isinstance(v, bytes) else v.encode()):
                            found.append({
                                "key": m.group(1).decode("ascii", errors="replace"),
                                "file": f"{path}.{k}",
                                "context": s[:200],
                            })
            else:
                search_plist(v, f"{path}.{k}", found)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            search_plist(item, f"{path}[{i}]", found)


def list_app_files(backup, bundle_id: str) -> list[str]:
    files = []
    try:
        for domain, rel_path in backup._iter_files():
            if bundle_id in (domain or "") or bundle_id in (rel_path or ""):
                files.append(rel_path)
    except Exception:
        pass
    return files


def main():
    parser = argparse.ArgumentParser(
        description="Extract Tuya local key from encrypted iPhone backup"
    )
    parser.add_argument("backup_path", help="Path to iPhone backup directory")
    parser.add_argument("--password", required=True, help="Backup encryption password")
    args = parser.parse_args()

    if not os.path.isdir(args.backup_path):
        print(f"ERROR: {args.backup_path} is not a directory")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"  iPhone Backup Key Extractor")
    print(f"{'='*60}")
    print(f"  Backup: {args.backup_path}")
    print(f"  Target: {DEVICE_ID}")
    print(f"{'='*60}\n")

    all_keys = extract_from_encrypted_backup(args.backup_path, args.password)

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")

    if all_keys:
        unique_keys = list({k["key"] for k in all_keys})
        print(f"  Found {len(all_keys)} potential key(s):")
        for k in all_keys:
            print(f"    🔑 Key: {k['key']}")
            print(f"       File: {k['file']}")
            print(f"       Context: {k['context'][:100]}")
            print()

        print(f"  Unique keys to try: {unique_keys}")
        print(f"\n  Validate each with:")
        for key in unique_keys:
            print(f"    python3 validate_key.py {key}")
    else:
        print(f"  ❌ No keys found in backup.")
        print(f"     The app may store keys in a format we didn't match.")
        print(f"     Try manually searching the extracted files.")

    print(f"{'='*60}")


if __name__ == "__main__":
    main()
