"""Integration tests for control entities (select, switch, button, number, time).

Tests entity behavior through HA service calls with the full runtime,
verifying that the correct MQTT commands are dispatched to the mock client.
"""

from __future__ import annotations

import pytest
from dataclasses import replace

from custom_components.robovac_mqtt.const import DPS_MAP


def _enable_all_entities(coordinator) -> None:
    """Set coordinator state so all control entities report as available."""
    new_data = replace(
        coordinator.data,
        dock_auto_cfg={
            "collectdust_v2": {
                "sw": {"value": False},
                "mode": {"value": "BY_TASK"},
            },
            "wash": {
                "cfg": "CLOSE",
                "wash_freq": {
                    "mode": "ByPartition",
                    "time_or_area": {"value": 15},
                },
            },
            "dry": {"duration": {"level": "MEDIUM"}},
        },
        received_fields=coordinator.data.received_fields
        | {"child_lock", "do_not_disturb", "fan_speed", "dock_status"},
        rooms=[{"id": 1, "name": "Kitchen"}, {"id": 2, "name": "Bedroom"}],
        scenes=[{"id": 5, "name": "Full Clean"}],
        fan_speed="Standard",
        cleaning_mode="Vacuum",
        mop_water_level="Medium",
        cleaning_intensity="Normal",
        dnd_enabled=False,
        dnd_start_hour=22,
        dnd_start_minute=0,
        dnd_end_hour=8,
        dnd_end_minute=0,
    )
    coordinator.async_set_updated_data(new_data)


def _last_command(mock_client) -> dict:
    """Return the last sent command dict, or fail if none sent."""
    cmds = mock_client.sent_commands
    assert len(cmds) > 0, "Expected at least one command to be sent"
    return cmds[-1]


# ---------------------------------------------------------------------------
# Switches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_robot_switch_on(hass, setup_integration, mock_mqtt_client):
    """Turning on find robot dispatches DPS 160 = True."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.test_vacuum_find_robot"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert cmd[DPS_MAP["FIND_ROBOT"]] is True


@pytest.mark.asyncio
async def test_find_robot_switch_off(hass, setup_integration, mock_mqtt_client):
    """Turning off find robot dispatches DPS 160 = False."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.test_vacuum_find_robot"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert cmd[DPS_MAP["FIND_ROBOT"]] is False


@pytest.mark.asyncio
async def test_child_lock_switch_on(hass, setup_integration, mock_mqtt_client):
    """Enabling child lock dispatches DPS 176 (UNSETTING)."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.test_vacuum_child_lock"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["UNSETTING"] in cmd


@pytest.mark.asyncio
async def test_do_not_disturb_switch_on(hass, setup_integration, mock_mqtt_client):
    """Enabling DND dispatches DPS 157 (UNDISTURBED)."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.test_vacuum_do_not_disturb"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["UNDISTURBED"] in cmd


@pytest.mark.asyncio
async def test_do_not_disturb_switch_off(hass, setup_integration, mock_mqtt_client):
    """Disabling DND dispatches DPS 157 (UNDISTURBED)."""
    coordinator = setup_integration["coordinators"][0]
    _enable_all_entities(coordinator)
    coordinator.async_set_updated_data(
        replace(coordinator.data, dnd_enabled=True)
    )
    await hass.async_block_till_done()

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.test_vacuum_do_not_disturb"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["UNDISTURBED"] in cmd


@pytest.mark.asyncio
async def test_auto_empty_switch_on(hass, setup_integration, mock_mqtt_client):
    """Enabling auto empty dispatches DPS 173 (set_auto_cfg via StationRequest)."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.test_vacuum_auto_empty"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["GO_HOME"] in cmd


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wash_mop_button(hass, setup_integration, mock_mqtt_client):
    """Pressing wash mop dispatches go_selfcleaning via DPS 173."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.test_vacuum_wash_mop"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["GO_HOME"] in cmd


@pytest.mark.asyncio
async def test_dry_mop_button(hass, setup_integration, mock_mqtt_client):
    """Pressing dry mop dispatches go_dry via DPS 173."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.test_vacuum_dry_mop"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["GO_HOME"] in cmd


@pytest.mark.asyncio
async def test_empty_dust_bin_button(hass, setup_integration, mock_mqtt_client):
    """Pressing empty dust bin dispatches collect_dust via DPS 173."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.test_vacuum_empty_dust_bin"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["GO_HOME"] in cmd


