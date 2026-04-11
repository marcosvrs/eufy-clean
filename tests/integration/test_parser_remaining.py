"""Protocol tests for remaining DPS key parsers."""

from __future__ import annotations

import json

from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import (
    DPS_MAP,
    EUFY_CLEAN_ERROR_CODES,
    EUFY_CLEAN_NOVEL_CLEAN_SPEED,
)
from custom_components.robovac_mqtt.models import AccessoryState, VacuumState
from custom_components.robovac_mqtt.proto.cloud.clean_statistics_pb2 import (
    CleanStatistics,
)
from custom_components.robovac_mqtt.proto.cloud.consumable_pb2 import (
    ConsumableResponse,
    ConsumableRuntime,
)
from custom_components.robovac_mqtt.proto.cloud.control_pb2 import (
    ModeCtrlRequest,
    SelectRoomsClean,
    SelectZonesClean,
)
from custom_components.robovac_mqtt.proto.cloud.error_code_pb2 import ErrorCode
from custom_components.robovac_mqtt.proto.cloud.multi_maps_pb2 import (
    MultiMapsManageResponse,
)
from custom_components.robovac_mqtt.proto.cloud.scene_pb2 import (
    SceneInfo,
    SceneResponse,
)
from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import WorkStatus
from tests.integration.conftest import load_fixture

from .helpers import assert_state_field, make_dps_payload, make_vacuum_state


class TestErrorCode:
    def test_error_code_zero_clears_error(self):
        state = make_vacuum_state(error_code=5, error_message="HOST TRAPPED CLEAR OBST")
        ec = ErrorCode(warn=[])
        dps = make_dps_payload(DPS_MAP["ERROR_CODE"], ec)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "error_code", 0)
        assert_state_field(new_state, "error_message", "")

    def test_error_code_known(self):
        state = make_vacuum_state()
        ec = ErrorCode(warn=[4])
        dps = make_dps_payload(DPS_MAP["ERROR_CODE"], ec)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "error_code", 4)
        assert_state_field(new_state, "error_message", EUFY_CLEAN_ERROR_CODES[4])

    def test_error_code_unknown_graceful(self):
        state = make_vacuum_state()
        ec = ErrorCode(warn=[99999])
        dps = make_dps_payload(DPS_MAP["ERROR_CODE"], ec)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "error_code", 99999)
        assert_state_field(new_state, "error_message", "Unknown (99999)")

    def test_error_code_multiple_warn_uses_first(self):
        state = make_vacuum_state()
        ec = ErrorCode(warn=[3, 7])
        dps = make_dps_payload(DPS_MAP["ERROR_CODE"], ec)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "error_code", 3)
        assert_state_field(new_state, "error_message", EUFY_CLEAN_ERROR_CODES[3])


class TestTaskStatus:
    def test_cleaning_mode_yields_cleaning(self):
        state = make_vacuum_state()
        ws = WorkStatus(state=5)
        dps = make_dps_payload(DPS_MAP["WORK_STATUS"], ws)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "task_status", "Cleaning")

    def test_paused_state_yields_paused(self):
        state = make_vacuum_state()
        ws = WorkStatus(state=5)
        ws.cleaning.state = 1  # PAUSED enum
        dps = make_dps_payload(DPS_MAP["WORK_STATUS"], ws)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "task_status", "Paused")

    def test_returning_to_charge(self):
        state = make_vacuum_state()
        ws = WorkStatus(state=7)
        ws.breakpoint.state = 0  # RESUMABLE enum
        dps = make_dps_payload(DPS_MAP["WORK_STATUS"], ws)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "task_status", "Returning to Charge")

    def test_go_wash_drying_yields_completed(self):
        state = make_vacuum_state()
        ws = WorkStatus(state=5)
        ws.go_wash.mode = 2  # DRYING enum
        dps = make_dps_payload(DPS_MAP["WORK_STATUS"], ws)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "task_status", "Completed")

    def test_charging_no_resume_yields_completed(self):
        state = make_vacuum_state()
        ws = WorkStatus(state=3)
        dps = make_dps_payload(DPS_MAP["WORK_STATUS"], ws)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "task_status", "Completed")


