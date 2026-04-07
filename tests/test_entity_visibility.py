from unittest.mock import MagicMock

from custom_components.robovac_mqtt.auto_entities import AutoSwitch
from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.sensor import RoboVacSensor
from custom_components.robovac_mqtt.vacuum import RoboVacMQTTEntity


def _mock_coordinator() -> MagicMock:
    coordinator = MagicMock(spec=EufyCleanCoordinator)
    coordinator.device_id = "test_device"
    coordinator.device_name = "Test Device"
    coordinator.device_model = "T2118"
    coordinator.device_info = MagicMock()
    coordinator.data = VacuumState()
    coordinator.last_update_success = True
    return coordinator


def test_vacuum_visible_default() -> None:
    coordinator = _mock_coordinator()
    entity = RoboVacMQTTEntity(coordinator)
    assert entity.entity_registry_visible_default is True


def test_sensor_hidden_default() -> None:
    coordinator = _mock_coordinator()
    entity = RoboVacSensor(
        coordinator,
        "battery_level",
        "Battery Level",
        lambda s: s.battery_level,
    )

    assert entity.entity_registry_visible_default is False


def test_auto_switch_hidden_default() -> None:
    coordinator = _mock_coordinator()
    entity = AutoSwitch(
        coordinator,
        "152",
        "test_switch",
        {},
    )

    assert entity.entity_registry_visible_default is False
