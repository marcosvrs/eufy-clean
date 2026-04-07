"""Tests for DPS catalog bridge, builder, overrides, and handled IDs in const.py."""

from __future__ import annotations

import pytest

from custom_components.robovac_mqtt.const import (
    AUTO_ENTITY_OVERRIDES,
    CLOUD_CODE_TO_FUNC,
    DEFAULT_DPS_MAP,
    DPS_MAP,
    HANDLED_DPS_IDS,
    build_dps_map_from_catalog,
    supported_dps_from_catalog,
)


def test_dps_map_alias():
    assert DPS_MAP is DEFAULT_DPS_MAP
    assert DPS_MAP["PLAY_PAUSE"] == "152"
    assert DPS_MAP["WORK_STATUS"] == "153"


def test_handled_dps_ids_excludes_simple_types():
    for dps_id in ("158", "159", "160", "161", "163"):
        assert dps_id not in HANDLED_DPS_IDS


def test_handled_dps_ids_includes_complex():
    for dps_id in ("152", "153", "154", "177", "180"):
        assert dps_id in HANDLED_DPS_IDS


def test_auto_entity_overrides_bat_level():
    entry = AUTO_ENTITY_OVERRIDES["bat_level"]
    assert entry["device_class"] == "battery"
    assert entry["entity_category"] is None
    assert entry["unit"] == "%"
    assert entry["state_class"] == "measurement"


def test_auto_entity_overrides_calling_robot():
    entry = AUTO_ENTITY_OVERRIDES["calling_robot"]
    assert entry["entity_category"] is None
    assert entry["icon"] == "mdi:magnify"


def test_build_dps_map_empty_catalog():
    result = build_dps_map_from_catalog([])
    assert result == DEFAULT_DPS_MAP
    assert result is not DEFAULT_DPS_MAP


def test_build_dps_map_from_catalog():
    catalog = [{"dp_id": 152, "code": "mode_ctrl"}]
    result = build_dps_map_from_catalog(catalog)
    assert result["PLAY_PAUSE"] == "152"


def test_build_dps_map_remaps_dp_id():
    catalog = [{"dp_id": 999, "code": "mode_ctrl"}]
    result = build_dps_map_from_catalog(catalog)
    assert result["PLAY_PAUSE"] == "999"


def test_build_dps_map_skips_unknown_codes():
    catalog = [{"dp_id": 200, "code": "pet_avoidance"}]
    result = build_dps_map_from_catalog(catalog)
    assert result == DEFAULT_DPS_MAP


def test_build_dps_map_malformed_entry_skipped():
    catalog = [
        {"dp_id": 152},
        {"code": "mode_ctrl"},
        {"dp_id": 153, "code": "work_status"},
    ]
    result = build_dps_map_from_catalog(catalog)
    assert result["WORK_STATUS"] == "153"
    assert result["WORK_MODE"] == "153"


def test_supported_dps_empty_catalog():
    result = supported_dps_from_catalog([])
    assert result == frozenset(DEFAULT_DPS_MAP.keys())


def test_supported_dps_partial_catalog():
    catalog = [{"dp_id": 152, "code": "mode_ctrl"}]
    result = supported_dps_from_catalog(catalog)
    assert "PLAY_PAUSE" in result
    assert "STATION_STATUS" not in result


def test_cloud_code_to_func_station():
    assert CLOUD_CODE_TO_FUNC["station"] == ["GO_HOME", "STATION_STATUS"]


def test_vacuum_state_has_dynamic_values():
    from custom_components.robovac_mqtt.models import VacuumState
    state = VacuumState()
    assert hasattr(state, "dynamic_values")
    assert isinstance(state.dynamic_values, dict)


def test_update_state_accepts_dps_map_param():
    from custom_components.robovac_mqtt.api.parser import update_state
    from custom_components.robovac_mqtt.models import VacuumState
    state, changes = update_state(VacuumState(), {}, dps_map=DEFAULT_DPS_MAP)
    assert state is not None


def test_battery_written_to_dynamic_values():
    from custom_components.robovac_mqtt.api.parser import update_state
    from custom_components.robovac_mqtt.models import VacuumState
    state, _ = update_state(VacuumState(), {"163": "85"})
    assert state.battery_level == 85
    assert state.dynamic_values.get("163") == 85


def test_generic_handler_bool_in_dynamic_values():
    from custom_components.robovac_mqtt.api.parser import update_state
    from custom_components.robovac_mqtt.models import VacuumState
    catalog_types = {"200": "Bool"}
    state, _ = update_state(VacuumState(), {"200": "true"}, catalog_types=catalog_types)
    assert state.dynamic_values.get("200") is True


