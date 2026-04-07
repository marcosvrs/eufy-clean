"""Tests for T10: DPS 176 UnisettingResponse — switch, numerical, unistate, wifi_data fields."""

from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DEFAULT_DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.common_pb2 import Active, Numerical, Switch
from custom_components.robovac_mqtt.proto.cloud.unisetting_pb2 import (
    UnisettingResponse,
    Unistate,
    WifiData,
)
from custom_components.robovac_mqtt.utils import encode_message


def _make_dps(resp: UnisettingResponse) -> dict:
    return {DEFAULT_DPS_MAP["UNSETTING"]: encode_message(resp)}


# --- Switch fields ---


def test_pet_mode_sw_parsed():
    resp = UnisettingResponse(pet_mode_sw=Switch(value=True))
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.pet_mode_sw is True


def test_ai_see_parsed():
    resp = UnisettingResponse(ai_see=Switch(value=True))
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.ai_see is True


def test_poop_avoidance_sw_parsed():
    resp = UnisettingResponse(poop_avoidance_sw=Switch(value=True))
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.poop_avoidance_sw is True


def test_switch_false_value():
    resp = UnisettingResponse(multi_map_sw=Switch(value=False))
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.multi_map_sw is False


def test_all_switch_fields_in_vacuum_state():
    s = VacuumState()
    for field in [
        "ai_see", "pet_mode_sw", "poop_avoidance_sw", "live_photo_sw",
        "deep_mop_corner_sw", "smart_follow_sw", "cruise_continue_sw",
        "multi_map_sw", "suggest_restricted_zone_sw", "water_level_sw",
    ]:
        assert hasattr(s, field), f"VacuumState missing {field}"
        assert getattr(s, field) is False


def test_all_switch_fields_tracked():
    resp = UnisettingResponse(
        ai_see=Switch(value=True),
        cruise_continue_sw=Switch(value=True),
        water_level_sw=Switch(value=True),
    )
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert "ai_see" in new_state.received_fields
    assert "cruise_continue_sw" in new_state.received_fields
    assert "water_level_sw" in new_state.received_fields


# --- Numerical field ---


def test_dust_full_remind_parsed():
    resp = UnisettingResponse(dust_full_remind=Numerical(value=5))
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.dust_full_remind == 5


def test_dust_full_remind_tracked():
    resp = UnisettingResponse(dust_full_remind=Numerical(value=3))
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert "dust_full_remind" in new_state.received_fields


# --- Unistate sub-fields ---


def test_unistate_mop_state():
    resp = UnisettingResponse(unistate=Unistate(mop_state=Switch(value=True)))
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.mop_state is True


def test_unistate_mop_holder_states():
    resp = UnisettingResponse(
        unistate=Unistate(
            mop_holder_state_l=Switch(value=True),
            mop_holder_state_r=Switch(value=False),
        )
    )
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.mop_holder_state_l is True
    assert new_state.mop_holder_state_r is False


def test_unistate_map_valid():
    resp = UnisettingResponse(unistate=Unistate(map_valid=Active(value=True)))
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.map_valid is True


def test_unistate_clean_strategy_version():
    resp = UnisettingResponse(unistate=Unistate(clean_strategy_version=42))
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.clean_strategy_version == 42


# --- WiFi data ---


def test_wifi_data_ssid():
    resp = UnisettingResponse(
        wifi_data=WifiData(ap=[WifiData.Ap(ssid="MyNetwork")])
    )
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.wifi_ap_ssid == "MyNetwork"


def test_wifi_data_frequency():
    resp = UnisettingResponse(
        wifi_data=WifiData(ap=[WifiData.Ap(frequency=WifiData.Ap.FREQ_5G)])
    )
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.wifi_frequency == int(WifiData.Ap.FREQ_5G)


def test_wifi_data_empty_ap_list():
    resp = UnisettingResponse(wifi_data=WifiData())
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.wifi_ap_ssid == ""
    assert new_state.wifi_frequency == 0


# --- Existing fields not broken ---


def test_existing_wifi_signal_still_works():
    resp = UnisettingResponse(ap_signal_strength=80)
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.wifi_signal == -60.0


def test_existing_child_lock_still_works():
    resp = UnisettingResponse(children_lock=Switch(value=True))
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.child_lock is True
