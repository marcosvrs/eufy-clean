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
