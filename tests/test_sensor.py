"""Unit tests for RoboVacSensor entities."""

# Removed: test_sensor_generic — covered by tests/integration/test_entity_sensor.py
# Removed: test_dock_status_sensor — covered by tests/integration/test_entity_sensor.py
# Removed: test_water_level_sensor — covered by tests/integration/test_entity_sensor.py
# Removed: test_error_message_sensor — covered by tests/integration/test_entity_sensor.py

from unittest.mock import MagicMock

import pytest

from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.sensor import (
    _active_rooms_available,
    _active_rooms_value,
)


@pytest.fixture
def mock_coordinator():
    """Mock the coordinator."""
    coordinator = MagicMock()
    coordinator.device_id = "test_id"
    coordinator.device_name = "Test Vac"
    coordinator.device_model = "T2118"
    coordinator.data = VacuumState()
    coordinator.last_update_success = True
    return coordinator


def test_active_rooms_uses_scene_name_when_room_ids_are_empty(mock_coordinator):
    """Test active rooms sensor falls back to scene names."""
    mock_coordinator.data.current_scene_id = 7
    mock_coordinator.data.current_scene_name = "After Dinner"

    assert _active_rooms_available(mock_coordinator.data) is True
    assert _active_rooms_value(mock_coordinator.data) == "After Dinner"


def test_active_rooms_uses_zone_count_when_present(mock_coordinator):
    """Test active rooms sensor falls back to zone count."""
    mock_coordinator.data.active_zone_count = 2

    assert _active_rooms_available(mock_coordinator.data) is True
    assert _active_rooms_value(mock_coordinator.data) == "2 zones"
