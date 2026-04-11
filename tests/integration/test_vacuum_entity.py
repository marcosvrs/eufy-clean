"""Integration tests for the vacuum entity through the real HA runtime.

Tests set up the full integration via setup_integration, simulate MQTT
messages, and assert on HA entity state via hass.states.get().
"""

from __future__ import annotations

import pytest

from custom_components.robovac_mqtt.const import DPS_MAP
from tests.integration.conftest import simulate_mqtt_message
from tests.integration.helpers import (
    make_clean_param_response,
    make_dps_payload,
    make_work_status,
)

ENTITY_ID = "vacuum.test_vacuum"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_coordinator(setup_data: dict):
    """Extract the first coordinator from setup_integration data."""
    return setup_data["coordinators"][0]


# ---------------------------------------------------------------------------
# State mapping tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vacuum_state_cleaning(hass, setup_integration):
    """WorkStatus state=5 → entity state 'cleaning'."""
    coordinator = _get_coordinator(setup_integration)
    ws = make_work_status(state=5)
    simulate_mqtt_message(coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "cleaning"


@pytest.mark.asyncio
async def test_vacuum_state_docked(hass, setup_integration):
    """WorkStatus state=3 → entity state 'docked'."""
    coordinator = _get_coordinator(setup_integration)
    ws = make_work_status(state=3)
    simulate_mqtt_message(coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "docked"


@pytest.mark.asyncio
async def test_vacuum_state_returning(hass, setup_integration):
    """WorkStatus state=7 → entity state 'returning'."""
    coordinator = _get_coordinator(setup_integration)
    ws = make_work_status(state=7)
    simulate_mqtt_message(coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "returning"


@pytest.mark.asyncio
async def test_vacuum_state_error(hass, setup_integration):
    """WorkStatus state=2 → entity state 'error'."""
    coordinator = _get_coordinator(setup_integration)
    ws = make_work_status(state=2)
    simulate_mqtt_message(coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "error"


# ---------------------------------------------------------------------------
# Attribute tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vacuum_fan_speed_attribute(hass, setup_integration):
    """CleanParam DPS updates fan_speed attribute on entity."""
    coordinator = _get_coordinator(setup_integration)

    proto = make_clean_param_response(clean_param={"fan": {"suction": 3}})
    simulate_mqtt_message(coordinator, make_dps_payload("154", proto))
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.attributes.get("fan_speed") is not None


@pytest.mark.asyncio
async def test_vacuum_battery_updates_coordinator(hass, setup_integration):
    """DPS 163 (battery) updates coordinator data through the MQTT pipeline."""
    coordinator = _get_coordinator(setup_integration)

    simulate_mqtt_message(coordinator, {"163": "72"})
    await hass.async_block_till_done()

    assert coordinator.data.battery_level == 72


@pytest.mark.asyncio
async def test_vacuum_fan_speed_list_nonempty(hass, setup_integration):
    """fan_speed_list attribute is a non-empty list."""
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    fan_speed_list = state.attributes.get("fan_speed_list")
    assert isinstance(fan_speed_list, list)
    assert len(fan_speed_list) > 0


@pytest.mark.asyncio
async def test_vacuum_extra_attributes_present(hass, setup_integration):
    """Extra state attributes from vacuum entity are present."""
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    attrs = state.attributes
    assert "error_code" in attrs
    assert "task_status" in attrs
    assert "work_mode" in attrs
    assert "cleaning_time" in attrs
    assert "cleaning_area" in attrs


# ---------------------------------------------------------------------------
# Command tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vacuum_start_command(hass, setup_integration, mock_mqtt_client):
    """vacuum.start service sends start_auto command via MQTT."""
    mock_mqtt_client.sent_commands.clear()

    await hass.services.async_call(
        "vacuum", "start", {"entity_id": ENTITY_ID}, blocking=True
    )
    await hass.async_block_till_done()

    assert len(mock_mqtt_client.sent_commands) >= 1
    cmd = mock_mqtt_client.sent_commands[-1]
    assert DPS_MAP["PLAY_PAUSE"] in cmd


@pytest.mark.asyncio
async def test_vacuum_stop_command(hass, setup_integration, mock_mqtt_client):
    """vacuum.stop service sends stop command via MQTT."""
    mock_mqtt_client.sent_commands.clear()

    await hass.services.async_call(
        "vacuum", "stop", {"entity_id": ENTITY_ID}, blocking=True
    )
    await hass.async_block_till_done()

    assert len(mock_mqtt_client.sent_commands) >= 1
    cmd = mock_mqtt_client.sent_commands[-1]
    assert DPS_MAP["PLAY_PAUSE"] in cmd


@pytest.mark.asyncio
async def test_vacuum_pause_command(hass, setup_integration, mock_mqtt_client):
    """vacuum.pause service sends pause command via MQTT."""
    mock_mqtt_client.sent_commands.clear()

    await hass.services.async_call(
        "vacuum", "pause", {"entity_id": ENTITY_ID}, blocking=True
    )
    await hass.async_block_till_done()

    assert len(mock_mqtt_client.sent_commands) >= 1
    cmd = mock_mqtt_client.sent_commands[-1]
    assert DPS_MAP["PLAY_PAUSE"] in cmd


@pytest.mark.asyncio
async def test_vacuum_return_to_base_command(hass, setup_integration, mock_mqtt_client):
    """vacuum.return_to_base service sends go_home command via MQTT."""
    mock_mqtt_client.sent_commands.clear()

    await hass.services.async_call(
        "vacuum", "return_to_base", {"entity_id": ENTITY_ID}, blocking=True
    )
    await hass.async_block_till_done()

    assert len(mock_mqtt_client.sent_commands) >= 1
    cmd = mock_mqtt_client.sent_commands[-1]
    assert DPS_MAP["PLAY_PAUSE"] in cmd


@pytest.mark.asyncio
async def test_vacuum_set_fan_speed_command(hass, setup_integration, mock_mqtt_client):
    """vacuum.set_fan_speed service sends set_fan_speed command via MQTT."""
    mock_mqtt_client.sent_commands.clear()

    await hass.services.async_call(
        "vacuum",
        "set_fan_speed",
        {"entity_id": ENTITY_ID, "fan_speed": "Turbo"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert len(mock_mqtt_client.sent_commands) >= 1
    cmd = mock_mqtt_client.sent_commands[-1]
    assert DPS_MAP["CLEAN_SPEED"] in cmd


@pytest.mark.asyncio
async def test_vacuum_locate_command(hass, setup_integration, mock_mqtt_client):
    """vacuum.locate service sends find_robot command via MQTT."""
    mock_mqtt_client.sent_commands.clear()

    await hass.services.async_call(
        "vacuum", "locate", {"entity_id": ENTITY_ID}, blocking=True
    )
    await hass.async_block_till_done()

    assert len(mock_mqtt_client.sent_commands) >= 1
    cmd = mock_mqtt_client.sent_commands[-1]
    assert DPS_MAP["FIND_ROBOT"] in cmd


# ---------------------------------------------------------------------------
# State transition test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vacuum_state_transition_cleaning_to_returning(hass, setup_integration):
    """Entity state transitions from cleaning to returning when WorkStatus changes."""
    coordinator = _get_coordinator(setup_integration)

    ws = make_work_status(state=5)
    simulate_mqtt_message(coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "cleaning"

    ws = make_work_status(state=7)
    simulate_mqtt_message(coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "returning"
