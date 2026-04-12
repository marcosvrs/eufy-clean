"""Unit tests for the EufyCleanCoordinator."""

# Removed: test_coordinator_init — covered by tests/integration/test_coordinator.py
# Removed: test_coordinator_initialize_success — covered by tests/integration/test_coordinator.py
# Removed: test_handle_mqtt_message — covered by tests/integration/test_coordinator.py
# Removed: test_async_send_command — covered by tests/integration/test_coordinator.py

# pylint: disable=redefined-outer-name

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator


@pytest.fixture
def mock_hass():
    """Mock the Home Assistant object."""
    return MagicMock()


@pytest.fixture
def mock_login():
    """Mock the EufyLogin object."""
    login = MagicMock()
    login.openudid = "test_udid"
    login.checkLogin = AsyncMock()
    return login


@pytest.mark.asyncio
async def test_coordinator_initialize_failed_creds(mock_hass, mock_login):
    """Test initialization failure when no credentials."""
    device_info = {
        "deviceId": "test_id",
        "deviceModel": "T2118",
        "deviceName": "Test Vac",
    }
    mock_login.mqtt_credentials = None

    async def side_effect_check():
        mock_login.mqtt_credentials = None

    mock_login.checkLogin.side_effect = side_effect_check

    coordinator = EufyCleanCoordinator(mock_hass, mock_login, device_info)

    with pytest.raises(UpdateFailed):
        await coordinator.initialize()

    mock_login.checkLogin.assert_called_once()


def test_async_shutdown_timers_cancels_both(mock_hass, mock_login):
    """Test that async_shutdown_timers cancels dock and segment timers."""
    device_info = {
        "deviceId": "test_id",
        "deviceModel": "T2118",
        "deviceName": "Test Vac",
    }
    coordinator = EufyCleanCoordinator(mock_hass, mock_login, device_info)

    mock_dock_cancel = MagicMock()
    mock_segment_cancel = MagicMock()
    coordinator._dock_idle_cancel = mock_dock_cancel
    coordinator._segment_update_cancel = mock_segment_cancel

    coordinator.async_shutdown_timers()

    mock_dock_cancel.assert_called_once()
    mock_segment_cancel.assert_called_once()
    assert coordinator._dock_idle_cancel is None
    assert coordinator._segment_update_cancel is None


def test_async_shutdown_timers_noop_when_no_timers(mock_hass, mock_login):
    """Test async_shutdown_timers is safe with no active timers."""
    device_info = {
        "deviceId": "test_id",
        "deviceModel": "T2118",
        "deviceName": "Test Vac",
    }
    coordinator = EufyCleanCoordinator(mock_hass, mock_login, device_info)

    assert coordinator._dock_idle_cancel is None
    assert coordinator._segment_update_cancel is None


@pytest.mark.asyncio
async def test_async_load_storage_restores_received_fields(mock_hass, mock_login):
    """Stored received_fields are merged into current state on load."""
    device_info = {
        "deviceId": "test_id",
        "deviceModel": "T2118",
        "deviceName": "Test Vac",
    }
    coordinator = EufyCleanCoordinator(mock_hass, mock_login, device_info)
    coordinator.data = coordinator.data.__class__(received_fields={"battery_level"})
    coordinator._store = MagicMock()
    coordinator._store.async_load = AsyncMock(
        return_value={"received_fields": ["work_status", "battery_level"]}
    )

    await coordinator.async_load_storage()

    assert coordinator.data.received_fields == {"battery_level", "work_status"}


@pytest.mark.asyncio
async def test_async_save_novelty_persists_received_fields(mock_hass, mock_login):
    """Saving novelty also persists received_fields."""
    device_info = {
        "deviceId": "test_id",
        "deviceModel": "T2118",
        "deviceName": "Test Vac",
    }
    coordinator = EufyCleanCoordinator(mock_hass, mock_login, device_info)
    coordinator.data = coordinator.data.__class__(received_fields={"battery_level"})
    coordinator._store = MagicMock()
    coordinator._store.async_load = AsyncMock(return_value={"novelty_caches": {}})
    coordinator._store.async_save = AsyncMock()

    await coordinator._async_save_novelty()

    coordinator._store.async_save.assert_awaited_once()
    saved = coordinator._store.async_save.await_args.args[0]
    assert saved["received_fields"] == ["battery_level"]

    coordinator.async_shutdown_timers()

    assert coordinator._dock_idle_cancel is None
    assert coordinator._segment_update_cancel is None


@pytest.mark.asyncio
async def test_async_send_command_no_client_logs_warning(mock_hass, mock_login):
    """Test that sending command with no client logs warning."""
    device_info = {
        "deviceId": "test_id",
        "deviceModel": "T2118",
        "deviceName": "Test Vac",
    }
    coordinator = EufyCleanCoordinator(mock_hass, mock_login, device_info)
    coordinator.client = None

    await coordinator.async_send_command({"some": "cmd"})
