"""Adversarial / edge-case tests for parser robustness."""

from __future__ import annotations

import base64

from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState

from .helpers import make_dps_payload, make_vacuum_state


class TestMalformedInput:

    def test_empty_dps_dict_leaves_state_unchanged(self):
        initial = VacuumState()
        result, changes = update_state(initial, {})
        assert result.activity == initial.activity
        assert result.battery_level == initial.battery_level
        assert result.fan_speed == initial.fan_speed

    def test_unknown_dps_key_does_not_crash(self):
        state, changes = update_state(VacuumState(), {"999": "some_value"})
        assert state is not None
        assert state.raw_dps.get("999") == "some_value"

    def test_invalid_base64_work_status_no_crash(self):
        dps = {DPS_MAP["WORK_STATUS"]: "NOT-VALID-BASE64!!!"}
        state, changes = update_state(VacuumState(), dps)
        assert state is not None
        assert state.activity == "idle"

    def test_truncated_protobuf_work_status_no_crash(self):
        truncated_b64 = base64.b64encode(b"\x08\x05\x10").decode()
        dps = {DPS_MAP["WORK_STATUS"]: truncated_b64}
        state, changes = update_state(VacuumState(), dps)
        assert state is not None

    def test_invalid_base64_station_status_no_crash(self):
        dps = {DPS_MAP["STATION_STATUS"]: "~~~bad~~~"}
        state, changes = update_state(VacuumState(), dps)
        assert state is not None

    def test_none_value_battery_level_no_crash(self):
        dps = {DPS_MAP["BATTERY_LEVEL"]: None}
        initial = make_vacuum_state(battery_level=50)
        state, changes = update_state(initial, dps)
        assert state is not None

    def test_none_value_work_status_no_crash(self):
        dps = {DPS_MAP["WORK_STATUS"]: None}
        state, changes = update_state(VacuumState(), dps)
        assert state is not None


class TestMissingOptionalFields:

    def test_work_status_without_station_field(self):
        from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import (
            WorkStatus,
        )

        ws = WorkStatus(state=5)
        dps = make_dps_payload(DPS_MAP["WORK_STATUS"], ws)
        state, changes = update_state(VacuumState(), dps)
        assert state.activity == "cleaning"

    def test_work_status_without_trigger_field(self):
        from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import (
            WorkStatus,
        )

        ws = WorkStatus(state=5)
        dps = make_dps_payload(DPS_MAP["WORK_STATUS"], ws)
        state, changes = update_state(VacuumState(), dps)
        assert state.trigger_source == "unknown"

    def test_work_status_without_mode_field(self):
        from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import (
            WorkStatus,
        )

        ws = WorkStatus(state=3)
        dps = make_dps_payload(DPS_MAP["WORK_STATUS"], ws)
        state, changes = update_state(VacuumState(), dps)
        assert state is not None
        assert state.activity == "docked"


class TestBoundaryValues:

    def test_battery_zero(self):
        dps = {DPS_MAP["BATTERY_LEVEL"]: "0"}
        state, changes = update_state(VacuumState(), dps)
        assert state.battery_level == 0

    def test_battery_hundred(self):
        dps = {DPS_MAP["BATTERY_LEVEL"]: "100"}
        state, changes = update_state(VacuumState(), dps)
        assert state.battery_level == 100

    def test_battery_out_of_range_high(self):
        dps = {DPS_MAP["BATTERY_LEVEL"]: "999"}
        state, changes = update_state(VacuumState(), dps)
        assert state is not None
        assert state.battery_level == 999

    def test_battery_as_integer(self):
        dps = {DPS_MAP["BATTERY_LEVEL"]: 42}
        state, changes = update_state(VacuumState(), dps)
        assert state.battery_level == 42


class TestRapidUpdates:

    def test_ten_rapid_battery_updates_last_write_wins(self):
        state = VacuumState()
        for i in range(10):
            state, _ = update_state(state, {DPS_MAP["BATTERY_LEVEL"]: str(i * 10)})
        assert state.battery_level == 90

    def test_rapid_mixed_dps_messages(self):
        state = VacuumState()
        for i in range(5):
            state, _ = update_state(
                state,
                {
                    DPS_MAP["BATTERY_LEVEL"]: str(50 + i),
                    DPS_MAP["FIND_ROBOT"]: "true" if i % 2 == 0 else "false",
                },
            )
        assert state.battery_level == 54
        assert state.find_robot is True


