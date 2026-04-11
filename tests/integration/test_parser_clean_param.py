from __future__ import annotations

from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import (
    CARPET_STRATEGY_NAMES,
    CLEANING_INTENSITY_NAMES,
    CLEANING_MODE_NAMES,
    CORNER_CLEANING_NAMES,
    FAN_SUCTION_NAMES,
    MOP_WATER_LEVEL_NAMES,
    CleaningMode,
    MopWaterLevel,
)
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.clean_param_pb2 import (
    CleanCarpet,
    CleanExtent,
    CleanParam,
    CleanParamRequest,
    CleanParamResponse,
    CleanType,
    Fan,
    MopMode,
)
from custom_components.robovac_mqtt.proto.cloud.common_pb2 import Switch
from custom_components.robovac_mqtt.utils import encode_message


def _clean_dps(proto_msg) -> dict[str, str]:
    return {"154": encode_message(proto_msg)}


def _full_clean_param(
    clean_type_val: int = 2,
    fan_suction: int = 2,
    mop_level: int = 1,
    corner_clean: int = 0,
    clean_extent_val: int = 0,
    carpet_strategy: int = 0,
    smart_mode: bool = False,
) -> CleanParam:
    return CleanParam(
        clean_type=CleanType(value=clean_type_val),
        fan=Fan(suction=fan_suction),
        mop_mode=MopMode(level=mop_level, corner_clean=corner_clean),
        clean_extent=CleanExtent(value=clean_extent_val),
        clean_carpet=CleanCarpet(strategy=carpet_strategy),
        smart_mode_sw=Switch(value=smart_mode),
    )


def test_response_format_all_fields_populated():
    cp = _full_clean_param(
        clean_type_val=2,
        fan_suction=2,
        mop_level=1,
        corner_clean=0,
        clean_extent_val=0,
        carpet_strategy=0,
        smart_mode=True,
    )
    resp = CleanParamResponse(clean_param=cp)
    state, changes = update_state(VacuumState(), _clean_dps(resp))

    assert state.cleaning_mode == CLEANING_MODE_NAMES[CleaningMode.SWEEP_AND_MOP]
    assert state.fan_speed == FAN_SUCTION_NAMES[2]
    assert state.mop_water_level == MOP_WATER_LEVEL_NAMES[MopWaterLevel.MIDDLE]
    assert state.cleaning_intensity == CLEANING_INTENSITY_NAMES[0]
    assert state.carpet_strategy == CARPET_STRATEGY_NAMES[0]
    assert state.corner_cleaning == CORNER_CLEANING_NAMES[0]
    assert state.smart_mode is True


def test_request_format_fallback():
    cp = _full_clean_param(
        clean_type_val=1,
        fan_suction=0,
        mop_level=2,
        corner_clean=1,
        clean_extent_val=1,
        carpet_strategy=1,
        smart_mode=False,
    )
    req = CleanParamRequest(clean_param=cp)
    state, changes = update_state(VacuumState(), _clean_dps(req))

    assert state.cleaning_mode == CLEANING_MODE_NAMES[CleaningMode.MOP_ONLY]
    assert state.fan_speed == FAN_SUCTION_NAMES[0]
    assert state.mop_water_level == MOP_WATER_LEVEL_NAMES[MopWaterLevel.HIGH]
    assert state.corner_cleaning == CORNER_CLEANING_NAMES[1]
    assert state.cleaning_intensity == CLEANING_INTENSITY_NAMES[1]
    assert state.carpet_strategy == CARPET_STRATEGY_NAMES[1]


def test_fan_speed_maps_to_names():
    for suction_val, expected_name in FAN_SUCTION_NAMES.items():
        cp = CleanParam(fan=Fan(suction=suction_val))
        resp = CleanParamResponse(clean_param=cp)
        state, _ = update_state(VacuumState(), _clean_dps(resp))
        assert (
            state.fan_speed == expected_name
        ), f"Fan suction {suction_val} → expected {expected_name!r}, got {state.fan_speed!r}"


def test_water_level_maps_to_names():
    for level_val, expected_name in MOP_WATER_LEVEL_NAMES.items():
        cp = CleanParam(mop_mode=MopMode(level=level_val.value))
        resp = CleanParamResponse(clean_param=cp)
        state, _ = update_state(VacuumState(), _clean_dps(resp))
        assert (
            state.mop_water_level == expected_name
        ), f"Mop level {level_val} → expected {expected_name!r}, got {state.mop_water_level!r}"


def test_cleaning_mode_maps_to_names():
    for mode_val, expected_name in CLEANING_MODE_NAMES.items():
        cp = CleanParam(clean_type=CleanType(value=mode_val.value))
        resp = CleanParamResponse(clean_param=cp)
        state, _ = update_state(VacuumState(), _clean_dps(resp))
        assert (
            state.cleaning_mode == expected_name
        ), f"CleanType {mode_val} → expected {expected_name!r}, got {state.cleaning_mode!r}"


def test_cleaning_intensity_maps_to_names():
    for extent_val, expected_name in CLEANING_INTENSITY_NAMES.items():
        cp = CleanParam(clean_extent=CleanExtent(value=extent_val))
        resp = CleanParamResponse(clean_param=cp)
        state, _ = update_state(VacuumState(), _clean_dps(resp))
        assert (
            state.cleaning_intensity == expected_name
        ), f"CleanExtent {extent_val} → expected {expected_name!r}, got {state.cleaning_intensity!r}"


def test_running_clean_param_variant():
    cp = _full_clean_param(clean_type_val=0, fan_suction=3)
    resp = CleanParamResponse(running_clean_param=cp)
    state, _ = update_state(VacuumState(), _clean_dps(resp))
    assert state.cleaning_mode == CLEANING_MODE_NAMES[CleaningMode.SWEEP_ONLY]
    assert state.fan_speed == FAN_SUCTION_NAMES[3]


def test_area_clean_param_response_variant():
    cp = _full_clean_param(clean_type_val=3, fan_suction=1)
    resp = CleanParamResponse(area_clean_param=cp)
    state, _ = update_state(VacuumState(), _clean_dps(resp))
    assert state.cleaning_mode == CLEANING_MODE_NAMES[CleaningMode.SWEEP_THEN_MOP]
    assert state.fan_speed == FAN_SUCTION_NAMES[1]


def test_area_clean_param_request_fallback():
    cp = _full_clean_param(clean_type_val=2, fan_suction=0, mop_level=0)
    req = CleanParamRequest(area_clean_param=cp)
    state, _ = update_state(VacuumState(), _clean_dps(req))
    assert state.cleaning_mode == CLEANING_MODE_NAMES[CleaningMode.SWEEP_AND_MOP]
    assert state.fan_speed == FAN_SUCTION_NAMES[0]
    assert state.mop_water_level == MOP_WATER_LEVEL_NAMES[MopWaterLevel.LOW]
