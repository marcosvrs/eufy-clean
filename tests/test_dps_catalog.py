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
