from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator
from custom_components.robovac_mqtt.event import RoboVacNotificationEvent
from custom_components.robovac_mqtt.models import VacuumState


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock(spec=EufyCleanCoordinator)
    coordinator.device_id = "test_device"
    coordinator.device_name = "Test Device"
    coordinator.device_info = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = VacuumState()
    return coordinator


@pytest.fixture
def event_entity(mock_coordinator):
    entity = RoboVacNotificationEvent(mock_coordinator)
    entity._trigger_event = MagicMock()
    entity.async_write_ha_state = MagicMock()
    return entity


def test_event_entity_unique_id(mock_coordinator):
    entity = RoboVacNotificationEvent(mock_coordinator)
    assert entity.unique_id == "test_device_notification_event"


def test_event_entity_event_types(mock_coordinator):
    entity = RoboVacNotificationEvent(mock_coordinator)
    assert entity.event_types == ["notification"]


def test_event_entity_disabled_by_default(mock_coordinator):
    entity = RoboVacNotificationEvent(mock_coordinator)
    assert entity.entity_registry_enabled_default is False


def test_event_entity_hidden_by_default(mock_coordinator):
    entity = RoboVacNotificationEvent(mock_coordinator)
    assert entity.entity_registry_visible_default is False


def test_event_fires_on_new_notification(mock_coordinator, event_entity):
    mock_coordinator.data = replace(
        mock_coordinator.data,
        notification_message="Dust bin full",
        notification_codes=[5],
        notification_time=12345,
    )
    event_entity._handle_coordinator_update()

    event_entity._trigger_event.assert_called_once_with(
        "notification",
        {
            "code": [5],
            "message": "Dust bin full",
            "timestamp": 12345,
        },
    )


def test_event_does_not_fire_when_empty_message(event_entity):
    event_entity._handle_coordinator_update()

    event_entity._trigger_event.assert_not_called()


def test_event_does_not_fire_duplicate(mock_coordinator, event_entity):
    mock_coordinator.data = replace(
        mock_coordinator.data,
        notification_message="Dust bin full",
        notification_codes=[5],
        notification_time=12345,
    )
    event_entity._handle_coordinator_update()
    event_entity._handle_coordinator_update()

    assert event_entity._trigger_event.call_count == 1
