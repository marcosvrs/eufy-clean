from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from custom_components.robovac_mqtt.api.parser import _parse_robot_telemetry
from custom_components.robovac_mqtt.proto.cloud.realtime_stream_pb2 import (
    RealtimeStream,
)
from custom_components.robovac_mqtt.utils import decode


FIXTURE_PATH = Path("tests/fixtures/mqtt/telemetry/position_update.json")
_LOGGER = logging.getLogger(__name__)


def _strip_length_prefix(data: bytes) -> bytes:
    i = 0
    while i < len(data) and (data[i] & 0x80):
        i += 1
    return data[i + 1 :]


def _all_dps_179_values() -> list[str]:
    data = json.loads(FIXTURE_PATH.read_text())
    values = list(data["dps"].values())
    for item in data["additional_captured_values"]:
        values.extend(item["dps"].values())
    return values


def _decode_stream(value: str) -> RealtimeStream:
    msg = RealtimeStream()
    msg.ParseFromString(_strip_length_prefix(base64.b64decode(value)))
    return msg


def test_all_position_ping_values_decode() -> None:
    values = [
        value
        for value in _all_dps_179_values()
        if len(base64.b64decode(value)) in {28, 29, 30}
    ]

    decoded = 0
    for value in values:
        stream = _decode_stream(value)
        assert stream.HasField("data")
        assert stream.data.HasField("position")

        position = stream.data.position
        if not (position.x or position.y):
            continue

        parsed = decode(RealtimeStream, value)
        assert parsed.data.position.x == position.x
        assert parsed.data.position.y == position.y
        decoded += 1

    _LOGGER.info("Decoded %s DPS 179 position pings", decoded)
    assert decoded == 87


def test_parser_telemetry_decoder_uses_proto() -> None:
    value = next(
        item
        for item in _all_dps_179_values()
        if len(base64.b64decode(item)) == 29
    )

    parsed = _parse_robot_telemetry(value)
    stream = _decode_stream(value)

    assert parsed == {
        "x": stream.data.position.x,
        "y": stream.data.position.y,
    }
