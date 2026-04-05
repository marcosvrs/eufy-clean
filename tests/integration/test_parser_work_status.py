"""Protocol/contract tests for WorkStatus (DPS 153) parsing.

Expected values from const.py mapping tables + proto definitions.
A test failure = discovered bug in parser.py.
"""

from __future__ import annotations

from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.station_pb2 import StationResponse
from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import WorkStatus
from tests.integration.conftest import load_fixture
from tests.integration.helpers import (
    make_dps_payload,
    make_station_response,
    make_work_status,
)


def test_state_0_is_idle():
    ws = make_work_status(state=0)
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.activity == "idle"


def test_state_1_is_idle_sleep():
    ws = make_work_status(state=1)
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.activity == "idle"


def test_state_2_is_error():
    ws = make_work_status(state=2)
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.activity == "error"


def test_state_3_is_docked():
    """Real captured: WorkStatus state=CHARGING (docked and charging)."""
    fixture = load_fixture("mqtt/work_status/docked_charging.json")
    dps = fixture["dps"]
    state, _ = update_state(VacuumState(), dps)
    assert state.activity == "docked"


def test_state_4_is_cleaning():
    ws = make_work_status(state=4)
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.activity == "cleaning"


def test_state_5_no_station_is_cleaning():
    """Real captured: WorkStatus state=CLEANING, mode=SELECT_ROOM."""
    fixture = load_fixture("mqtt/work_status/cleaning_active.json")
    dps = fixture["dps"]
    state, _ = update_state(VacuumState(), dps)
    assert state.activity == "cleaning"


def test_state_7_is_returning():
    """Real captured: WorkStatus state=GO_HOME."""
    fixture = load_fixture("mqtt/work_status/returning.json")
    dps = fixture["dps"]
    state, _ = update_state(VacuumState(), dps)
    assert state.activity == "returning"


def test_state_5_station_washing_is_docked():
    """Real captured: WorkStatus state=CLEANING + go_wash.mode=WASHING."""
    fixture = load_fixture("mqtt/work_status/docked_washing.json")
    dps = fixture["dps"]
    state, _ = update_state(VacuumState(), dps)
    assert state.activity == "docked"
    assert state.dock_status in (
        "Washing",
        "Washing Mop",
        "Adding clean water",
        "Recycling waste water",
    ), f"dock_status should indicate dock washing activity, got {state.dock_status!r}"


def test_state_5_station_drying_is_docked():
    """Real captured: WorkStatus state=CLEANING + go_wash.mode=DRYING."""
    fixture = load_fixture("mqtt/work_status/docked_drying.json")
    dps = fixture["dps"]
    state, _ = update_state(VacuumState(), dps)
    assert state.activity == "docked"


def test_state_5_station_idle_is_cleaning():
    ws = make_work_status(state=5)
    station = make_station_response(
        status=StationResponse.StationStatus(state=0, connected=True),  # IDLE
    )
    dps = {**make_dps_payload("153", ws), **make_dps_payload("173", station)}
    state, _ = update_state(VacuumState(), dps)
    assert state.activity == "cleaning"


def test_trigger_source_app():
    """Real captured: WorkStatus state=CLEANING, mode=AUTO (app-triggered)."""
    fixture = load_fixture("mqtt/work_status/trigger_app.json")
    dps = fixture["dps"]
    state, _ = update_state(VacuumState(), dps)
    assert state.trigger_source == "app"


def test_trigger_source_button():
    ws = make_work_status(state=5, trigger=WorkStatus.Trigger(source=2))  # KEY
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.trigger_source == "button"


def test_trigger_source_schedule():
    ws = make_work_status(state=5, trigger=WorkStatus.Trigger(source=3))  # TIMING
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.trigger_source == "schedule"


def test_trigger_source_robot():
    ws = make_work_status(state=5, trigger=WorkStatus.Trigger(source=4))  # ROBOT
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.trigger_source == "robot"


