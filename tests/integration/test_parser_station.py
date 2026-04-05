from __future__ import annotations

from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.common_pb2 import Numerical
from custom_components.robovac_mqtt.proto.cloud.station_pb2 import (
    AutoActionCfg,
    StationResponse,
    WashCfg,
)
from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import WorkStatus
from custom_components.robovac_mqtt.utils import encode_message


def _station_dps(station: StationResponse) -> dict[str, str]:
    return {"173": encode_message(station)}


def _work_dps(ws: WorkStatus) -> dict[str, str]:
    return {"153": encode_message(ws)}


def test_idle_station_dock_status():
    station = StationResponse(
        status=StationResponse.StationStatus(
            connected=True,
            state=StationResponse.StationStatus.IDLE,
        ),
    )
    state, changes = update_state(VacuumState(), _station_dps(station))
    assert state.dock_status == "Idle"
    assert changes["dock_status"] == "Idle"


def test_washing_active_dock_status():
    station = StationResponse(
        status=StationResponse.StationStatus(
            connected=True,
            state=StationResponse.StationStatus.WASHING,
        ),
    )
    state, changes = update_state(VacuumState(), _station_dps(station))
    assert state.dock_status == "Washing"


def test_drying_active_dock_status():
    station = StationResponse(
        status=StationResponse.StationStatus(
            connected=True,
            state=StationResponse.StationStatus.DRYING,
        ),
    )
    state, changes = update_state(VacuumState(), _station_dps(station))
    assert state.dock_status == "Drying"


def test_emptying_dust_dock_status():
    station = StationResponse(
        status=StationResponse.StationStatus(
            connected=True,
            collecting_dust=True,
        ),
    )
    state, changes = update_state(VacuumState(), _station_dps(station))
    assert state.dock_status == "Emptying dust"


def test_clean_water_level_populated():
    station = StationResponse(
        status=StationResponse.StationStatus(connected=True),
        clean_water=Numerical(value=75),
    )
    state, changes = update_state(VacuumState(), _station_dps(station))
    assert state.station_clean_water == 75
    assert "station_clean_water" in changes


def test_auto_cfg_status_populated():
    station = StationResponse(
        status=StationResponse.StationStatus(connected=True),
        auto_cfg_status=AutoActionCfg(
            wash=WashCfg(cfg=WashCfg.STANDARD),
        ),
    )
    state, changes = update_state(VacuumState(), _station_dps(station))
    assert state.dock_auto_cfg is not None
    assert "dock_auto_cfg" in changes
    assert "wash" in state.dock_auto_cfg


def test_clear_water_adding_dock_status():
    station = StationResponse(
        status=StationResponse.StationStatus(
            connected=True,
            clear_water_adding=True,
        ),
    )
    state, _ = update_state(VacuumState(), _station_dps(station))
    assert state.dock_status == "Adding clean water"


def test_waste_water_recycling_dock_status():
    station = StationResponse(
        status=StationResponse.StationStatus(
            connected=True,
            waste_water_recycling=True,
        ),
    )
    state, _ = update_state(VacuumState(), _station_dps(station))
    assert state.dock_status == "Recycling waste water"


def test_cross_dps_work_status_and_station_washing():
    ws = WorkStatus(
        state=5,
        go_wash=WorkStatus.GoWash(mode=WorkStatus.GoWash.WASHING),
    )
    station = StationResponse(
        status=StationResponse.StationStatus(
            connected=True,
            state=StationResponse.StationStatus.WASHING,
        ),
    )
    dps: dict[str, str] = {}
    dps.update(_work_dps(ws))
    dps.update(_station_dps(station))
    state, changes = update_state(VacuumState(), dps)
    assert state.activity == "docked"
    assert state.dock_status == "Washing"


def test_dock_status_field_tracked():
    station = StationResponse(
        status=StationResponse.StationStatus(
            connected=True,
            state=StationResponse.StationStatus.IDLE,
        ),
    )
    state, _ = update_state(VacuumState(), _station_dps(station))
    assert "dock_status" in state.received_fields
