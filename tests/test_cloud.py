"""Unit tests for the cloud login module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.robovac_mqtt.api.cloud import EufyLogin


def _make_login(
    mqtt_credentials=None,
    eufy_api_devices=None,
) -> EufyLogin:
    """Create an EufyLogin with a mocked eufyApi."""
    with patch(
        "custom_components.robovac_mqtt.api.cloud.EufyHTTPClient", autospec=True
    ):
        login = EufyLogin("user@example.com", "password123", "open-udid")
    login.eufyApi = MagicMock()
    login.eufyApi.login = AsyncMock(
        return_value={"mqtt": {"endpoint": "mqtt.example.com"}}
    )
    login.eufyApi.get_device_list = AsyncMock(return_value=[])
    login.eufyApi.get_cloud_device_list = AsyncMock(return_value=[])
    if mqtt_credentials is not None:
        login.mqtt_credentials = mqtt_credentials
    if eufy_api_devices is not None:
        login.eufy_api_devices = eufy_api_devices
    return login


@pytest.mark.asyncio
async def test_check_login_uses_mqtt_credentials():
    """When mqtt_credentials is None, checkLogin() calls login().
    When mqtt_credentials is already set, checkLogin() does NOT call login()."""
    login = _make_login(mqtt_credentials=None)

    await login.checkLogin()
    login.eufyApi.login.assert_called_once()

    # Reset and set credentials
    login.eufyApi.login.reset_mock()
    login.mqtt_credentials = {"endpoint": "mqtt.example.com"}

    await login.checkLogin()
    login.eufyApi.login.assert_not_called()


def test_check_api_type_novel():
    """checkApiType returns 'novel' when DPS contains a known key (e.g. '153')."""
    assert EufyLogin.checkApiType({"153": "some_value"}) == "novel"


def test_check_api_type_legacy():
    """checkApiType returns 'legacy' when DPS contains no known keys."""
    assert EufyLogin.checkApiType({"999": "value"}) == "legacy"


def test_find_model_found():
    """findModel returns device info with invalid=False for a known device."""
    login = _make_login(
        eufy_api_devices=[
            {
                "id": "DEV001",
                "product": {"product_code": "T2261xxx", "name": "X8 Pro"},
                "alias_name": "Living Room Vacuum",
                "device_model": "T2261",
            }
        ]
    )

    result = login.findModel("DEV001")

    assert result["deviceId"] == "DEV001"
    assert result["deviceModel"] == "T2261"
    assert result["deviceName"] == "Living Room Vacuum"
    assert result["invalid"] is False


def test_find_model_not_found():
    """findModel returns invalid=True and empty strings for unknown device."""
    login = _make_login(eufy_api_devices=[])

    result = login.findModel("UNKNOWN")

    assert result["deviceId"] == "UNKNOWN"
    assert result["deviceModel"] == ""
    assert result["deviceName"] == ""
    assert result["invalid"] is True


def test_find_model_empty_product_code():
    """When product_code is empty, findModel falls back to device_model."""
    login = _make_login(
        eufy_api_devices=[
            {
                "id": "DEV002",
                "product": {"product_code": "", "name": "Some Vacuum"},
                "alias_name": "Kitchen Vacuum",
                "device_model": "T2210fallback",
            }
        ]
    )

    result = login.findModel("DEV002")

    assert result["deviceModel"] == "T2210"
    assert result["deviceName"] == "Kitchen Vacuum"
    assert result["invalid"] is False


def _cloud_device(device_id, product_code="T2351xxx", name="X10 Pro"):
    return {
        "id": device_id,
        "product": {"product_code": product_code, "name": name},
        "alias_name": f"Vacuum {device_id}",
        "device_model": product_code[:5],
    }


def _raw_device(device_sn, dps=None):
    return {"device_sn": device_sn, "dps": dps or {}, "main_sw_version": "1.0.0"}


@pytest.mark.asyncio
async def test_get_devices_includes_dps_catalog():
    login = _make_login(
        eufy_api_devices=[_cloud_device("DEV001")],
    )
    catalog_data = [{"dp_id": "153", "dp_code": "work_status"}]
    login.eufyApi.get_cloud_device_list = AsyncMock(
        return_value=[_cloud_device("DEV001")]
    )
    login.eufyApi.get_device_list = AsyncMock(
        return_value=[_raw_device("DEV001")]
    )
    login.eufyApi.get_product_data_points = AsyncMock(return_value=catalog_data)

    await login.getDevices()

    assert len(login.mqtt_devices) == 1
    assert login.mqtt_devices[0]["dps_catalog"] == catalog_data


@pytest.mark.asyncio
async def test_get_devices_caches_catalog_per_product_code():
    login = _make_login(
        eufy_api_devices=[
            _cloud_device("DEV001", product_code="T2351xxx"),
            _cloud_device("DEV002", product_code="T2351xxx"),
        ],
    )
    login.eufyApi.get_cloud_device_list = AsyncMock(
        return_value=[
            _cloud_device("DEV001", product_code="T2351xxx"),
            _cloud_device("DEV002", product_code="T2351xxx"),
        ]
    )
    login.eufyApi.get_device_list = AsyncMock(
        return_value=[_raw_device("DEV001"), _raw_device("DEV002")]
    )
    login.eufyApi.get_product_data_points = AsyncMock(return_value=[{"dp_id": "153"}])

    await login.getDevices()

    login.eufyApi.get_product_data_points.assert_called_once_with("T2351")
    assert len(login.mqtt_devices) == 2
    assert login.mqtt_devices[0]["dps_catalog"] == [{"dp_id": "153"}]
    assert login.mqtt_devices[1]["dps_catalog"] == [{"dp_id": "153"}]


@pytest.mark.asyncio
async def test_get_devices_catalog_failure_fallback():
    login = _make_login(
        eufy_api_devices=[_cloud_device("DEV001")],
    )
    login.eufyApi.get_cloud_device_list = AsyncMock(
        return_value=[_cloud_device("DEV001")]
    )
    login.eufyApi.get_device_list = AsyncMock(
        return_value=[_raw_device("DEV001")]
    )
    login.eufyApi.get_product_data_points = AsyncMock(
        side_effect=Exception("API error")
    )

    await login.getDevices()

    assert len(login.mqtt_devices) == 1
    assert login.mqtt_devices[0]["dps_catalog"] == []
