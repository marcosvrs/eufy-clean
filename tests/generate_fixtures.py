#!/usr/bin/env python3
"""Generate synthetic fixture files for all DPS key types.

Uses real protobuf serialization via encode_message() to produce valid base64-encoded
DPS values. Run from the project root:

    python -m tests.generate_fixtures
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import types

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Stub the HA-dependent parent packages so proto relative imports resolve
# without triggering homeassistant imports from __init__.py.
_CC = os.path.join(PROJECT_ROOT, "custom_components")
_RM = os.path.join(_CC, "robovac_mqtt")
_PROTO = os.path.join(_RM, "proto")
_CLOUD = os.path.join(_PROTO, "cloud")

for pkg_name, pkg_path in (
    ("custom_components", _CC),
    ("custom_components.robovac_mqtt", _RM),
    ("custom_components.robovac_mqtt.proto", _PROTO),
    ("custom_components.robovac_mqtt.proto.cloud", _CLOUD),
):
    if pkg_name not in sys.modules:
        mod = types.ModuleType(pkg_name)
        mod.__path__ = [pkg_path]
        mod.__package__ = pkg_name
        sys.modules[pkg_name] = mod

# encode_message also needs the stub workaround (utils.py has no HA imports)
import importlib.util

from custom_components.robovac_mqtt.proto.cloud.clean_param_pb2 import (  # noqa: E402
    CleanCarpet,
    CleanExtent,
    CleanParam,
    CleanParamRequest,
    CleanParamResponse,
    CleanType,
    Fan,
    MopMode,
)
from custom_components.robovac_mqtt.proto.cloud.clean_statistics_pb2 import (  # noqa: E402
    CleanStatistics,
)
from custom_components.robovac_mqtt.proto.cloud.common_pb2 import (  # noqa: E402
    RoomScene,
    Switch,
)
from custom_components.robovac_mqtt.proto.cloud.consumable_pb2 import (  # noqa: E402
    ConsumableResponse,
    ConsumableRuntime,
)
from custom_components.robovac_mqtt.proto.cloud.error_code_pb2 import ErrorCode  # noqa: E402
from custom_components.robovac_mqtt.proto.cloud.scene_pb2 import (  # noqa: E402
    SceneInfo,
    SceneResponse,
)
from custom_components.robovac_mqtt.proto.cloud.station_pb2 import StationResponse  # noqa: E402
from custom_components.robovac_mqtt.proto.cloud.stream_pb2 import RoomParams  # noqa: E402
from custom_components.robovac_mqtt.proto.cloud.universal_data_pb2 import (  # noqa: E402
    UniversalDataResponse,
)
from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import WorkStatus  # noqa: E402

_utils_spec = importlib.util.spec_from_file_location(
    "robovac_utils",
    os.path.join(PROJECT_ROOT, "custom_components", "robovac_mqtt", "utils.py"),
)
_utils_mod = importlib.util.module_from_spec(_utils_spec)
_utils_spec.loader.exec_module(_utils_mod)
encode_message = _utils_mod.encode_message

FIXTURES_DIR = os.path.join(PROJECT_ROOT, "tests", "fixtures")


def write_fixture(path: str, data: dict) -> None:
    """Write a fixture JSON file."""
    full_path = os.path.join(FIXTURES_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"  wrote {path}")


# ──────────────────────────────────────────────────────────────
# WORK STATUS FIXTURES (DPS 153)
# ──────────────────────────────────────────────────────────────


def gen_work_status_idle_standby():
    ws = WorkStatus(state=WorkStatus.STANDBY)
    write_fixture(
        "mqtt/work_status/idle_standby.json",
        {
            "description": "WorkStatus state=0 (idle/standby)",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "idle",
                "task_status": "Idle",
                "charging": False,
                "trigger_source": "unknown",
            },
        },
    )


def gen_work_status_idle_sleep():
    ws = WorkStatus(state=WorkStatus.SLEEP)
    write_fixture(
        "mqtt/work_status/idle_sleep.json",
        {
            "description": "WorkStatus state=1 (idle/sleep)",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "idle",
                "task_status": "Idle",
                "charging": False,
                "trigger_source": "unknown",
            },
        },
    )


def gen_work_status_error():
    ws = WorkStatus(state=WorkStatus.FAULT)
    write_fixture(
        "mqtt/work_status/error.json",
        {
            "description": "WorkStatus state=2 (fault/error)",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "error",
                "task_status": "Error",
                "charging": False,
                "trigger_source": "unknown",
            },
        },
    )


def gen_work_status_docked_charging():
    ws = WorkStatus(state=WorkStatus.CHARGING)
    ws.charging.state = WorkStatus.Charging.DOING
    write_fixture(
        "mqtt/work_status/docked_charging.json",
        {
            "description": "WorkStatus state=3 (charging), charging.state=DOING",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "docked",
                "task_status": "Completed",
                "charging": True,
                "trigger_source": "unknown",
            },
        },
    )


def gen_work_status_cleaning_positioning():
    ws = WorkStatus(state=WorkStatus.FAST_MAPPING)
    ws.mode.value = WorkStatus.Mode.AUTO
    write_fixture(
        "mqtt/work_status/cleaning_positioning.json",
        {
            "description": "WorkStatus state=4 (positioning/fast_mapping)",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "cleaning",
                "task_status": "Positioning",
                "charging": False,
                "work_mode": "Auto",
            },
        },
    )


def gen_work_status_cleaning_active():
    ws = WorkStatus(state=WorkStatus.CLEANING)
    ws.mode.value = WorkStatus.Mode.AUTO
    ws.cleaning.state = WorkStatus.Cleaning.DOING
    ws.trigger.source = WorkStatus.Trigger.APP
    write_fixture(
        "mqtt/work_status/cleaning_active.json",
        {
            "description": "WorkStatus state=5 (active cleaning), no station activity",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "cleaning",
                "task_status": "Cleaning",
                "charging": False,
                "trigger_source": "app",
                "work_mode": "Auto",
            },
        },
    )


def gen_work_status_docked_washing():
    """WorkStatus state=5 + station washing. Both DPS 153 and 173."""
    ws = WorkStatus(state=WorkStatus.CLEANING)
    ws.go_wash.state = WorkStatus.GoWash.DOING
    ws.go_wash.mode = WorkStatus.GoWash.WASHING
    ws.station.washing_drying_system.state = (
        WorkStatus.Station.WashingDryingSystem.WASHING
    )

    sr = StationResponse()
    sr.status.connected = True
    sr.status.state = StationResponse.StationStatus.WASHING

    write_fixture(
        "mqtt/work_status/docked_washing.json",
        {
            "description": "WorkStatus state=5 + station washing (cross-DPS: 153+173)",
            "dps": {
                "153": encode_message(ws),
                "173": encode_message(sr),
            },
            "expected_state": {
                "activity": "docked",
                "task_status": "Washing Mop",
                "dock_status": "Washing",
                "charging": False,
            },
        },
    )


def gen_work_status_docked_drying():
    """WorkStatus state=5 + station drying. Both DPS 153 and 173."""
    ws = WorkStatus(state=WorkStatus.CLEANING)
    ws.go_wash.state = WorkStatus.GoWash.DOING
    ws.go_wash.mode = WorkStatus.GoWash.DRYING
    ws.station.washing_drying_system.state = (
        WorkStatus.Station.WashingDryingSystem.DRYING
    )

    sr = StationResponse()
    sr.status.connected = True
    sr.status.state = StationResponse.StationStatus.DRYING

    write_fixture(
        "mqtt/work_status/docked_drying.json",
        {
            "description": "WorkStatus state=5 + station drying (cross-DPS: 153+173)",
            "dps": {
                "153": encode_message(ws),
                "173": encode_message(sr),
            },
            "expected_state": {
                "activity": "docked",
                "task_status": "Completed",
                "dock_status": "Drying",
                "charging": False,
            },
        },
    )


def gen_work_status_returning():
    ws = WorkStatus(state=WorkStatus.GO_HOME)
    ws.go_home.state = WorkStatus.GoHome.DOING
    ws.go_home.mode = WorkStatus.GoHome.COMPLETE_TASK
    write_fixture(
        "mqtt/work_status/returning.json",
        {
            "description": "WorkStatus state=7 (go home / returning)",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "returning",
                "task_status": "Returning",
                "charging": False,
            },
        },
    )


def gen_work_status_trigger_app():
    ws = WorkStatus(state=WorkStatus.CLEANING)
    ws.mode.value = WorkStatus.Mode.AUTO
    ws.cleaning.state = WorkStatus.Cleaning.DOING
    ws.trigger.source = WorkStatus.Trigger.APP
    write_fixture(
        "mqtt/work_status/trigger_app.json",
        {
            "description": "WorkStatus with trigger.source=1 (APP)",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "cleaning",
                "trigger_source": "app",
                "work_mode": "Auto",
            },
        },
    )


def gen_work_status_trigger_button():
    ws = WorkStatus(state=WorkStatus.CLEANING)
    ws.mode.value = WorkStatus.Mode.AUTO
    ws.cleaning.state = WorkStatus.Cleaning.DOING
    ws.trigger.source = WorkStatus.Trigger.KEY
    write_fixture(
        "mqtt/work_status/trigger_button.json",
        {
            "description": "WorkStatus with trigger.source=2 (KEY/button)",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "cleaning",
                "trigger_source": "button",
                "work_mode": "Auto",
            },
        },
    )


def gen_work_status_trigger_schedule():
    ws = WorkStatus(state=WorkStatus.CLEANING)
    ws.mode.value = WorkStatus.Mode.AUTO
    ws.cleaning.state = WorkStatus.Cleaning.DOING
    ws.trigger.source = WorkStatus.Trigger.TIMING
    write_fixture(
        "mqtt/work_status/trigger_schedule.json",
        {
            "description": "WorkStatus with trigger.source=3 (TIMING/schedule)",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "cleaning",
                "trigger_source": "schedule",
                "work_mode": "Auto",
            },
        },
    )


def gen_work_status_trigger_missing_app_mode():
    """No trigger field, mode=1 (SELECT_ROOM) which IS in APP_TRIGGER_MODES."""
    ws = WorkStatus(state=WorkStatus.CLEANING)
    ws.mode.value = WorkStatus.Mode.SELECT_ROOM
    ws.cleaning.state = WorkStatus.Cleaning.DOING
    # Deliberately NO trigger field set
    write_fixture(
        "mqtt/work_status/trigger_missing_app_mode.json",
        {
            "description": "WorkStatus with no trigger field, mode=1 (SELECT_ROOM in APP_TRIGGER_MODES) → inferred app",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "cleaning",
                "trigger_source": "app",
                "work_mode": "Room",
            },
        },
    )


# ──────────────────────────────────────────────────────────────
# STATION STATUS FIXTURES (DPS 173)
# ──────────────────────────────────────────────────────────────


def gen_station_idle():
    sr = StationResponse()
    sr.status.connected = True
    sr.status.state = StationResponse.StationStatus.IDLE
    write_fixture(
        "mqtt/station_status/idle.json",
        {
            "description": "StationResponse: idle, connected",
            "dps": {"173": encode_message(sr)},
            "expected_state": {
                "dock_status": "Idle",
            },
        },
    )


def gen_station_washing():
    sr = StationResponse()
    sr.status.connected = True
    sr.status.state = StationResponse.StationStatus.WASHING
    write_fixture(
        "mqtt/station_status/washing.json",
        {
            "description": "StationResponse: washing mop",
            "dps": {"173": encode_message(sr)},
            "expected_state": {
                "dock_status": "Washing",
            },
        },
    )


def gen_station_drying():
    sr = StationResponse()
    sr.status.connected = True
    sr.status.state = StationResponse.StationStatus.DRYING
    write_fixture(
        "mqtt/station_status/drying.json",
        {
            "description": "StationResponse: drying mop",
            "dps": {"173": encode_message(sr)},
            "expected_state": {
                "dock_status": "Drying",
            },
        },
    )


def gen_station_emptying_dust():
    sr = StationResponse()
    sr.status.connected = True
    sr.status.state = StationResponse.StationStatus.IDLE
    sr.status.collecting_dust = True
    write_fixture(
        "mqtt/station_status/emptying_dust.json",
        {
            "description": "StationResponse: emptying dust (collecting_dust=True)",
            "dps": {"173": encode_message(sr)},
            "expected_state": {
                "dock_status": "Emptying dust",
            },
        },
    )


# ──────────────────────────────────────────────────────────────
# CLEANING PARAMETERS FIXTURES (DPS 154)
# ──────────────────────────────────────────────────────────────


def gen_cleaning_params_response():
    cp = CleanParam()
    cp.clean_type.value = CleanType.SWEEP_AND_MOP
    cp.clean_carpet.strategy = CleanCarpet.AUTO_RAISE
    cp.clean_extent.value = CleanExtent.NORMAL
    cp.mop_mode.level = MopMode.MIDDLE
    cp.mop_mode.corner_clean = MopMode.NORMAL
    cp.smart_mode_sw.CopyFrom(Switch(value=False))
    cp.fan.suction = Fan.TURBO
    cp.clean_times = 1

    resp = CleanParamResponse()
    resp.clean_param.CopyFrom(cp)

    write_fixture(
        "mqtt/cleaning_params/response_format.json",
        {
            "description": "CleanParamResponse with full cleaning parameters",
            "dps": {"154": encode_message(resp)},
            "expected_state": {
                "cleaning_mode": "Vacuum and mop",
                "fan_speed": "Turbo",
                "mop_water_level": "Medium",
                "cleaning_intensity": "Normal",
                "carpet_strategy": "Auto Raise",
                "corner_cleaning": "Normal",
                "smart_mode": False,
            },
        },
    )


def gen_cleaning_params_request():
    cp = CleanParam()
    cp.clean_type.value = CleanType.MOP_ONLY
    cp.mop_mode.level = MopMode.HIGH
    cp.fan.suction = Fan.QUIET

    req = CleanParamRequest()
    req.clean_param.CopyFrom(cp)

    write_fixture(
        "mqtt/cleaning_params/request_format.json",
        {
            "description": "CleanParamRequest fallback format",
            "dps": {"154": encode_message(req)},
            "expected_state": {
                "cleaning_mode": "Mop",
                "fan_speed": "Quiet",
                "mop_water_level": "High",
            },
        },
    )


# ──────────────────────────────────────────────────────────────
# MAP DATA FIXTURES (DPS 165)
# ──────────────────────────────────────────────────────────────


def gen_map_universal_data():
    udr = UniversalDataResponse()
    room_table = udr.cur_map_room
    room_table.map_id = 4

    r1 = room_table.data.add()
    r1.id = 1
    r1.name = "Kitchen"
    r1.scene.type = RoomScene.KITCHEN
    r1.scene.index.value = 1

    r2 = room_table.data.add()
    r2.id = 2
    r2.name = "Living Room"
    r2.scene.type = RoomScene.LIVINGROOM
    r2.scene.index.value = 1

    r3 = room_table.data.add()
    r3.id = 3
    r3.name = "Bedroom"
    r3.scene.type = RoomScene.BEDROOM
    r3.scene.index.value = 1

    write_fixture(
        "mqtt/map_data/universal_data_response.json",
        {
            "description": "UniversalDataResponse with 3 rooms on map_id=4",
            "dps": {"165": encode_message(udr)},
            "expected_state": {
                "map_id": 4,
                "rooms": [
                    {"id": 1, "name": "Kitchen"},
                    {"id": 2, "name": "Living Room"},
                    {"id": 3, "name": "Bedroom"},
                ],
            },
        },
    )


def gen_map_room_params():
    rp = RoomParams()
    rp.map_id = 6
    rp.releases = 1

    rm1 = rp.rooms.add()
    rm1.id = 1
    rm1.name = "Office"
    rm1.scene.type = RoomScene.STUDYROOM
    rm1.scene.index.value = 1

    rm2 = rp.rooms.add()
    rm2.id = 2
    rm2.name = "Hallway"
    rm2.scene.type = RoomScene.CORRIDOR
    rm2.scene.index.value = 1

    write_fixture(
        "mqtt/map_data/room_params.json",
        {
            "description": "RoomParams with 2 rooms on map_id=6",
            "dps": {"165": encode_message(rp)},
            "expected_state": {
                "map_id": 6,
                "rooms": [
                    {"id": 1, "name": "Office"},
                    {"id": 2, "name": "Hallway"},
                ],
            },
        },
    )


# ──────────────────────────────────────────────────────────────
# ERROR CODE FIXTURES (DPS 177)
# ──────────────────────────────────────────────────────────────


def gen_error_no_error():
    ec = ErrorCode()
    # No error/warn fields set → code 0
    write_fixture(
        "mqtt/error_code/no_error.json",
        {
            "description": "ErrorCode with no errors (code=0)",
            "dps": {"177": encode_message(ec)},
            "expected_state": {
                "error_code": 0,
                "error_message": "",
            },
        },
    )


def gen_error_wheel_stuck():
    ec = ErrorCode()
    ec.warn.append(2)  # WHEEL STUCK
    write_fixture(
        "mqtt/error_code/wheel_stuck.json",
        {
            "description": "ErrorCode with warn=2 (WHEEL STUCK)",
            "dps": {"177": encode_message(ec)},
            "expected_state": {
                "error_code": 2,
                "error_message": "WHEEL STUCK",
            },
        },
    )


# ──────────────────────────────────────────────────────────────
# TASK STATUS FIXTURES (DPS 153 — different WorkStatus configs)
# ──────────────────────────────────────────────────────────────


def gen_task_cleaning():
    ws = WorkStatus(state=WorkStatus.CLEANING)
    ws.mode.value = WorkStatus.Mode.AUTO
    ws.cleaning.state = WorkStatus.Cleaning.DOING
    write_fixture(
        "mqtt/task_status/cleaning.json",
        {
            "description": "Task status: actively cleaning (state=5, cleaning.state=DOING)",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "cleaning",
                "task_status": "Cleaning",
            },
        },
    )


def gen_task_paused():
    ws = WorkStatus(state=WorkStatus.CLEANING)
    ws.mode.value = WorkStatus.Mode.AUTO
    ws.cleaning.state = WorkStatus.Cleaning.PAUSED
    write_fixture(
        "mqtt/task_status/paused.json",
        {
            "description": "Task status: paused (state=5, cleaning.state=PAUSED, no go_wash)",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "paused",
                "task_status": "Paused",
            },
        },
    )


def gen_task_returning_to_charge():
    ws = WorkStatus(state=WorkStatus.GO_HOME)
    ws.go_home.state = WorkStatus.GoHome.DOING
    ws.go_home.mode = WorkStatus.GoHome.COLLECT_DUST
    ws.breakpoint.state = WorkStatus.Breakpoint.DOING
    write_fixture(
        "mqtt/task_status/returning_to_charge.json",
        {
            "description": "Task status: returning to charge with breakpoint (resume pending)",
            "dps": {"153": encode_message(ws)},
            "expected_state": {
                "activity": "returning",
                "task_status": "Returning to Charge",
            },
        },
    )


# ──────────────────────────────────────────────────────────────
# ACCESSORIES FIXTURES (DPS 168)
# ──────────────────────────────────────────────────────────────


def gen_accessories_full():
    runtime = ConsumableRuntime()
    runtime.side_brush.duration = 120
    runtime.rolling_brush.duration = 200
    runtime.filter_mesh.duration = 150
    runtime.scrape.duration = 20
    runtime.sensor.duration = 30
    runtime.mop.duration = 100
    runtime.dustbag.duration = 50
    runtime.dirty_watertank.duration = 40
    runtime.dirty_waterfilter.duration = 35
    runtime.last_time = 1700000000000000000  # nanoseconds

    resp = ConsumableResponse()
    resp.runtime.CopyFrom(runtime)

    write_fixture(
        "mqtt/accessories/consumable_full.json",
        {
            "description": "ConsumableResponse with all accessory types and Runtime durations",
            "dps": {"168": encode_message(resp)},
            "expected_state": {
                "accessories": {
                    "filter_usage": 150,
                    "main_brush_usage": 200,
                    "side_brush_usage": 120,
                    "sensor_usage": 30,
                    "scrape_usage": 20,
                    "mop_usage": 100,
                    "dustbag_usage": 50,
                    "dirty_watertank_usage": 40,
                    "dirty_waterfilter_usage": 35,
                },
            },
        },
    )


def gen_accessories_no_runtime():
    resp = ConsumableResponse()
    # No runtime field set at all
    write_fixture(
        "mqtt/accessories/consumable_no_runtime.json",
        {
            "description": "ConsumableResponse with missing Runtime field (no changes)",
            "dps": {"168": encode_message(resp)},
            "expected_state": {
                "accessories": "unchanged",
            },
        },
    )


# ──────────────────────────────────────────────────────────────
# SCENE INFO FIXTURES (DPS 180)
# ──────────────────────────────────────────────────────────────


def gen_scene_list():
    sr = SceneResponse()
    sr.method = 0  # DEFAULT
    sr.seq = 0

    s1 = sr.infos.add()
    s1.id.value = 1
    s1.valid = True
    s1.name = "Full Home Daily Clean"
    s1.mapid = 4
    s1.type = SceneInfo.WHOLE_HOUSE_DAILY_CLEANING
    s1.index = 1

    s2 = sr.infos.add()
    s2.id.value = 2
    s2.valid = True
    s2.name = "Full Home Deep Clean"
    s2.mapid = 4
    s2.type = SceneInfo.WHOLE_HOUSE_DEEP_CLEANING
    s2.index = 2

    s3 = sr.infos.add()
    s3.id.value = 4
    s3.valid = True
    s3.name = "Kitchen Quick Clean"
    s3.mapid = 4
    s3.type = SceneInfo.SCENE_NORMAL
    s3.index = 3

    write_fixture(
        "mqtt/scene_info/scenes_list.json",
        {
            "description": "SceneResponse with 3 valid scenes (2 default + 1 custom)",
            "dps": {"180": encode_message(sr)},
            "expected_state": {
                "scenes": [
                    {"id": 1, "name": "Full Home Daily Clean", "type": 1},
                    {"id": 2, "name": "Full Home Deep Clean", "type": 2},
                    {"id": 4, "name": "Kitchen Quick Clean", "type": 0},
                ],
            },
        },
    )


# ──────────────────────────────────────────────────────────────
# CLEANING STATISTICS FIXTURES (DPS 167)
# ──────────────────────────────────────────────────────────────


def gen_cleaning_stats():
    cs = CleanStatistics()
    cs.single.clean_duration = 2400  # 40 minutes in seconds
    cs.single.clean_area = 85  # 85 m2
    cs.total.clean_duration = 36000
    cs.total.clean_area = 1200
    cs.total.clean_count = 50

    write_fixture(
        "mqtt/cleaning_stats/stats_response.json",
        {
            "description": "CleanStatistics with single session and total stats",
            "dps": {"167": encode_message(cs)},
            "expected_state": {
                "cleaning_time": 2400,
                "cleaning_area": 85,
            },
        },
    )


# ──────────────────────────────────────────────────────────────
# PLAIN DPS FIXTURES (no protobuf)
# ──────────────────────────────────────────────────────────────


def gen_dps_battery_50():
    write_fixture(
        "mqtt/dps_plain/battery_50.json",
        {
            "description": "DPS 163: battery level 50% (plain int string)",
            "dps": {"163": "50"},
            "expected_state": {
                "battery_level": 50,
            },
        },
    )


def gen_dps_battery_100():
    write_fixture(
        "mqtt/dps_plain/battery_100.json",
        {
            "description": "DPS 163: battery level 100% (plain int string)",
            "dps": {"163": "100"},
            "expected_state": {
                "battery_level": 100,
            },
        },
    )


def gen_dps_battery_0():
    write_fixture(
        "mqtt/dps_plain/battery_0.json",
        {
            "description": "DPS 163: battery level 0% (plain int string)",
            "dps": {"163": "0"},
            "expected_state": {
                "battery_level": 0,
            },
        },
    )


def gen_dps_clean_speed_standard():
    # DPS 158: index into EUFY_CLEAN_NOVEL_CLEAN_SPEED
    # Index 1 = Standard (list: Quiet=0, Standard=1, Turbo=2, Max=3, Boost_IQ=4)
    write_fixture(
        "mqtt/dps_plain/clean_speed_standard.json",
        {
            "description": "DPS 158: clean speed index 1 (Standard)",
            "dps": {"158": "1"},
            "expected_state": {
                "fan_speed": "Standard",
            },
        },
    )


def gen_dps_find_robot_true():
    write_fixture(
        "mqtt/dps_plain/find_robot_true.json",
        {
            "description": "DPS 160: find_robot=true (plain bool string)",
            "dps": {"160": "true"},
            "expected_state": {
                "find_robot": True,
            },
        },
    )


# ──────────────────────────────────────────────────────────────
# HTTP FIXTURES (placeholder / anonymized)
# ──────────────────────────────────────────────────────────────


def gen_http_fixtures():
    write_fixture(
        "http/login_response.json",
        {
            "description": "Login response (anonymized)",
            "access_token": "ANON_TOKEN_ACCESS_001",
            "user_id": "ANON_USER_001",
            "email": "anon@example.com",
            "token_expires_at": 1700000000,
        },
    )

    write_fixture(
        "http/user_info_response.json",
        {
            "description": "User info response (anonymized)",
            "user_center_id": "ANON_USER_CENTER_001",
            "user_center_token": "ANON_TOKEN_CENTER_001",
            "user_name": "Anonymous User",
            "email": "anon@example.com",
        },
    )

    write_fixture(
        "http/device_list_response.json",
        {
            "description": "Device list response (anonymized T2351)",
            "devices": [
                {
                    "device_sn": "ANON_DEVICE_SN_001",
                    "device_name": "RoboVac X10 Pro Omni",
                    "device_model": "T2351",
                    "device_type": 1,
                    "product_code": "T2351",
                    "wifi_mac": "AA:BB:CC:DD:EE:FF",
                    "share": False,
                    "device_sw_version": "2.0.7.6",
                }
            ],
        },
    )

    write_fixture(
        "http/cloud_device_list_response.json",
        {
            "description": "Cloud device list V2 response (anonymized)",
            "items": [
                {
                    "id": "ANON_DEVICE_ID_001",
                    "device_sn": "ANON_DEVICE_SN_001",
                    "device_name": "RoboVac X10 Pro Omni",
                    "device_model": "T2351",
                    "firmware_version": "2.0.7.6",
                    "time_zone": "Europe/Copenhagen",
                    "ip_addr": "",
                }
            ],
        },
    )

    write_fixture(
        "http/mqtt_credentials_response.json",
        {
            "description": "MQTT credentials response (anonymized)",
            "thing_name": "ANON_THING_001",
            "endpoint": "mqtt-endpoint.example.com",
            "certificate_pem": "ANON_CERT_PEM_PLACEHOLDER",
            "private_key": "ANON_PRIVATE_KEY_PLACEHOLDER",
        },
    )


# ──────────────────────────────────────────────────────────────
# SEQUENCE FIXTURES
# ──────────────────────────────────────────────────────────────


def gen_sequence_full_cleaning_cycle():
    """Full auto cleaning cycle: docked → cleaning → returning → docked."""
    # Step 1: Start from docked/charging
    ws1 = WorkStatus(state=WorkStatus.CHARGING)
    ws1.charging.state = WorkStatus.Charging.DOING

    # Step 2: Begin cleaning
    ws2 = WorkStatus(state=WorkStatus.CLEANING)
    ws2.mode.value = WorkStatus.Mode.AUTO
    ws2.cleaning.state = WorkStatus.Cleaning.DOING
    ws2.trigger.source = WorkStatus.Trigger.APP

    # Step 3: Positioning/navigating
    ws3 = WorkStatus(state=WorkStatus.FAST_MAPPING)
    ws3.mode.value = WorkStatus.Mode.AUTO

    # Step 4: Active cleaning
    ws4 = WorkStatus(state=WorkStatus.CLEANING)
    ws4.mode.value = WorkStatus.Mode.AUTO
    ws4.cleaning.state = WorkStatus.Cleaning.DOING
    ws4.trigger.source = WorkStatus.Trigger.APP

    # Step 5: Returning home
    ws5 = WorkStatus(state=WorkStatus.GO_HOME)
    ws5.go_home.state = WorkStatus.GoHome.DOING
    ws5.go_home.mode = WorkStatus.GoHome.COMPLETE_TASK

    # Step 6: Back to charging
    ws6 = WorkStatus(state=WorkStatus.CHARGING)
    ws6.charging.state = WorkStatus.Charging.DOING

    write_fixture(
        "sequences/full_cleaning_cycle.json",
        {
            "description": "Full auto cleaning cycle: docked → positioning → cleaning → returning → docked",
            "messages": [
                {
                    "dps": {"153": encode_message(ws1)},
                    "expected_state_after": {"activity": "docked", "charging": True},
                    "delay_seconds": 0,
                },
                {
                    "dps": {"153": encode_message(ws2)},
                    "expected_state_after": {
                        "activity": "cleaning",
                        "trigger_source": "app",
                    },
                    "delay_seconds": 2,
                },
                {
                    "dps": {"153": encode_message(ws3)},
                    "expected_state_after": {
                        "activity": "cleaning",
                        "task_status": "Positioning",
                    },
                    "delay_seconds": 5,
                },
                {
                    "dps": {"153": encode_message(ws4)},
                    "expected_state_after": {
                        "activity": "cleaning",
                        "task_status": "Cleaning",
                    },
                    "delay_seconds": 10,
                },
                {
                    "dps": {"153": encode_message(ws5)},
                    "expected_state_after": {
                        "activity": "returning",
                        "task_status": "Returning",
                    },
                    "delay_seconds": 1800,
                },
                {
                    "dps": {"153": encode_message(ws6)},
                    "expected_state_after": {"activity": "docked", "charging": True},
                    "delay_seconds": 120,
                },
            ],
        },
    )


def gen_sequence_dock_wash_dry():
    """Dock wash+dry cycle: cleaning → returning to wash → washing → drying → idle."""
    # Step 1: Cleaning
    ws1 = WorkStatus(state=WorkStatus.CLEANING)
    ws1.mode.value = WorkStatus.Mode.AUTO
    ws1.cleaning.state = WorkStatus.Cleaning.DOING

    # Step 2: Going to wash (mid-cleaning)
    ws2 = WorkStatus(state=WorkStatus.CLEANING)
    ws2.go_wash.state = WorkStatus.GoWash.DOING
    ws2.go_wash.mode = WorkStatus.GoWash.NAVIGATION

    # Step 3: Washing mop at station (DPS 153 + 173)
    ws3 = WorkStatus(state=WorkStatus.CLEANING)
    ws3.go_wash.state = WorkStatus.GoWash.DOING
    ws3.go_wash.mode = WorkStatus.GoWash.WASHING
    ws3.station.washing_drying_system.state = (
        WorkStatus.Station.WashingDryingSystem.WASHING
    )
    sr3 = StationResponse()
    sr3.status.connected = True
    sr3.status.state = StationResponse.StationStatus.WASHING

    # Step 4: Drying mop (DPS 153 + 173)
    ws4 = WorkStatus(state=WorkStatus.CLEANING)
    ws4.go_wash.state = WorkStatus.GoWash.DOING
    ws4.go_wash.mode = WorkStatus.GoWash.DRYING
    ws4.station.washing_drying_system.state = (
        WorkStatus.Station.WashingDryingSystem.DRYING
    )
    sr4 = StationResponse()
    sr4.status.connected = True
    sr4.status.state = StationResponse.StationStatus.DRYING

    # Step 5: Back to charging
    ws5 = WorkStatus(state=WorkStatus.CHARGING)
    ws5.charging.state = WorkStatus.Charging.DOING
    sr5 = StationResponse()
    sr5.status.connected = True
    sr5.status.state = StationResponse.StationStatus.IDLE

    write_fixture(
        "sequences/dock_wash_dry_cycle.json",
        {
            "description": "Dock wash+dry cycle: cleaning → return to wash → washing → drying → idle",
            "messages": [
                {
                    "dps": {"153": encode_message(ws1)},
                    "expected_state_after": {
                        "activity": "cleaning",
                        "task_status": "Cleaning",
                    },
                    "delay_seconds": 0,
                },
                {
                    "dps": {"153": encode_message(ws2)},
                    "expected_state_after": {
                        "activity": "cleaning",
                        "task_status": "Returning to Wash",
                    },
                    "delay_seconds": 900,
                },
                {
                    "dps": {"153": encode_message(ws3), "173": encode_message(sr3)},
                    "expected_state_after": {
                        "activity": "docked",
                        "dock_status": "Washing",
                    },
                    "delay_seconds": 30,
                },
                {
                    "dps": {"153": encode_message(ws4), "173": encode_message(sr4)},
                    "expected_state_after": {
                        "activity": "docked",
                        "dock_status": "Drying",
                    },
                    "delay_seconds": 180,
                },
                {
                    "dps": {"153": encode_message(ws5), "173": encode_message(sr5)},
                    "expected_state_after": {
                        "activity": "docked",
                        "charging": True,
                        "dock_status": "Idle",
                    },
                    "delay_seconds": 7200,
                },
            ],
        },
    )


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────


def main():
    print("Generating fixtures...")

    # Work Status (DPS 153)
    gen_work_status_idle_standby()
    gen_work_status_idle_sleep()
    gen_work_status_error()
    gen_work_status_docked_charging()
    gen_work_status_cleaning_positioning()
    gen_work_status_cleaning_active()
    gen_work_status_docked_washing()
    gen_work_status_docked_drying()
    gen_work_status_returning()
    gen_work_status_trigger_app()
    gen_work_status_trigger_button()
    gen_work_status_trigger_schedule()
    gen_work_status_trigger_missing_app_mode()

    # Station Status (DPS 173)
    gen_station_idle()
    gen_station_washing()
    gen_station_drying()
    gen_station_emptying_dust()

    # Cleaning Parameters (DPS 154)
    gen_cleaning_params_response()
    gen_cleaning_params_request()

    # Map Data (DPS 165)
    gen_map_universal_data()
    gen_map_room_params()

    # Error Code (DPS 177)
    gen_error_no_error()
    gen_error_wheel_stuck()

    # Task Status (via DPS 153 WorkStatus variations)
    gen_task_cleaning()
    gen_task_paused()
    gen_task_returning_to_charge()

    # Accessories (DPS 168)
    gen_accessories_full()
    gen_accessories_no_runtime()

    # Scene Info (DPS 180)
    gen_scene_list()

    # Cleaning Stats (DPS 167)
    gen_cleaning_stats()

    # Plain DPS (no protobuf)
    gen_dps_battery_50()
    gen_dps_battery_100()
    gen_dps_battery_0()
    gen_dps_clean_speed_standard()
    gen_dps_find_robot_true()

    # HTTP fixtures
    gen_http_fixtures()

    # Sequence fixtures
    gen_sequence_full_cleaning_cycle()
    gen_sequence_dock_wash_dry()

    print("\nDone!")


if __name__ == "__main__":
    main()