def test_generic_handler_value_in_dynamic_values():
    from custom_components.robovac_mqtt.api.parser import update_state
    from custom_components.robovac_mqtt.models import VacuumState
    catalog_types = {"200": "Value"}
    state, _ = update_state(VacuumState(), {"200": "42"}, catalog_types=catalog_types)
    assert state.dynamic_values.get("200") == 42


def test_generic_handler_accumulates_multiple_dps():
    from custom_components.robovac_mqtt.api.parser import update_state
    from custom_components.robovac_mqtt.models import VacuumState
    catalog_types = {"200": "Bool", "201": "Value"}
    state, _ = update_state(VacuumState(), {"200": "true", "201": "7"}, catalog_types=catalog_types)
    assert state.dynamic_values.get("200") is True
    assert state.dynamic_values.get("201") == 7


from custom_components.robovac_mqtt.api.commands import build_command, build_generic_command


def test_build_generic_command_bool():
    result = build_command("generic", dp_id="159", value=True)
    assert result == {"159": True}


def test_build_generic_command_int():
    result = build_command("generic", dp_id="161", value=75)
    assert result == {"161": 75}


def test_build_generic_command_direct():
    result = build_generic_command("159", True)
    assert result == {"159": True}


def test_existing_commands_unchanged_with_default_dps_map():
    result = build_command("start_auto")
    assert "152" in result


# ─── T3: additional parser dynamic_values tests ───────────────────────────────

def test_generic_handler_bool_false():
    """Unknown Bool DPS stored as False."""
    from custom_components.robovac_mqtt.api.parser import update_state
    from custom_components.robovac_mqtt.models import VacuumState
    state, _ = update_state(
        VacuumState(),
        {"200": "false"},
        catalog_types={"200": "Bool"},
    )
    assert state.dynamic_values.get("200") is False


def test_generic_handler_skips_raw():
    """Raw DPS without catalog_types does NOT go into dynamic_values."""
    from custom_components.robovac_mqtt.api.parser import update_state
    from custom_components.robovac_mqtt.models import VacuumState
    state, _ = update_state(
        VacuumState(),
        {"200": "some_value"},
    )
    assert "200" not in state.dynamic_values


def test_generic_handler_skips_handled_dps():
    """DPS in HANDLED_DPS_IDS are not put into dynamic_values by generic handler."""
    from custom_components.robovac_mqtt.api.parser import update_state
    from custom_components.robovac_mqtt.models import VacuumState
    # "152" is in HANDLED_DPS_IDS — it goes through _process_play_pause, not generic
    state, _ = update_state(VacuumState(), {"152": ""})
    assert "152" not in state.dynamic_values


def test_dps_map_param_respected():
    """Custom dps_map parameter is used instead of DEFAULT_DPS_MAP."""
    from custom_components.robovac_mqtt.api.parser import update_state
    from custom_components.robovac_mqtt.models import VacuumState
    custom_map = dict(DEFAULT_DPS_MAP)
    custom_map["BATTERY_LEVEL"] = "999"
    state, _ = update_state(VacuumState(), {"999": "75"}, dps_map=custom_map)
    assert state.battery_level == 75


def test_update_state_find_robot_dual_writes_dynamic_values():
    from custom_components.robovac_mqtt.api.parser import update_state
    from custom_components.robovac_mqtt.models import VacuumState
    state, _ = update_state(VacuumState(), {"160": "true"})
    assert state.find_robot is True
    assert state.dynamic_values.get("160") is True


def test_update_state_custom_dps_map():
    from custom_components.robovac_mqtt.api.parser import update_state
    from custom_components.robovac_mqtt.models import VacuumState
    custom_map = dict(DEFAULT_DPS_MAP)
    custom_map["BATTERY_LEVEL"] = "999"
    state, _ = update_state(VacuumState(), {"999": "77"}, dps_map=custom_map)
    assert state.battery_level == 77


def test_multiple_dps_in_one_message_accumulate_dynamic_values():
    """Critical: multiple DPS in one MQTT message must all appear in dynamic_values."""
    from custom_components.robovac_mqtt.api.parser import update_state
    from custom_components.robovac_mqtt.models import VacuumState
    catalog_types = {"200": "Bool", "199": "Value"}
    state, _ = update_state(
        VacuumState(),
        {"200": "true", "199": "42", "163": "90"},
        catalog_types=catalog_types,
    )
    assert state.dynamic_values.get("200") is True
    assert state.dynamic_values.get("199") == 42
    assert state.dynamic_values.get("163") == 90


# ── T6: auto_entities factory tests ──────────────────────────────────────────

