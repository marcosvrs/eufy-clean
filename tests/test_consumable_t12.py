from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.consumable_pb2 import (
    ConsumableResponse,
    ConsumableRuntime,
)
from custom_components.robovac_mqtt.utils import encode_message


def test_consumable_last_time_is_parsed_to_vacuum_state():
    response = ConsumableResponse(
        runtime=ConsumableRuntime(
            last_time=123456,
            dustbag=ConsumableRuntime.Duration(duration=70),
        )
    )

    state = VacuumState()
    new_state, _ = update_state(
        state, {DPS_MAP["ACCESSORIES_STATUS"]: encode_message(response)}
    )

    assert new_state.consumable_last_time == 123456
    assert new_state.accessories.dustbag_usage == 70


def test_consumable_last_time_defaults_to_zero_when_missing():
    response = ConsumableResponse(runtime=ConsumableRuntime())

    state = VacuumState(consumable_last_time=99)
    new_state, _ = update_state(
        state, {DPS_MAP["ACCESSORIES_STATUS"]: encode_message(response)}
    )

    assert new_state.consumable_last_time == 99


def test_new_consumable_accessory_usage_fields_are_parsed():
    response = ConsumableResponse(
        runtime=ConsumableRuntime(
            dustbag=ConsumableRuntime.Duration(duration=11),
            dirty_watertank=ConsumableRuntime.Duration(duration=22),
            dirty_waterfilter=ConsumableRuntime.Duration(duration=33),
        )
    )

    state = VacuumState()
    new_state, _ = update_state(
        state, {DPS_MAP["ACCESSORIES_STATUS"]: encode_message(response)}
    )

    accessories = new_state.accessories
    assert accessories.dustbag_usage == 11
    assert accessories.dirty_watertank_usage == 22
    assert accessories.dirty_waterfilter_usage == 33