@pytest.mark.asyncio
async def test_reset_filter_button(hass, setup_integration, mock_mqtt_client):
    """Pressing reset filter dispatches reset_accessory via DPS 168."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.test_vacuum_reset_filter"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["ACCESSORIES_STATUS"] in cmd


# ---------------------------------------------------------------------------
# Select entities
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleaning_mode_select(hass, setup_integration, mock_mqtt_client):
    """Selecting cleaning mode 'Mop' dispatches DPS 154."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.test_vacuum_cleaning_mode", "option": "Mop"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["CLEANING_PARAMETERS"] in cmd


@pytest.mark.asyncio
async def test_suction_level_select(hass, setup_integration, mock_mqtt_client):
    """Selecting suction 'Turbo' dispatches DPS 158 with index 2."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.test_vacuum_suction_level", "option": "Turbo"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["CLEAN_SPEED"] in cmd
    assert cmd[DPS_MAP["CLEAN_SPEED"]] == "2"


@pytest.mark.asyncio
async def test_water_level_select(hass, setup_integration, mock_mqtt_client):
    """Selecting water level 'High' dispatches DPS 154."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.test_vacuum_water_level", "option": "High"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["CLEANING_PARAMETERS"] in cmd


@pytest.mark.asyncio
async def test_mop_intensity_select(hass, setup_integration, mock_mqtt_client):
    """Selecting mop intensity 'Max' dispatches DPS 154 (mapped to water level)."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.test_vacuum_mop_intensity", "option": "Max"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["CLEANING_PARAMETERS"] in cmd


@pytest.mark.asyncio
async def test_cleaning_intensity_select(hass, setup_integration, mock_mqtt_client):
    """Selecting cleaning intensity 'Quick' dispatches DPS 154."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "select",
        "select_option",
        {
            "entity_id": "select.test_vacuum_cleaning_intensity",
            "option": "Quick",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["CLEANING_PARAMETERS"] in cmd


@pytest.mark.asyncio
async def test_scene_select(hass, setup_integration, mock_mqtt_client):
    """Selecting a scene dispatches scene_clean via DPS 152."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "select",
        "select_option",
        {
            "entity_id": "select.test_vacuum_scene",
            "option": "Full Clean (ID: 5)",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["PLAY_PAUSE"] in cmd


@pytest.mark.asyncio
async def test_room_select(hass, setup_integration, mock_mqtt_client):
    """Selecting a room dispatches room_clean via DPS 152."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "select",
        "select_option",
        {
            "entity_id": "select.test_vacuum_clean_room",
            "option": "Kitchen (ID: 1)",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["PLAY_PAUSE"] in cmd


@pytest.mark.asyncio
async def test_dry_duration_select(hass, setup_integration, mock_mqtt_client):
    """Selecting dry duration '4h' dispatches set_auto_cfg via DPS 173."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.test_vacuum_dry_duration", "option": "4h"},
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["GO_HOME"] in cmd


# ---------------------------------------------------------------------------
# Number entities
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wash_frequency_number(hass, setup_integration, mock_mqtt_client):
    """Setting wash frequency to 20 dispatches set_auto_cfg via DPS 173."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": "number.test_vacuum_wash_frequency_value_time",
            "value": 20,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["GO_HOME"] in cmd


# ---------------------------------------------------------------------------
# Time entities
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dnd_start_time(hass, setup_integration, mock_mqtt_client):
    """Setting DND start time dispatches set_do_not_disturb via DPS 157."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "time",
        "set_value",
        {
            "entity_id": "time.test_vacuum_do_not_disturb_start",
            "time": "23:30:00",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["UNDISTURBED"] in cmd


@pytest.mark.asyncio
async def test_dnd_end_time(hass, setup_integration, mock_mqtt_client):
    """Setting DND end time dispatches set_do_not_disturb via DPS 157."""
    _enable_all_entities(setup_integration["coordinators"][0])
    await hass.async_block_till_done()

    await hass.services.async_call(
        "time",
        "set_value",
        {
            "entity_id": "time.test_vacuum_do_not_disturb_end",
            "time": "07:00:00",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    cmd = _last_command(mock_mqtt_client)
    assert DPS_MAP["UNDISTURBED"] in cmd
