"""Unit tests for api/parser.py: room name deduplication, task status edge cases,
and const lookups. Work status mapping and cleaning parameter tests are covered
by the integration suite."""

# Removed: test_map_work_status_idle — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_error — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_docked — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_cleaning — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_returning — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_washing_shows_docked — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_drying_shows_docked — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_navigation_to_wash_shows_cleaning — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_station_wash_drying_shows_docked — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_plain_cleaning — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_state_15_paused — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_cleaning_paused — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_cleaning_paused_with_go_wash_ignored — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_cleaning_doing — covered by tests/integration/test_parser_work_status.py
# Removed: test_map_work_status_emptying_dust — covered by tests/integration/test_parser_station.py
# Removed: test_process_cleaning_params_cleaning_mode — covered by tests/integration/test_parser_station.py
# Removed: test_process_cleaning_params_fan_speed — covered by tests/integration/test_parser_station.py
# Removed: test_process_cleaning_params_mop_water_level — covered by tests/integration/test_parser_station.py
# Removed: test_process_cleaning_params_corner_cleaning_normal — covered by tests/integration/test_parser_station.py
# Removed: test_process_cleaning_params_corner_cleaning_deep — covered by tests/integration/test_parser_station.py
# Removed: test_process_cleaning_params_cleaning_intensity — covered by tests/integration/test_parser_station.py
# Removed: test_process_cleaning_params_carpet_strategy — covered by tests/integration/test_parser_station.py
# Removed: test_process_cleaning_params_smart_mode — covered by tests/integration/test_parser_station.py
# Removed: test_process_cleaning_params_all_fields — covered by tests/integration/test_parser_station.py
# Removed: test_process_cleaning_params_decode_failure — covered by tests/integration/test_edge_cases.py
# Removed: test_process_cleaning_params_fallback_to_request — covered by tests/integration/test_parser_station.py
# Removed: test_map_data_room_names_no_id_suffix — covered by tests/integration/test_parser_station.py

from unittest.mock import MagicMock

import pytest  # pyright: ignore[reportMissingImports]

from custom_components.robovac_mqtt.api.parser import (
    _deduplicate_room_names,
    _log_proto_novelty,
    _map_task_status,
    update_state,
)
from custom_components.robovac_mqtt.const import DEFAULT_DPS_MAP, WORK_MODE_NAMES
from custom_components.robovac_mqtt.models import VacuumState


def test_map_task_status_emptying_dust():
    """Test task status when emptying dust at dock."""
    ws = MagicMock()
    ws.state = 3
    ws.HasField.side_effect = lambda f: f in {"station", "dust_collection_system"}
    ws.station.HasField.side_effect = lambda f: f == "dust_collection_system"
    ws.station.dust_collection_system.state = 0
    assert _map_task_status(ws, "Idle") == "Emptying Dust"


def test_deduplicate_room_names():
    """Test that duplicate room names get a numbered suffix."""
    rooms = [
        {"id": 1, "name": "Kitchen"},
        {"id": 2, "name": "Kitchen"},
        {"id": 3, "name": "Bedroom"},
        {"id": 4, "name": "Kitchen"},
    ]
    result = _deduplicate_room_names(rooms)

    assert result[0] == {"id": 1, "name": "Kitchen"}
    assert result[1] == {"id": 2, "name": "Kitchen (2)"}
    assert result[2] == {"id": 3, "name": "Bedroom"}
    assert result[3] == {"id": 4, "name": "Kitchen (3)"}


def test_deduplicate_room_names_no_duplicates():
    """Test that unique room names are unchanged."""
    rooms = [
        {"id": 1, "name": "Kitchen"},
        {"id": 2, "name": "Bedroom"},
    ]
    result = _deduplicate_room_names(rooms)
    assert result == rooms


def test_work_mode_names_mapping():
    """Test that work mode values are correctly mapped to names."""
    assert WORK_MODE_NAMES[0] == "Auto"
    assert WORK_MODE_NAMES[1] == "Room"
    assert WORK_MODE_NAMES[3] == "Spot"
    assert WORK_MODE_NAMES[8] == "Scene"


def test_log_proto_novelty_exception_logs_debug(caplog):
    """_log_proto_novelty swallows exceptions but logs at debug level."""
    import logging
    from unittest.mock import patch

    with caplog.at_level(logging.DEBUG, logger="custom_components.robovac_mqtt.api.parser"):
        with patch(
            "custom_components.robovac_mqtt.api.parser._listfields_paths",
            side_effect=Exception("boom"),
        ):
            _log_proto_novelty("153", MagicMock(), "AAAA")

    assert "Proto novelty detection failed" in caplog.text


def test_update_state_consumable_runtime_exception_logs_warning(caplog):
    """update_state() logs warning when consumable runtime decode fails."""
    import logging
    from unittest.mock import patch

    base_state = VacuumState()
    dps_key = DEFAULT_DPS_MAP.get("ACCESSORIES_STATUS", "168")

    with caplog.at_level(logging.WARNING, logger="custom_components.robovac_mqtt.api.parser"):
        with patch("custom_components.robovac_mqtt.api.parser.decode", side_effect=Exception("decode error")):
            update_state(base_state, {dps_key: "AAAA"})

    assert "Failed to parse consumable runtime" in caplog.text
