from __future__ import annotations

from custom_components.robovac_mqtt.api.commands import build_command
from custom_components.robovac_mqtt.const import (
    DPS_MAP,
    EUFY_CLEAN_CONTROL,
)
from custom_components.robovac_mqtt.proto.cloud.clean_param_pb2 import (
    CleanExtent,
    CleanParamRequest,
    CleanType,
    MopMode,
)
from custom_components.robovac_mqtt.proto.cloud.consumable_pb2 import ConsumableRequest
from custom_components.robovac_mqtt.proto.cloud.control_pb2 import ModeCtrlRequest
from custom_components.robovac_mqtt.proto.cloud.map_edit_pb2 import MapEditRequest
from custom_components.robovac_mqtt.proto.cloud.station_pb2 import StationRequest
from custom_components.robovac_mqtt.proto.cloud.undisturbed_pb2 import (
    UndisturbedRequest,
)
from custom_components.robovac_mqtt.proto.cloud.unisetting_pb2 import UnisettingRequest
from custom_components.robovac_mqtt.utils import decode

DPS_PLAY_PAUSE = DPS_MAP["PLAY_PAUSE"]
DPS_GO_HOME = DPS_MAP["GO_HOME"]
DPS_CLEAN_SPEED = DPS_MAP["CLEAN_SPEED"]
DPS_FIND_ROBOT = DPS_MAP["FIND_ROBOT"]
DPS_CLEANING_PARAMS = DPS_MAP["CLEANING_PARAMETERS"]
DPS_ACCESSORIES = DPS_MAP["ACCESSORIES_STATUS"]
DPS_MAP_EDIT_REQ = DPS_MAP["MAP_EDIT_REQUEST"]
DPS_UNSETTING = DPS_MAP["UNSETTING"]
DPS_UNDISTURBED = DPS_MAP["UNDISTURBED"]


def _decode_mode_ctrl(result: dict[str, str]) -> ModeCtrlRequest:
    assert DPS_PLAY_PAUSE in result
    return decode(ModeCtrlRequest, result[DPS_PLAY_PAUSE])


def _decode_station(result: dict[str, str]) -> StationRequest:
    assert DPS_GO_HOME in result
    return decode(StationRequest, result[DPS_GO_HOME])


class TestModeControlCommands:

    def test_start_auto(self):
        result = build_command("start_auto")
        proto = _decode_mode_ctrl(result)
        assert proto.method == EUFY_CLEAN_CONTROL.START_AUTO_CLEAN
        assert proto.auto_clean.clean_times == 1
        assert proto.auto_clean.force_mapping is False

    def test_pause(self):
        result = build_command("pause")
        proto = _decode_mode_ctrl(result)
        assert proto.method == EUFY_CLEAN_CONTROL.PAUSE_TASK

    def test_resume(self):
        result = build_command("resume")
        proto = _decode_mode_ctrl(result)
        assert proto.method == EUFY_CLEAN_CONTROL.RESUME_TASK

    def test_stop(self):
        result = build_command("stop")
        proto = _decode_mode_ctrl(result)
        assert proto.method == EUFY_CLEAN_CONTROL.STOP_TASK

    def test_go_home(self):
        result = build_command("go_home")
        proto = _decode_mode_ctrl(result)
        assert proto.method == EUFY_CLEAN_CONTROL.START_GOHOME

    def test_clean_spot(self):
        result = build_command("clean_spot")
        proto = _decode_mode_ctrl(result)
        assert proto.method == EUFY_CLEAN_CONTROL.START_SPOT_CLEAN
        assert proto.spot_clean.clean_times == 1

    def test_scene_clean(self):
        result = build_command("scene_clean", scene_id=42)
        proto = _decode_mode_ctrl(result)
        assert proto.method == EUFY_CLEAN_CONTROL.START_SCENE_CLEAN
        assert proto.scene_clean.scene_id == 42

    def test_room_clean_general(self):
        result = build_command("room_clean", room_ids=[1, 2, 3], map_id=5)
        proto = _decode_mode_ctrl(result)
        assert proto.method == EUFY_CLEAN_CONTROL.START_SELECT_ROOMS_CLEAN
        assert proto.select_rooms_clean.map_id == 5
        assert proto.select_rooms_clean.clean_times == 1
        assert len(proto.select_rooms_clean.rooms) == 3
        for i, room in enumerate(proto.select_rooms_clean.rooms):
            assert room.id == i + 1
            assert room.order == i + 1

    def test_room_clean_customize_mode(self):
        result = build_command(
            "room_clean", room_ids=[10, 20], map_id=3, mode="CUSTOMIZE"
        )
        proto = _decode_mode_ctrl(result)
        assert proto.method == EUFY_CLEAN_CONTROL.START_SELECT_ROOMS_CLEAN
        assert proto.select_rooms_clean.mode == 1

    def test_room_clean_default_map_id(self):
        result = build_command("room_clean", room_ids=[1])
        proto = _decode_mode_ctrl(result)
        assert proto.select_rooms_clean.map_id == 3


