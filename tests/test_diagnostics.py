"""Tests for robovac_mqtt diagnostics."""

# pyright: reportAny=false, reportUnknownVariableType=false

from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.robovac_mqtt.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.robovac_mqtt.models import EufyCleanData, VacuumState


async def test_diagnostics_returns_expected_structure(hass: HomeAssistant) -> None:
    """Diagnostics include redacted config entry data and device state."""
    entry = MagicMock()
    entry.data = {
        "username": "user@example.com",
        "password": "secret",
        "token": "abc123",
    }
    entry.runtime_data = EufyCleanData(
        coordinators={
            "dev-1": SimpleNamespace(
                device_model="T2261",
                device_name="Test Vacuum",
                firmware_version="1.0.0",
                client=SimpleNamespace(connected=True),
                last_update_success=True,
                data=VacuumState(activity="cleaning", battery_level=80),
            )
        },
        cloud=MagicMock(),
    )

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["config_entry"]["username"] == "user@example.com"
    assert result["config_entry"]["password"] == "**REDACTED**"
    assert result["config_entry"]["token"] == "**REDACTED**"
    assert result["devices"]["dev-1"]["device_model"] == "T2261"
    assert result["devices"]["dev-1"]["mqtt_connected"] is True
    assert result["devices"]["dev-1"]["state"]["activity"] == "cleaning"
    assert result["devices"]["dev-1"]["state"]["battery_level"] == 80


async def test_diagnostics_redacts_nested_sensitive_config_data(
    hass: HomeAssistant,
) -> None:
    """Known sensitive diagnostics fields are redacted recursively."""
    entry = MagicMock()
    entry.data = {
        "password": "secret",
        "mqtt_credentials": {
            "certificate_pem": "cert",
            "private_key": "key",
            "endpoint_addr": "host",
        },
        "openudid": "device-id",
    }
    entry.runtime_data = EufyCleanData(coordinators={}, cloud=MagicMock())

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["config_entry"]["password"] == "**REDACTED**"
    assert result["config_entry"]["mqtt_credentials"] == "**REDACTED**"
    assert result["config_entry"]["openudid"] == "**REDACTED**"


async def test_diagnostics_with_multiple_devices_and_unserializable_state(
    hass: HomeAssistant,
) -> None:
    """Diagnostics cover multiple devices and fallback state serialization."""
    entry = MagicMock()
    entry.data = {"username": "user@example.com"}
    entry.runtime_data = EufyCleanData(
        coordinators={
            "dev-1": SimpleNamespace(
                device_model="T2261",
                device_name="Vacuum One",
                firmware_version="1.0.0",
                client=SimpleNamespace(connected=False),
                last_update_success=False,
                data=VacuumState(activity="idle"),
            ),
            "dev-2": SimpleNamespace(
                device_model="T2351",
                device_name="Vacuum Two",
                firmware_version="2.0.0",
                client=None,
                last_update_success=True,
                data=object(),
            ),
        },
        cloud=MagicMock(),
    )

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert set(cast(dict[str, object], result["devices"])) == {"dev-1", "dev-2"}
    assert result["devices"]["dev-1"]["mqtt_connected"] is False
    assert result["devices"]["dev-2"]["mqtt_connected"] is False
    assert str(result["devices"]["dev-2"]["state"]).startswith("<object object at")
