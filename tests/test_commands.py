"""Unit tests for api/commands.py: invalid command edge cases."""

from custom_components.robovac_mqtt.api.commands import (
    build_command,
    build_set_child_lock_command,
    build_set_cleaning_intensity_command,
    build_set_cleaning_mode_command,
    build_set_water_level_command,
)
from custom_components.robovac_mqtt.const import DPS_MAP
from custom_components.robovac_mqtt.proto.cloud.unisetting_pb2 import UnisettingRequest
from custom_components.robovac_mqtt.utils import decode


def test_set_cleaning_mode_invalid():
    """Invalid cleaning mode should return empty dict."""
    result = build_set_cleaning_mode_command("nonexistent_mode")
    assert not result


def test_set_water_level_invalid():
    """Invalid water level should return empty dict."""
    result = build_set_water_level_command("super_high")
    assert not result


def test_set_cleaning_intensity_invalid():
    """Invalid cleaning intensity should return empty dict."""
    result = build_set_cleaning_intensity_command("ultra_deep")
    assert not result


def test_build_command_unknown_returns_empty():
    """Test build_command with unknown command returns empty dict."""
    assert not build_command("nonexistent_command")


def test_set_child_lock_command():
    """Child lock command should encode a writable UnisettingRequest."""
    result = build_set_child_lock_command(True)

    assert DPS_MAP["UNSETTING"] in result
    decoded = decode(UnisettingRequest, result[DPS_MAP["UNSETTING"]])
    assert decoded.children_lock.value is True
