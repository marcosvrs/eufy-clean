"""Integration tests for sensor and binary_sensor entities through the HA runtime.

Tests inject MQTT messages via the coordinator and assert on entity states
obtained from ``hass.states.get(entity_id)``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.robovac_mqtt.const import (
    ACCESSORY_MAX_LIFE,
    DOMAIN,
    DPS_MAP,
    EUFY_CLEAN_ERROR_CODES,
)
from custom_components.robovac_mqtt.proto.cloud.clean_statistics_pb2 import (
    CleanStatistics,
)
from custom_components.robovac_mqtt.proto.cloud.consumable_pb2 import (
    ConsumableResponse,
    ConsumableRuntime,
)
from custom_components.robovac_mqtt.proto.cloud.error_code_pb2 import ErrorCode
from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import WorkStatus
from tests.integration.conftest import (
    MOCK_DEVICE_INFO,
    MOCK_MQTT_CREDENTIALS,
    simulate_mqtt_message,
)
from tests.integration.helpers import make_dps_payload, make_work_status

# ---------------------------------------------------------------------------
# Inline setup helper (same pattern as T12)
# ---------------------------------------------------------------------------


async def setup_vacuum(
    hass: HomeAssistant,
    mock_eufy_login: MagicMock,
    mock_mqtt_client: MagicMock,
) -> dict:
    """Set up the integration with a single vacuum device and return context."""
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
        return {
            "entry": config_entry,
            "coordinators": coordinators,
            "coordinator": coordinators[0],
        }


async def enable_entity(hass: HomeAssistant, entity_id: str) -> None:
    """Enable an entity that is disabled by integration by default."""
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(entity_id)
    assert entry is not None, f"Entity not found in registry: {entity_id}"
    entity_registry.async_update_entity(entity_id, disabled_by=None)
    await hass.async_block_till_done()


# ---------------------------------------------------------------------------
# Battery sensor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_battery_sensor_value(hass, mock_eufy_login, mock_mqtt_client):
    """DPS 163 '75' → sensor.test_vacuum_battery state == '75'."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    coordinator = ctx["coordinator"]

    simulate_mqtt_message(coordinator, {"163": "75"})
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_vacuum_battery")
    assert state is not None
    assert state.state == "75"


# ---------------------------------------------------------------------------
# Error sensor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_sensor_known_code(hass, mock_eufy_login, mock_mqtt_client):
    """DPS 177 with error warn=[2] → error message shows 'WHEEL STUCK'."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    coordinator = ctx["coordinator"]

    error_proto = ErrorCode(warn=[2])
    dps = make_dps_payload(DPS_MAP["ERROR_CODE"], error_proto)
    simulate_mqtt_message(coordinator, dps)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_vacuum_error_message")
    assert state is not None
    expected = EUFY_CLEAN_ERROR_CODES[2]
    assert state.state == expected


@pytest.mark.asyncio
async def test_error_sensor_no_error(hass, mock_eufy_login, mock_mqtt_client):
    """DPS 177 with empty warn clears the sensor to an unknown state."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    coordinator = ctx["coordinator"]

    error_proto = ErrorCode(warn=[3])
    dps = make_dps_payload(DPS_MAP["ERROR_CODE"], error_proto)
    simulate_mqtt_message(coordinator, dps)
    await hass.async_block_till_done()

    error_proto_clear = ErrorCode(warn=[])
    dps_clear = make_dps_payload(DPS_MAP["ERROR_CODE"], error_proto_clear)
    simulate_mqtt_message(coordinator, dps_clear)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_vacuum_error_message")
    assert state is not None
    assert state.state == "unknown"


