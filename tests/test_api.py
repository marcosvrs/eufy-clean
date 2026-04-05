"""Unit tests for the API layer (parser and commands)."""

# Removed: test_update_state_work_status — covered by tests/integration/test_parser_work_status.py
# Removed: test_update_state_work_mode — covered by tests/integration/test_parser_work_status.py
# Removed: test_update_state_error_code — covered by tests/integration/test_parser_error_code.py
# Removed: test_update_state_station_status — covered by tests/integration/test_parser_station.py
# Removed: test_build_spot_clean_command — covered by tests/integration/test_command_roundtrip.py
# Removed: test_build_set_cleaning_mode_command — covered by tests/integration/test_command_roundtrip.py
# Removed: test_build_set_water_level_command — covered by tests/integration/test_command_roundtrip.py
# Removed: test_build_set_cleaning_intensity_command — covered by tests/integration/test_command_roundtrip.py
# Removed: test_build_scene_clean_command — covered by tests/integration/test_command_roundtrip.py
# Removed: test_build_room_clean_command — covered by tests/integration/test_command_roundtrip.py
# Removed: test_build_set_auto_cfg — covered by tests/integration/test_command_roundtrip.py
# Removed: test_build_set_undisturbed_command — covered by tests/integration/test_command_roundtrip.py
# Removed: test_empty_room_clean_echo_preserves_existing_active_rooms — covered by tests/integration/test_parser_work_status.py

from unittest.mock import MagicMock, patch

from custom_components.robovac_mqtt.api.commands import (
    build_command,
    build_find_robot_command,
    build_set_clean_speed_command,
)
from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.unisetting_pb2 import (
    UnisettingResponse,
)
from custom_components.robovac_mqtt.utils import encode


def test_update_state_battery():
    """Test updating battery level."""
    state = VacuumState()
    dps = {DPS_MAP["BATTERY_LEVEL"]: "85"}
    new_state, _ = update_state(state, dps)
    assert new_state.battery_level == 85


def test_build_set_clean_speed():
    """Test building set clean speed command."""
    cmd = build_set_clean_speed_command("Standard")
    assert cmd == {DPS_MAP["CLEAN_SPEED"]: "1"}

    cmd = build_command("set_fan_speed", fan_speed="Max")
    assert cmd == {DPS_MAP["CLEAN_SPEED"]: "3"}


def test_build_find_robot_command():
    """Test building find robot command."""
    cmd = build_find_robot_command(True)
    assert cmd == {DPS_MAP["FIND_ROBOT"]: True}

    cmd = build_find_robot_command(False)
    assert cmd == {DPS_MAP["FIND_ROBOT"]: False}


def test_update_state_find_robot():
    """Test updating find robot state."""
    state = VacuumState()

    dps = {DPS_MAP["FIND_ROBOT"]: True}
    new_state, changes = update_state(state, dps)
    assert new_state.find_robot is True
    assert changes["find_robot"] is True

    dps = {DPS_MAP["FIND_ROBOT"]: "false"}
    new_state, changes = update_state(state, dps)
    assert new_state.find_robot is False


def test_update_state_undisturbed():
    """Test parsing Do Not Disturb state from DPS 157."""
    state = VacuumState()
    dps = {DPS_MAP["UNDISTURBED"]: "EAoAEgwKAggBEgIIFhoCCAg="}

    new_state, changes = update_state(state, dps)

    assert new_state.dnd_enabled is True
    assert new_state.dnd_start_hour == 22
    assert new_state.dnd_start_minute == 0
    assert new_state.dnd_end_hour == 8
    assert new_state.dnd_end_minute == 0
    assert "do_not_disturb" in changes["received_fields"]


def test_completed_docked_refresh_keeps_cleared_targets():
    """Test repeated completed docked updates keep targets cleared."""
    state = VacuumState(
        activity="docked",
        task_status="Completed",
        active_room_ids=[],
        active_room_names="",
    )

    dps = {DPS_MAP["WORK_STATUS"]: "ChADGgByAiIAegA="}
    new_state, _ = update_state(state, dps)

    assert new_state.activity == "docked"
    assert new_state.task_status == "Completed"
    assert new_state.active_room_ids == []
    assert new_state.active_room_names == ""


@patch("custom_components.robovac_mqtt.api.parser.decode")
def test_mid_clean_washing_does_not_clear_active_targets(mock_decode):
    """Test dock-side washing preserves the active room target."""
    state = VacuumState(
        activity="cleaning",
        active_room_ids=[1],
        active_room_names="Kitchen1",
    )

    mock_status = MagicMock()
    mock_status.state = 5
    mock_status.cleaning.state = 1
    mock_status.go_wash.mode = 1
    mock_status.mode.value = 1
    mock_status.HasField.side_effect = lambda field: field in {
        "mode",
        "charging",
        "cleaning",
        "go_wash",
        "station",
    }
    mock_status.station.HasField.return_value = True
    mock_decode.return_value = mock_status

    dps = {DPS_MAP["WORK_STATUS"]: "encoded"}
    new_state, _ = update_state(state, dps)

    assert new_state.activity == "docked"
    assert new_state.task_status == "Washing Mop"
    assert new_state.active_room_ids == [1]
    assert new_state.active_room_names == "Kitchen1"