class TestSceneInfo:
    def test_scenes_with_entries(self):
        state = make_vacuum_state()
        scene_resp = SceneResponse(
            infos=[
                SceneInfo(
                    id=SceneInfo.Id(value=42),
                    name="Morning Clean",
                    valid=True,
                    type=SceneInfo.SCENE_NORMAL,
                ),
                SceneInfo(
                    id=SceneInfo.Id(value=99),
                    name="Pet Area",
                    valid=True,
                    type=SceneInfo.PET_AREA_CLEANING,
                ),
            ]
        )
        dps = make_dps_payload(DPS_MAP["SCENE_INFO"], scene_resp)
        new_state, changes = update_state(state, dps)
        assert len(new_state.scenes) == 2
        assert new_state.scenes[0]["id"] == 42
        assert new_state.scenes[0]["name"] == "Morning Clean"
        assert "type" in new_state.scenes[0]
        assert new_state.scenes[1]["id"] == 99
        assert new_state.scenes[1]["name"] == "Pet Area"

    def test_empty_scene_list(self):
        state = make_vacuum_state(scenes=[{"id": 1, "name": "Old", "type": 0}])
        scene_resp = SceneResponse(infos=[])
        dps = make_dps_payload(DPS_MAP["SCENE_INFO"], scene_resp)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "scenes", [])

    def test_invalid_scene_filtered(self):
        state = make_vacuum_state()
        scene_resp = SceneResponse(
            infos=[
                SceneInfo(
                    id=SceneInfo.Id(value=10),
                    name="Good Scene",
                    valid=True,
                    type=SceneInfo.SCENE_NORMAL,
                ),
                SceneInfo(
                    id=SceneInfo.Id(value=11),
                    name="Bad Scene",
                    valid=False,
                    type=SceneInfo.SCENE_NORMAL,
                ),
            ]
        )
        dps = make_dps_payload(DPS_MAP["SCENE_INFO"], scene_resp)
        new_state, changes = update_state(state, dps)
        assert len(new_state.scenes) == 1
        assert new_state.scenes[0]["name"] == "Good Scene"

    def test_scene_info_real_4_scenes(self):
        fixture = load_fixture("mqtt/scene_info/scenes_list.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert isinstance(new_state.scenes, list)
        assert len(new_state.scenes) >= 1
        assert new_state.scenes[0]["name"] == "Daily"

    def test_scene_info_real_5_scenes(self):
        fixture = load_fixture("mqtt/scene_info/scenes_list_5.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert isinstance(new_state.scenes, list)
        assert len(new_state.scenes) >= 2
        names = [s["name"] for s in new_state.scenes]
        assert "Daily" in names
        assert "Customize" in names


class TestAccessories:
    def test_all_accessory_types(self):
        state = make_vacuum_state()
        runtime = ConsumableRuntime(
            filter_mesh=ConsumableRuntime.Duration(duration=120),
            rolling_brush=ConsumableRuntime.Duration(duration=200),
            side_brush=ConsumableRuntime.Duration(duration=80),
            sensor=ConsumableRuntime.Duration(duration=30),
            scrape=ConsumableRuntime.Duration(duration=15),
            mop=ConsumableRuntime.Duration(duration=50),
            dustbag=ConsumableRuntime.Duration(duration=10),
            dirty_watertank=ConsumableRuntime.Duration(duration=5),
            dirty_waterfilter=ConsumableRuntime.Duration(duration=3),
        )
        resp = ConsumableResponse(runtime=runtime)
        dps = make_dps_payload(DPS_MAP["ACCESSORIES_STATUS"], resp)
        new_state, changes = update_state(state, dps)
        acc = new_state.accessories
        assert acc.filter_usage == 120
        assert acc.main_brush_usage == 200
        assert acc.side_brush_usage == 80
        assert acc.sensor_usage == 30
        assert acc.scrape_usage == 15
        assert acc.mop_usage == 50
        assert acc.dustbag_usage == 10
        assert acc.dirty_watertank_usage == 5
        assert acc.dirty_waterfilter_usage == 3

    def test_no_runtime_field_returns_current_state(self):
        existing_acc = AccessoryState(filter_usage=100, main_brush_usage=200)
        state = make_vacuum_state(accessories=existing_acc)
        resp = ConsumableResponse()
        dps = make_dps_payload(DPS_MAP["ACCESSORIES_STATUS"], resp)
        new_state, changes = update_state(state, dps)
        assert new_state.accessories.filter_usage == 100
        assert new_state.accessories.main_brush_usage == 200

    def test_partial_runtime_updates_only_present(self):
        existing_acc = AccessoryState(
            filter_usage=100,
            main_brush_usage=200,
            side_brush_usage=50,
        )
        state = make_vacuum_state(accessories=existing_acc)
        runtime = ConsumableRuntime(
            filter_mesh=ConsumableRuntime.Duration(duration=150),
        )
        resp = ConsumableResponse(runtime=runtime)
        dps = make_dps_payload(DPS_MAP["ACCESSORIES_STATUS"], resp)
        new_state, changes = update_state(state, dps)
        assert new_state.accessories.filter_usage == 150
        # _parse_accessories uses replace(current_state, **changes) — unmentioned fields preserved
        assert new_state.accessories.main_brush_usage == 200
        assert new_state.accessories.side_brush_usage == 50


class TestCleaningStats:
    def test_single_stats_populated(self):
        state = make_vacuum_state()
        stats = CleanStatistics(
            single=CleanStatistics.Single(clean_duration=3600, clean_area=45),
        )
        dps = make_dps_payload(DPS_MAP["CLEANING_STATISTICS"], stats)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "cleaning_time", 3600)
        assert_state_field(new_state, "cleaning_area", 45)

    def test_stats_without_single_no_update(self):
        state = make_vacuum_state(cleaning_time=100, cleaning_area=10)
        stats = CleanStatistics(
            total=CleanStatistics.Total(
                clean_duration=50000, clean_area=1000, clean_count=50
            ),
        )
        dps = make_dps_payload(DPS_MAP["CLEANING_STATISTICS"], stats)
        new_state, changes = update_state(state, dps)
        assert "cleaning_time" not in changes
        assert "cleaning_area" not in changes
        assert new_state.cleaning_time == 100
        assert new_state.cleaning_area == 10


class TestPlainDPS:
    def test_battery_level_normal(self):
        state = make_vacuum_state()
        new_state, changes = update_state(state, {"163": "50"})
        assert_state_field(new_state, "battery_level", 50)

    def test_battery_level_zero(self):
        state = make_vacuum_state()
        new_state, changes = update_state(state, {"163": "0"})
        assert_state_field(new_state, "battery_level", 0)

    def test_battery_level_full(self):
        state = make_vacuum_state()
        new_state, changes = update_state(state, {"163": "100"})
        assert_state_field(new_state, "battery_level", 100)

    def test_clean_speed_index_0(self):
        state = make_vacuum_state()
        new_state, changes = update_state(state, {"158": "0"})
        assert_state_field(
            new_state, "fan_speed", EUFY_CLEAN_NOVEL_CLEAN_SPEED[0].value
        )

    def test_clean_speed_index_1(self):
        state = make_vacuum_state()
        new_state, changes = update_state(state, {"158": "1"})
        assert_state_field(
            new_state, "fan_speed", EUFY_CLEAN_NOVEL_CLEAN_SPEED[1].value
        )

    def test_clean_speed_index_3(self):
        state = make_vacuum_state()
        new_state, changes = update_state(state, {"158": "3"})
        assert_state_field(
            new_state, "fan_speed", EUFY_CLEAN_NOVEL_CLEAN_SPEED[3].value
        )

    def test_clean_speed_as_int(self):
        state = make_vacuum_state()
        new_state, changes = update_state(state, {"158": 2})
        assert_state_field(
            new_state, "fan_speed", EUFY_CLEAN_NOVEL_CLEAN_SPEED[2].value
        )

    def test_find_robot_true(self):
        state = make_vacuum_state()
        new_state, changes = update_state(state, {"160": "true"})
        assert_state_field(new_state, "find_robot", True)

    def test_find_robot_false(self):
        state = make_vacuum_state(find_robot=True)
        new_state, changes = update_state(state, {"160": "false"})
        assert_state_field(new_state, "find_robot", False)

    def test_find_robot_case_insensitive(self):
        state = make_vacuum_state()
        new_state, changes = update_state(state, {"160": "True"})
        assert_state_field(new_state, "find_robot", True)


class TestMultiMap:
    def test_multi_map_none_value_no_crash(self):
        state = make_vacuum_state()
        new_state, changes = update_state(state, {"172": None})
        assert "172" in new_state.raw_dps

    def test_multi_map_response_no_crash(self):
        state = make_vacuum_state()
        resp = MultiMapsManageResponse(
            method=MultiMapsManageResponse.SUCCESS,
            result=MultiMapsManageResponse.SUCCESS,
        )
        dps = make_dps_payload(DPS_MAP["MULTI_MAP_MANAGE"], resp)
        new_state, changes = update_state(state, dps)
        assert DPS_MAP["MULTI_MAP_MANAGE"] in new_state.raw_dps


class TestPlayPauseEcho:
    def test_room_clean_echo_populates_room_ids(self):
        state = make_vacuum_state(
            rooms=[
                {"id": 1, "name": "Kitchen"},
                {"id": 2, "name": "Living Room"},
                {"id": 3, "name": "Bedroom"},
            ]
        )
        mode_ctrl = ModeCtrlRequest(
            method=ModeCtrlRequest.START_SELECT_ROOMS_CLEAN,
            select_rooms_clean=SelectRoomsClean(
                rooms=[
                    SelectRoomsClean.Room(id=1, order=0),
                    SelectRoomsClean.Room(id=3, order=1),
                ],
                map_id=1,
            ),
        )
        dps = make_dps_payload(DPS_MAP["PLAY_PAUSE"], mode_ctrl)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "active_room_ids", [1, 3])
        assert "Kitchen" in new_state.active_room_names
        assert "Bedroom" in new_state.active_room_names
        assert_state_field(new_state, "active_zone_count", 0)

    def test_zone_clean_echo_populates_zone_count(self):
        state = make_vacuum_state()
        from custom_components.robovac_mqtt.proto.cloud.common_pb2 import (
            Point,
            Quadrangle,
        )

        mode_ctrl = ModeCtrlRequest(
            method=ModeCtrlRequest.START_SELECT_ZONES_CLEAN,
            select_zones_clean=SelectZonesClean(
                zones=[
                    SelectZonesClean.Zone(
                        quadrangle=Quadrangle(
                            p0=Point(x=0, y=0),
                            p1=Point(x=100, y=0),
                            p2=Point(x=100, y=100),
                            p3=Point(x=0, y=100),
                        )
                    ),
                    SelectZonesClean.Zone(
                        quadrangle=Quadrangle(
                            p0=Point(x=200, y=200),
                            p1=Point(x=300, y=200),
                            p2=Point(x=300, y=300),
                            p3=Point(x=200, y=300),
                        )
                    ),
                ],
                map_id=1,
            ),
        )
        dps = make_dps_payload(DPS_MAP["PLAY_PAUSE"], mode_ctrl)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "active_zone_count", 2)
        assert_state_field(new_state, "active_room_ids", [])

    def test_room_clean_echo_unknown_room_uses_fallback(self):
        state = make_vacuum_state(rooms=[{"id": 1, "name": "Kitchen"}])
        mode_ctrl = ModeCtrlRequest(
            method=ModeCtrlRequest.START_SELECT_ROOMS_CLEAN,
            select_rooms_clean=SelectRoomsClean(
                rooms=[
                    SelectRoomsClean.Room(id=1, order=0),
                    SelectRoomsClean.Room(id=99, order=1),
                ],
                map_id=1,
            ),
        )
        dps = make_dps_payload(DPS_MAP["PLAY_PAUSE"], mode_ctrl)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "active_room_ids", [1, 99])
        assert "Kitchen" in new_state.active_room_names
        assert "Room 99" in new_state.active_room_names

    def test_pause_resume_echo_no_target_change(self):
        state = make_vacuum_state(active_room_ids=[1, 2], active_zone_count=0)
        mode_ctrl = ModeCtrlRequest(method=ModeCtrlRequest.PAUSE_TASK)
        dps = make_dps_payload(DPS_MAP["PLAY_PAUSE"], mode_ctrl)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "active_room_ids", [1, 2])

    def test_room_clean_echo_clears_scene(self):
        state = make_vacuum_state(current_scene_id=42, current_scene_name="My Scene")
        mode_ctrl = ModeCtrlRequest(
            method=ModeCtrlRequest.START_SELECT_ROOMS_CLEAN,
            select_rooms_clean=SelectRoomsClean(
                rooms=[SelectRoomsClean.Room(id=1, order=0)],
                map_id=1,
            ),
        )
        dps = make_dps_payload(DPS_MAP["PLAY_PAUSE"], mode_ctrl)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "current_scene_id", 0)
        assert_state_field(new_state, "current_scene_name", None)

    def test_room_clean_echo_empty_rooms_preserves_targets(self):
        state = make_vacuum_state(active_room_ids=[5, 6], active_room_names="Old Room")
        mode_ctrl = ModeCtrlRequest(
            method=ModeCtrlRequest.START_SELECT_ROOMS_CLEAN,
            select_rooms_clean=SelectRoomsClean(rooms=[], map_id=1),
        )
        dps = make_dps_payload(DPS_MAP["PLAY_PAUSE"], mode_ctrl)
        new_state, changes = update_state(state, dps)
        assert_state_field(new_state, "active_room_ids", [5, 6])


