"""Unit tests for api/commands.py: invalid command edge cases."""

from custom_components.robovac_mqtt.api.commands import (
    build_command,
    build_set_cleaning_intensity_command,
    build_set_cleaning_mode_command,
    build_set_water_level_command,
)


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