# ---------------------------------------------------------------------------
# Task status sensor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_status_cleaning(hass, mock_eufy_login, mock_mqtt_client):
    """WorkStatus state=5 (cleaning) → task status shows 'Cleaning'."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    coordinator = ctx["coordinator"]

    ws = make_work_status(state=5)
    simulate_mqtt_message(coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_vacuum_task_status")
    assert state is not None
    assert state.state == "Cleaning"


@pytest.mark.asyncio
async def test_task_status_returning(hass, mock_eufy_login, mock_mqtt_client):
    """WorkStatus state=7 (returning) → task status shows 'Returning'."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    coordinator = ctx["coordinator"]

    ws = make_work_status(state=7)
    simulate_mqtt_message(coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_vacuum_task_status")
    assert state is not None
    assert state.state == "Returning"


# ---------------------------------------------------------------------------
# Cleaning stats sensors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleaning_area_sensor(hass, mock_eufy_login, mock_mqtt_client):
    """DPS 167 CleanStatistics → cleaning_area sensor updated."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    await enable_entity(hass, "sensor.test_vacuum_cleaning_area")
    coordinator = ctx["coordinator"]

    stats = CleanStatistics(
        single=CleanStatistics.Single(clean_area=42, clean_duration=1200)
    )
    dps = make_dps_payload(DPS_MAP["CLEANING_STATISTICS"], stats)
    simulate_mqtt_message(coordinator, dps)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_vacuum_cleaning_area")
    assert state is not None
    assert state.state == "42"


@pytest.mark.asyncio
async def test_cleaning_time_sensor(hass, mock_eufy_login, mock_mqtt_client):
    """DPS 167 CleanStatistics → cleaning_time sensor updated."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    await enable_entity(hass, "sensor.test_vacuum_cleaning_time")
    coordinator = ctx["coordinator"]

    stats = CleanStatistics(
        single=CleanStatistics.Single(clean_area=10, clean_duration=900)
    )
    dps = make_dps_payload(DPS_MAP["CLEANING_STATISTICS"], stats)
    simulate_mqtt_message(coordinator, dps)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_vacuum_cleaning_time")
    assert state is not None
    assert state.state == "900"


# ---------------------------------------------------------------------------
# Consumable sensors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consumable_filter_remaining(hass, mock_eufy_login, mock_mqtt_client):
    """DPS 168 ConsumableResponse → filter_remaining sensor shows remaining hours."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    await enable_entity(hass, "sensor.test_vacuum_filter_remaining")
    coordinator = ctx["coordinator"]

    consumable = ConsumableResponse(
        runtime=ConsumableRuntime(
            filter_mesh=ConsumableRuntime.Duration(duration=100),
        )
    )
    dps = make_dps_payload(DPS_MAP["ACCESSORIES_STATUS"], consumable)
    simulate_mqtt_message(coordinator, dps)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_vacuum_filter_remaining")
    assert state is not None
    expected_remaining = ACCESSORY_MAX_LIFE["filter_usage"] - 100
    assert state.state == str(expected_remaining)


@pytest.mark.asyncio
async def test_consumable_side_brush_remaining(hass, mock_eufy_login, mock_mqtt_client):
    """DPS 168 ConsumableResponse → side brush remaining sensor shows correct hours."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    await enable_entity(hass, "sensor.test_vacuum_side_brush_remaining")
    coordinator = ctx["coordinator"]

    consumable = ConsumableResponse(
        runtime=ConsumableRuntime(
            side_brush=ConsumableRuntime.Duration(duration=50),
        )
    )
    dps = make_dps_payload(DPS_MAP["ACCESSORIES_STATUS"], consumable)
    simulate_mqtt_message(coordinator, dps)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_vacuum_side_brush_remaining")
    assert state is not None
    expected = ACCESSORY_MAX_LIFE["side_brush_usage"] - 50
    assert state.state == str(expected)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleaning_stats_unavailable_before_dps(
    hass, mock_eufy_login, mock_mqtt_client
):
    """Before any DPS 167, cleaning_area sensor should be unavailable."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    await enable_entity(hass, "sensor.test_vacuum_cleaning_area")

    state = hass.states.get("sensor.test_vacuum_cleaning_area")
    assert state is not None
    assert state.state == "unavailable"


@pytest.mark.asyncio
async def test_cleaning_stats_available_after_dps(
    hass, mock_eufy_login, mock_mqtt_client
):
    """After DPS 167, cleaning_area sensor becomes available."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    await enable_entity(hass, "sensor.test_vacuum_cleaning_area")
    coordinator = ctx["coordinator"]

    state = hass.states.get("sensor.test_vacuum_cleaning_area")
    assert state is not None
    assert state.state == "unavailable"

    stats = CleanStatistics(
        single=CleanStatistics.Single(clean_area=15, clean_duration=300)
    )
    dps = make_dps_payload(DPS_MAP["CLEANING_STATISTICS"], stats)
    simulate_mqtt_message(coordinator, dps)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_vacuum_cleaning_area")
    assert state is not None
    assert state.state == "15"


@pytest.mark.asyncio
async def test_consumable_unavailable_before_dps(
    hass, mock_eufy_login, mock_mqtt_client
):
    """Before any DPS 168, consumable sensors should be unavailable."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    await enable_entity(hass, "sensor.test_vacuum_filter_remaining")

    state = hass.states.get("sensor.test_vacuum_filter_remaining")
    assert state is not None
    assert state.state == "unavailable"


# ---------------------------------------------------------------------------
# Binary sensor: charging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_charging_binary_sensor_on(hass, mock_eufy_login, mock_mqtt_client):
    """WorkStatus state=3 (docked/charging) → binary_sensor charging == 'on'."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    coordinator = ctx["coordinator"]

    ws = make_work_status(
        state=3,
        charging=WorkStatus.Charging(state=0),
    )
    simulate_mqtt_message(coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test_vacuum_charging")
    assert state is not None
    assert state.state == "on"


@pytest.mark.asyncio
async def test_charging_binary_sensor_off(hass, mock_eufy_login, mock_mqtt_client):
    """WorkStatus state=5 (cleaning) → binary_sensor charging == 'off'."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    coordinator = ctx["coordinator"]

    ws = make_work_status(state=5)
    simulate_mqtt_message(coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test_vacuum_charging")
    assert state is not None
    assert state.state == "off"


# ---------------------------------------------------------------------------
# Work mode sensor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_work_mode_sensor(hass, mock_eufy_login, mock_mqtt_client):
    """WorkStatus with cleaning state → work_mode sensor shows mode string."""
    ctx = await setup_vacuum(hass, mock_eufy_login, mock_mqtt_client)
    coordinator = ctx["coordinator"]

    ws = make_work_status(state=5)
    simulate_mqtt_message(coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_vacuum_work_mode")
    assert state is not None
    assert isinstance(state.state, str)