def test_trigger_source_remote_control():
    ws = make_work_status(state=5, trigger=WorkStatus.Trigger(source=5))  # REMOTE_CTRL
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.trigger_source == "remote_control"


def test_trigger_inferred_from_app_mode():
    """Real captured: mode=SELECT_ROOM (1, in APP_TRIGGER_MODES) + no trigger → 'app'."""
    fixture = load_fixture("mqtt/work_status/trigger_missing_app_mode.json")
    dps = fixture["dps"]
    state, _ = update_state(VacuumState(), dps)
    assert state.trigger_source == "app"


def test_trigger_auto_mode_no_trigger_infers_app():
    """mode=AUTO (0, in APP_TRIGGER_MODES) + no trigger → 'app'."""
    ws = make_work_status(state=5, mode=WorkStatus.Mode(value=0))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.trigger_source == "app"


def test_charging_true_when_docked():
    """Real captured: WorkStatus state=CHARGING → charging=True."""
    fixture = load_fixture("mqtt/work_status/docked_charging.json")
    dps = fixture["dps"]
    state, _ = update_state(VacuumState(), dps)
    assert state.charging is True


def test_charging_false_when_cleaning():
    """Real captured: WorkStatus state=CLEANING → charging=False."""
    fixture = load_fixture("mqtt/work_status/cleaning_active.json")
    dps = fixture["dps"]
    state, _ = update_state(VacuumState(), dps)
    assert state.charging is False


def test_state_transition_idle_to_cleaning_to_returning_to_docked():
    state = VacuumState()

    ws = make_work_status(state=0)
    state, _ = update_state(state, make_dps_payload("153", ws))
    assert state.activity == "idle"

    # Real captured: cleaning (room select)
    fixture = load_fixture("mqtt/work_status/cleaning_active.json")
    state, _ = update_state(state, fixture["dps"])
    assert state.activity == "cleaning"

    # Real captured: returning
    fixture = load_fixture("mqtt/work_status/returning.json")
    state, _ = update_state(state, fixture["dps"])
    assert state.activity == "returning"

    # Real captured: docked charging
    fixture = load_fixture("mqtt/work_status/docked_charging.json")
    state, _ = update_state(state, fixture["dps"])
    assert state.activity == "docked"
    assert state.charging is True


def test_work_mode_auto():
    ws = make_work_status(state=5, mode=WorkStatus.Mode(value=0))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.work_mode == "Auto"


def test_work_mode_room():
    ws = make_work_status(state=5, mode=WorkStatus.Mode(value=1))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.work_mode == "Room"


def test_work_mode_zone():
    ws = make_work_status(state=5, mode=WorkStatus.Mode(value=2))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.work_mode == "Zone"


def test_work_mode_spot():
    ws = make_work_status(state=5, mode=WorkStatus.Mode(value=3))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.work_mode == "Spot"


def test_work_mode_fast_mapping():
    ws = make_work_status(state=4, mode=WorkStatus.Mode(value=4))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.work_mode == "Fast Mapping"


def test_work_mode_scene():
    ws = make_work_status(state=5, mode=WorkStatus.Mode(value=8))
    dps = make_dps_payload("153", ws)
    state, _ = update_state(VacuumState(), dps)
    assert state.work_mode == "Scene"


def test_status_code_reflects_raw_state():
    """Real captured: WorkStatus state=CLEANING → status_code=5."""
    fixture = load_fixture("mqtt/work_status/cleaning_active.json")
    dps = fixture["dps"]
    state, _ = update_state(VacuumState(), dps)
    assert state.status_code == 5


def test_status_code_docked():
    """Real captured: WorkStatus state=CHARGING → status_code=3."""
    fixture = load_fixture("mqtt/work_status/docked_charging.json")
    dps = fixture["dps"]
    state, _ = update_state(VacuumState(), dps)
    assert state.status_code == 3


