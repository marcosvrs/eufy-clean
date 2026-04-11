"""Unit tests for entities: waste_water sensor, carpet_strategy select,
corner_cleaning select, smart_mode switch."""

from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import EntityCategory

from custom_components.robovac_mqtt.api.commands import (
    build_command,
    build_set_boost_iq_command,
    build_set_carpet_strategy_command,
    build_set_corner_cleaning_command,
    build_set_smart_mode_command,
    build_set_volume_command,
)
from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import (
    DEFAULT_DPS_MAP,
    DPS_MAP,
    EUFY_CLEAN_CARPET_STRATEGIES,
    EUFY_CLEAN_CORNER_CLEANING_MODES,
)
from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator
from custom_components.robovac_mqtt.descriptions.sensor import RoboVacSensorDescription
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.select import (
    CarpetStrategySelectEntity,
    CornerCleaningSelectEntity,
)
from custom_components.robovac_mqtt.sensor import RoboVacSensor
from custom_components.robovac_mqtt.switch import SmartModeSwitchEntity


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock(spec=EufyCleanCoordinator)
    coordinator.data = VacuumState()
    coordinator.device_id = "test_device"
    coordinator.device_name = "Test Device"
    coordinator.device_model = "T2351"
    coordinator.last_update_success = True
    coordinator.async_send_command = AsyncMock()
    coordinator.dps_map = dict(DEFAULT_DPS_MAP)
    return coordinator


# ---------------------------------------------------------------------------
# Waste Water Sensor
# ---------------------------------------------------------------------------


def _waste_water_desc():
    return RoboVacSensorDescription(
        key="waste_water_level",
        name="Waste Water Level",
        native_unit_of_measurement="%",
        icon="mdi:water-minus",
        value_fn=lambda s: s.station_waste_water,
        availability_fn=lambda s: "dock_status" in s.received_fields,
    )


def test_waste_water_sensor_value(mock_coordinator):
    mock_coordinator.data = replace(
        mock_coordinator.data,
        station_waste_water=42,
        received_fields={"dock_status"},
    )

    entity = RoboVacSensor(mock_coordinator, _waste_water_desc())

    assert entity.native_value == 42
    assert entity.available is True


def test_waste_water_sensor_unavailable_without_dock_status(mock_coordinator):
    entity = RoboVacSensor(mock_coordinator, _waste_water_desc())

    assert entity.available is False


# ---------------------------------------------------------------------------
# Carpet Strategy Select
# ---------------------------------------------------------------------------


def test_carpet_strategy_select_options(mock_coordinator):
    entity = CarpetStrategySelectEntity(mock_coordinator)

    assert entity.options == EUFY_CLEAN_CARPET_STRATEGIES
    assert "Auto Raise" in entity.options
    assert "Avoid" in entity.options
    assert "Ignore" in entity.options


def test_carpet_strategy_select_current_option(mock_coordinator):
    mock_coordinator.data = replace(
        mock_coordinator.data,
        carpet_strategy="Avoid",
        received_fields={"carpet_strategy"},
    )
    entity = CarpetStrategySelectEntity(mock_coordinator)

    assert entity.current_option == "Avoid"
    assert entity.available is True


def test_carpet_strategy_select_unavailable_without_field(mock_coordinator):
    entity = CarpetStrategySelectEntity(mock_coordinator)

    assert entity.available is False


@pytest.mark.asyncio
async def test_carpet_strategy_select_sends_command(mock_coordinator):
    mock_coordinator.data = replace(
        mock_coordinator.data,
        carpet_strategy="Auto Raise",
        received_fields={"carpet_strategy"},
    )
    entity = CarpetStrategySelectEntity(mock_coordinator)
    entity.hass = MagicMock()
    entity.entity_id = "select.test_device_carpet_strategy"
    entity.async_write_ha_state = MagicMock()

    await entity.async_select_option("Avoid")

    mock_coordinator.async_send_command.assert_called_once()
    cmd = mock_coordinator.async_send_command.call_args[0][0]
    assert DPS_MAP["CLEANING_PARAMETERS"] in cmd


# ---------------------------------------------------------------------------
# Corner Cleaning Select
# ---------------------------------------------------------------------------


def test_corner_cleaning_select_options(mock_coordinator):
    entity = CornerCleaningSelectEntity(mock_coordinator)

    assert entity.options == EUFY_CLEAN_CORNER_CLEANING_MODES
    assert "Normal" in entity.options
    assert "Deep" in entity.options


def test_corner_cleaning_select_current_option(mock_coordinator):
    mock_coordinator.data = replace(
        mock_coordinator.data,
        corner_cleaning="Deep",
        received_fields={"corner_cleaning"},
    )
    entity = CornerCleaningSelectEntity(mock_coordinator)

    assert entity.current_option == "Deep"
    assert entity.available is True


def test_corner_cleaning_select_unavailable_without_field(mock_coordinator):
    entity = CornerCleaningSelectEntity(mock_coordinator)

    assert entity.available is False