class TestCommandAliases:

    def test_play_is_resume(self):
        result = build_command("play")
        proto = _decode_mode_ctrl(result)
        assert proto.method == EUFY_CLEAN_CONTROL.RESUME_TASK

    def test_return_to_base_is_go_home(self):
        result = build_command("return_to_base")
        proto = _decode_mode_ctrl(result)
        assert proto.method == EUFY_CLEAN_CONTROL.START_GOHOME

    def test_find_robot_is_locate(self):
        result_locate = build_command("locate")
        result_find = build_command("find_robot")
        assert result_locate == result_find
        assert DPS_FIND_ROBOT in result_locate
        assert result_locate[DPS_FIND_ROBOT] is True


class TestStationCommands:

    def test_go_dry(self):
        result = build_command("go_dry")
        proto = _decode_station(result)
        assert proto.manual_cmd.go_dry is True

    def test_stop_dry(self):
        result = build_command("stop_dry")
        proto = _decode_station(result)
        assert proto.manual_cmd.go_dry is False

    def test_go_selfcleaning(self):
        result = build_command("go_selfcleaning")
        proto = _decode_station(result)
        assert proto.manual_cmd.go_selfcleaning is True

    def test_collect_dust(self):
        result = build_command("collect_dust")
        proto = _decode_station(result)
        assert proto.manual_cmd.go_collect_dust is True

    def test_set_auto_cfg(self):
        cfg = {"detergent": True}
        result = build_command("set_auto_cfg", cfg=cfg)
        proto = _decode_station(result)
        assert proto.auto_cfg.detergent is True


class TestPlainValueCommands:

    def test_locate_active(self):
        result = build_command("locate", active=True)
        assert DPS_FIND_ROBOT in result
        assert result[DPS_FIND_ROBOT] is True

    def test_locate_inactive(self):
        result = build_command("locate", active=False)
        assert DPS_FIND_ROBOT in result
        assert result[DPS_FIND_ROBOT] is False

    def test_set_fan_speed_quiet(self):
        result = build_command("set_fan_speed", fan_speed="Quiet")
        assert DPS_CLEAN_SPEED in result
        assert result[DPS_CLEAN_SPEED] == "0"

    def test_set_fan_speed_standard(self):
        result = build_command("set_fan_speed", fan_speed="Standard")
        assert DPS_CLEAN_SPEED in result
        assert result[DPS_CLEAN_SPEED] == "1"

    def test_set_fan_speed_turbo(self):
        result = build_command("set_fan_speed", fan_speed="Turbo")
        assert DPS_CLEAN_SPEED in result
        assert result[DPS_CLEAN_SPEED] == "2"

    def test_set_fan_speed_max(self):
        result = build_command("set_fan_speed", fan_speed="Max")
        assert DPS_CLEAN_SPEED in result
        assert result[DPS_CLEAN_SPEED] == "3"

    def test_set_fan_speed_boost_iq(self):
        result = build_command("set_fan_speed", fan_speed="Boost_IQ")
        assert DPS_CLEAN_SPEED in result
        assert result[DPS_CLEAN_SPEED] == "4"

    def test_set_fan_speed_case_insensitive(self):
        result = build_command("set_fan_speed", fan_speed="turbo")
        assert DPS_CLEAN_SPEED in result
        assert result[DPS_CLEAN_SPEED] == "2"

    def test_set_fan_speed_invalid_returns_empty(self):
        result = build_command("set_fan_speed", fan_speed="NonExistent")
        assert result == {}