def _make_coordinator(catalog_entries, dynamic_values=None):
    """Helper: build a minimal mock coordinator for factory tests."""
    from unittest.mock import MagicMock
    from custom_components.robovac_mqtt.models import VacuumState
    coord = MagicMock()
    coord.dps_catalog = {str(e["dp_id"]): e for e in catalog_entries}
    coord.data = VacuumState(dynamic_values=dynamic_values or {})
    coord.device_id = "test_device_abc"
    coord.device_info = {}
    return coord


def test_get_auto_switches_creates_for_bool_rw():
    from custom_components.robovac_mqtt.auto_entities import get_auto_switches
    coord = _make_coordinator([{"dp_id": 200, "code": "boost_iq", "data_type": "Bool", "mode": "rw"}])
    entities = get_auto_switches(coord)
    assert len(entities) == 1
    assert entities[0]._dp_id == "200"
    assert entities[0]._attr_name == "Boost IQ"
    assert entities[0]._attr_icon == "mdi:car-turbocharger"


def test_get_auto_switches_skips_handled_dps():
    from custom_components.robovac_mqtt.auto_entities import get_auto_switches
    # DPS 152 is in HANDLED_DPS_IDS — must be skipped
    coord = _make_coordinator([{"dp_id": 152, "code": "mode_ctrl", "data_type": "Bool", "mode": "rw"}])
    entities = get_auto_switches(coord)
    assert len(entities) == 0


def test_get_auto_switches_skips_raw_type():
    from custom_components.robovac_mqtt.auto_entities import get_auto_switches
    coord = _make_coordinator([{"dp_id": 200, "code": "some_raw", "data_type": "Raw", "mode": "rw"}])
    entities = get_auto_switches(coord)
    assert len(entities) == 0


def test_get_auto_sensors_creates_for_value_ro():
    from custom_components.robovac_mqtt.auto_entities import get_auto_sensors
    coord = _make_coordinator([{"dp_id": 163, "code": "bat_level", "data_type": "Value", "mode": "ro"}])
    entities = get_auto_sensors(coord)
    assert len(entities) == 1
    assert entities[0]._dp_id == "163"
    assert entities[0]._attr_name == "Battery"
    assert entities[0]._attr_device_class == "battery"
    assert entities[0]._attr_entity_registry_enabled_default is True


def test_get_auto_numbers_creates_for_value_rw():
    from custom_components.robovac_mqtt.auto_entities import get_auto_numbers
    coord = _make_coordinator([{"dp_id": 161, "code": "volume", "data_type": "Value", "mode": "rw"}])
    entities = get_auto_numbers(coord)
    assert len(entities) == 1
    assert entities[0]._dp_id == "161"
    assert entities[0]._attr_native_min_value == 0
    assert entities[0]._attr_native_max_value == 100


def test_get_auto_selects_creates_for_enum_with_options_map():
    from custom_components.robovac_mqtt.auto_entities import get_auto_selects
    coord = _make_coordinator([{"dp_id": 158, "code": "suction_level", "data_type": "Enum", "mode": "rw"}])
    entities = get_auto_selects(coord)
    assert len(entities) == 1
    assert set(entities[0].options) == {"Quiet", "Standard", "Turbo", "Max", "Boost_IQ"}


def test_get_auto_selects_skips_enum_without_options_map():
    from custom_components.robovac_mqtt.auto_entities import get_auto_selects
    # Unknown enum — no options_map in override → skip
    coord = _make_coordinator([{"dp_id": 200, "code": "unknown_enum", "data_type": "Enum", "mode": "rw"}])
    entities = get_auto_selects(coord)
    assert len(entities) == 0


def test_unknown_code_gets_defaults():
    from custom_components.robovac_mqtt.auto_entities import get_auto_switches
    from homeassistant.helpers.entity import EntityCategory
    coord = _make_coordinator([{"dp_id": 200, "code": "pet_avoidance", "data_type": "Bool", "mode": "rw"}])
    entities = get_auto_switches(coord)
    assert len(entities) == 1
    assert entities[0]._attr_name == "Pet Avoidance"
    assert entities[0]._attr_entity_registry_enabled_default is False
    assert entities[0]._attr_entity_category == EntityCategory.CONFIG


def test_primary_entity_category_none_from_override():
    from custom_components.robovac_mqtt.auto_entities import get_auto_switches
    # calling_robot has entity_category: None in override → PRIMARY (no category)
    coord = _make_coordinator([{"dp_id": 160, "code": "calling_robot", "data_type": "Bool", "mode": "rw"}])
    entities = get_auto_switches(coord)
    assert len(entities) == 1
    # PRIMARY entities must NOT have _attr_entity_category set to CONFIGURATION
    assert not hasattr(entities[0], '_attr_entity_category') or entities[0]._attr_entity_category is None