@pytest.mark.asyncio
async def test_corner_cleaning_select_sends_command(mock_coordinator):
    mock_coordinator.data = replace(
        mock_coordinator.data,
        corner_cleaning="Normal",
        received_fields={"corner_cleaning"},
    )
    entity = CornerCleaningSelectEntity(mock_coordinator)
    entity.hass = MagicMock()
    entity.entity_id = "select.test_device_corner_cleaning"
    entity.async_write_ha_state = MagicMock()

    await entity.async_select_option("Deep")

    mock_coordinator.async_send_command.assert_called_once()
    cmd = mock_coordinator.async_send_command.call_args[0][0]
    assert DPS_MAP["CLEANING_PARAMETERS"] in cmd


# ---------------------------------------------------------------------------
# Smart Mode Switch
# ---------------------------------------------------------------------------


def test_smart_mode_switch_state(mock_coordinator):
    mock_coordinator.data = replace(
        mock_coordinator.data,
        smart_mode=True,
        received_fields={"smart_mode"},
    )
    entity = SmartModeSwitchEntity(mock_coordinator)

    assert entity.is_on is True
    assert entity.available is True
    assert entity.entity_category == EntityCategory.CONFIG


def test_smart_mode_switch_unavailable_without_field(mock_coordinator):
    entity = SmartModeSwitchEntity(mock_coordinator)

    assert entity.available is False


@pytest.mark.asyncio
async def test_smart_mode_switch_turn_on(mock_coordinator):
    mock_coordinator.data = replace(
        mock_coordinator.data,
        smart_mode=False,
        received_fields={"smart_mode"},
    )
    entity = SmartModeSwitchEntity(mock_coordinator)

    await entity.async_turn_on()

    mock_coordinator.async_send_command.assert_called_once()
    cmd = mock_coordinator.async_send_command.call_args[0][0]
    assert DPS_MAP["CLEANING_PARAMETERS"] in cmd


@pytest.mark.asyncio
async def test_smart_mode_switch_turn_off(mock_coordinator):
    mock_coordinator.data = replace(
        mock_coordinator.data,
        smart_mode=True,
        received_fields={"smart_mode"},
    )
    entity = SmartModeSwitchEntity(mock_coordinator)

    await entity.async_turn_off()

    mock_coordinator.async_send_command.assert_called_once()
    cmd = mock_coordinator.async_send_command.call_args[0][0]
    assert DPS_MAP["CLEANING_PARAMETERS"] in cmd


# ---------------------------------------------------------------------------
# DPS Parser: boost_iq and volume
# ---------------------------------------------------------------------------


def test_parser_dps_159_boost_iq():
    state = VacuumState()
    new_state, changes = update_state(state, {"159": True})

    assert new_state.boost_iq is True
    assert "boost_iq" in new_state.received_fields


def test_parser_dps_159_boost_iq_false():
    state = VacuumState()
    new_state, changes = update_state(state, {"159": False})

    assert new_state.boost_iq is False
    assert "boost_iq" in new_state.received_fields


def test_parser_dps_161_volume():
    state = VacuumState()
    new_state, changes = update_state(state, {"161": 75})

    assert new_state.volume == 75
    assert "volume" in new_state.received_fields


def test_parser_dps_161_volume_float():
    state = VacuumState()
    new_state, changes = update_state(state, {"161": 42.0})

    assert new_state.volume == 42
    assert "volume" in new_state.received_fields


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------


def test_build_set_carpet_strategy_command_valid():
    result = build_set_carpet_strategy_command("Avoid")
    assert DPS_MAP["CLEANING_PARAMETERS"] in result


def test_build_set_carpet_strategy_command_invalid():
    result = build_set_carpet_strategy_command("nonexistent")
    assert not result


def test_build_set_corner_cleaning_command_valid():
    result = build_set_corner_cleaning_command("Deep")
    assert DPS_MAP["CLEANING_PARAMETERS"] in result


def test_build_set_corner_cleaning_command_invalid():
    result = build_set_corner_cleaning_command("nonexistent")
    assert not result


def test_build_set_smart_mode_command():
    result = build_set_smart_mode_command(True)
    assert DPS_MAP["CLEANING_PARAMETERS"] in result


def test_build_set_boost_iq_command():
    result = build_set_boost_iq_command(True)
    assert DPS_MAP["BOOST_IQ"] in result
    assert result[DPS_MAP["BOOST_IQ"]] is True


def test_build_set_volume_command():
    result = build_set_volume_command(75)
    assert DPS_MAP["VOLUME"] in result
    assert result[DPS_MAP["VOLUME"]] == 75


def test_build_command_dispatches_new_commands():
    assert DPS_MAP["CLEANING_PARAMETERS"] in build_command(
        "set_carpet_strategy", carpet_strategy="Avoid"
    )
    assert DPS_MAP["CLEANING_PARAMETERS"] in build_command(
        "set_corner_cleaning", corner_cleaning="Deep"
    )
    assert DPS_MAP["CLEANING_PARAMETERS"] in build_command(
        "set_smart_mode", active=True
    )
    assert DPS_MAP["BOOST_IQ"] in build_command("set_boost_iq", active=True)
    assert DPS_MAP["VOLUME"] in build_command("set_volume", volume=50)
