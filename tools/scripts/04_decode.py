#!/usr/bin/env python3
"""
Phase 4: Brute-force map decoder.

Tries every plausible combination of decompression, header skipping,
and dimension detection on extracted binary payloads. Renders any
successful decode as a PNG image.

Usage:
    python3 scripts/04_decode.py output/map_payloads/port_XXXX_outgoing/
    python3 scripts/04_decode.py some_file.bin
"""

import argparse
import io
import os
import struct
import sys
import zlib
import gzip
import lzma
import base64
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)


TUYA_MAP_PIXEL_COLORS = {
    0: (180, 200, 220),  # unknown / room (light blue-gray)
    1: (40, 40, 60),     # obstacle / wall (dark)
    2: (160, 120, 80),   # carpet (brownish)
    3: (240, 240, 240),  # blank / unpartitioned (near-white)
}

RENDER_OUTPUT_DIR = Path("output/map_renders")


def try_all_decompressions(data: bytes) -> list[tuple[str, bytes]]:
    results = []
    methods = [
        ("raw", lambda d: d),
        ("zlib", lambda d: zlib.decompress(d)),
        ("zlib_raw", lambda d: zlib.decompress(d, -15)),
        ("zlib_gzip", lambda d: zlib.decompress(d, 31)),
        ("gzip", lambda d: gzip.decompress(d)),
        ("lzma", lambda d: lzma.decompress(d)),
    ]

    for skip in [0, 2, 4, 8, 12, 16, 20, 24, 32, 48, 64, 128]:
        if skip >= len(data):
            break
        chunk = data[skip:]
        for name, fn in methods:
            try:
                result = fn(chunk)
                if len(result) > 100:
                    label = f"skip({skip})+{name}" if skip else name
                    results.append((label, result))
            except Exception:
                pass

    # base64 decode then try again
    try:
        b64 = base64.b64decode(data)
        for name, fn in methods:
            try:
                result = fn(b64)
                if len(result) > 100:
                    results.append((f"b64+{name}", result))
            except Exception:
                pass
    except Exception:
        pass

    return results


def find_dimensions(data: bytes) -> list[dict]:
    """
    Scan binary data for plausible (width, height) pairs where
    width * height approximately equals the available pixel data.
    This is necessary because the Tuya map format packs header fields
    at unknown offsets — we brute-force all plausible positions.
    """
    candidates = []

    for offset in range(0, min(256, len(data) - 8), 2):
        for endian, label in [('<', 'LE'), ('>', 'BE')]:
            for fmt_char, size in [('H', 2), ('I', 4)]:
                fmt = f"{endian}{fmt_char}{fmt_char}"
                try:
                    w, h = struct.unpack_from(fmt, data, offset)
                except struct.error:
                    continue

                if not (50 < w < 4000 and 50 < h < 4000):
                    continue

                pixel_count = w * h
                header_size = offset + struct.calcsize(fmt)
                remaining = len(data) - header_size

                # 1 byte per pixel is most common; 2 or 4 also possible
                for bpp in [1, 2, 4]:
                    expected = pixel_count * bpp
                    ratio = remaining / max(expected, 1)
                    if 0.7 < ratio < 1.5:
                        candidates.append({
                            "offset": offset,
                            "endian": label,
                            "fmt": fmt,
                            "width": w,
                            "height": h,
                            "bpp": bpp,
                            "header_size": header_size,
                            "data_start": header_size,
                            "remaining": remaining,
                            "ratio": ratio,
                        })

    candidates.sort(key=lambda c: abs(c["ratio"] - 1.0))
    return candidates[:20]


