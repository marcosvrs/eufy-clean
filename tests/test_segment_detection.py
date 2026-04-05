"""Tests for segment change detection functionality."""

# Removed: test_vacuum_entity_with_segment_detection — covered by tests/integration/test_ha_lifecycle.py
# Removed: test_async_create_segments_issue — covered by tests/integration/test_ha_lifecycle.py
# Removed: test_store_last_seen_segments — covered by tests/integration/test_ha_lifecycle.py
# Removed: test_check_for_segment_changes_no_previous — covered by tests/integration/test_ha_lifecycle.py
# Removed: test_check_for_segment_changes_with_changes — covered by tests/integration/test_ha_lifecycle.py
# Removed: test_check_for_segment_changes_no_changes — covered by tests/integration/test_ha_lifecycle.py
# Removed: test_storage_load_on_coordinator_init — covered by tests/integration/test_ha_lifecycle.py
# Removed: test_storage_save_on_segment_store — covered by tests/integration/test_ha_lifecycle.py
# Removed: test_segment_change_detection_end_to_end — covered by tests/integration/test_ha_lifecycle.py

# pylint: disable=redefined-outer-name

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.vacuum import (
    RoboVacMQTTEntity,
    Segment,
    _deserialize_segments,
    _serialize_segments,
)


def test_serialize_deserialize_segments():
    """Test segment serialization and deserialization."""
    segments = [
        Segment(id="1", name="Living Room", group="main"),
        Segment(id="2", name="Kitchen", group="main"),
        Segment(id="3", name="Bedroom", group=None),
    ]

    serialized = _serialize_segments(segments)
    expected = [
        {"id": "1", "name": "Living Room", "group": "main"},
        {"id": "2", "name": "Kitchen", "group": "main"},
        {"id": "3", "name": "Bedroom", "group": None},
    ]
    assert serialized == expected

    deserialized = _deserialize_segments(serialized)
    assert len(deserialized) == 3
    assert deserialized[0].id == "1"
    assert deserialized[0].name == "Living Room"
    assert deserialized[0].group == "main"
    assert deserialized[2].group is None


@pytest.fixture
def mock_coordinator():
    """Mock the coordinator."""
    coordinator = MagicMock()
    coordinator.device_id = "test_id"
    coordinator.device_name = "Test Vac"
    coordinator.device_model = "T2118"
    coordinator.data = VacuumState()
    coordinator.async_send_command = AsyncMock()
    coordinator.hass = MagicMock()
    coordinator.hass.config_entries.async_update_entry = MagicMock()

    def _create_task(coro):
        return asyncio.create_task(coro)

    coordinator.hass.async_create_task = MagicMock(side_effect=_create_task)
    coordinator.last_seen_segments = None
    coordinator.async_save_segments = AsyncMock()

    def _save_segments(segments):
        coordinator.last_seen_segments = segments

    coordinator.async_save_segments.side_effect = _save_segments
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Mock the config entry."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    return config_entry


def test_last_seen_segments_property(mock_coordinator, mock_config_entry):
    """Test last_seen_segments property."""
    stored_segments = [
        {"id": "1", "name": "Living Room", "group": None},
        {"id": "2", "name": "Kitchen", "group": None},
    ]
    mock_coordinator.last_seen_segments = stored_segments

    entity = RoboVacMQTTEntity(mock_coordinator, mock_config_entry)

    last_seen = entity.last_seen_segments
    assert len(last_seen) == 2
    assert last_seen[0].id == "1"
    assert last_seen[0].name == "Living Room"
    assert last_seen[1].id == "2"
    assert last_seen[1].name == "Kitchen"


def test_last_seen_segments_none_when_not_stored(mock_coordinator, mock_config_entry):
    """Test last_seen_segments returns None when not stored."""
    mock_coordinator.last_seen_segments = None

    entity = RoboVacMQTTEntity(mock_coordinator, mock_config_entry)

    assert entity.last_seen_segments is None


@pytest.mark.asyncio
async def test_backward_compatibility_no_config_entry():
    """Test that entity works without config entry (backward compatibility)."""
    coordinator = MagicMock()
    coordinator.device_id = "test_id"
    coordinator.device_name = "Test Vac"
    coordinator.data = VacuumState(rooms=[{"id": 1, "name": "Kitchen"}])
    coordinator.hass = MagicMock()
    coordinator.last_seen_segments = None
    coordinator.async_save_segments = AsyncMock()

    entity = RoboVacMQTTEntity(coordinator)

    assert entity.last_seen_segments is None

    from unittest.mock import patch

    with patch(
        "custom_components.robovac_mqtt.vacuum.async_create_issue"
    ) as mock_create:
        entity.async_create_segments_issue()
        mock_create.assert_not_called()

    with patch.object(entity, "async_create_segments_issue") as mock_create:
        entity._check_for_segment_changes()
        await asyncio.sleep(0)
        mock_create.assert_not_called()

    assert len(entity._get_room_segments()) == 1
    assert entity._get_room_segments()[0].name == "Kitchen"
