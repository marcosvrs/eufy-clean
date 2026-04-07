from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DEFAULT_DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.clean_param_pb2 import (
    CleanParam,
    CleanParamRequest,
)
from custom_components.robovac_mqtt.utils import encode_message


def _make_dps(req: CleanParamRequest) -> dict:
    return {DEFAULT_DPS_MAP["CLEANING_PARAMETERS"]: encode_message(req)}


def test_clean_times_parsed():
    param = CleanParam(clean_times=2)
    req = CleanParamRequest(clean_param=param)
    state = VacuumState()

    new_state, _ = update_state(state, _make_dps(req))

    assert new_state.clean_times == 2


def test_clean_times_default_one():
    assert VacuumState().clean_times == 1


def test_clean_times_in_received_fields():
    param = CleanParam(clean_times=3)
    req = CleanParamRequest(clean_param=param)
    state = VacuumState()

    new_state, _ = update_state(state, _make_dps(req))

    assert "clean_times" in new_state.received_fields
