from __future__ import annotations

"""Diagnostics support for Eufy Clean."""

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .typing_defs import EufyCleanConfigEntry

TO_REDACT = {
    "password",
    "access_token",
    "user_id",
    "user_center_id",
    "user_center_token",
    "gtoken",
    "mqtt_credentials",
    "certificate_pem",
    "private_key",
    "client_cert",
    "client_key",
    "openudid",
    "token",
    "x-auth-token",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: EufyCleanConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    devices: dict[str, Any] = {}

    for device_id, coordinator in entry.runtime_data.coordinators.items():
        device_diag: dict[str, Any] = {
            "device_model": coordinator.device_model,
            "device_name": coordinator.device_name,
            "firmware_version": coordinator.firmware_version,
            "mqtt_connected": (
                coordinator.client.connected if coordinator.client else False
            ),
            "last_update_success": coordinator.last_update_success,
        }

        if coordinator.data:
            try:
                device_diag["state"] = asdict(coordinator.data)
            except Exception:
                device_diag["state"] = str(coordinator.data)

        devices[device_id] = device_diag

    return {
        "config_entry": async_redact_data(dict(entry.data), TO_REDACT),
        "devices": devices,
    }
