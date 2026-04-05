"""Integration tests for HA lifecycle: entry unload, device removal, storage, migration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.robovac_mqtt import async_remove_config_entry_device
from custom_components.robovac_mqtt.const import DOMAIN

from .conftest import MOCK_DEVICE_INFO, MOCK_MQTT_CREDENTIALS


def _make_login(devices=None):
    login = MagicMock()
    login.openudid = "0123456789abcdef0123456789abcdef"
    login.mqtt_devices = devices or [dict(MOCK_DEVICE_INFO)]
    login.mqtt_credentials = dict(MOCK_MQTT_CREDENTIALS)
    login.init = AsyncMock()
    login.checkLogin = AsyncMock()
    return login


def _make_client():
    client = MagicMock()
    client.sent_commands = []
    client.on_message = None

    async def _send_command(cmd):
        client.sent_commands.append(cmd)

    def _set_on_message(cb):
        client.on_message = cb

    client.send_command = AsyncMock(side_effect=_send_command)
    client.set_on_message = MagicMock(side_effect=_set_on_message)
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    return client


async def _setup_entry(hass, *, login=None, client=None, extra_data=None):
    """Inline integration setup.  Returns (entry, client, coordinators)."""
    login = login or _make_login()
    client = client or _make_client()

    entry_data = {CONF_USERNAME: "test@example.com", CONF_PASSWORD: "test"}
    if extra_data:
        entry_data.update(extra_data)

    entry = MockConfigEntry(domain=DOMAIN, data=entry_data)
    entry.add_to_hass(hass)

    with (
        patch("custom_components.robovac_mqtt.EufyLogin", return_value=login),
        patch(
            "custom_components.robovac_mqtt.coordinator.EufyCleanClient",
            return_value=client,
        ),
    ):
        result = await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert result is True
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]
    return entry, client, coordinators


async def test_unload_entry_cleans_up(hass: HomeAssistant):
    """Unloading disconnects MQTT client and removes hass.data entry."""
    entry, mock_client, _ = await _setup_entry(hass)

    result = await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    mock_client.disconnect.assert_called()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_unload_entry_shuts_down_timers(hass: HomeAssistant):
    """Debounce timers are cancelled during unload — callback never fires."""
    entry, _, coordinators = await _setup_entry(hass)
    coordinator = coordinators[0]

    timer_fired = []

    def _spy(_now):
        timer_fired.append(True)

    coordinator._dock_idle_cancel = async_call_later(hass, 999, _spy)

    result = await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    assert coordinator._dock_idle_cancel is None
    assert timer_fired == []


async def test_remove_config_entry_device_returns_true(hass: HomeAssistant):
    """async_remove_config_entry_device always returns True."""
    entry, _, _ = await _setup_entry(hass)

    device_entry = MagicMock()
    device_entry.identifiers = {(DOMAIN, "T2261_ANON_001")}

    result = await async_remove_config_entry_device(hass, entry, device_entry)
    assert result is True

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_storage_save_and_load_roundtrip(hass: HomeAssistant):
    """Segments survive a save → load roundtrip through HA Store."""
    entry, _, coordinators = await _setup_entry(hass)
    coordinator = coordinators[0]

    test_segments = [{"id": 1, "name": "Kitchen"}, {"id": 2, "name": "Bedroom"}]
    await coordinator.async_save_segments(test_segments)
    assert coordinator.last_seen_segments == test_segments

    coordinator.last_seen_segments = None
    await coordinator.async_load_storage()
    assert coordinator.last_seen_segments == test_segments

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_storage_load_empty_does_not_overwrite(hass: HomeAssistant):
    """Loading from a Store with no data leaves last_seen_segments unchanged."""
    entry, _, coordinators = await _setup_entry(hass)
    coordinator = coordinators[0]

    coordinator._store = Store(hass, 1, f"{DOMAIN}.nonexistent_device_xyz")
    coordinator.last_seen_segments = None

    await coordinator.async_load_storage()
    assert coordinator.last_seen_segments is None

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_segment_migration_single_device(hass: HomeAssistant):
    """Segments in config entry data are migrated to Store for single-device setups."""
    legacy_segments = [{"id": 10, "name": "Hall"}, {"id": 11, "name": "Study"}]

    entry, _, coordinators = await _setup_entry(
        hass, extra_data={"last_seen_segments": legacy_segments}
    )
    coordinator = coordinators[0]

    assert coordinator.last_seen_segments == legacy_segments
    assert "last_seen_segments" not in entry.data

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_segment_migration_skipped_multi_device(hass: HomeAssistant):
    """Segment migration is skipped when multiple devices are present."""
    legacy_segments = [{"id": 20, "name": "Garage"}]

    second_device = dict(MOCK_DEVICE_INFO)
    second_device["deviceId"] = "T2261_ANON_002"
    second_device["deviceName"] = "Test Vacuum 2"

    login = _make_login(devices=[dict(MOCK_DEVICE_INFO), second_device])

    entry, _, coordinators = await _setup_entry(
        hass,
        login=login,
        extra_data={"last_seen_segments": legacy_segments},
    )

    for coord in coordinators:
        assert coord.last_seen_segments is None

    assert entry.data.get("last_seen_segments") == legacy_segments

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
