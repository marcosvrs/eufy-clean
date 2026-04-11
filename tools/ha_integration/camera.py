#!/usr/bin/env python3
"""
Phase 6: Home Assistant camera entity skeleton.

Once you've decoded the map format, wire this into your HA custom_components
to display the vacuum map as a camera entity. Update decode_map_frame() with
the parameters discovered in Phase 4.

Install: copy ha_integration/ to config/custom_components/eufy_vacuum_map/
"""

import io
import logging
import struct
import threading
import time

_LOGGER = logging.getLogger(__name__)

DOMAIN = "eufy_vacuum_map"
SCAN_INTERVAL = 5


# ──────────────────────────────────────────────────────────────
#  FILL IN: Your decode parameters discovered in Phase 4
# ──────────────────────────────────────────────────────────────
MAP_HEADER_SIZE = 38
MAP_WIDTH_OFFSET = 6
MAP_HEIGHT_OFFSET = 10
MAP_ENDIAN = "<"
MAP_PIXEL_START = 38
DECOMPRESS_METHOD = None  # "zlib", "gzip", or None for raw


PIXEL_COLORS = {
    0: (180, 200, 220, 255),
    1: (40, 40, 60, 255),
    2: (160, 120, 80, 255),
    3: (240, 240, 240, 255),
}

CHARGER_COLOR = (0, 200, 0, 255)
ROBOT_COLOR = (0, 100, 255, 255)


def decode_map_frame(raw_data: bytes) -> bytes | None:
    """
    Decode raw vacuum data into a PNG image.
    Update the struct offsets and pixel mapping based on your Phase 4 findings.
    Returns PNG bytes or None on failure.
    """
    try:
        from PIL import Image
    except ImportError:
        _LOGGER.error("Pillow not installed")
        return None

    data = raw_data
    if DECOMPRESS_METHOD == "zlib":
        import zlib

        data = zlib.decompress(raw_data)
    elif DECOMPRESS_METHOD == "gzip":
        import gzip

        data = gzip.decompress(raw_data)

    if len(data) < MAP_HEADER_SIZE + 100:
        return None

    try:
        width = struct.unpack_from(f"{MAP_ENDIAN}I", data, MAP_WIDTH_OFFSET)[0]
        height = struct.unpack_from(f"{MAP_ENDIAN}I", data, MAP_HEIGHT_OFFSET)[0]
    except struct.error:
        return None

    if not (50 < width < 4000 and 50 < height < 4000):
        return None

    pixels = data[MAP_PIXEL_START : MAP_PIXEL_START + width * height]
    if len(pixels) < width * height:
        return None

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for i, px in enumerate(pixels):
        x = i % width
        y = i // width
        img.putpixel((x, y), PIXEL_COLORS.get(px, (255, 0, 0, 128)))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class EufyVacuumMapCamera:
    """
    HA Camera entity that displays the vacuum map.
    Subclass homeassistant.components.camera.Camera and register
    via async_setup_entry in your integration.
    """

    def __init__(
        self,
        vacuum_ip: str,
        device_id: str,
        local_key: str,
        protocol_version: str = "3.4",
        map_port: int | None = None,
    ):
        self._ip = vacuum_ip
        self._device_id = device_id
        self._local_key = local_key
        self._version = protocol_version
        self._map_port = map_port
        self._latest_image: bytes | None = None
        self._running = False

    def camera_image(self) -> bytes | None:
        return self._latest_image

    def start_polling(self, interval: int = SCAN_INTERVAL):
        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop, args=(interval,), daemon=True
        )
        self._thread.start()

    def stop_polling(self):
        self._running = False

    def _poll_loop(self, interval: int):
        import tinytuya

        device = tinytuya.Device(self._device_id, self._ip, self._local_key)
        device.set_version(float(self._version))
        device.set_socketPersistent(True)

        while self._running:
            try:
                raw_map = self._fetch_map_data(device)
                if raw_map:
                    png = decode_map_frame(raw_map)
                    if png:
                        self._latest_image = png
            except Exception as e:
                _LOGGER.warning("Map fetch failed: %s", e)

            time.sleep(interval)

    def _fetch_map_data(self, device) -> bytes | None:
        """
        Fetch map data from the vacuum.

        Strategy depends on your Phase 2/3/5 findings:
        - DPS method: query DPS 15/17/26/102/103
        - P2P method: connect to self._map_port and read stream
        - Both: try DPS first, fall back to stream

        Update this method based on what works for your X10 Pro Omni.
        """
        import base64

        device.set_multiple_values({"17": "get_map"})
        time.sleep(1)
        status = device.status()
        dps = status.get("dps", {})

        for dp_id in ["26", "102", "15"]:
            if dp_id in dps and dps[dp_id]:
                value = dps[dp_id]
                if isinstance(value, str) and len(value) > 50:
                    try:
                        return base64.b64decode(value)
                    except Exception:
                        return value.encode()

        return None


def standalone_test():
    """Run outside HA for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Test vacuum map camera")
    parser.add_argument("--ip", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--local-key", required=True)
    parser.add_argument("--version", default="3.4")
    parser.add_argument("--output", default="output/map_renders/ha_test.png")
    args = parser.parse_args()

    cam = EufyVacuumMapCamera(args.ip, args.device_id, args.local_key, args.version)

    print("Fetching map data...")
    import tinytuya

    device = tinytuya.Device(args.device_id, args.ip, args.local_key)
    device.set_version(float(args.version))

    raw = cam._fetch_map_data(device)
    if raw:
        print(f"Got {len(raw)} bytes of map data")
        png = decode_map_frame(raw)
        if png:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_bytes(png)
            print(f"Map saved to {args.output}")
        else:
            print("Failed to decode map data. Run 04_decode.py on the raw data.")
            Path("output/dps_payloads/ha_test_raw.bin").write_bytes(raw)
    else:
        print("No map data received. Try 05_tuya_probe.py first.")


if __name__ == "__main__":
    from pathlib import Path

    standalone_test()
