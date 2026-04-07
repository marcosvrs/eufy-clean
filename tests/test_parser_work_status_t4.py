"""Tests for 9 new WorkStatus proto field extractions in _process_work_status()."""

from __future__ import annotations

from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import WorkStatus
from tests.integration.helpers import make_dps_payload, make_work_status


def test_upgrading_parsed():
    ws = make_work_status(state=0, upgrading=WorkStatus.Upgrading(state=1))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.upgrading is True
    assert "upgrading" in state.received_fields


def test_upgrading_false_when_state_zero():
    ws = make_work_status(state=0, upgrading=WorkStatus.Upgrading(state=0))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.upgrading is False


def test_mapping_state_parsed():
    ws = make_work_status(state=5, mapping=WorkStatus.Mapping(state=1, mode=0))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.mapping_state == 1
    assert state.mapping_mode == 0
    assert "mapping_state" in state.received_fields


def test_relocating_parsed():
    ws = make_work_status(state=5, relocating=WorkStatus.Relocating(state=1))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.relocating is True
    assert "relocating" in state.received_fields


def test_relocating_false_when_state_zero():
    ws = make_work_status(state=5, relocating=WorkStatus.Relocating(state=0))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.relocating is False


def test_roller_brush_cleaning_parsed():
    ws = make_work_status(
        state=5,
        roller_brush_cleaning=WorkStatus.RollerBrushCleaning(state=1),
    )
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.roller_brush_cleaning is True
    assert "roller_brush_cleaning" in state.received_fields


def test_breakpoint_available_parsed():
    ws = make_work_status(state=7, breakpoint=WorkStatus.Breakpoint(state=1))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.breakpoint_available is True
    assert "breakpoint_available" in state.received_fields


def test_breakpoint_available_false_when_doing():
    ws = make_work_status(state=3, breakpoint=WorkStatus.Breakpoint(state=0))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.breakpoint_available is False


def test_station_work_status_with_dust_collection():
    ws = make_work_status(
        state=3,
        station=WorkStatus.Station(
            dust_collection_system=WorkStatus.Station.DustCollectionSystem(state=1),
        ),
    )
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.station_work_status == 1
    assert "station_work_status" in state.received_fields


def test_station_work_status_zero_without_dust_collection():
    ws = make_work_status(
        state=3,
        station=WorkStatus.Station(
            washing_drying_system=WorkStatus.Station.WashingDryingSystem(state=0),
        ),
    )
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.station_work_status == 0


def test_cruise_state_parsed():
    ws = make_work_status(
        state=5,
        cruisiing=WorkStatus.Cruisiing(state=1, mode=0),
    )
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.cruise_state == 1
    assert state.cruise_mode == 0
    assert "cruise_state" in state.received_fields


def test_smart_follow_parsed():
    ws = make_work_status(
        state=5,
        smart_follow=WorkStatus.SmartFollow(
            state=1, mode=0, elapsed_time=120, area=15,
        ),
    )
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.smart_follow_state == 1
    assert state.smart_follow_mode == 0
    assert state.smart_follow_elapsed == 120
    assert state.smart_follow_area == 15
    assert "smart_follow_state" in state.received_fields


def test_all_new_fields_in_vacuum_state():
    vs = VacuumState()
    new_fields = [
        "upgrading", "mapping_state", "mapping_mode", "relocating",
        "roller_brush_cleaning", "breakpoint_available", "station_work_status",
        "cruise_state", "cruise_mode", "smart_follow_state", "smart_follow_mode",
        "smart_follow_elapsed", "smart_follow_area",
    ]
    for f in new_fields:
        assert hasattr(vs, f), f"VacuumState missing field: {f}"
