"""Tests for T14 (unistate entities) and T15 (wifi_data entities)."""

from unittest.mock import MagicMock

from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DEFAULT_DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.common_pb2 import Active, Switch
from custom_components.robovac_mqtt.proto.cloud.unisetting_pb2 import (
    UnisettingResponse,
    Unistate,
    WifiData,
)
from custom_components.robovac_mqtt.utils import encode_message


def _make_dps(resp: UnisettingResponse) -> dict:
    return {DEFAULT_DPS_MAP["UNSETTING"]: encode_message(resp)}


# --- T14: Unistate parser → model ---


def test_live_map_state_bits_parsed():
    resp = UnisettingResponse(unistate=Unistate(live_map=Unistate.LiveMap(state_bits=5)))
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.live_map_state_bits == 5
    assert "live_map_state_bits" in new_state.received_fields


def test_custom_clean_mode_parsed():
    resp = UnisettingResponse(unistate=Unistate(custom_clean_mode=Switch(value=True)))
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.custom_clean_mode is True
    assert "custom_clean_mode" in new_state.received_fields


def test_unistate_all_fields_together():
    resp = UnisettingResponse(
        unistate=Unistate(
            mop_state=Switch(value=True),
            mop_holder_state_l=Switch(value=True),
            mop_holder_state_r=Switch(value=False),
            map_valid=Active(value=True),
            live_map=Unistate.LiveMap(state_bits=3),
            clean_strategy_version=7,
            custom_clean_mode=Switch(value=False),
        )
    )
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.mop_state is True
    assert new_state.mop_holder_state_l is True
    assert new_state.mop_holder_state_r is False
    assert new_state.map_valid is True
    assert new_state.live_map_state_bits == 3
    assert new_state.clean_strategy_version == 7
    assert new_state.custom_clean_mode is False


def test_unistate_fields_tracked():
    resp = UnisettingResponse(
        unistate=Unistate(
            mop_state=Switch(value=True),
            live_map=Unistate.LiveMap(state_bits=1),
        )
    )
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert "mop_state" in new_state.received_fields
    assert "live_map_state_bits" in new_state.received_fields


def test_model_has_live_map_and_custom_clean_mode():
    s = VacuumState()
    assert s.live_map_state_bits == 0
    assert s.custom_clean_mode is False


# --- T15: WiFi data parser → model ---


def test_wifi_connection_result_parsed():
    resp = UnisettingResponse(
        wifi_data=WifiData(ap=[WifiData.Ap(
            connection=WifiData.Ap.Connection(result=WifiData.Ap.Connection.OK, timestamp=1700000000)
        )])
    )
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.wifi_connection_result == 0
    assert new_state.wifi_connection_timestamp == 1700000000


def test_wifi_connection_password_error():
    resp = UnisettingResponse(
        wifi_data=WifiData(ap=[WifiData.Ap(
            connection=WifiData.Ap.Connection(result=WifiData.Ap.Connection.PASSWD_ERR, timestamp=1700000001)
        )])
    )
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.wifi_connection_result == 1
    assert new_state.wifi_connection_timestamp == 1700000001


def test_wifi_connection_tracked():
    resp = UnisettingResponse(
        wifi_data=WifiData(ap=[WifiData.Ap(
            ssid="TestNet",
            frequency=WifiData.Ap.FREQ_5G,
            connection=WifiData.Ap.Connection(result=WifiData.Ap.Connection.OK, timestamp=100),
        )])
    )
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert "wifi_ap_ssid" in new_state.received_fields
    assert "wifi_frequency" in new_state.received_fields
    assert "wifi_connection_result" in new_state.received_fields
    assert "wifi_connection_timestamp" in new_state.received_fields


def test_wifi_frequency_2_4g():
    resp = UnisettingResponse(
        wifi_data=WifiData(ap=[WifiData.Ap(frequency=WifiData.Ap.FREQ_2_4G)])
    )
    new_state, _ = update_state(VacuumState(), _make_dps(resp))
    assert new_state.wifi_frequency == 0


def test_model_has_wifi_connection_fields():
    s = VacuumState()
    assert s.wifi_connection_result == 0
    assert s.wifi_connection_timestamp == 0


# --- T14: Entity availability gating ---


def _mock_coordinator(received: list[str] | None = None) -> MagicMock:
    coord = MagicMock()
    coord.device_id = "test"
    coord.device_name = "TestVac"
    state = VacuumState()
    if received:
        state = VacuumState(received_fields=set(received))
    coord.data = state
    coord.device_info = {"identifiers": {("robovac_mqtt", "test")}}
    coord.supported_dps = {"UNSETTING"}
    return coord


def test_live_map_binary_sensor_availability():
    from custom_components.robovac_mqtt.binary_sensor import RoboVacBinarySensor

    coord = _mock_coordinator(received=["live_map_state_bits"])
    coord.data = VacuumState(
        live_map_state_bits=5,
        received_fields={"live_map_state_bits"},
    )
    bs = RoboVacBinarySensor(
        coord, "live_map", "Live Map",
        lambda s: bool(s.live_map_state_bits),
        availability_fn=lambda s: "live_map_state_bits" in s.received_fields,
    )
    assert bs.is_on is True


def test_live_map_binary_sensor_off_when_zero():
    from custom_components.robovac_mqtt.binary_sensor import RoboVacBinarySensor

    coord = _mock_coordinator(received=["live_map_state_bits"])
    coord.data = VacuumState(
        live_map_state_bits=0,
        received_fields={"live_map_state_bits"},
    )
    bs = RoboVacBinarySensor(
        coord, "live_map", "Live Map",
        lambda s: bool(s.live_map_state_bits),
        availability_fn=lambda s: "live_map_state_bits" in s.received_fields,
    )
    assert bs.is_on is False