def test_get_auto_binary_sensors_creates_for_bool_ro():
    from custom_components.robovac_mqtt.auto_entities import get_auto_binary_sensors
    coord = _make_coordinator([{"dp_id": 200, "code": "dust_full", "data_type": "Bool", "mode": "ro"}])
    entities = get_auto_binary_sensors(coord)
    assert len(entities) == 1
    assert entities[0]._dp_id == "200"
    assert entities[0]._attr_name == "Dust Full"


# ── T8: Entity gating and auto-entity integration tests ─────────────────────


def _make_setup_coordinator(supported_dps=None, catalog_entries=None):
    """Helper: build a mock coordinator for platform setup tests."""
    from unittest.mock import MagicMock
    from custom_components.robovac_mqtt.models import VacuumState

    entries = catalog_entries or []
    coord = MagicMock()
    coord.dps_catalog = {str(e["dp_id"]): e for e in entries}
    coord.data = VacuumState()
    coord.device_id = "test_device_abc"
    coord.device_name = "Test Vacuum"
    coord.device_info = {}
    if supported_dps is not None:
        coord.supported_dps = frozenset(supported_dps)
    else:
        coord.supported_dps = frozenset(DEFAULT_DPS_MAP.keys())
    return coord


@pytest.mark.asyncio
async def test_sensor_entity_gating_excludes_station_sensors():
    """Station sensors excluded when STATION_STATUS not in supported_dps."""
    from unittest.mock import MagicMock
    from custom_components.robovac_mqtt.const import DOMAIN
    from custom_components.robovac_mqtt.sensor import async_setup_entry

    coord = _make_setup_coordinator(
        supported_dps={"PLAY_PAUSE", "WORK_STATUS", "BATTERY_LEVEL", "ERROR_CODE"}
    )
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {config_entry.entry_id: {"coordinators": [coord]}}}

    added = []
    await async_setup_entry(hass, config_entry, lambda ents: added.extend(ents))

    unique_ids = [e._attr_unique_id for e in added if hasattr(e, "_attr_unique_id")]
    assert "test_device_abc_water_level" not in unique_ids
    assert "test_device_abc_waste_water_level" not in unique_ids
    assert "test_device_abc_dock_status" not in unique_ids


@pytest.mark.asyncio
async def test_select_entity_gating_excludes_scene_when_unsupported():
    """Scene select excluded when SCENE_INFO not in supported_dps."""
    from unittest.mock import MagicMock
    from custom_components.robovac_mqtt.const import DOMAIN
    from custom_components.robovac_mqtt.select import async_setup_entry

    coord = _make_setup_coordinator(
        supported_dps={"PLAY_PAUSE", "WORK_STATUS", "CLEANING_PARAMETERS"}
    )
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {config_entry.entry_id: {"coordinators": [coord]}}}

    added = []
    await async_setup_entry(hass, config_entry, lambda ents: added.extend(ents))

    unique_ids = [e._attr_unique_id for e in added if hasattr(e, "_attr_unique_id")]
    assert "test_device_abc_scene_select" not in unique_ids


@pytest.mark.asyncio
async def test_switch_entity_gating_excludes_dock_switches():
    """Dock switches excluded when STATION_STATUS not in supported_dps."""
    from unittest.mock import MagicMock
    from custom_components.robovac_mqtt.const import DOMAIN
    from custom_components.robovac_mqtt.switch import async_setup_entry

    coord = _make_setup_coordinator(
        supported_dps={"PLAY_PAUSE", "WORK_STATUS"}
    )
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {config_entry.entry_id: {"coordinators": [coord]}}}

    added = []
    await async_setup_entry(hass, config_entry, lambda ents: added.extend(ents))

    unique_ids = [e._attr_unique_id for e in added if hasattr(e, "_attr_unique_id")]
    assert "test_device_abc_auto_empty" not in unique_ids
    assert "test_device_abc_auto_wash" not in unique_ids


@pytest.mark.asyncio
async def test_sensor_setup_includes_auto_sensors():
    """sensor.py setup appends auto-generated sensors from factory."""
    from unittest.mock import MagicMock
    from custom_components.robovac_mqtt.auto_entities import AutoSensor
    from custom_components.robovac_mqtt.const import DOMAIN
    from custom_components.robovac_mqtt.sensor import async_setup_entry

    coord = _make_setup_coordinator(
        catalog_entries=[
            {"dp_id": 163, "code": "bat_level", "data_type": "Value", "mode": "ro"},
        ]
    )
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {config_entry.entry_id: {"coordinators": [coord]}}}

    added = []
    await async_setup_entry(hass, config_entry, lambda ents: added.extend(ents))

    auto_sensors = [e for e in added if isinstance(e, AutoSensor)]
    assert len(auto_sensors) >= 1
    assert any(e._cloud_code == "bat_level" for e in auto_sensors)


