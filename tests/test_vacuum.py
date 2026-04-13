# Removed: test_vacuum_properties — covered by tests/integration/test_entity_vacuum.py
# Removed: test_vacuum_attributes — covered by tests/integration/test_entity_vacuum.py
# Removed: test_vacuum_commands — covered by tests/integration/test_entity_vacuum.py
# Removed: test_set_fan_speed — covered by tests/integration/test_entity_vacuum.py
# Removed: test_async_send_command_raw — covered by tests/integration/test_entity_vacuum.py
# Removed: test_room_clean_applies_user_preferences — covered by tests/integration/test_entity_vacuum.py
# Removed: test_room_clean_with_explicit_params_overrides_preferences — covered by tests/integration/test_entity_vacuum.py
# Removed: test_mqtt_malformed_message_does_not_crash — covered by tests/integration/test_edge_cases.py
# Removed: test_app_segment_clean_command — covered by tests/integration/test_entity_vacuum.py
# Removed: test_app_segment_clean_invalid_ids — covered by tests/integration/test_entity_vacuum.py
# Removed: test_async_clean_segments_empty_list — covered by tests/integration/test_entity_vacuum.py
# All tests in this file were REDUNDANT per tests/integration/AUDIT.md (Task 12/15 integration coverage).

import logging
from unittest.mock import MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.robovac_mqtt.api.http import EufyConnectionError
from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.vacuum import RoboVacMQTTEntity

# pyright: reportAny=false, reportPrivateUsage=false, reportUnknownParameterType=false


def test_vacuum_unrecorded_attributes():
    assert "rooms" in RoboVacMQTTEntity._unrecorded_attributes
    assert "segments" in RoboVacMQTTEntity._unrecorded_attributes


@pytest.mark.asyncio
async def test_app_segment_clean_invalid_room_id_logs_warning(caplog):
    coordinator = MagicMock(spec=EufyCleanCoordinator)
    coordinator.device_id = "test_device"
    coordinator.device_name = "Test Device"
    coordinator.device_info = MagicMock()

    entity = RoboVacMQTTEntity(coordinator)

    with caplog.at_level(logging.WARNING):
        await entity.async_send_command("app_segment_clean", ["not_a_number"])

    assert "Skipping room with invalid id: not_a_number" in caplog.text


@pytest.mark.asyncio
async def test_async_start_raises_home_assistant_error_on_connection_failure():
    coordinator = MagicMock(spec=EufyCleanCoordinator)
    coordinator.device_id = "test_device"
    coordinator.device_name = "Test Device"
    coordinator.device_info = MagicMock()
    coordinator.data = VacuumState(activity="idle")
    coordinator.async_send_command.side_effect = EufyConnectionError("offline")

    entity = RoboVacMQTTEntity(coordinator)

    with pytest.raises(HomeAssistantError) as exc:
        await entity.async_start()

    assert exc.value.translation_key == "not_connected"


@pytest.mark.asyncio
async def test_async_pause_raises_home_assistant_error_on_generic_failure():
    coordinator = MagicMock(spec=EufyCleanCoordinator)
    coordinator.device_id = "test_device"
    coordinator.device_name = "Test Device"
    coordinator.device_info = MagicMock()
    coordinator.async_send_command.side_effect = RuntimeError("boom")

    entity = RoboVacMQTTEntity(coordinator)

    with pytest.raises(HomeAssistantError) as exc:
        await entity.async_pause()

    assert exc.value.translation_key == "command_failed"


@pytest.mark.asyncio
async def test_async_set_fan_speed_rejects_invalid_option():
    coordinator = MagicMock(spec=EufyCleanCoordinator)
    coordinator.device_id = "test_device"
    coordinator.device_name = "Test Device"
    coordinator.device_info = MagicMock()

    entity = RoboVacMQTTEntity(coordinator)

    with pytest.raises(ServiceValidationError) as exc:
        await entity.async_set_fan_speed("Warp Speed")

    assert exc.value.translation_key == "invalid_fan_speed"