def test_trigger_all_app_modes_infer_app():
    """All EUFY_CLEAN_APP_TRIGGER_MODES values (0-9) infer 'app' without trigger field."""
    for mode_val in range(0, 10):
        ws = make_work_status(state=5, mode=WorkStatus.Mode(value=mode_val))
        dps = make_dps_payload("153", ws)
        state, _ = update_state(VacuumState(), dps)
        assert state.trigger_source == "app", (
            f"mode={mode_val}: expected trigger_source='app', "
            f"got {state.trigger_source!r}"
        )


# --- New fixture-backed tests for additional captured WorkStatus variants ---


def test_cleaning_room_select_v2_is_cleaning():
    """Real captured: WorkStatus state=CLEANING, mode=SELECT_ROOM, no charging field."""
    fixture = load_fixture("mqtt/work_status/cleaning_room_select_v2.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "cleaning"
    assert state.work_mode == "Room"


def test_paused_room_select_is_paused():
    """Real captured: WorkStatus state=CLEANING, mode=SELECT_ROOM, cleaning.state=PAUSED."""
    fixture = load_fixture("mqtt/work_status/paused_room_select.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "paused"
    assert state.task_status == "Paused"
    assert state.work_mode == "Room"


def test_returning_v2_is_returning():
    """Real captured: WorkStatus state=GO_HOME, charging.state=2, go_home.mode=10."""
    fixture = load_fixture("mqtt/work_status/returning_v2.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "returning"


def test_returning_charging_is_returning():
    """Real captured: WorkStatus state=GO_HOME with charging.state=0 (Doing)."""
    fixture = load_fixture("mqtt/work_status/returning_charging.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "returning"


def test_docked_washing_water_emptying():
    """Real captured: WorkStatus WASHING + station.water_injection_system.state=EMPTYING."""
    fixture = load_fixture("mqtt/work_status/docked_washing_water_emptying.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "docked"
    assert state.dock_status == "Recycling waste water"


def test_docked_washing_water_injection():
    """Real captured: WorkStatus WASHING + station.water_injection_system={} (adding water)."""
    fixture = load_fixture("mqtt/work_status/docked_washing_water_injection.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "docked"
    assert state.dock_status == "Adding clean water"


def test_docked_washing_wds():
    """Real captured: WorkStatus WASHING + station.washing_drying_system={} (wash via WDS)."""
    fixture = load_fixture("mqtt/work_status/docked_washing_wds.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "docked"
    assert state.dock_status == "Washing"


def test_docked_charging_dust_collecting():
    """Real captured: WorkStatus state=CHARGING + station.dust_collection_system={}."""
    fixture = load_fixture("mqtt/work_status/docked_charging_dust_collecting.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "docked"
    assert state.dock_status == "Emptying dust"


def test_cleaning_auto_fixture():
    """Real captured: WorkStatus state=CLEANING, mode=AUTO (with charging field)."""
    fixture = load_fixture("mqtt/work_status/cleaning_auto.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "cleaning"
    assert state.work_mode == "Auto"


def test_cleaning_auto_v2_fixture():
    """Real captured: WorkStatus state=CLEANING, mode=AUTO (without charging field)."""
    fixture = load_fixture("mqtt/work_status/cleaning_auto_v2.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "cleaning"
    assert state.work_mode == "Auto"


def test_paused_auto_is_paused():
    """Real captured: WorkStatus state=CLEANING, mode=AUTO, cleaning.state=PAUSED."""
    fixture = load_fixture("mqtt/work_status/paused_auto.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "paused"
    assert state.task_status == "Paused"
    assert state.work_mode == "Auto"


def test_cleaning_zone_select():
    """Real captured: WorkStatus state=CLEANING, mode=SELECT_ZONE."""
    fixture = load_fixture("mqtt/work_status/cleaning_zone_select.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "cleaning"
    assert state.work_mode == "Zone"


def test_cleaning_zone_select_v2():
    """Real captured: WorkStatus state=CLEANING, mode=SELECT_ZONE (no charging field)."""
    fixture = load_fixture("mqtt/work_status/cleaning_zone_select_v2.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "cleaning"
    assert state.work_mode == "Zone"


def test_cleaning_positioning_fixture():
    """Real captured: state=CLEANING + cleaning.state=PAUSED (positioning phase).

    BUG: Parser treats cleaning.state=PAUSED as activity='paused', but on the X10 Pro
    Omni this state represents positioning/preparing (state=4/FAST_MAPPING is never sent).
    """
    fixture = load_fixture("mqtt/work_status/cleaning_positioning.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    # Parser bug: real positioning appears as paused (cleaning.state=PAUSED)
    assert state.activity == "paused"
    assert state.task_status == "Paused"


def test_error_fixture():
    """Real captured: WorkStatus state=FAULT (2), mode=SELECT_ZONE — error during zone clean."""
    fixture = load_fixture("mqtt/work_status/error.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "error"
    assert state.work_mode == "Zone"


def test_idle_sleep_fixture():
    fixture = load_fixture("mqtt/work_status/idle_sleep.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "idle"


def test_idle_standby_fixture():
    """Real captured: WorkStatus state=STANDBY (0) — real standby after returning to dock."""
    fixture = load_fixture("mqtt/work_status/idle_standby.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "idle"


def test_trigger_button_fixture():
    """Real captured: mode=SPOT (physical button starts spot clean).

    Note: trigger.source is NEVER set on X10 Pro Omni.
    The "button" trigger is identified by mode=SPOT, not trigger.source=2.
    Since mode=SPOT(3) is in APP_TRIGGER_MODES, trigger_source infers as 'app'.
    """
    fixture = load_fixture("mqtt/work_status/trigger_button.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "cleaning"
    assert state.work_mode == "Spot"
    # trigger.source not set on this device; mode 3 (SPOT) is in APP_TRIGGER_MODES
    assert state.trigger_source == "app"


def test_trigger_schedule_fixture():
    """Real captured: scheduled scene clean — cleaning.scheduled_task=true.

    Note: trigger.source is NEVER set on X10 Pro Omni.
    Schedule detection relies on cleaning.scheduled_task=true in WorkStatus proto.
    """
    fixture = load_fixture("mqtt/work_status/trigger_schedule.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "cleaning"
    assert state.work_mode == "Scene"
    # Parser detects cleaning.scheduled_task=true → trigger_source="schedule"
    assert state.trigger_source == "schedule"


def test_scene_clean_mode():
    """Real captured: WorkStatus mode=SCENE (8), state=CLEANING — scene clean in progress."""
    fixture = load_fixture("mqtt/work_status/scene_clean.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "cleaning"
    assert state.work_mode == "Scene"
    assert state.task_status == "Cleaning"


def test_scene_clean_washing():
    """Real captured: WorkStatus mode=SCENE (8), go_wash=WASHING — docked for mid-clean wash.

    The parser correctly detects go_wash.mode=WASHING and overrides state=5 to activity='docked'.
    """
    fixture = load_fixture("mqtt/work_status/scene_clean_washing.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "docked"
    assert state.work_mode == "Scene"
    assert state.dock_status == "Recycling waste water"


def test_remote_ctrl_state():
    """Real captured: WorkStatus state=REMOTE_CTRL (state=6) — RC joystick mode.

    Parser maps state=6 to activity='cleaning' (unmapped state defaults to cleaning).
    """
    fixture = load_fixture("mqtt/work_status/remote_ctrl.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "cleaning"
    assert state.status_code == 6


def test_fast_mapping_state():
    """Real captured: WorkStatus state=4, mode=4 (FAST_MAPPING) — map scan without cleaning."""
    fixture = load_fixture("mqtt/work_status/fast_mapping.json")
    state, _ = update_state(VacuumState(), fixture["dps"])
    assert state.activity == "cleaning"
    assert state.work_mode == "Fast Mapping"
    assert state.status_code == 4
