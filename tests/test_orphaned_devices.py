from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.robovac_mqtt import async_remove_config_entry_device
from custom_components.robovac_mqtt.const import DOMAIN


@pytest.mark.asyncio
async def test_manual_remove_orphaned_devices(hass: HomeAssistant):
    """Test that orphaned devices are NOT removed automatically but can be removed manually."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test", "password": "password"},
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    device_registry = dr.async_get(hass)

    # Pre-populate registry with two devices
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "device_1")},
        name="Device 1",
    )
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "device_2")},
        name="Device 2",
    )

    assert len(dr.async_entries_for_config_entry(device_registry, entry.entry_id)) == 2

    # Mock EufyLogin to only return device_1
    with patch("custom_components.robovac_mqtt.EufyLogin") as mock_login_cls, patch(
        "custom_components.robovac_mqtt.EufyCleanCoordinator"
    ) as mock_coord_cls:

        mock_login = mock_login_cls.return_value
        mock_login.init = AsyncMock()
        mock_login.mqtt_devices = [
            {"deviceId": "device_1", "deviceName": "Device 1", "deviceModel": "T2118"}
        ]

        mock_coord = MagicMock()
        mock_coord.initialize = AsyncMock()
        mock_coord.device_id = "device_1"
        mock_coord.device_name = "Device 1"
        mock_coord.client = MagicMock()
        mock_coord.client.disconnect = AsyncMock()
        mock_coord_cls.return_value = mock_coord

        # Initialize the entry
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Check registry again - device_2 should still be there!
        registry_devices = dr.async_entries_for_config_entry(
            device_registry, entry.entry_id
        )
        assert len(registry_devices) == 2

        device_ids = [list(d.identifiers)[0][1] for d in registry_devices]
        assert "device_1" in device_ids
        assert "device_2" in device_ids

        # Test manual removal support
        device_2_entry = next(
            d for d in registry_devices if list(d.identifiers)[0][1] == "device_2"
        )

        # Verify callback exists and returns True
        result = await async_remove_config_entry_device(hass, entry, device_2_entry)
        assert result is True

        # Manually remove it from registry (as HA would do after calling the callback)
        device_registry.async_remove_device(device_2_entry.id)

        # Verify it's gone
        registry_devices = dr.async_entries_for_config_entry(
            device_registry, entry.entry_id
        )
        assert len(registry_devices) == 1
        assert list(registry_devices[0].identifiers)[0][1] == "device_1"