class TestConcurrentDpsKeys:

    def test_work_status_and_battery_in_same_message(self):
        from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import (
            WorkStatus,
        )

        ws = WorkStatus(state=5)
        dps = make_dps_payload(DPS_MAP["WORK_STATUS"], ws)
        dps[DPS_MAP["BATTERY_LEVEL"]] = "73"
        state, changes = update_state(VacuumState(), dps)
        assert state.activity == "cleaning"
        assert state.battery_level == 73

    def test_battery_and_find_robot_in_same_message(self):
        dps = {
            DPS_MAP["BATTERY_LEVEL"]: "88",
            DPS_MAP["FIND_ROBOT"]: "true",
        }
        state, changes = update_state(VacuumState(), dps)
        assert state.battery_level == 88
        assert state.find_robot is True


class TestReceivedFieldsTracking:

    def test_battery_tracked_in_received_fields(self):
        dps = {DPS_MAP["BATTERY_LEVEL"]: "75"}
        state, changes = update_state(VacuumState(), dps)
        assert "battery_level" in state.received_fields

    def test_received_fields_grow_over_multiple_messages(self):
        state = VacuumState()

        state, _ = update_state(state, {DPS_MAP["BATTERY_LEVEL"]: "50"})
        assert "battery_level" in state.received_fields
        fields_after_first = len(state.received_fields)

        state, _ = update_state(state, {DPS_MAP["CLEAN_SPEED"]: "1"})
        assert "fan_speed" in state.received_fields
        assert "battery_level" in state.received_fields
        assert len(state.received_fields) >= fields_after_first

    def test_received_fields_never_shrink(self):
        state = VacuumState()

        state, _ = update_state(state, {DPS_MAP["BATTERY_LEVEL"]: "80"})
        assert "battery_level" in state.received_fields

        state, _ = update_state(state, {DPS_MAP["FIND_ROBOT"]: "false"})
        assert "battery_level" in state.received_fields


class TestPlainDpsHandling:

    def test_clean_speed_plain_int(self):
        dps = {DPS_MAP["CLEAN_SPEED"]: "1"}
        state, changes = update_state(VacuumState(), dps)
        assert state.fan_speed == "Standard"

    def test_clean_speed_as_actual_int(self):
        dps = {DPS_MAP["CLEAN_SPEED"]: 0}
        state, changes = update_state(VacuumState(), dps)
        assert state.fan_speed == "Quiet"

    def test_find_robot_plain_bool_string(self):
        dps = {DPS_MAP["FIND_ROBOT"]: "true"}
        state, changes = update_state(VacuumState(), dps)
        assert state.find_robot is True

        dps2 = {DPS_MAP["FIND_ROBOT"]: "false"}
        state2, _ = update_state(state, dps2)
        assert state2.find_robot is False

    def test_clean_speed_out_of_range_index(self):
        dps = {DPS_MAP["CLEAN_SPEED"]: "99"}
        state, changes = update_state(VacuumState(), dps)
        assert state is not None
        assert isinstance(state.fan_speed, str)


class TestRawDpsStorage:

    def test_known_unprocessed_dps_stored_in_raw(self):
        dps = {"155": "some_direction_data"}
        state, changes = update_state(VacuumState(), dps)
        assert state.raw_dps["155"] == "some_direction_data"

    def test_unknown_dps_stored_in_raw(self):
        dps = {"888": "mystery_value"}
        state, changes = update_state(VacuumState(), dps)
        assert state.raw_dps["888"] == "mystery_value"

    def test_raw_dps_accumulates_across_updates(self):
        state = VacuumState()
        state, _ = update_state(state, {"999": "first"})
        state, _ = update_state(state, {"998": "second"})
        assert state.raw_dps["999"] == "first"
        assert state.raw_dps["998"] == "second"
