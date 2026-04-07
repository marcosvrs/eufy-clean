from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DEFAULT_DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.error_code_pb2 import ErrorCode
from custom_components.robovac_mqtt.utils import encode_message


def _make_dps(error: ErrorCode) -> dict:
    return {DEFAULT_DPS_MAP["ERROR_CODE"]: encode_message(error)}


def test_single_error_backward_compat() -> None:
    error = ErrorCode(warn=[101])
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(error))
    assert new_state.error_code == 101
    assert new_state.error_codes_all == [101]
    assert new_state.error_message
    assert len(new_state.error_messages_all) == 1


def test_multiple_errors_captured() -> None:
    error = ErrorCode(warn=[101, 202])
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(error))
    assert new_state.error_code == 101
    assert new_state.error_codes_all == [101, 202]
    assert len(new_state.error_messages_all) == 2


def test_no_errors_clears_state() -> None:
    error = ErrorCode(warn=[])
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(error))
    assert new_state.error_code == 0
    assert new_state.error_message == ""
    assert new_state.error_codes_all == []
    assert new_state.error_messages_all == []


def test_error_codes_all_in_model() -> None:
    state = VacuumState()
    assert state.error_codes_all == []
    assert state.error_messages_all == []