def try_render_with_dimensions(data: bytes, candidates: list[dict], prefix: str) -> list[str]:
    saved = []
    RENDER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for c in candidates:
        w, h, bpp = c["width"], c["height"], c["bpp"]
        start = c["data_start"]
        pixels = data[start:start + w * h * bpp]

        if bpp == 1:
            img = Image.frombytes('L', (w, h), pixels[:w * h])
        elif bpp == 2:
            raw = []
            for i in range(0, len(pixels) - 1, 2):
                val = struct.unpack_from('<H', pixels, i)[0]
                raw.append(min(val, 255))
            if len(raw) < w * h:
                continue
            img = Image.frombytes('L', (w, h), bytes(raw[:w * h]))
        else:
            continue

        histogram = img.histogram()
        nonzero_bins = sum(1 for v in histogram if v > 0)

        # Maps have very few distinct pixel values (typically 3-10).
        # Random noise/encrypted data has 100+.
        if nonzero_bins > 50:
            continue

        path = RENDER_OUTPUT_DIR / f"{prefix}_{w}x{h}_off{c['offset']}_{c['endian']}.png"
        img.save(str(path))
        saved.append(str(path))
        print(f"    🖼️  {path.name} — {nonzero_bins} distinct values")

    return saved


def try_render_brute_force(data: bytes, prefix: str) -> list[str]:
    """
    When no header dimensions are found, try common vacuum map widths
    and check if the result looks structured (few distinct pixel values)
    rather than noise (many distinct values).
    """
    saved = []
    RENDER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for w in range(100, 2000, 25):
        h = len(data) // w
        if h < 50 or h > 3000:
            continue

        try:
            img = Image.frombytes('L', (w, h), data[:w * h])
        except Exception:
            continue

        histogram = img.histogram()
        nonzero_bins = sum(1 for v in histogram if v > 0)

        if nonzero_bins < 15:
            path = RENDER_OUTPUT_DIR / f"{prefix}_brute_{w}x{h}.png"
            img.save(str(path))
            saved.append(str(path))
            print(f"    🖼️  {path.name} — {nonzero_bins} distinct values (brute force)")

    return saved


def try_tuya_standard_decode(data: bytes, prefix: str) -> list[str]:
    """
    Attempt to decode using the known TuyaOS RVC map structure:
      offset 0: map_id (uint16)
      offset 2: status (uint32)
      offset 6: width (uint32)
      offset 10: height (uint32)
      offset 14: resolution (uint32) — cm per pixel
      offset 18: origin_x (int32)
      offset 22: origin_y (int32)
      offset 26: charge_x (int32)
      offset 30: charge_y (int32)
      offset 34: charge_angle (uint32)
      offset 38: pixel data (width * height bytes)
    """
    saved = []
    if len(data) < 40:
        return saved

    for endian in ['<', '>']:
        try:
            map_id = struct.unpack_from(f'{endian}H', data, 0)[0]
            status = struct.unpack_from(f'{endian}I', data, 2)[0]
            width = struct.unpack_from(f'{endian}I', data, 6)[0]
            height = struct.unpack_from(f'{endian}I', data, 10)[0]
            resolution = struct.unpack_from(f'{endian}I', data, 14)[0]
            origin_x = struct.unpack_from(f'{endian}i', data, 18)[0]
            origin_y = struct.unpack_from(f'{endian}i', data, 22)[0]
            charge_x = struct.unpack_from(f'{endian}i', data, 26)[0]
            charge_y = struct.unpack_from(f'{endian}i', data, 30)[0]
        except struct.error:
            continue

        if not (50 < width < 4000 and 50 < height < 4000):
            continue
        if status not in (0, 1):
            continue
        if resolution == 0 or resolution > 100:
            continue

        pixel_data = data[38:38 + width * height]
        if len(pixel_data) < width * height:
            continue

        e_label = "LE" if endian == '<' else "BE"
        print(f"    ✅ Tuya standard header ({e_label}):")
        print(f"       map_id={map_id}, status={status}, "
              f"{width}x{height}, res={resolution}cm")
        print(f"       origin=({origin_x},{origin_y}), "
              f"charger=({charge_x},{charge_y})")

        img = Image.new('RGB', (width, height), (0, 0, 0))
        for i, px in enumerate(pixel_data):
            x = i % width
            y = i // width
            color = TUYA_MAP_PIXEL_COLORS.get(px, (255, 0, 0))
            img.putpixel((x, y), color)

        path = RENDER_OUTPUT_DIR / f"{prefix}_tuya_{e_label}_{width}x{height}.png"
        img.save(str(path))
        saved.append(str(path))
        print(f"    🖼️  {path.name}")

    return saved


