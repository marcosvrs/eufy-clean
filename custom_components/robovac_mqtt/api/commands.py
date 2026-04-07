from __future__ import annotations

import logging
from typing import Any, cast

from ..const import (
    CARPET_STRATEGY_REVERSE,
    CLEAN_EXTENT_MAP,
    CLEAN_TYPE_MAP,
    CORNER_CLEANING_REVERSE,
    DEFAULT_DPS_MAP,
    EUFY_CLEAN_CONTROL,
    EUFY_CLEAN_NOVEL_CLEAN_SPEED,
    MEDIA_RESOLUTION_REVERSE,
    MOP_CORNER_MAP,
    MOP_LEVEL_MAP,
)
from ..proto.cloud.clean_param_pb2 import CleanParam, CleanParamRequest, Fan
from ..proto.cloud.error_code_pb2 import ErrorCode, ErrorSetting
from ..proto.cloud.consumable_pb2 import ConsumableRequest
from ..proto.cloud.common_pb2 import Point, Quadrangle
from ..proto.cloud.control_pb2 import (
    GlobalCruise,
    Goto,
    ModeCtrlRequest,
    PointCruise,
    SelectRoomsClean,
    SelectZonesClean,
    SpotClean,
    ZonesCruise,
)
from ..proto.cloud.map_edit_pb2 import MapEditRequest
from ..proto.cloud.media_manager_pb2 import MediaManagerRequest, MediaSetting
from ..proto.cloud.station_pb2 import StationRequest
from ..proto.cloud.timing_pb2 import TimerInfo, TimerRequest
from ..proto.cloud.undisturbed_pb2 import UndisturbedRequest
from ..proto.cloud.unisetting_pb2 import UnisettingRequest
from ..utils import encode, encode_message

_LOGGER = logging.getLogger(__name__)


def _normalize_clean_mode(clean_mode: str) -> str:
    """Normalize a cleaning mode label into a map lookup key."""
    return clean_mode.strip().lower().replace("_", " ")


