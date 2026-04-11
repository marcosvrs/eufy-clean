"""Reusable factory functions and formatters for integration tests.

Pure Python — no Home Assistant imports. Provides helpers to build
VacuumState instances, protobuf messages, DPS payloads, and MQTT
JSON wrappers used throughout the integration test suite.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.clean_param_pb2 import (
    CleanParamResponse,
)
from custom_components.robovac_mqtt.proto.cloud.station_pb2 import StationResponse
from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import WorkStatus
from custom_components.robovac_mqtt.utils import encode_message


def make_vacuum_state(**overrides: Any) -> VacuumState:
    """Create a VacuumState with X-Series defaults (docked, charged, no error).

    Accept any VacuumState field as keyword override.

    Default values:
        activity="docked", battery_level=100, error_code=0, charging=True
    """
    defaults = {
        "activity": "docked",
        "battery_level": 100,
        "error_code": 0,
        "charging": True,
    }
    defaults.update(overrides)
    return replace(VacuumState(), **defaults)


def make_dps_payload(dps_key: str, proto_msg: Any) -> dict[str, str]:
    """Encode a protobuf message as a DPS payload dict {dps_key: base64_value}.

    Uses ``encode_message()`` from utils.py to serialize the protobuf with
    a varint length prefix and base64-encode it.

    Do NOT use for plain-value DPS keys (163, 158, 160) — those are raw
    int/bool strings, not protobuf.
    """
    return {dps_key: encode_message(proto_msg)}


def make_mqtt_bytes(dps: dict[str, Any], device_sn: str = "T2261_ANON_001") -> bytes:
    """Wrap DPS dict into full MQTT JSON message bytes for coordinator input.

    Produces the same JSON structure the MQTT broker sends::

        {
            "head": {"cmd": 65537, "client_id": "anon"},
            "payload": {"data": dps, "device_sn": device_sn}
        }

    NOTE: DPS 163 (battery), 158 (speed), 160 (find_robot) are plain values,
    NOT base64 protobuf. Pass them as regular strings in *dps*.
    """
    msg = {
        "head": {
            "cmd": 65537,
            "client_id": "anon",
        },
        "payload": {
            "data": dps,
            "device_sn": device_sn,
        },
    }
    return json.dumps(msg).encode("utf-8")


def make_work_status(state: int = 0, **kwargs: Any) -> WorkStatus:
    """Build a WorkStatus proto message.

    Args:
        state: WorkStatus state enum int (0=idle, 3=docked, 5=cleaning,
               7=returning).
        **kwargs: Any WorkStatus field. Note the charging field is
                  ``charging`` (a nested Charging message), NOT
                  ``charge_state``.
    """
    ws = WorkStatus(state=state, **kwargs)
    return ws


def make_station_response(**kwargs: Any) -> StationResponse:
    """Build a StationResponse proto message with given fields."""
    return StationResponse(**kwargs)


def make_clean_param_response(**kwargs: Any) -> CleanParamResponse:
    """Build a CleanParamResponse proto message with given fields."""
    return CleanParamResponse(**kwargs)


def make_device_info_dict(
    device_id: str = "T2261_ANON_001",
    model: str = "T2261",
    name: str = "Test Vacuum",
    soft_version: str = "1.0.0",
) -> dict[str, str]:
    """Return device info dict matching EufyCleanCoordinator constructor format.

    Keys match the camelCase names used by coordinator.py (lines 38-41):
    ``deviceId``, ``deviceModel``, ``deviceName``, ``softVersion``.
    """
    return {
        "deviceId": device_id,
        "deviceModel": model,
        "deviceName": name,
        "softVersion": soft_version,
    }


def assert_state_field(state: VacuumState, field: str, expected: Any) -> None:
    """Assert a VacuumState field equals expected, with helpful failure message.

    Raises:
        AssertionError: When the actual value doesn't match *expected*.
    """
    actual = getattr(state, field)
    assert (
        actual == expected
    ), f"VacuumState.{field}: expected {expected!r}, got {actual!r}"