def process_file(filepath: Path):
    data = filepath.read_bytes()
    prefix = filepath.stem
    all_saved = []

    print(f"\n{'='*60}")
    print(f"  FILE: {filepath.name} ({len(data)} bytes)")
    print(f"  Header: {data[:32].hex()}")
    print(f"{'='*60}")

    print(f"\n  [1] Trying Tuya standard header decode...")
    saved = try_tuya_standard_decode(data, prefix)
    all_saved.extend(saved)

    print(f"\n  [2] Trying decompression methods...")
    decomp_results = try_all_decompressions(data)
    for label, decompressed in decomp_results:
        print(f"    ✅ {label}: {len(data)} → {len(decompressed)} bytes")

        saved = try_tuya_standard_decode(decompressed, f"{prefix}_{label}")
        all_saved.extend(saved)

        candidates = find_dimensions(decompressed)
        if candidates:
            print(f"    Found {len(candidates)} dimension candidates")
            saved = try_render_with_dimensions(decompressed, candidates, f"{prefix}_{label}")
            all_saved.extend(saved)

    print(f"\n  [3] Scanning raw data for dimension pairs...")
    candidates = find_dimensions(data)
    if candidates:
        print(f"    Found {len(candidates)} candidates")
        for c in candidates[:5]:
            print(f"      {c['width']}x{c['height']} at offset {c['offset']} "
                  f"({c['endian']}, {c['bpp']}bpp, ratio={c['ratio']:.2f})")
        saved = try_render_with_dimensions(data, candidates, prefix)
        all_saved.extend(saved)

    print(f"\n  [4] Brute-force dimension sweep...")
    for target_data, label in [(data, prefix)] + [
        (d, f"{prefix}_{l}") for l, d in decomp_results[:3]
    ]:
        saved = try_render_brute_force(target_data, label)
        all_saved.extend(saved)

    if all_saved:
        print(f"\n  ✅ Generated {len(all_saved)} image(s) — check output/map_renders/")
    else:
        print(f"\n  ❌ No map images decoded from this file.")
        print(f"     The format may be encrypted or use an unknown structure.")
        print(f"     Check the hex dump and look for patterns manually.")

    return all_saved


def main():
    parser = argparse.ArgumentParser(description="Brute-force decode map payloads")
    parser.add_argument(
        "path",
        help="Path to a .bin file or directory of .bin files"
    )
    parser.add_argument(
        "--max-files", type=int, default=50,
        help="Maximum number of files to process"
    )
    args = parser.parse_args()

    target = Path(args.path)

    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(target.glob("**/*.bin"))[:args.max_files]
    else:
        print(f"ERROR: {target} not found")
        sys.exit(1)

    if not files:
        print(f"No .bin files found in {target}")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"  Eufy Map Decoder")
    print(f"{'='*60}")
    print(f"  Input: {target}")
    print(f"  Files: {len(files)}")
    print(f"  Output: {RENDER_OUTPUT_DIR}/")
    print(f"{'='*60}")

    total_saved = []
    for f in files:
        saved = process_file(f)
        total_saved.extend(saved)

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    if total_saved:
        print(f"  ✅ Generated {len(total_saved)} map image(s):")
        for p in total_saved:
            print(f"     {p}")
        print(f"\n  Open these images and look for one that resembles your floor plan.")
        print(f"  Once you find the right decode parameters, note the filename")
        print(f"  (it encodes the method, dimensions, and offset used).")
    else:
        print(f"  ❌ No maps decoded. Possible reasons:")
        print(f"     - Data is encrypted (Tuya AES-128-ECB with local_key)")
        print(f"     - Format is non-standard for this Eufy model")
        print(f"     - The captured data isn't actually map data")
        print(f"\n  Try 05_tuya_probe.py to query the vacuum directly via Tuya protocol.")


if __name__ == "__main__":
    main()