class TestPlayPauseFixtures:
    def test_start_room_clean_echo_no_crash(self):
        fixture = load_fixture("mqtt/play_pause/start_room_clean.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert DPS_MAP["PLAY_PAUSE"] in new_state.raw_dps

    def test_pause_task_echo_preserves_targets(self):
        fixture = load_fixture("mqtt/play_pause/pause_task.json")
        state = make_vacuum_state(active_room_ids=[1, 2], active_zone_count=0)
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "active_room_ids", [1, 2])

    def test_resume_task_echo_preserves_targets(self):
        fixture = load_fixture("mqtt/play_pause/resume_task.json")
        state = make_vacuum_state(active_room_ids=[3], active_zone_count=0)
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "active_room_ids", [3])

    def test_start_gohome_echo_no_crash(self):
        fixture = load_fixture("mqtt/play_pause/start_gohome.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert DPS_MAP["PLAY_PAUSE"] in new_state.raw_dps

    def test_start_auto_clean_echo_no_crash(self):
        fixture = load_fixture("mqtt/play_pause/start_auto_clean.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert DPS_MAP["PLAY_PAUSE"] in new_state.raw_dps

    def test_start_zone_clean_echo_no_crash(self):
        fixture = load_fixture("mqtt/play_pause/start_zone_clean.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert DPS_MAP["PLAY_PAUSE"] in new_state.raw_dps


class TestCleaningParamsFixtures:
    def test_response_narrow_intensity(self):
        fixture = load_fixture("mqtt/cleaning_params/response_narrow.json")
        state = make_vacuum_state()
        new_state, changes = update_state(state, fixture["dps"])
        assert_state_field(new_state, "cleaning_intensity", "Narrow")

    def test_response_format_existing(self):
        fixture = load_fixture("mqtt/cleaning_params/response_format.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "cleaning_intensity", "Quick")


class TestPlainDPSFixtures:
    def test_clean_speed_max_fixture(self):
        fixture = load_fixture("mqtt/dps_plain/clean_speed_max.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(
            new_state, "fan_speed", EUFY_CLEAN_NOVEL_CLEAN_SPEED[3].value
        )


class TestMapEditFixture:
    def test_map_edit_request_stored_in_raw_dps(self):
        fixture = load_fixture("mqtt/map_data/map_edit_request.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert DPS_MAP["TIMING"] in new_state.raw_dps

    def test_map_edit_request_170_stored_in_raw_dps(self):
        fixture = load_fixture("mqtt/map_data/map_edit_request_170.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert DPS_MAP["MAP_EDIT_REQUEST"] in new_state.raw_dps


class TestAccessoryFixtures:
    def test_consumable_early_session(self):
        fixture = load_fixture("mqtt/accessories/consumable_early_session.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        acc = new_state.accessories
        assert acc.side_brush_usage == 9
        assert acc.main_brush_usage == 9
        assert acc.filter_usage == 9
        assert acc.sensor_usage == 404
        assert acc.mop_usage == 6

    def test_consumable_late_session(self):
        fixture = load_fixture("mqtt/accessories/consumable_late_session.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        acc = new_state.accessories
        assert acc.sensor_usage == 405
        assert acc.side_brush_usage == 9

    def test_consumable_mid_session(self):
        fixture = load_fixture("mqtt/accessories/consumable_mid_session.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        acc = new_state.accessories
        assert acc.sensor_usage == 404
        assert acc.side_brush_usage == 9


class TestDeviceInfoFixture:
    def test_device_info_extracts_network(self):
        fixture = load_fixture("mqtt/device_info/device_info.json")
        state = make_vacuum_state()
        new_state, changes = update_state(state, fixture["dps"])
        assert_state_field(new_state, "wifi_ssid", "Rubido")
        assert_state_field(new_state, "wifi_ip", "192.168.50.246")
        assert_state_field(new_state, "device_mac", "98:a8:29:52:c6:af")


class TestStationStatusFixtures:
    def test_idle_connected(self):
        fixture = load_fixture("mqtt/station_status/idle_connected.json")
        state, _ = update_state(VacuumState(), fixture["dps"])
        assert_state_field(state, "dock_status", "Idle")

    def test_washing_adding_water(self):
        fixture = load_fixture("mqtt/station_status/washing_adding_water.json")
        state, _ = update_state(VacuumState(), fixture["dps"])
        assert_state_field(state, "dock_status", "Adding clean water")

    def test_washing_plain(self):
        fixture = load_fixture("mqtt/station_status/washing_plain.json")
        state, _ = update_state(VacuumState(), fixture["dps"])
        assert_state_field(state, "dock_status", "Washing")

    def test_washing_recycling(self):
        fixture = load_fixture("mqtt/station_status/washing_recycling.json")
        state, _ = update_state(VacuumState(), fixture["dps"])
        assert_state_field(state, "dock_status", "Recycling waste water")

    def test_idle_low_water(self):
        fixture = load_fixture("mqtt/station_status/idle_low_water.json")
        state, _ = update_state(VacuumState(), fixture["dps"])
        assert_state_field(state, "dock_status", "Idle")
        assert state.station_clean_water == 37


class TestUnsettingFixtures:
    def test_wifi_signal_68(self):
        fixture = load_fixture("mqtt/unsetting/wifi_signal_68.json")
        state = make_vacuum_state()
        new_state, changes = update_state(state, fixture["dps"])
        # Parser: wifi_signal = (ap_signal_strength / 2) - 100
        # ap_signal_strength=68 → (68/2) - 100 = -66.0
        assert_state_field(new_state, "wifi_signal", -66.0)
        assert_state_field(new_state, "child_lock", False)

    def test_wifi_signal_82(self):
        fixture = load_fixture("mqtt/unsetting/wifi_signal_82.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        # ap_signal_strength=82 → (82/2) - 100 = -59.0
        assert_state_field(new_state, "wifi_signal", -59.0)


class TestErrorCodeFixtures:
    def test_no_error_v2(self):
        fixture = load_fixture("mqtt/error_code/no_error_v2.json")
        state = make_vacuum_state(error_code=5, error_message="Some error")
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "error_code", 0)
        assert_state_field(new_state, "error_message", "")

    def test_no_error_warn_mask(self):
        fixture = load_fixture("mqtt/error_code/no_error_warn_mask.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "error_code", 0)
        assert_state_field(new_state, "error_message", "")

    def test_error_code_7002(self):
        """Real error=[7002] is surfaced from the error list."""
        fixture = load_fixture("mqtt/error_code/error_7002.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "error_code", 7002)
        assert_state_field(new_state, "error_message", EUFY_CLEAN_ERROR_CODES[7002])

    def test_error_code_7000(self):
        """Real error=[7000] is surfaced from the error list."""
        fixture = load_fixture("mqtt/error_code/error_7000.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "error_code", 7000)
        assert_state_field(new_state, "error_message", EUFY_CLEAN_ERROR_CODES[7000])


class TestUnknownDPSFixtures:
    def test_dps_178_no_crash(self):
        fixture = load_fixture("mqtt/unknown/dps_178.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "178" in new_state.raw_dps


class TestTelemetryFixtures:
    def test_position_update_extracts_coords(self):
        fixture = load_fixture("mqtt/telemetry/position_update.json")
        state = make_vacuum_state()
        new_state, changes = update_state(state, fixture["dps"])
        assert new_state.robot_position_x is not None
        assert new_state.robot_position_y is not None

    def test_position_ping_no_crash(self):
        fixture = load_fixture("mqtt/telemetry/position_ping.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "179" in new_state.raw_dps

    def test_status_report_no_crash(self):
        fixture = load_fixture("mqtt/telemetry/status_report.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "179" in new_state.raw_dps

    def test_multi_waypoint_no_crash(self):
        fixture = load_fixture("mqtt/telemetry/multi_waypoint.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "179" in new_state.raw_dps

    def test_full_status_report_no_crash(self):
        fixture = load_fixture("mqtt/telemetry/full_status_report.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "179" in new_state.raw_dps

    def test_sensor_readings_no_crash(self):
        fixture = load_fixture("mqtt/telemetry/sensor_readings.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "179" in new_state.raw_dps

    def test_short_report_no_crash(self):
        fixture = load_fixture("mqtt/telemetry/short_report.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "179" in new_state.raw_dps


class TestPreExistingFixtures:
    def test_consumable_full(self):
        fixture = load_fixture("mqtt/accessories/consumable_full.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert new_state.accessories.side_brush_usage == 9

    def test_consumable_no_runtime(self):
        fixture = load_fixture("mqtt/accessories/consumable_no_runtime.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert DPS_MAP["ACCESSORIES_STATUS"] in new_state.raw_dps

    def test_cleaning_params_request_format(self):
        fixture = load_fixture("mqtt/cleaning_params/request_format.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert DPS_MAP["CLEANING_PARAMETERS"] in new_state.raw_dps

    def test_cleaning_stats_response(self):
        fixture = load_fixture("mqtt/cleaning_stats/stats_response.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert DPS_MAP["CLEANING_STATISTICS"] in new_state.raw_dps

    def test_battery_0(self):
        fixture = load_fixture("mqtt/dps_plain/battery_0.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "battery_level", 0)

    def test_battery_50(self):
        fixture = load_fixture("mqtt/dps_plain/battery_50.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "battery_level", 50)

    def test_battery_100(self):
        fixture = load_fixture("mqtt/dps_plain/battery_100.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "battery_level", 100)

    def test_clean_speed_standard(self):
        fixture = load_fixture("mqtt/dps_plain/clean_speed_standard.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(
            new_state, "fan_speed", EUFY_CLEAN_NOVEL_CLEAN_SPEED[0].value
        )

    def test_find_robot_true(self):
        fixture = load_fixture("mqtt/dps_plain/find_robot_true.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "find_robot", True)

    def test_error_no_error(self):
        fixture = load_fixture("mqtt/error_code/no_error.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "error_code", 0)

    def test_error_wheel_stuck(self):
        fixture = load_fixture("mqtt/error_code/wheel_stuck.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert new_state.error_code != 0

    def test_map_data_room_params(self):
        fixture = load_fixture("mqtt/map_data/room_params.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert DPS_MAP["RESERVED2"] in new_state.raw_dps
        assert new_state.map_id == 8
        assert len(new_state.rooms) == 8
        room_names = [r["name"] for r in new_state.rooms]
        assert "Living Room" in room_names
        assert "Kitchen" in room_names

    def test_map_data_universal(self):
        fixture = load_fixture("mqtt/map_data/universal_data_response.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert DPS_MAP["RESERVED2"] in new_state.raw_dps

    def test_scene_info_list(self):
        fixture = load_fixture("mqtt/scene_info/scenes_list.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert isinstance(new_state.scenes, list)
        assert len(new_state.scenes) >= 1
        assert new_state.scenes[0]["name"] == "Daily"

    def test_station_drying(self):
        fixture = load_fixture("mqtt/station_status/drying.json")
        state, _ = update_state(VacuumState(), fixture["dps"])
        assert_state_field(state, "dock_status", "Drying")

    def test_station_emptying_dust(self):
        fixture = load_fixture("mqtt/station_status/emptying_dust.json")
        state, _ = update_state(VacuumState(), fixture["dps"])
        assert_state_field(state, "dock_status", "Emptying dust")

    def test_station_idle(self):
        fixture = load_fixture("mqtt/station_status/idle.json")
        state, _ = update_state(VacuumState(), fixture["dps"])
        assert_state_field(state, "dock_status", "Idle")

    def test_station_washing(self):
        fixture = load_fixture("mqtt/station_status/washing.json")
        state, _ = update_state(VacuumState(), fixture["dps"])
        assert state.dock_status in ("Washing", "Adding clean water")

    def test_task_status_cleaning(self):
        fixture = load_fixture("mqtt/task_status/cleaning.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "task_status", "Cleaning")

    def test_task_status_paused(self):
        fixture = load_fixture("mqtt/task_status/paused.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "task_status", "Paused")

    def test_task_status_returning_to_charge(self):
        fixture = load_fixture("mqtt/task_status/returning_to_charge.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "task_status", "Returning")


class TestUndisturbedFixtures:
    def test_dnd_enabled(self):
        fixture = load_fixture("mqtt/undisturbed/dnd_enabled.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "157" in new_state.raw_dps

    def test_dnd_disabled(self):
        fixture = load_fixture("mqtt/undisturbed/dnd_disabled.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "157" in new_state.raw_dps


class TestFindRobotFixtures:
    def test_find_robot_true_real(self):
        fixture = load_fixture("mqtt/dps_plain/find_robot_true.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "find_robot", True)

    def test_find_robot_false_real(self):
        fixture = load_fixture("mqtt/dps_plain/find_robot_false.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert_state_field(new_state, "find_robot", False)


class TestMapStreamFixtures:
    def test_map_stream_metadata(self):
        fixture = load_fixture("mqtt/map_data/map_stream_metadata.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "166" in new_state.raw_dps

    def test_map_stream_metadata_v2(self):
        fixture = load_fixture("mqtt/map_data/map_stream_metadata_v2.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "166" in new_state.raw_dps


class TestMultiMapFixtures:
    def test_multi_map_rename(self):
        fixture = load_fixture("mqtt/map_data/multi_map_rename.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "172" in new_state.raw_dps

    def test_multi_map_load_failed(self):
        fixture = load_fixture("mqtt/map_data/multi_map_load_failed.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "172" in new_state.raw_dps

    def test_multi_map_load_ok(self):
        fixture = load_fixture("mqtt/map_data/multi_map_load_ok.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "172" in new_state.raw_dps

    def test_multi_map_delete(self):
        fixture = load_fixture("mqtt/map_data/multi_map_delete.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "172" in new_state.raw_dps


class TestRoomParamsUnnamed:
    def test_room_params_unnamed(self):
        fixture = load_fixture("mqtt/map_data/room_params_unnamed.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert new_state.map_id == 15
        assert len(new_state.rooms) == 3


class TestPromptCodeFixtures:
    def test_prompt_code_45(self):
        fixture = load_fixture("mqtt/unknown/prompt_code_45.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "178" in new_state.raw_dps

    def test_prompt_code_6533(self):
        fixture = load_fixture("mqtt/unknown/prompt_code_6533.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "178" in new_state.raw_dps

    def test_prompt_code_3024(self):
        fixture = load_fixture("mqtt/unknown/prompt_code_3024.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert "178" in new_state.raw_dps


class TestWarnCodeFixtures:
    def test_warn_6011(self):
        fixture = load_fixture("mqtt/error_code/warn_6011.json")
        state = make_vacuum_state()
        new_state, _ = update_state(state, fixture["dps"])
        assert new_state.error_code == 6011


class TestStationStatusNewFixtures:
    def test_station_idle_empty_tank(self):
        fixture = load_fixture("mqtt/station_status/idle_empty_tank.json")
        state, _ = update_state(VacuumState(), fixture["dps"])
        assert_state_field(state, "dock_status", "Idle")

    def test_station_drying_complete(self):
        fixture = load_fixture("mqtt/station_status/drying_complete.json")
        state, _ = update_state(VacuumState(), fixture["dps"])
        assert_state_field(state, "dock_status", "Drying")


class TestAdditionalCapturedValues:
    """Exercises every additional_captured_values entry across all fixtures.

    Each entry is a semantic duplicate of its parent fixture's primary DPS
    value (different only in timestamps, water levels, or sequence numbers).
    Parsing must not crash and must produce the same semantic outcome.
    """

    @staticmethod
    def _collect_additional_pairs():
        """Yield (fixture_path, primary_dps, additional_dps) for every entry."""
        from pathlib import Path

        fixtures_root = Path(__file__).resolve().parents[1] / "fixtures" / "mqtt"
        for fixture_path in sorted(fixtures_root.glob("**/*.json")):
            with fixture_path.open() as fh:
                d = json.load(fh)
            acvs = d.get("additional_captured_values", [])
            if not acvs:
                continue
            primary_dps = d["dps"]
            for acv in acvs:
                yield str(fixture_path), primary_dps, acv["dps"]

    def test_all_additional_values_parse_without_crash(self):
        pairs = list(self._collect_additional_pairs())
        assert len(pairs) > 0, "No additional_captured_values found"
        for fpath, primary_dps, extra_dps in pairs:
            state = make_vacuum_state()
            new_state, _ = update_state(state, extra_dps)
            for dps_key in extra_dps:
                assert (
                    dps_key in new_state.raw_dps
                ), f"{fpath}: DPS {dps_key} missing from raw_dps"

    def test_additional_values_match_primary_semantics(self):
        pairs = list(self._collect_additional_pairs())
        for fpath, primary_dps, extra_dps in pairs:
            state = make_vacuum_state()
            primary_state, _ = update_state(state, primary_dps)
            extra_state, _ = update_state(state, extra_dps)
            assert (
                primary_state.activity == extra_state.activity
            ), f"{fpath}: activity mismatch {primary_state.activity!r} vs {extra_state.activity!r}"
            assert (
                primary_state.dock_status == extra_state.dock_status
            ), f"{fpath}: dock_status mismatch {primary_state.dock_status!r} vs {extra_state.dock_status!r}"
            assert (
                primary_state.error_code == extra_state.error_code
            ), f"{fpath}: error_code mismatch {primary_state.error_code!r} vs {extra_state.error_code!r}"