class TestCleanParamCommands:

    def test_set_cleaning_mode_vacuum(self):
        result = build_command("set_cleaning_mode", clean_mode="vacuum")
        assert DPS_CLEANING_PARAMS in result
        proto = decode(CleanParamRequest, result[DPS_CLEANING_PARAMS])
        assert proto.clean_param.clean_type.value == CleanType.SWEEP_ONLY

    def test_set_cleaning_mode_mop(self):
        result = build_command("set_cleaning_mode", clean_mode="mop")
        assert DPS_CLEANING_PARAMS in result
        proto = decode(CleanParamRequest, result[DPS_CLEANING_PARAMS])
        assert proto.clean_param.clean_type.value == CleanType.MOP_ONLY

    def test_set_cleaning_mode_vacuum_mop(self):
        result = build_command("set_cleaning_mode", clean_mode="vacuum_mop")
        assert DPS_CLEANING_PARAMS in result
        proto = decode(CleanParamRequest, result[DPS_CLEANING_PARAMS])
        assert proto.clean_param.clean_type.value == CleanType.SWEEP_AND_MOP

    def test_set_cleaning_mode_invalid_returns_empty(self):
        result = build_command("set_cleaning_mode", clean_mode="bogus")
        assert result == {}

    def test_set_water_level_low(self):
        result = build_command("set_water_level", water_level="low")
        assert DPS_CLEANING_PARAMS in result
        proto = decode(CleanParamRequest, result[DPS_CLEANING_PARAMS])
        assert proto.clean_param.mop_mode.level == MopMode.LOW

    def test_set_water_level_high(self):
        result = build_command("set_water_level", water_level="high")
        assert DPS_CLEANING_PARAMS in result
        proto = decode(CleanParamRequest, result[DPS_CLEANING_PARAMS])
        assert proto.clean_param.mop_mode.level == MopMode.HIGH

    def test_set_water_level_invalid_returns_empty(self):
        result = build_command("set_water_level", water_level="super_high")
        assert result == {}

    def test_set_cleaning_intensity_standard(self):
        result = build_command(
            "set_cleaning_intensity", cleaning_intensity="standard"
        )
        assert DPS_CLEANING_PARAMS in result
        proto = decode(CleanParamRequest, result[DPS_CLEANING_PARAMS])
        assert proto.clean_param.clean_extent.value == CleanExtent.NORMAL

    def test_set_cleaning_intensity_quick(self):
        result = build_command("set_cleaning_intensity", cleaning_intensity="quick")
        assert DPS_CLEANING_PARAMS in result
        proto = decode(CleanParamRequest, result[DPS_CLEANING_PARAMS])
        assert proto.clean_param.clean_extent.value == CleanExtent.QUICK

    def test_set_cleaning_intensity_invalid_returns_empty(self):
        result = build_command(
            "set_cleaning_intensity", cleaning_intensity="ultra_deep"
        )
        assert result == {}


class TestAccessoryCommands:

    def test_reset_accessory_side_brush(self):
        result = build_command("reset_accessory", reset_type=0)
        assert DPS_ACCESSORIES in result
        proto = decode(ConsumableRequest, result[DPS_ACCESSORIES])
        assert ConsumableRequest.SIDE_BRUSH in proto.reset_types

    def test_reset_accessory_rolling_brush(self):
        result = build_command("reset_accessory", reset_type=1)
        assert DPS_ACCESSORIES in result
        proto = decode(ConsumableRequest, result[DPS_ACCESSORIES])
        assert ConsumableRequest.ROLLING_BRUSH in proto.reset_types