def build_set_cleaning_mode_command(
    clean_mode: str, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to set global cleaning mode."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    clean_type_val = CLEAN_TYPE_MAP.get(_normalize_clean_mode(clean_mode))
    if clean_type_val is None:
        _LOGGER.warning("Invalid clean_mode '%s' ignored", clean_mode)
        return {}

    req = CleanParamRequest(
        clean_param=CleanParam(clean_type={"value": clean_type_val}),
    )
    value = encode_message(req)
    return {dps_map["CLEANING_PARAMETERS"]: value}


def build_set_error_blocklist_command(
    suppressed_error_codes: list[int], dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP

    req = ErrorCode(
        setting=ErrorSetting(warn_mask=suppressed_error_codes),
    )
    value = encode_message(req)
    return {dps_map["ERROR_WARNING"]: value}


def _build_mode_ctrl(
    method: int, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Helper for ModeCtrlRequest commands."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    data: dict[str, Any] = {"method": int(method)}

    # Special handling for methods that require a parameter in the "oneof Param"
    if method == EUFY_CLEAN_CONTROL.START_AUTO_CLEAN:
        # AutoClean message: clean_times=1, force_mapping=False
        data["auto_clean"] = {"clean_times": 1, "force_mapping": False}
    elif method == EUFY_CLEAN_CONTROL.START_MAPPING_THEN_CLEAN:
        # AutoClean message: clean_times=1, force_mapping=True
        data["auto_clean"] = {"clean_times": 1, "force_mapping": True}
    elif method == EUFY_CLEAN_CONTROL.START_SPOT_CLEAN:
        # SpotClean message: clean_times=1
        data["spot_clean"] = {"clean_times": 1}

    value = encode(ModeCtrlRequest, data)
    return {dps_map["PLAY_PAUSE"]: value}


def _build_manual_cmd(
    cmd_name: str, active: bool = True, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Helper for StationRequest manual commands."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    value = encode(StationRequest, {"manual_cmd": {cmd_name: active}})
    return {dps_map["GO_HOME"]: value}


def build_set_clean_speed_command(
    clean_speed: str, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to set fan speed."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    try:
        speed_lower = clean_speed.lower()
        variants = [s.lower() for s in EUFY_CLEAN_NOVEL_CLEAN_SPEED]

        if speed_lower in variants:
            idx = variants.index(speed_lower)
            return {dps_map["CLEAN_SPEED"]: str(idx) if isinstance(idx, int) else idx}

    except ValueError:
        pass

    return {}


def build_set_water_level_command(
    water_level: str, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to set global mop water level."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    level_val = MOP_LEVEL_MAP.get(water_level.lower())
    if level_val is None:
        _LOGGER.warning("Invalid water_level '%s' ignored", water_level)
        return {}
    req = CleanParamRequest(
        clean_param=CleanParam(mop_mode={"level": level_val}),
    )
    value = encode_message(req)
    return {dps_map["CLEANING_PARAMETERS"]: value}


def build_set_cleaning_intensity_command(
    cleaning_intensity: str, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to set global cleaning intensity."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    extent_val = CLEAN_EXTENT_MAP.get(cleaning_intensity.lower())
    if extent_val is None:
        _LOGGER.warning("Invalid cleaning_intensity '%s' ignored", cleaning_intensity)
        return {}

    req = CleanParamRequest(
        clean_param=CleanParam(clean_extent={"value": extent_val}),
    )
    value = encode_message(req)
    return {dps_map["CLEANING_PARAMETERS"]: value}


def build_scene_clean_command(
    scene_id: int, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to trigger a specific scene."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    value = encode(
        ModeCtrlRequest,
        {
            "method": EUFY_CLEAN_CONTROL.START_SCENE_CLEAN,
            "scene_clean": {"scene_id": scene_id},
        },
    )
    return {dps_map["PLAY_PAUSE"]: value}


def build_room_clean_command(
    room_ids: list[int],
    map_id: int = 3,
    mode: str = "GENERAL",
    dps_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build command to clean specific rooms."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    if mode == "CUSTOMIZE":
        proto_mode = SelectRoomsClean.CUSTOMIZE
    else:
        proto_mode = SelectRoomsClean.GENERAL

    rooms_clean = SelectRoomsClean(
        rooms=[
            SelectRoomsClean.Room(id=rid, order=i + 1) for i, rid in enumerate(room_ids)
        ],
        mode=proto_mode,
        clean_times=1,
        map_id=map_id,
    )
    value = encode_message(
        ModeCtrlRequest(
            method=cast(
                ModeCtrlRequest.Method, int(EUFY_CLEAN_CONTROL.START_SELECT_ROOMS_CLEAN)
            ),
            select_rooms_clean=rooms_clean,
        )
    )
    return {dps_map["PLAY_PAUSE"]: value}


def build_zone_clean_command(
    zones: list[dict[str, Any]],
    map_id: int = 0,
    dps_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build command to clean specific rectangular zones."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP

    zone_protos = []
    for z in zones:
        quad = Quadrangle(
            p0=Point(x=z.get("x1", 0), y=z.get("y1", 0)),
            p1=Point(x=z.get("x2", 0), y=z.get("y1", 0)),
            p2=Point(x=z.get("x2", 0), y=z.get("y2", 0)),
            p3=Point(x=z.get("x1", 0), y=z.get("y2", 0)),
        )
        zone_protos.append(
            SelectZonesClean.Zone(
                quadrangle=quad,
                clean_times=z.get("clean_times", 1),
            )
        )

    zones_clean = SelectZonesClean(zones=zone_protos, map_id=map_id)
    value = encode_message(
        ModeCtrlRequest(
            method=cast(
                ModeCtrlRequest.Method,
                int(EUFY_CLEAN_CONTROL.START_SELECT_ZONES_CLEAN),
            ),
            select_zones_clean=zones_clean,
        )
    )
    return {dps_map["PLAY_PAUSE"]: value}


def build_spot_clean_command(
    clean_times: int = 1,
    dps_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build command to clean current position (spot clean)."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP

    value = encode_message(
        ModeCtrlRequest(
            method=cast(
                ModeCtrlRequest.Method,
                int(EUFY_CLEAN_CONTROL.START_SPOT_CLEAN),
            ),
            spot_clean=SpotClean(clean_times=clean_times),
        )
    )
    return {dps_map["PLAY_PAUSE"]: value}


def build_goto_clean_command(
    x: int,
    y: int,
    map_id: int = 0,
    dps_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build command to go to specific coordinates and clean."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP

    go_to = Goto(destination=Point(x=x, y=y), map_id=map_id)
    value = encode_message(
        ModeCtrlRequest(
            method=cast(
                ModeCtrlRequest.Method,
                int(EUFY_CLEAN_CONTROL.START_GOTO_CLEAN),
            ),
            go_to=go_to,
        )
    )
    return {dps_map["PLAY_PAUSE"]: value}


def build_set_room_custom_command(
    room_config: list[dict[str, Any]] | list[int],
    map_id: int = 3,
    # Legacy arguments for backward compatibility (used if room_config is list[int])
    fan_speed: str | None = None,
    water_level: str | None = None,
    clean_times: int | None = None,
    clean_mode: str | None = None,
    clean_intensity: str | None = None,
    edge_mopping: bool | None = None,
    dps_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build command to set custom cleaning parameters for specific rooms.

    Supports two formats for `room_config`:
    1. list[int]: Simple list of room IDs. Applies global params (fan_speed, etc.) to all.
    2. list[dict]: List of room objects {id: 1, fan_speed: "Turbo", ...}.
    """
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    rooms_parm = MapEditRequest.RoomsCustom.Parm()

    # Normalize input to list of dicts
    normalized_rooms: list[dict[str, Any]] = []

    if room_config and isinstance(room_config[0], int):
        # Legacy format: [1, 2] + global params
        for r_id in room_config:
            normalized_rooms.append(
                {
                    "id": r_id,
                    "fan_speed": fan_speed,
                    "water_level": water_level,
                    "clean_times": clean_times,
                    "clean_mode": clean_mode,
                    "clean_intensity": clean_intensity,
                    "edge_mopping": edge_mopping,
                }
            )
    elif room_config:
        # New format: [{id: 1, fan_speed: ...}, ...]
        normalized_rooms = cast(list[dict[str, Any]], room_config)

    for room_data in normalized_rooms:
        room_id = room_data.get("id")
        if not room_id:
            continue

        custom_cfg = MapEditRequest.RoomsCustom.Parm.Room.Custom()

        # Extract per-room params
        r_fan_speed = room_data.get("fan_speed")
        r_water_level = room_data.get("water_level")
        r_clean_times = room_data.get("clean_times")
        r_clean_mode = room_data.get("clean_mode")
        r_clean_intensity = room_data.get("clean_intensity")
        r_edge_mopping = room_data.get("edge_mopping")

        # Clean Mode
        if r_clean_mode:
            clean_type_val = CLEAN_TYPE_MAP.get(_normalize_clean_mode(r_clean_mode))
            if clean_type_val is not None:
                custom_cfg.clean_type.value = clean_type_val
            else:
                _LOGGER.warning("Invalid clean_mode '%s' ignored", r_clean_mode)

        # Clean Times (Repeats)
        if r_clean_times:
            custom_cfg.clean_times = int(r_clean_times)

        # Clean Intensity (Extent)
        if r_clean_intensity:
            if r_clean_intensity.lower() in CLEAN_EXTENT_MAP:
                custom_cfg.clean_extent.value = CLEAN_EXTENT_MAP[
                    r_clean_intensity.lower()
                ]
            else:
                _LOGGER.warning(
                    "Invalid clean_intensity '%s' ignored", r_clean_intensity
                )

        # Edge Mopping (Corner Clean)
        if r_edge_mopping is not None:
            if r_edge_mopping in MOP_CORNER_MAP:
                custom_cfg.mop_mode.corner_clean = MOP_CORNER_MAP[r_edge_mopping]
            else:
                _LOGGER.warning("Invalid edge_mopping '%s' ignored", r_edge_mopping)

        # Fan Speed (Suction)
        if r_fan_speed:
            try:
                speed_lower = r_fan_speed.lower()
                variants = [s.lower() for s in EUFY_CLEAN_NOVEL_CLEAN_SPEED]
                if speed_lower in variants:
                    val = variants.index(speed_lower)
                    custom_cfg.fan.suction = cast(Fan.Suction, val)
                else:
                    _LOGGER.warning("Invalid fan_speed '%s' ignored", r_fan_speed)
            except ValueError:
                _LOGGER.warning("Error processing fan_speed '%s'", r_fan_speed)

        # Water Level (Mop Mode)
        if r_water_level:
            if r_water_level.lower() in MOP_LEVEL_MAP:
                custom_cfg.mop_mode.level = MOP_LEVEL_MAP[r_water_level.lower()]
            else:
                _LOGGER.warning("Invalid water_level '%s' ignored", r_water_level)

        # Create Room Message
        room_msg = MapEditRequest.RoomsCustom.Parm.Room()
        room_msg.id = int(room_id)
        room_msg.custom.CopyFrom(custom_cfg)
        rooms_parm.rooms.append(room_msg)

    # Wrap in MapEditRequest
    req = MapEditRequest(
        map_id=int(map_id),
        method=MapEditRequest.SET_ROOMS_CUSTOM,
        rooms_custom=MapEditRequest.RoomsCustom(
            rooms_parm=rooms_parm,
        ),
    )

    value = encode_message(req)
    return {dps_map["MAP_EDIT_REQUEST"]: value}


def build_start_global_cruise_command(
    map_id: int = 0,
    dps_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build command to start a global cruise."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    value = encode_message(
        ModeCtrlRequest(
            method=cast(
                ModeCtrlRequest.Method,
                int(EUFY_CLEAN_CONTROL.START_GLOBAL_CRUISE),
            ),
            global_cruise=GlobalCruise(map_id=map_id),
        )
    )
    return {dps_map["PLAY_PAUSE"]: value}


def build_start_point_cruise_command(
    x: int,
    y: int,
    map_id: int = 0,
    dps_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build command to start a point cruise to specific coordinates."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    value = encode_message(
        ModeCtrlRequest(
            method=cast(
                ModeCtrlRequest.Method,
                int(EUFY_CLEAN_CONTROL.START_POINT_CRUISE),
            ),
            point_cruise=PointCruise(
                points=Point(x=x, y=y),
                map_id=map_id,
            ),
        )
    )
    return {dps_map["PLAY_PAUSE"]: value}


def build_start_zones_cruise_command(
    points: list[dict[str, int]],
    map_id: int = 0,
    dps_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build command to start a zones cruise through specific points."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    point_protos = [Point(x=p.get("x", 0), y=p.get("y", 0)) for p in points]
    value = encode_message(
        ModeCtrlRequest(
            method=cast(
                ModeCtrlRequest.Method,
                int(EUFY_CLEAN_CONTROL.START_ZONES_CRUISE),
            ),
            zones_cruise=ZonesCruise(
                points=point_protos,
                map_id=map_id,
            ),
        )
    )
    return {dps_map["PLAY_PAUSE"]: value}


def build_stop_smart_follow_command(
    dps_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build command to stop smart follow mode."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    return _build_mode_ctrl(EUFY_CLEAN_CONTROL.STOP_SMART_FOLLOW, dps_map)


def build_reset_accessory_command(
    reset_type: int, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to reset accessory usage."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    value = encode(ConsumableRequest, {"reset_types": [reset_type]})
    return {dps_map["ACCESSORIES_STATUS"]: value}


def build_set_auto_action_cfg_command(
    cfg_dict: dict[str, Any], dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to set dock auto-action config."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    value = encode(StationRequest, {"auto_cfg": cfg_dict})
    return {dps_map["GO_HOME"]: value}


def build_find_robot_command(
    active: bool, dps_map: dict[str, str] | None = None
) -> dict[str, Any]:
    """Build command to find robot."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    # false = stop finding, true = start finding
    return {dps_map["FIND_ROBOT"]: active}


_UNISETTING_SWITCH_FIELDS = [
    "ai_see",
    "pet_mode_sw",
    "poop_avoidance_sw",
    "live_photo_sw",
    "deep_mop_corner_sw",
    "smart_follow_sw",
    "cruise_continue_sw",
    "multi_map_sw",
    "suggest_restricted_zone_sw",
    "water_level_sw",
]


def build_set_unisetting_command(
    field_name: str,
    value: Any,
    current_state: Any,
    dps_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build UnisettingRequest preserving all current switch states (Read-Modify-Write)."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP

    payload: dict[str, Any] = {}
    payload["children_lock"] = {"value": current_state.child_lock}

    for sw in _UNISETTING_SWITCH_FIELDS:
        payload[sw] = {"value": getattr(current_state, sw, False)}

    payload["dust_full_remind"] = {"value": current_state.dust_full_remind}

    if field_name == "dust_full_remind":
        payload["dust_full_remind"] = {"value": int(value)}
    else:
        payload[field_name] = {"value": bool(value)}

    encoded = encode(UnisettingRequest, payload)
    return {dps_map["UNSETTING"]: encoded}


def build_set_child_lock_command(
    active: bool, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to toggle the child lock setting."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    value = encode(UnisettingRequest, {"children_lock": {"value": active}})
    return {dps_map["UNSETTING"]: value}


def build_set_undisturbed_command(
    active: bool,
    begin_hour: int,
    begin_minute: int,
    end_hour: int,
    end_minute: int,
    dps_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build command to update the Do Not Disturb schedule."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    value = encode(
        UndisturbedRequest,
        {
            "undisturbed": {
                "sw": {"value": active},
                "begin": {"hour": begin_hour, "minute": begin_minute},
                "end": {"hour": end_hour, "minute": end_minute},
            }
        },
    )
    return {dps_map["UNDISTURBED"]: value}


def build_set_carpet_strategy_command(
    carpet_strategy: str, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to set carpet cleaning strategy."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    strategy_val = CARPET_STRATEGY_REVERSE.get(carpet_strategy)
    if strategy_val is None:
        _LOGGER.warning("Invalid carpet_strategy '%s' ignored", carpet_strategy)
        return {}
    req = CleanParamRequest(
        clean_param=CleanParam(clean_carpet={"strategy": strategy_val}),
    )
    value = encode_message(req)
    return {dps_map["CLEANING_PARAMETERS"]: value}


def build_set_corner_cleaning_command(
    corner_cleaning: str, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to set corner cleaning mode."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    corner_val = CORNER_CLEANING_REVERSE.get(corner_cleaning)
    if corner_val is None:
        _LOGGER.warning("Invalid corner_cleaning '%s' ignored", corner_cleaning)
        return {}
    req = CleanParamRequest(
        clean_param=CleanParam(mop_mode={"corner_clean": corner_val}),
    )
    value = encode_message(req)
    return {dps_map["CLEANING_PARAMETERS"]: value}


def build_set_smart_mode_command(
    active: bool, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to toggle smart mode."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    req = CleanParamRequest(
        clean_param=CleanParam(smart_mode_sw={"value": active}),
    )
    value = encode_message(req)
    return {dps_map["CLEANING_PARAMETERS"]: value}


def build_set_boost_iq_command(
    active: bool, dps_map: dict[str, str] | None = None
) -> dict[str, Any]:
    """Build command to toggle boost IQ."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    return {dps_map["BOOST_IQ"]: active}


def build_set_volume_command(
    volume: int, dps_map: dict[str, str] | None = None
) -> dict[str, Any]:
    """Build command to set voice volume."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    return {dps_map["VOLUME"]: volume}


def build_timer_inquiry_command(
    dps_map: dict[str, str] | None = None,
) -> dict[str, str]:
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    value = encode(TimerRequest, {"method": TimerRequest.INQUIRY})
    return {dps_map["TIMING"]: value}


def build_timer_add_command(
    timer_info: dict[str, Any], dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to add a new timer schedule (no id field per proto spec)."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    req = TimerRequest(method=TimerRequest.ADD, timer=TimerInfo(**timer_info))
    value = encode_message(req)
    return {dps_map["TIMING"]: value}


def build_timer_delete_command(
    timer_id: int, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to delete a timer schedule (only id required)."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    req = TimerRequest(
        method=TimerRequest.DELETE,
        timer=TimerInfo(id=TimerInfo.Id(value=timer_id)),
    )
    value = encode_message(req)
    return {dps_map["TIMING"]: value}


def build_timer_modify_command(
    timer_info: dict[str, Any], dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to modify an existing timer (full fields required)."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    req = TimerRequest(method=TimerRequest.MOTIFY, timer=TimerInfo(**timer_info))
    value = encode_message(req)
    return {dps_map["TIMING"]: value}


def build_timer_open_command(
    timer_id: int, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to enable a timer schedule (only id required)."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    req = TimerRequest(
        method=TimerRequest.OPEN,
        timer=TimerInfo(id=TimerInfo.Id(value=timer_id)),
    )
    value = encode_message(req)
    return {dps_map["TIMING"]: value}


def build_timer_close_command(
    timer_id: int, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    """Build command to disable a timer schedule (only id required)."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    req = TimerRequest(
        method=TimerRequest.CLOSE,
        timer=TimerInfo(id=TimerInfo.Id(value=timer_id)),
    )
    value = encode_message(req)
    return {dps_map["TIMING"]: value}


def build_media_capture_command(
    seq: int = 1, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    req = MediaManagerRequest(
        control=MediaManagerRequest.Control(
            method=MediaManagerRequest.Control.CAPTURE,
            seq=seq,
        ),
    )
    value = encode_message(req)
    return {dps_map["MEDIA_MANAGER"]: value}


def build_media_record_command(
    start: bool, seq: int = 1, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    method = (
        MediaManagerRequest.Control.RECORD_START
        if start
        else MediaManagerRequest.Control.RECORD_STOP
    )
    req = MediaManagerRequest(
        control=MediaManagerRequest.Control(method=method, seq=seq),
    )
    value = encode_message(req)
    return {dps_map["MEDIA_MANAGER"]: value}


def build_media_set_resolution_command(
    resolution: str, dps_map: dict[str, str] | None = None
) -> dict[str, str]:
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    res_val = MEDIA_RESOLUTION_REVERSE.get(resolution)
    if res_val is None:
        _LOGGER.warning("Invalid media resolution '%s' ignored", resolution)
        return {}
    _RESOLUTION_TO_PROTO = {
        0: MediaSetting.R_480P,
        1: MediaSetting.R_720P,
        2: MediaSetting.R_1080P,
    }
    proto_res = _RESOLUTION_TO_PROTO.get(res_val)
    if proto_res is None:
        _LOGGER.warning("Invalid media resolution '%s' ignored", resolution)
        return {}
    req = MediaManagerRequest(
        setting=MediaSetting(
            record=MediaSetting.Record(resolution=proto_res),
        ),
    )
    value = encode_message(req)
    return {dps_map["MEDIA_MANAGER"]: value}


def build_generic_command(dp_id: str, value: Any) -> dict[str, Any]:
    """Build a generic command for simple-type DPS (Bool/Value/Enum).

    No protobuf encoding — value sent as-is.
    """
    return {dp_id: value}


def build_command(
    command: str, dps_map: dict[str, str] | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Unified command builder."""
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP
    cmd = command.lower()

    # Mode Control
    if cmd == "start_auto":
        return _build_mode_ctrl(EUFY_CLEAN_CONTROL.START_AUTO_CLEAN, dps_map)
    if cmd in ("play", "resume"):
        return _build_mode_ctrl(EUFY_CLEAN_CONTROL.RESUME_TASK, dps_map)
    if cmd == "pause":
        return _build_mode_ctrl(EUFY_CLEAN_CONTROL.PAUSE_TASK, dps_map)
    if cmd == "stop":
        return _build_mode_ctrl(EUFY_CLEAN_CONTROL.STOP_TASK, dps_map)
    if cmd in ("return_to_base", "go_home"):
        return _build_mode_ctrl(EUFY_CLEAN_CONTROL.START_GOHOME, dps_map)
    if cmd == "clean_spot":
        return _build_mode_ctrl(EUFY_CLEAN_CONTROL.START_SPOT_CLEAN, dps_map)
    if cmd == "start_rc":
        return _build_mode_ctrl(EUFY_CLEAN_CONTROL.START_RC_CLEAN, dps_map)
    if cmd == "stop_rc":
        return _build_mode_ctrl(EUFY_CLEAN_CONTROL.STOP_RC_CLEAN, dps_map)
    if cmd == "stop_gohome":
        return _build_mode_ctrl(EUFY_CLEAN_CONTROL.STOP_GOHOME, dps_map)
    if cmd == "mapping_then_clean":
        return _build_mode_ctrl(EUFY_CLEAN_CONTROL.START_MAPPING_THEN_CLEAN, dps_map)
    if cmd in ("locate", "find_robot"):
        return build_find_robot_command(kwargs.get("active", True), dps_map)
    if cmd == "start_global_cruise":
        return build_start_global_cruise_command(
            kwargs.get("map_id", 0), dps_map
        )
    if cmd == "start_point_cruise":
        return build_start_point_cruise_command(
            kwargs.get("x", 0),
            kwargs.get("y", 0),
            kwargs.get("map_id", 0),
            dps_map,
        )
    if cmd == "start_zones_cruise":
        return build_start_zones_cruise_command(
            kwargs.get("points", []),
            kwargs.get("map_id", 0),
            dps_map,
        )
    if cmd == "stop_smart_follow":
        return build_stop_smart_follow_command(dps_map)

    # Manual Control
    if cmd == "go_dry":
        return _build_manual_cmd("go_dry", True, dps_map)
    if cmd == "stop_dry":
        return _build_manual_cmd("go_dry", False, dps_map)
    if cmd == "go_selfcleaning":
        return _build_manual_cmd("go_selfcleaning", True, dps_map)
    if cmd == "collect_dust":
        return _build_manual_cmd("go_collect_dust", True, dps_map)

    # Complex
    if cmd == "set_cleaning_mode":
        return build_set_cleaning_mode_command(kwargs.get("clean_mode", ""), dps_map)
    if cmd == "set_cleaning_intensity":
        return build_set_cleaning_intensity_command(
            kwargs.get("cleaning_intensity", ""), dps_map
        )
    if cmd == "set_fan_speed":
        return build_set_clean_speed_command(kwargs.get("fan_speed", ""), dps_map)
    if cmd == "set_water_level":
        return build_set_water_level_command(kwargs.get("water_level", ""), dps_map)
    if cmd == "scene_clean":
        return build_scene_clean_command(int(kwargs.get("scene_id", 0)), dps_map)
    if cmd == "room_clean":
        return build_room_clean_command(
            kwargs.get("room_ids", []),
            kwargs.get("map_id", 3),
            kwargs.get("mode", "GENERAL"),
            dps_map,
        )
    if cmd == "zone_clean":
        return build_zone_clean_command(
            kwargs.get("zones", []),
            kwargs.get("map_id", 0),
            dps_map,
        )
    if cmd == "spot_clean":
        return build_spot_clean_command(
            kwargs.get("clean_times", 1),
            dps_map,
        )
    if cmd == "goto_clean":
        return build_goto_clean_command(
            kwargs.get("x", 0),
            kwargs.get("y", 0),
            kwargs.get("map_id", 0),
            dps_map,
        )
    if cmd == "set_room_custom":
        return build_set_room_custom_command(
            kwargs.get("room_config", []),
            kwargs.get("map_id", 3),
            kwargs.get("fan_speed"),
            kwargs.get("water_level"),
            kwargs.get("clean_times"),
            kwargs.get("clean_mode"),
            kwargs.get("clean_intensity"),
            kwargs.get("edge_mopping"),
            dps_map,
        )
    if cmd == "set_auto_cfg":
        return build_set_auto_action_cfg_command(kwargs.get("cfg", {}), dps_map)
    if cmd == "reset_accessory":
        return build_reset_accessory_command(int(kwargs.get("reset_type", 0)), dps_map)
    if cmd == "set_child_lock":
        return build_set_child_lock_command(bool(kwargs.get("active", True)), dps_map)
    if cmd == "set_unisetting":
        return build_set_unisetting_command(
            kwargs.get("field", ""),
            kwargs.get("value"),
            kwargs.get("current_state"),
            dps_map,
        )
    if cmd == "set_do_not_disturb":
        return build_set_undisturbed_command(
            bool(kwargs.get("active", True)),
            int(kwargs.get("begin_hour", 22)),
            int(kwargs.get("begin_minute", 0)),
            int(kwargs.get("end_hour", 8)),
            int(kwargs.get("end_minute", 0)),
            dps_map,
        )
    if cmd == "set_carpet_strategy":
        return build_set_carpet_strategy_command(
            kwargs.get("carpet_strategy", ""), dps_map
        )
    if cmd == "set_corner_cleaning":
        return build_set_corner_cleaning_command(
            kwargs.get("corner_cleaning", ""), dps_map
        )
    if cmd == "set_smart_mode":
        return build_set_smart_mode_command(bool(kwargs.get("active", True)), dps_map)
    if cmd == "set_boost_iq":
        return build_set_boost_iq_command(bool(kwargs.get("active", True)), dps_map)
    if cmd == "set_volume":
        return build_set_volume_command(int(kwargs.get("volume", 50)), dps_map)
    if cmd == "timer_inquiry":
        return build_timer_inquiry_command(dps_map)
    if cmd == "timer_add":
        return build_timer_add_command(kwargs.get("timer_info", {}), dps_map)
    if cmd == "timer_delete":
        return build_timer_delete_command(int(kwargs.get("timer_id", 0)), dps_map)
    if cmd == "timer_modify":
        return build_timer_modify_command(kwargs.get("timer_info", {}), dps_map)
    if cmd == "timer_open":
        return build_timer_open_command(int(kwargs.get("timer_id", 0)), dps_map)
    if cmd == "timer_close":
        return build_timer_close_command(int(kwargs.get("timer_id", 0)), dps_map)

    if cmd == "media_capture":
        return build_media_capture_command(int(kwargs.get("seq", 1)), dps_map)
    if cmd == "media_record":
        return build_media_record_command(bool(kwargs.get("start", True)), int(kwargs.get("seq", 1)), dps_map)
    if cmd == "media_set_resolution":
        return build_media_set_resolution_command(kwargs.get("resolution", "720p"), dps_map)

    if cmd == "generic":
        return build_generic_command(
            str(kwargs.get("dp_id", "")),
            kwargs.get("value"),
        )

    return {}