@pytest.mark.asyncio
async def test_select_setup_includes_auto_selects():
    """select.py setup appends auto-generated selects from factory."""
    from unittest.mock import MagicMock
    from custom_components.robovac_mqtt.auto_entities import AutoSelect
    from custom_components.robovac_mqtt.const import DOMAIN
    from custom_components.robovac_mqtt.select import async_setup_entry

    coord = _make_setup_coordinator(
        catalog_entries=[
            {"dp_id": 158, "code": "suction_level", "data_type": "Enum", "mode": "rw"},
        ]
    )
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {config_entry.entry_id: {"coordinators": [coord]}}}

    added = []
    await async_setup_entry(hass, config_entry, lambda ents: added.extend(ents))

    auto_selects = [e for e in added if isinstance(e, AutoSelect)]
    assert len(auto_selects) >= 1
    assert any(e._cloud_code == "suction_level" for e in auto_selects)


@pytest.mark.asyncio
async def test_switch_setup_includes_auto_switches():
    """switch.py setup appends auto-generated switches from factory."""
    from unittest.mock import MagicMock
    from custom_components.robovac_mqtt.auto_entities import AutoSwitch
    from custom_components.robovac_mqtt.const import DOMAIN
    from custom_components.robovac_mqtt.switch import async_setup_entry

    coord = _make_setup_coordinator(
        catalog_entries=[
            {"dp_id": 159, "code": "boost_iq", "data_type": "Bool", "mode": "rw"},
            {"dp_id": 160, "code": "calling_robot", "data_type": "Bool", "mode": "rw"},
        ]
    )
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {config_entry.entry_id: {"coordinators": [coord]}}}

    added = []
    await async_setup_entry(hass, config_entry, lambda ents: added.extend(ents))

    auto_switches = [e for e in added if isinstance(e, AutoSwitch)]
    assert len(auto_switches) >= 2
    codes = {e._cloud_code for e in auto_switches}
    assert "boost_iq" in codes
    assert "calling_robot" in codes


# ── T7: coordinator DPS catalog integration tests ─────────────────────────────


def test_coordinator_builds_dps_map_from_catalog():
    from unittest.mock import MagicMock
    from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator

    catalog = [{"dp_id": 158, "code": "suction_level", "data_type": "Enum", "mode": "rw"}]
    device_info = {
        "deviceId": "test_id",
        "deviceModel": "T2351",
        "deviceName": "Test Vac",
        "dps_catalog": catalog,
    }
    coord = EufyCleanCoordinator(MagicMock(), MagicMock(), device_info)
    assert coord.dps_map["CLEAN_SPEED"] == "158"


def test_coordinator_defaults_without_catalog():
    from unittest.mock import MagicMock
    from custom_components.robovac_mqtt.const import DEFAULT_DPS_MAP
    from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator

    device_info = {
        "deviceId": "test_id",
        "deviceModel": "T2351",
        "deviceName": "Test Vac",
    }
    coord = EufyCleanCoordinator(MagicMock(), MagicMock(), device_info)
    assert coord.dps_map == DEFAULT_DPS_MAP


def test_coordinator_catalog_types_from_catalog():
    from unittest.mock import MagicMock
    from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator

    catalog = [
        {"dp_id": 163, "code": "bat_level", "data_type": "Value", "mode": "ro"},
        {"dp_id": 159, "code": "boost_iq", "data_type": "Bool", "mode": "rw"},
    ]
    device_info = {
        "deviceId": "test_id",
        "deviceModel": "T2351",
        "deviceName": "Test Vac",
        "dps_catalog": catalog,
    }
    coord = EufyCleanCoordinator(MagicMock(), MagicMock(), device_info)
    assert coord.catalog_types["163"] == "Value"
    assert coord.catalog_types["159"] == "Bool"


def test_coordinator_shutdown_cancels_catalog_timer():
    from unittest.mock import MagicMock
    from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator

    device_info = {
        "deviceId": "test_id",
        "deviceModel": "T2351",
        "deviceName": "Test Vac",
    }
    coord = EufyCleanCoordinator(MagicMock(), MagicMock(), device_info)
    mock_cancel = MagicMock()
    coord._catalog_refresh_cancel = mock_cancel
    coord.async_shutdown_timers()
    mock_cancel.assert_called_once()