class TestMapEditCommands:

    def test_set_room_custom_basic(self):
        room_config = [{"id": 1}, {"id": 2}]
        result = build_command("set_room_custom", room_config=room_config, map_id=5)
        assert DPS_MAP_EDIT_REQ in result
        proto = decode(MapEditRequest, result[DPS_MAP_EDIT_REQ])
        assert proto.map_id == 5
        assert proto.method == MapEditRequest.SET_ROOMS_CUSTOM
        rooms = proto.rooms_custom.rooms_parm.rooms
        assert len(rooms) == 2
        assert rooms[0].id == 1
        assert rooms[1].id == 2

    def test_set_room_custom_with_fan_speed(self):
        room_config = [{"id": 1, "fan_speed": "Turbo"}]
        result = build_command("set_room_custom", room_config=room_config)
        assert DPS_MAP_EDIT_REQ in result
        proto = decode(MapEditRequest, result[DPS_MAP_EDIT_REQ])
        room = proto.rooms_custom.rooms_parm.rooms[0]
        assert room.id == 1
        assert room.custom.fan.suction == 2

    def test_set_room_custom_default_map_id(self):
        room_config = [{"id": 1}]
        result = build_command("set_room_custom", room_config=room_config)
        proto = decode(MapEditRequest, result[DPS_MAP_EDIT_REQ])
        assert proto.map_id == 3

    def test_set_room_custom_legacy_list_of_ints(self):
        result = build_command(
            "set_room_custom", room_config=[1, 2], map_id=3, fan_speed="Standard"
        )
        assert DPS_MAP_EDIT_REQ in result
        proto = decode(MapEditRequest, result[DPS_MAP_EDIT_REQ])
        rooms = proto.rooms_custom.rooms_parm.rooms
        assert len(rooms) == 2
        assert rooms[0].custom.fan.suction == 1
        assert rooms[1].custom.fan.suction == 1


class TestChildLockCommand:

    def test_set_child_lock_on(self):
        result = build_command("set_child_lock", active=True)
        assert DPS_UNSETTING in result
        proto = decode(UnisettingRequest, result[DPS_UNSETTING])
        assert proto.children_lock.value is True

    def test_set_child_lock_off(self):
        result = build_command("set_child_lock", active=False)
        assert DPS_UNSETTING in result
        proto = decode(UnisettingRequest, result[DPS_UNSETTING])
        assert proto.children_lock.value is False


class TestDoNotDisturbCommand:
    """DPS 157 (NOT 178) — critical routing assertion."""

    def test_set_do_not_disturb_defaults(self):
        result = build_command("set_do_not_disturb")
        assert DPS_UNDISTURBED in result
        assert "178" not in result
        proto = decode(UndisturbedRequest, result[DPS_UNDISTURBED])
        assert proto.undisturbed.sw.value is True
        assert proto.undisturbed.begin.hour == 22
        assert proto.undisturbed.begin.minute == 0
        assert proto.undisturbed.end.hour == 8
        assert proto.undisturbed.end.minute == 0

    def test_set_do_not_disturb_custom_times(self):
        result = build_command(
            "set_do_not_disturb",
            active=True,
            begin_hour=23,
            begin_minute=30,
            end_hour=7,
            end_minute=15,
        )
        assert DPS_UNDISTURBED in result
        proto = decode(UndisturbedRequest, result[DPS_UNDISTURBED])
        assert proto.undisturbed.begin.hour == 23
        assert proto.undisturbed.begin.minute == 30
        assert proto.undisturbed.end.hour == 7
        assert proto.undisturbed.end.minute == 15

    def test_set_do_not_disturb_disabled(self):
        result = build_command("set_do_not_disturb", active=False)
        assert DPS_UNDISTURBED in result
        proto = decode(UndisturbedRequest, result[DPS_UNDISTURBED])
        assert proto.undisturbed.sw.value is False


class TestInvalidCommands:

    def test_unknown_command_returns_empty(self):
        assert build_command("nonexistent_command") == {}

    def test_unknown_command_with_params_returns_empty(self):
        assert build_command("totally_bogus", foo="bar") == {}

    def test_empty_string_command_returns_empty(self):
        assert build_command("") == {}

    def test_case_insensitive_command(self):
        result = build_command("START_AUTO")
        proto = _decode_mode_ctrl(result)
        assert proto.method == EUFY_CLEAN_CONTROL.START_AUTO_CLEAN
