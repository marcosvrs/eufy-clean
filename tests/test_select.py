"""Unit tests for the Select entities."""

# Removed: test_dock_select_entity_async — covered by tests/integration/test_entity_controls.py
# Removed: test_scene_select_entity — covered by tests/integration/test_entity_controls.py
# Removed: test_room_select_entity — covered by tests/integration/test_entity_controls.py
# Removed: test_cleaning_mode_select_entity — covered by tests/integration/test_entity_controls.py
# Removed: test_water_level_select_entity — covered by tests/integration/test_entity_controls.py
# Removed: test_cleaning_intensity_select_entity — covered by tests/integration/test_entity_controls.py
# Removed: test_mop_intensity_select_entity_entity_category — covered by tests/integration/test_entity_controls.py
# Removed: test_mop_intensity_select_entity_async — covered by tests/integration/test_entity_controls.py
# Removed: test_dock_select_deepcopy_no_mutation — covered by tests/integration/test_entity_controls.py
# Removed: test_dock_select_unavailable_no_cfg — covered by tests/integration/test_entity_controls.py
# Removed: test_scene_select_current_option_with_id — covered by tests/integration/test_entity_controls.py
# Removed: test_suction_level_unavailable_without_fan_speed — covered by tests/integration/test_entity_controls.py
# Removed: test_suction_level_available_with_fan_speed — covered by tests/integration/test_entity_controls.py

# pylint: disable=redefined-outer-name

from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory

from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.select import (
    DockSelectEntity,
    MopIntensitySelectEntity,
)


@pytest.fixture
def mock_coordinator():
    """Mock the coordinator."""
    coordinator = MagicMock(spec=EufyCleanCoordinator)
    coordinator.data = VacuumState()
    coordinator.device_id = "test_device"
    coordinator.device_name = "Test Device"
    coordinator.device_model = "T2118"
    coordinator.last_update_success = True
    return coordinator


def test_dock_select_entity(mock_coordinator):
    """Test DockSelectEntity property assertions."""
    mock_coordinator.data.dock_auto_cfg = {
        "wash": {"wash_freq": {"mode": "ByPartition"}}
    }

    def _get_wash_freq(cfg):
        mode = cfg.get("wash", {}).get("wash_freq", {}).get("mode", "ByPartition")
        return "ByRoom" if mode == "ByPartition" else "ByTime"

    def _set_wash_freq(cfg, val):
        if "wash" not in cfg:
            cfg["wash"] = {}
        if "wash_freq" not in cfg["wash"]:
            cfg["wash"]["wash_freq"] = {}
        mode = "ByPartition" if val == "ByRoom" else "ByTime"
        cfg["wash"]["wash_freq"]["mode"] = mode

    entity = DockSelectEntity(
        mock_coordinator,
        "wash_frequency_mode",
        "Wash Frequency Mode",
        ["ByRoom", "ByTime"],
        _get_wash_freq,
        _set_wash_freq,
        "mdi:calendar-sync",
    )

    assert entity.name == "Wash Frequency Mode"
    assert entity.unique_id == "test_device_wash_frequency_mode"
    assert entity.icon == "mdi:calendar-sync"
    assert entity.entity_category == EntityCategory.CONFIG
    assert entity.options == ["ByRoom", "ByTime"]
    assert entity.current_option == "ByRoom"


def test_mop_intensity_select_entity_mapping(mock_coordinator):
    """Test MopIntensitySelectEntity option to state mapping."""
    entity = MopIntensitySelectEntity(mock_coordinator)

    assert entity._option_to_state("Quiet") == "Low"
    assert entity._option_to_state("Automatic") == "Medium"
    assert entity._option_to_state("Max") == "High"

    assert entity._state_to_option("Low") == "Quiet"
    assert entity._state_to_option("Medium") == "Automatic"
    assert entity._state_to_option("High") == "Max"
    assert entity._state_to_option("Unknown") is None