@patch("custom_components.robovac_mqtt.api.parser.decode")
def test_charging_paused_state_does_not_clear_active_targets(mock_decode):
    """Test paused charging during wash preparation does not clear target."""
    state = VacuumState(
        activity="cleaning",
        active_room_ids=[1],
        active_room_names="Kitchen1",
    )

    mock_status = MagicMock()
    mock_status.state = 3
    mock_status.cleaning.state = 1
    mock_status.HasField.side_effect = lambda field: field in {
        "charging",
        "cleaning",
        "station",
        "mode",
    }
    mock_status.mode.value = 1
    mock_status.station.HasField.return_value = False
    mock_decode.return_value = mock_status

    dps = {DPS_MAP["WORK_STATUS"]: "encoded"}
    new_state, _ = update_state(state, dps)

    assert new_state.activity == "docked"
    assert new_state.task_status == "Paused"
    assert new_state.active_room_ids == [1]
    assert new_state.active_room_names == "Kitchen1"


@patch("custom_components.robovac_mqtt.api.parser.decode")
def test_completed_docked_state_clears_active_targets(mock_decode):
    """Test completed docked states clear the active room target."""
    state = VacuumState(
        activity="docked",
        task_status="Washing Mop",
        active_room_ids=[1],
        active_room_names="Kitchen1",
    )

    mock_status = MagicMock()
    mock_status.state = 3
    mock_status.HasField.side_effect = lambda field: field in {"charging"}
    mock_decode.return_value = mock_status

    dps = {DPS_MAP["WORK_STATUS"]: "encoded"}
    new_state, _ = update_state(state, dps)

    assert new_state.activity == "docked"
    assert new_state.task_status == "Completed"
    assert new_state.active_room_ids == []
    assert new_state.active_room_names == ""


def test_update_state_device_info_dps169():
    """Test parsing DPS 169 (DeviceInfo) for MAC, WiFi SSID, and WiFi IP."""
    state = VacuumState()
    dps = {
        DPS_MAP["MAP_MANAGE"]: "vgEKF2V1ZnkgQ2xlYW4gWDEwIFBybyBPbW5pGhFhYTpi"
        "YjpjYzpkZDplZTpmZiIGMy40Ljg1KAMyCUFOT05fV0lGSToNMTkyLjE2OC4xLjEwMEIS"
        "QU5PTl9VU0VSX0hBU0hfMDAxWgoKBjEuMi4yNxAIYi0IARIECAIQAxoECAIQDyIECAEQ"
        "ATIECAEQAzoECAEQAUIECAEQA1IFCAEQsyRqCVQyMzUxX290YQ=="
    }
    new_state, _ = update_state(state, dps)
    assert new_state.device_mac == "aa:bb:cc:dd:ee:ff"
    assert new_state.wifi_ssid == "ANON_WIFI"
    assert new_state.wifi_ip == "192.168.1.100"
    assert "wifi_ssid" in new_state.received_fields
    assert "wifi_ip" in new_state.received_fields


def test_update_state_wifi_signal_dps176():
    """Test parsing WiFi signal strength from DPS 176 (UnisettingResponse)."""
    encoded = encode(UnisettingResponse, {"ap_signal_strength": 80})

    state = VacuumState()
    dps = {DPS_MAP["UNSETTING"]: encoded}
    new_state, _ = update_state(state, dps)
    assert new_state.wifi_signal == -60.0
    assert "wifi_signal" in new_state.received_fields


def test_update_state_robot_position_dps179():
    """Test parsing robot position from DPS 179 telemetry."""
    state = VacuumState()
    dps = {"179": "HBIaOhgIlrujzgYQYxhiIPx9KIcOMgbO3QKg6gI="}
    new_state, changes = update_state(state, dps)
    assert "robot_position_x" in changes
    assert "robot_position_y" in changes
    assert isinstance(new_state.robot_position_x, int)
    assert isinstance(new_state.robot_position_y, int)
    assert "robot_position" in new_state.received_fields


def test_known_unprocessed_dps_does_not_crash():
    """Test that known-but-unprocessed DPS keys are handled gracefully."""
    state = VacuumState()
    dps = {"155": None, "156": True, "161": 80}
    new_state, _ = update_state(state, dps)
    assert new_state.activity == "idle"
