from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DEFAULT_DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.app_device_info_pb2 import DeviceInfo
from custom_components.robovac_mqtt.utils import encode_message


def _make_dps(info: DeviceInfo) -> dict:
    return {DEFAULT_DPS_MAP["APP_DEV_INFO"]: encode_message(info)}


def test_firmware_version_parsed():
    info = DeviceInfo(software="2.4.7.8")
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(info))
    assert new_state.firmware_version == "2.4.7.8"


def test_hardware_version_parsed():
    info = DeviceInfo(hardware=3)
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(info))
    assert new_state.hardware_version == 3


def test_product_name_parsed():
    info = DeviceInfo(product_name="RoboVac X10 Pro Omni")
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(info))
    assert new_state.product_name == "RoboVac X10 Pro Omni"


def test_video_sn_parsed():
    info = DeviceInfo(video_sn="CAM123")
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(info))
    assert new_state.video_sn == "CAM123"


def test_station_firmware_parsed():
    info = DeviceInfo(station=DeviceInfo.Station(software="1.0.0"))
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(info))
    assert new_state.station_firmware == "1.0.0"


def test_station_hardware_parsed():
    info = DeviceInfo(station=DeviceInfo.Station(hardware=7))
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(info))
    assert new_state.station_hardware == 7


def test_firmware_field_exists_in_vacuum_state():
    s = VacuumState()
    assert hasattr(s, "firmware_version")
    assert s.firmware_version == ""
