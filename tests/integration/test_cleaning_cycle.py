"""End-to-end cleaning lifecycle tests: MQTT → coordinator → HA entity states."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from tests.integration.conftest import load_fixture, simulate_mqtt_message
from tests.integration.helpers import make_dps_payload, make_work_status

ENTITY_ID = "vacuum.test_vacuum"


@pytest.mark.asyncio
async def test_full_auto_clean_cycle(hass, setup_integration):
    """Replay full_cleaning_cycle.json: docked → cleaning → returning → docked."""
    coordinator = setup_integration["coordinators"][0]
    fixture = load_fixture("sequences/full_cleaning_cycle.json")

    for i, msg in enumerate(fixture["messages"]):
        simulate_mqtt_message(coordinator, msg["dps"])
        await hass.async_block_till_done()

        for field, expected in msg["expected_state_after"].items():
            actual = getattr(coordinator.data, field, None)
            assert (
                actual == expected
            ), f"Message {i}: {field}={actual!r}, expected {expected!r}"

    assert coordinator.data.activity == "docked"
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "docked"


@pytest.mark.asyncio
async def test_dock_wash_dry_cycle(hass, setup_integration):
    """Replay dock_wash_dry_cycle.json with debounce: Washing → Drying → Idle."""
    coordinator = setup_integration["coordinators"][0]
    fixture = load_fixture("sequences/dock_wash_dry_cycle.json")

    for i, msg in enumerate(fixture["messages"]):
        simulate_mqtt_message(coordinator, msg["dps"])
        await hass.async_block_till_done()

        # Advance past 2s debounce window to commit pending dock_status
        async_fire_time_changed(hass, utcnow() + timedelta(seconds=3))
        await hass.async_block_till_done()

        for field, expected in msg["expected_state_after"].items():
            actual = getattr(coordinator.data, field, None)
            assert (
                actual == expected
            ), f"Message {i}: {field}={actual!r}, expected {expected!r}"

    assert coordinator.data.dock_status == "Idle"
    assert coordinator.data.activity == "docked"


@pytest.mark.asyncio
async def test_interrupted_clean_cycle(hass, setup_integration):
    """cleaning → error → idle: HA entity reflects each transition."""
    coordinator = setup_integration["coordinators"][0]

    simulate_mqtt_message(
        coordinator, make_dps_payload("153", make_work_status(state=5))
    )
    await hass.async_block_till_done()
    assert coordinator.data.activity == "cleaning"
    assert hass.states.get(ENTITY_ID).state == "cleaning"

    simulate_mqtt_message(
        coordinator, make_dps_payload("153", make_work_status(state=2))
    )
    await hass.async_block_till_done()
    assert coordinator.data.activity == "error"
    assert hass.states.get(ENTITY_ID).state == "error"

    simulate_mqtt_message(
        coordinator, make_dps_payload("153", make_work_status(state=0))
    )
    await hass.async_block_till_done()
    assert coordinator.data.activity == "idle"
    assert hass.states.get(ENTITY_ID).state == "idle"


@pytest.mark.asyncio
async def test_start_command_triggers_cleaning(
    hass, setup_integration, mock_mqtt_client
):
    """HA start service → start_auto sent → cleaning response → entity cleaning."""
    coordinator = setup_integration["coordinators"][0]

    await hass.services.async_call(
        "vacuum", "start", {"entity_id": ENTITY_ID}, blocking=True
    )
    mock_mqtt_client.send_command.assert_called_once()

    simulate_mqtt_message(
        coordinator, make_dps_payload("153", make_work_status(state=5))
    )
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY_ID).state == "cleaning"


@pytest.mark.asyncio
async def test_return_to_base_during_cleaning(
    hass, setup_integration, mock_mqtt_client
):
    """cleaning → return_to_base → returning → docked through full HA pipeline."""
    coordinator = setup_integration["coordinators"][0]

    simulate_mqtt_message(
        coordinator, make_dps_payload("153", make_work_status(state=5))
    )
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "cleaning"

    await hass.services.async_call(
        "vacuum", "return_to_base", {"entity_id": ENTITY_ID}, blocking=True
    )
    mock_mqtt_client.send_command.assert_called()

    simulate_mqtt_message(
        coordinator, make_dps_payload("153", make_work_status(state=7))
    )
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "returning"

    simulate_mqtt_message(
        coordinator, make_dps_payload("153", make_work_status(state=3))
    )
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "docked"
