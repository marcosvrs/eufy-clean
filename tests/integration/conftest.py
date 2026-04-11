from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.robovac_mqtt.const import DOMAIN
from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator

pytest = import_module("pytest")
ha_const = import_module("homeassistant.const")
MockConfigEntry = import_module(
    "pytest_homeassistant_custom_component.common"
).MockConfigEntry
CONF_USERNAME = ha_const.CONF_USERNAME
CONF_PASSWORD = ha_const.CONF_PASSWORD

MOCK_DEVICE_INFO = {
    "deviceId": "T2261_ANON_001",
    "deviceModel": "T2261",
    "deviceName": "Test Vacuum",
    "softVersion": "1.0.0",
    "dps": {},
    "dps_catalog": [
        {"dp_id": 152, "code": "mode_ctrl", "data_type": "Raw", "mode": "rw"},
        {"dp_id": 153, "code": "work_status", "data_type": "Raw", "mode": "ro"},
        {"dp_id": 154, "code": "clean_params", "data_type": "Raw", "mode": "rw"},
        {"dp_id": 157, "code": "dnd", "data_type": "Raw", "mode": "rw"},
        {"dp_id": 158, "code": "suction_level", "data_type": "Enum", "mode": "rw"},
        {"dp_id": 159, "code": "boost_iq", "data_type": "Bool", "mode": "rw"},
        {"dp_id": 160, "code": "calling_robot", "data_type": "Bool", "mode": "rw"},
        {"dp_id": 161, "code": "volume", "data_type": "Value", "mode": "rw"},
        {"dp_id": 163, "code": "bat_level", "data_type": "Value", "mode": "ro"},
        {"dp_id": 167, "code": "clean_statistics", "data_type": "Raw", "mode": "ro"},
        {"dp_id": 168, "code": "consumables", "data_type": "Raw", "mode": "rw"},
        {"dp_id": 169, "code": "app_dev_info", "data_type": "Raw", "mode": "rw"},
        {"dp_id": 170, "code": "map_edit", "data_type": "Raw", "mode": "rw"},
        {"dp_id": 172, "code": "multi_maps_mng", "data_type": "Raw", "mode": "rw"},
        {"dp_id": 173, "code": "station", "data_type": "Raw", "mode": "rw"},
        {"dp_id": 176, "code": "unisetting", "data_type": "Raw", "mode": "rw"},
        {"dp_id": 177, "code": "error_warning", "data_type": "Raw", "mode": "rw"},
        {"dp_id": 180, "code": "scenes", "data_type": "Raw", "mode": "rw"},
    ],
}

MOCK_MQTT_CREDENTIALS = {
    "user_id": "test-user-id",
    "app_name": "eufy_clean",
    "thing_name": "test-thing-name",
    "certificate_pem": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
    "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
    "endpoint_addr": "test-endpoint.amazonaws.com",
}

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def make_mqtt_payload(dps: dict[str, Any], device_sn: str = "T2261_ANON_001") -> bytes:
    return json.dumps(
        {
            "head": {"cmd": 65537, "client_id": "anon"},
            "payload": {"data": dps, "device_sn": device_sn},
        }
    ).encode()


def simulate_mqtt_message(
    coordinator: EufyCleanCoordinator, dps: dict[str, Any]
) -> None:
    coordinator._handle_mqtt_message(make_mqtt_payload(dps))


def load_fixture(relative_path: str) -> dict[str, Any]:
    fixture_path = FIXTURES_DIR / relative_path
    if not fixture_path.is_file():
        raise FileNotFoundError(
            f"Fixture not found: {relative_path} (expected at {fixture_path})"
        )

    with fixture_path.open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


@pytest.fixture
def mock_eufy_login() -> MagicMock:
    login = MagicMock()
    login.openudid = "0123456789abcdef0123456789abcdef"
    login.mqtt_devices = [dict(MOCK_DEVICE_INFO)]
    login.mqtt_credentials = dict(MOCK_MQTT_CREDENTIALS)
    login.init = AsyncMock(side_effect=lambda: None)
    login.checkLogin = AsyncMock(side_effect=lambda: None)
    return login


@pytest.fixture
def mock_mqtt_client() -> MagicMock:
    client = MagicMock()
    client.sent_commands = []
    client.on_message = None

    async def _send_command(command: dict[str, Any]) -> None:
        client.sent_commands.append(command)

    def _set_on_message(callback: Any) -> None:
        client.on_message = callback

    client.send_command = AsyncMock(side_effect=_send_command)
    client.set_on_message = MagicMock(side_effect=_set_on_message)
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    return client


@pytest.fixture
def integration_coordinator(hass, mock_eufy_login, mock_mqtt_client):
    coordinator = EufyCleanCoordinator(hass, mock_eufy_login, dict(MOCK_DEVICE_INFO))

    with patch(
        "custom_components.robovac_mqtt.coordinator.EufyCleanClient",
        return_value=mock_mqtt_client,
    ):
        yield coordinator

    coordinator.async_shutdown_timers()


@pytest.fixture
async def setup_integration(hass, mock_eufy_login, mock_mqtt_client):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test",
        },
    )
    config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.robovac_mqtt.EufyLogin",
            return_value=mock_eufy_login,
        ),
        patch(
            "custom_components.robovac_mqtt.coordinator.EufyCleanClient",
            return_value=mock_mqtt_client,
        ),
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        coordinators = hass.data[DOMAIN][config_entry.entry_id]["coordinators"]
        yield {
            "hass": hass,
            "entry": config_entry,
            "coordinators": coordinators,
        }

        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()
