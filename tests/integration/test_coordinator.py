"""Integration tests for EufyCleanCoordinator lifecycle.

Tests the full MQTT→state pipeline with real update_state(), mocking only
at the transport boundary (EufyCleanClient). Uses the real HA event loop
for debounce timer tests.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator
from custom_components.robovac_mqtt.proto.cloud.station_pb2 import StationResponse
from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import WorkStatus
from tests.integration.conftest import load_fixture, simulate_mqtt_message
from tests.integration.helpers import (
    make_device_info_dict,
    make_dps_payload,
    make_station_response,
    make_work_status,
)

# ---------------------------------------------------------------------------
# MQTT pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mqtt_message_updates_activity(hass, integration_coordinator):
    """Real captured WorkStatus state=CLEANING → coordinator.data.activity == 'cleaning'."""
    fixture = load_fixture("mqtt/work_status/cleaning_active.json")
    simulate_mqtt_message(integration_coordinator, fixture["dps"])
    await hass.async_block_till_done()

    assert integration_coordinator.data.activity == "cleaning"


@pytest.mark.asyncio
async def test_mqtt_battery_update(hass, integration_coordinator):
    """DPS 163 '85' → coordinator.data.battery_level == 85."""
    simulate_mqtt_message(integration_coordinator, {"163": "85"})
    await hass.async_block_till_done()

    assert integration_coordinator.data.battery_level == 85


@pytest.mark.asyncio
async def test_mqtt_multiple_dps_in_one_message(hass, integration_coordinator):
    """A single MQTT message with both DPS 153 and 163 updates both fields."""
    ws = make_work_status(state=5)
    dps = make_dps_payload("153", ws)
    dps["163"] = "92"

    simulate_mqtt_message(integration_coordinator, dps)
    await hass.async_block_till_done()

    assert integration_coordinator.data.activity == "cleaning"
    assert integration_coordinator.data.battery_level == 92


@pytest.mark.asyncio
async def test_mqtt_malformed_payload_no_crash(hass, integration_coordinator):
    """Invalid JSON bytes must not crash; state stays unchanged."""
    coordinator = integration_coordinator

    # Establish baseline state
    simulate_mqtt_message(coordinator, {"163": "85"})
    await hass.async_block_till_done()
    assert coordinator.data.battery_level == 85

    # Inject garbage — no exception should propagate
    coordinator._handle_mqtt_message(b"not valid json{{{")
    await hass.async_block_till_done()

    # State unchanged
    assert coordinator.data.battery_level == 85


@pytest.mark.asyncio
async def test_mqtt_message_updates_charging_status(hass, integration_coordinator):
    """WorkStatus state=3 with Charging(state=0) → charging=True, docked."""
    ws = make_work_status(
        state=3,
        charging=WorkStatus.Charging(state=0),  # DOING
    )
    simulate_mqtt_message(integration_coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    assert integration_coordinator.data.charging is True
    assert integration_coordinator.data.activity == "docked"


@pytest.mark.asyncio
async def test_mqtt_trigger_source_from_work_status(hass, integration_coordinator):
    """WorkStatus with trigger.source=1 → trigger_source='app'."""
    ws = make_work_status(
        state=5,
        trigger=WorkStatus.Trigger(source=1),  # APP
    )
    simulate_mqtt_message(integration_coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    assert integration_coordinator.data.trigger_source == "app"


@pytest.mark.asyncio
async def test_mqtt_error_state(hass, integration_coordinator):
    """WorkStatus state=2 (FAULT) → activity='error'."""
    ws = make_work_status(state=2)
    simulate_mqtt_message(integration_coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    assert integration_coordinator.data.activity == "error"


# ---------------------------------------------------------------------------
# Dock debouncing (real HA timers via async_fire_time_changed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dock_debounce_basic(hass, integration_coordinator):
    """Station washing → dock_status NOT committed → fire 2s → committed."""
    coordinator = integration_coordinator
    assert coordinator.data.dock_status is None

    # Inject station WASHING (state=1)
    station = make_station_response(
        status=StationResponse.StationStatus(state=1),  # WASHING
    )
    simulate_mqtt_message(coordinator, make_dps_payload("173", station))
    await hass.async_block_till_done()

    # dock_status must NOT be committed yet (debounce pending)
    assert coordinator.data.dock_status is None
    assert coordinator._pending_dock_status == "Washing"

    # Fire time forward past the 2-second debounce window
    async_fire_time_changed(hass, utcnow() + timedelta(seconds=3))
    await hass.async_block_till_done()

    # Now dock_status is committed
    assert coordinator.data.dock_status == "Washing"
    assert coordinator._pending_dock_status is None


@pytest.mark.asyncio
async def test_dock_debounce_rapid_change(hass, integration_coordinator):
    """Washing then idle within 2s → only 'Idle' committed after timer."""
    coordinator = integration_coordinator

    # Inject washing
    station_washing = make_station_response(
        status=StationResponse.StationStatus(state=1),  # WASHING
    )
    simulate_mqtt_message(coordinator, make_dps_payload("173", station_washing))
    await hass.async_block_till_done()
    assert coordinator._pending_dock_status == "Washing"

    # Rapid change to idle (within debounce window)
    station_idle = make_station_response(
        status=StationResponse.StationStatus(state=0),  # IDLE
    )
    simulate_mqtt_message(coordinator, make_dps_payload("173", station_idle))
    await hass.async_block_till_done()
    assert coordinator._pending_dock_status == "Idle"

    # Fire time past debounce
    async_fire_time_changed(hass, utcnow() + timedelta(seconds=3))
    await hass.async_block_till_done()

    # Only the last value should be committed
    assert coordinator.data.dock_status == "Idle"


@pytest.mark.asyncio
async def test_dock_debounce_non_dock_message_does_not_reset_timer(
    hass, integration_coordinator
):
    """Battery update within debounce window must NOT reset the dock timer.

    Tests the critical ``'dock_status' in changes`` guard on line 134 of
    coordinator.py — non-dock messages skip the debounce block entirely.
    """
    coordinator = integration_coordinator

    # Inject station washing → starts debounce timer
    station = make_station_response(
        status=StationResponse.StationStatus(state=1),
    )
    simulate_mqtt_message(coordinator, make_dps_payload("173", station))
    await hass.async_block_till_done()

    assert coordinator._pending_dock_status == "Washing"
    assert coordinator._dock_idle_cancel is not None
    original_cancel = coordinator._dock_idle_cancel

    # Inject battery update (non-dock message) within debounce window
    simulate_mqtt_message(coordinator, {"163": "90"})
    await hass.async_block_till_done()

    # Timer must NOT have been replaced
    assert coordinator._dock_idle_cancel is original_cancel
    assert coordinator._pending_dock_status == "Washing"

    # Fire time past debounce
    async_fire_time_changed(hass, utcnow() + timedelta(seconds=3))
    await hass.async_block_till_done()

    # Dock status committed as expected
    assert coordinator.data.dock_status == "Washing"
    # Battery also updated
    assert coordinator.data.battery_level == 90


@pytest.mark.asyncio
async def test_dock_debounce_not_committed_before_timer(hass, integration_coordinator):
    """Verify dock_status stays at old value until the timer fires."""
    coordinator = integration_coordinator

    # Set a known dock_status first by committing one cycle
    station_idle = make_station_response(
        status=StationResponse.StationStatus(state=0),  # IDLE
    )
    simulate_mqtt_message(coordinator, make_dps_payload("173", station_idle))
    await hass.async_block_till_done()
    async_fire_time_changed(hass, utcnow() + timedelta(seconds=3))
    await hass.async_block_till_done()
    assert coordinator.data.dock_status == "Idle"

    # Now inject washing → pending, not yet committed
    station_washing = make_station_response(
        status=StationResponse.StationStatus(state=1),
    )
    simulate_mqtt_message(coordinator, make_dps_payload("173", station_washing))
    await hass.async_block_till_done()

    # Published state still shows "Idle"
    assert coordinator.data.dock_status == "Idle"
    assert coordinator._pending_dock_status == "Washing"


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_state_transition_sequence(hass, integration_coordinator):
    """idle → cleaning → returning → docked in sequence."""
    coordinator = integration_coordinator
    transitions = [
        (0, "idle"),
        (5, "cleaning"),
        (7, "returning"),
        (3, "docked"),
    ]
    for state_code, expected_activity in transitions:
        ws = make_work_status(state=state_code)
        simulate_mqtt_message(coordinator, make_dps_payload("153", ws))
        await hass.async_block_till_done()
        assert coordinator.data.activity == expected_activity, (
            f"state={state_code}: expected {expected_activity!r}, "
            f"got {coordinator.data.activity!r}"
        )


@pytest.mark.asyncio
async def test_mqtt_paused_state(hass, integration_coordinator):
    """WorkStatus state=5 with cleaning.state=PAUSED → 'paused'."""
    ws = make_work_status(
        state=5,
        cleaning=WorkStatus.Cleaning(state=1),  # PAUSED
    )
    simulate_mqtt_message(integration_coordinator, make_dps_payload("153", ws))
    await hass.async_block_till_done()

    assert integration_coordinator.data.activity == "paused"


# ---------------------------------------------------------------------------
# Initialization with DPS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coordinator_init_with_dps(hass, mock_eufy_login):
    """Initial DPS is applied during initialize(), not bare construction."""
    device_info = make_device_info_dict()
    device_info["dps"] = {"163": "77"}

    mock_client = MagicMock()
    mock_client.set_on_message = MagicMock()
    mock_client.connect = AsyncMock()

    coordinator = EufyCleanCoordinator(hass, mock_eufy_login, device_info)

    with patch(
        "custom_components.robovac_mqtt.coordinator.EufyCleanClient",
        return_value=mock_client,
    ):
        await coordinator.initialize()

    assert coordinator.data.battery_level == 77


@pytest.mark.asyncio
async def test_coordinator_init_without_dps(hass, mock_eufy_login):
    """Construct coordinator without dps → default VacuumState."""
    device_info = make_device_info_dict()
    coordinator = EufyCleanCoordinator(hass, mock_eufy_login, device_info)

    assert coordinator.data.activity == "idle"
    assert coordinator.data.battery_level == 0


# ---------------------------------------------------------------------------
# send_command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_command_calls_client(
    hass, integration_coordinator, mock_mqtt_client
):
    """async_send_command forwards payload to the MQTT client."""
    await integration_coordinator.initialize()

    payload = {"152": "base64data=="}
    await integration_coordinator.async_send_command(payload)

    mock_mqtt_client.send_command.assert_called_once_with(payload)


@pytest.mark.asyncio
async def test_send_command_without_client_no_crash(hass, integration_coordinator):
    """async_send_command before initialize() must not crash."""
    assert integration_coordinator.client is None
    # Should log a warning but not raise
    await integration_coordinator.async_send_command({"152": "test"})


# ---------------------------------------------------------------------------
# Coordinator utilities
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shutdown_timers_cancels_debounce(hass, integration_coordinator):
    """async_shutdown_timers cancels active dock debounce timer."""
    coordinator = integration_coordinator

    # Start a dock debounce timer
    station = make_station_response(
        status=StationResponse.StationStatus(state=1),
    )
    simulate_mqtt_message(coordinator, make_dps_payload("173", station))
    await hass.async_block_till_done()
    assert coordinator._dock_idle_cancel is not None

    coordinator.async_shutdown_timers()

    assert coordinator._dock_idle_cancel is None
    assert coordinator._segment_update_cancel is None


@pytest.mark.asyncio
async def test_async_update_data_returns_current_state(hass, integration_coordinator):
    """_async_update_data returns the current VacuumState (push-based)."""
    coordinator = integration_coordinator
    simulate_mqtt_message(coordinator, {"163": "75"})
    await hass.async_block_till_done()

    result = await coordinator._async_update_data()
    assert result.battery_level == 75
    assert result is coordinator.data


@pytest.mark.asyncio
async def test_set_active_cleaning_targets(hass, integration_coordinator):
    """set_active_cleaning_targets updates room IDs and names."""
    coordinator = integration_coordinator
    # Prepopulate room info
    coordinator.data = replace(
        coordinator.data,
        rooms=[{"id": 1, "name": "Kitchen"}, {"id": 2, "name": "Bedroom"}],
    )

    coordinator.set_active_cleaning_targets(room_ids=[1, 2])

    assert coordinator.data.active_room_ids == [1, 2]
    assert "Kitchen" in coordinator.data.active_room_names
    assert "Bedroom" in coordinator.data.active_room_names


@pytest.mark.asyncio
async def test_set_active_scene(hass, integration_coordinator):
    """set_active_scene updates scene and clears room targets."""
    coordinator = integration_coordinator
    coordinator.set_active_scene(42, "Quick Clean")

    assert coordinator.data.current_scene_id == 42
    assert coordinator.data.current_scene_name == "Quick Clean"
    assert coordinator.data.active_room_ids == []
    assert coordinator.data.active_zone_count == 0
