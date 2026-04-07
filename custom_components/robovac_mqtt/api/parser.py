from __future__ import annotations

import base64
import logging
from dataclasses import replace
from typing import Any

from google.protobuf.json_format import MessageToDict

from ..const import (
    CARPET_STRATEGY_NAMES,
    CLEANING_INTENSITY_NAMES,
    CLEANING_MODE_NAMES,
    CORNER_CLEANING_NAMES,
    DEFAULT_DPS_MAP,
    DOCK_ACTIVITY_STATES,
    DPS_ROBOT_TELEMETRY,
    EUFY_CLEAN_APP_TRIGGER_MODES,
    EUFY_CLEAN_ERROR_CODES,
    EUFY_CLEAN_NOVEL_CLEAN_SPEED,
    EUFY_CLEAN_PROMPT_CODES,
    FAN_SUCTION_NAMES,
    HANDLED_DPS_IDS,
    KNOWN_UNPROCESSED_DPS,
    MEDIA_RECORDING_STATE_NAMES,
    MEDIA_RESOLUTION_NAMES,
    MEDIA_STORAGE_STATE_NAMES,
    MOP_WATER_LEVEL_NAMES,
    SCHEDULE_ACTION_NAMES,
    TRIGGER_SOURCE_NAMES,
    WORK_MODE_NAMES,
    CleaningMode,
    MopWaterLevel,
    TriggerSource,
)
from ..models import AccessoryState, VacuumState
from ..proto.cloud.app_device_info_pb2 import DeviceInfo
from ..proto.cloud.clean_param_pb2 import CleanParamRequest, CleanParamResponse
from ..proto.cloud.clean_statistics_pb2 import CleanStatistics
from ..proto.cloud.consumable_pb2 import ConsumableResponse
from ..proto.cloud.control_pb2 import ModeCtrlRequest
from ..proto.cloud.error_code_pb2 import ErrorCode, PromptCode
from ..proto.cloud.media_manager_pb2 import MediaManagerResponse
from ..proto.cloud.multi_maps_pb2 import MultiMapsManageResponse
from ..proto.cloud.scene_pb2 import SceneResponse
from ..proto.cloud.station_pb2 import StationResponse
from ..proto.cloud.stream_pb2 import RoomParams
from ..proto.cloud.timing_pb2 import TimerResponse
from ..proto.cloud.undisturbed_pb2 import UndisturbedResponse
from ..proto.cloud.unisetting_pb2 import UnisettingResponse
from ..proto.cloud.universal_data_pb2 import UniversalDataResponse
from ..proto.cloud.analysis_pb2 import AnalysisResponse
from ..proto.cloud.work_status_pb2 import WorkStatus
from ..utils import decode, deduplicate_names

_LOGGER = logging.getLogger(__name__)


def _decode_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Decode a protobuf varint starting at *pos*. Returns (value, new_pos)."""
    value = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        value |= (b & 0x7F) << shift
        pos += 1
        if not b & 0x80:
            return value, pos
        shift += 7
    return value, pos


def _decode_raw_varints(data: bytes) -> dict[int, int | bytes]:
    """Decode raw protobuf fields from bytes (no schema needed).

    Returns a dict of field_number -> value (int for varints, bytes for
    length-delimited fields).
    """
    fields: dict[int, int | bytes] = {}
    i = 0
    while i < len(data):
        tag, i = _decode_varint(data, i)
        fn, wt = tag >> 3, tag & 7
        if wt == 0:  # varint
            val, i = _decode_varint(data, i)
            fields[fn] = val
        elif wt == 2:  # length-delimited
            blen, i = _decode_varint(data, i)
            fields[fn] = data[i : i + blen]
            i += blen
        else:
            break
    return fields


def _parse_robot_telemetry(value: str) -> dict[str, Any] | None:
    """Parse DPS 179 robot telemetry (no proto definition available).

    Wire format: varint-length-prefixed message containing:
      field 2 (bytes) -> sub-message with field 7 (bytes) -> inner message:
        field 1: uint32  Unix timestamp
        field 2: uint32  battery percentage
        field 3: uint32  unknown (slowly increasing value)
        field 4: uint32  map X coordinate
        field 5: uint32  map Y coordinate
        field 6: bytes   additional data (2 packed varints)

    See docs/DPS_179_TELEMETRY.md for detailed format documentation.
    """
    try:
        raw = base64.b64decode(value)
    except Exception:
        _LOGGER.debug("Failed to decode DPS 179 base64: %.50s", value)
        return None
    _length, pos = _decode_varint(raw, 0)
    outer = _decode_raw_varints(raw[pos:])
    sub_bytes = outer.get(2)
    if not isinstance(sub_bytes, bytes):
        return None
    sub = _decode_raw_varints(sub_bytes)
    inner_bytes = sub.get(7)
    if not isinstance(inner_bytes, bytes):
        return None
    inner = _decode_raw_varints(inner_bytes)
    if 4 not in inner or 5 not in inner:
        return None
    return {"x": inner[4], "y": inner[5]}


def _track_field(state: VacuumState, changes: dict[str, Any], field_name: str) -> None:
    """Track that a field has been received from the device.

    This is used by sensors to determine availability.
    Only updates if the field isn't already tracked.
    """
    if field_name not in state.received_fields:
        _LOGGER.debug("Tracking new field for availability: %s", field_name)
        # Get current set from changes if already modified, else from state
        current = changes.get("received_fields", state.received_fields).copy()
        current.add(field_name)
        changes["received_fields"] = current


def update_state(
    state: VacuumState,
    dps: dict[str, Any],
    *,
    dps_map: dict[str, str] | None = None,
    catalog_types: dict[str, str] | None = None,
    dps_catalog: dict[str, dict[str, Any]] | None = None,
) -> tuple[VacuumState, dict[str, Any]]:
    """Update VacuumState with new DPS data.

    Returns:
        A tuple of (new_state, changes_dict) where changes_dict contains
        only the fields that were explicitly set from this DPS message.
        This allows callers to distinguish between a field being actively
        set vs inherited from previous state.
    """
    if dps_map is None:
        dps_map = DEFAULT_DPS_MAP

    changes: dict[str, Any] = {}

    # Always update raw_dps
    new_raw_dps = state.raw_dps.copy()
    new_raw_dps.update(dps)
    changes["raw_dps"] = new_raw_dps

    _process_station_status(state, dps, changes, dps_map)
    _process_work_status(state, dps, changes, dps_map)
    _process_play_pause(state, dps, changes, dps_map)
    _process_other_dps(state, dps, changes, dps_map, catalog_types, dps_catalog)

    # Log received_fields for debugging sensor availability
    if "received_fields" in changes:
        _LOGGER.debug("Received fields now: %s", changes["received_fields"])

    return replace(state, **changes), changes


def _process_station_status(
    state: VacuumState, dps: dict[str, Any], changes: dict[str, Any],
    dps_map: dict[str, str],
) -> None:
    """Process Station Status DPS."""
    if dps_map["STATION_STATUS"] not in dps:
        return

    value = dps[dps_map["STATION_STATUS"]]
    try:
        station = decode(StationResponse, value)
        _LOGGER.debug("Decoded StationResponse: %s", station)
        new_dock_status = _map_dock_status(station)
        # Debouncing is handled in coordinator, not here
        changes["dock_status"] = new_dock_status
        _track_field(state, changes, "dock_status")

        if station.HasField("clean_water"):
            changes["station_clean_water"] = station.clean_water.value
            _track_field(state, changes, "station_clean_water")

        changes["station_waste_water"] = int(station.dirty_level)
        _track_field(state, changes, "station_waste_water")

        changes["station_clean_level"] = int(station.clean_level)
        _track_field(state, changes, "station_clean_level")

        # Auto Empty Config
        if station.HasField("auto_cfg_status"):
            changes["dock_auto_cfg"] = MessageToDict(
                station.auto_cfg_status, preserving_proto_field_name=True
            )
    except Exception as e:
        _LOGGER.warning("Error parsing Station Status: %s", e, exc_info=True)


def _process_work_status(
    state: VacuumState, dps: dict[str, Any], changes: dict[str, Any],
    dps_map: dict[str, str],
) -> None:
    """Process Work Status DPS."""
    if dps_map["WORK_STATUS"] not in dps:
        return

    value = dps[dps_map["WORK_STATUS"]]
    try:
        work_status = decode(WorkStatus, value)
        _LOGGER.debug("Decoded WorkStatus: %s", work_status)
        changes["activity"] = _map_work_status(work_status)
        changes["status_code"] = work_status.state

        # Use current or updated dock status
        current_dock_status = changes.get("dock_status", state.dock_status)
        changes["task_status"] = _map_task_status(work_status, current_dock_status)

        # Check for charging status
        # State 3 (CHARGING) is the authoritative signal. For other states,
        # the charging sub-message may be present with default values (state=0)
        # due to protobuf field presence semantics, so we only trust it when
        # the main state confirms the device is actually charging.
        if work_status.state == 3:
            changes["charging"] = True
        elif work_status.HasField("charging") and work_status.charging.state == 0:
            # charging.state=0 (DOING) is only meaningful when main state is 3
            # For state=5 (CLEANING), an empty charging{} sub-message is a
            # protobuf default, not an actual charging signal
            changes["charging"] = False
        else:
            changes["charging"] = False

        # Check for trigger source
        trigger_source = "unknown"
        if work_status.HasField("trigger"):
            trigger_source = _map_trigger_source(work_status.trigger.source)

        # Infer trigger source from Work Mode if unknown
        # Many robots (like X10 Pro Omni) do not send trigger field
        # for specific cleaning modes
        if trigger_source == "unknown" and work_status.HasField("mode"):
            mode_val = work_status.mode.value
            if mode_val in EUFY_CLEAN_APP_TRIGGER_MODES:
                trigger_source = "app"

        changes["trigger_source"] = trigger_source

        # Extract Work Mode
        if work_status.HasField("mode"):
            mode_val = work_status.mode.value
            changes["work_mode"] = WORK_MODE_NAMES.get(mode_val, "unknown")
            _track_field(state, changes, "work_mode")
        elif state.work_mode == "unknown" and changes.get("activity") == "cleaning":
            # If we don't know the mode yet but we are cleaning, default to Auto
            changes["work_mode"] = "Auto"
        elif changes.get("activity") not in ("cleaning", "returning"):
            # If we are not cleaning or returning, reset to unknown
            # This handles the case where a previous run's mode might stick around
            if state.work_mode != "unknown":
                changes["work_mode"] = "unknown"

        # Fallback/Override if cleaning.scheduled_task is explicit
        if work_status.HasField("cleaning") and work_status.cleaning.scheduled_task:
            changes["trigger_source"] = "schedule"

        # Update dock_status from WorkStatus.
        # go_wash.mode is the authoritative signal for wash/dry cycle state.
        # Station sub-fields (washing_drying_system, water_injection_system)
        # report sub-phases within that cycle and must not overwrite the
        # primary dock status when go_wash is active.
        is_go_wash_active = (
            work_status.HasField("go_wash")
            and work_status.go_wash.mode in (1, 2)
        )

        if is_go_wash_active:
            if work_status.go_wash.mode == 2:
                changes["dock_status"] = "Drying"
            else:
                changes["dock_status"] = "Washing"
        elif work_status.HasField("station"):
            st = work_status.station

            has_dock_activity = False

            if st.HasField("washing_drying_system"):
                has_dock_activity = True
                if st.washing_drying_system.state == 1:
                    changes["dock_status"] = "Drying"
                else:
                    changes["dock_status"] = "Washing"

            if st.HasField("dust_collection_system"):
                has_dock_activity = True
                changes["dock_status"] = "Emptying dust"

            if st.HasField("water_injection_system") and not has_dock_activity:
                has_dock_activity = True
                if st.water_injection_system.state == 0:
                    changes["dock_status"] = "Adding clean water"
                else:
                    changes["dock_status"] = "Recycling waste water"

            if not has_dock_activity:
                current_dock = changes.get("dock_status", state.dock_status)
                if current_dock in DOCK_ACTIVITY_STATES:
                    changes["dock_status"] = "Idle"

        elif work_status.HasField("go_wash") and work_status.go_wash.mode in (1, 2):
            if work_status.go_wash.mode == 2:
                changes["dock_status"] = "Drying"
            else:
                changes["dock_status"] = "Washing"

        else:
            # No station field - if charging and was in dock activity, reset to Idle
            if work_status.state == 3:  # CHARGING
                current_dock = changes.get("dock_status", state.dock_status)
                if current_dock in DOCK_ACTIVITY_STATES:
                    changes["dock_status"] = "Idle"

        # Process Current Scene
        # 1. If explicit scene info provided, use it.
        if work_status.HasField("current_scene"):
            changes["current_scene_id"] = work_status.current_scene.id
            changes["current_scene_name"] = work_status.current_scene.name
            if (
                state.active_room_ids
                or state.active_room_names
                or state.active_zone_count
            ):
                changes["active_room_ids"] = []
                changes["active_room_names"] = ""
                changes["active_zone_count"] = 0

        # 2. If explicit Mode provided and it's NOT Scene (8), clear it.
        # 8 = SCENE mode
        elif work_status.HasField("mode") and work_status.mode.value != 8:
            changes["current_scene_id"] = 0
            changes["current_scene_name"] = None

        # 3. If State is explicitly Charging (3) or Go Home (7), clear it.
        # We avoid clearing on 0 (Standby) because partial updates might default to 0.
        elif work_status.state in [3, 7]:
            changes["current_scene_id"] = 0
            changes["current_scene_name"] = None

        # Clear active cleaning targets when the task is actually over.
        # Docked can also mean an in-progress wash/dry cycle, so rely on the
        # derived task_status instead of duplicating that interpretation here.
        activity = changes.get("activity")
        task_status = changes.get("task_status")
        should_clear_targets = (
            activity in ("idle", "error") and state.activity not in ("idle", "error")
        ) or (
            activity == "docked"
            and task_status == "Completed"
            and state.task_status != "Completed"
        )
        if should_clear_targets:
            if state.active_room_ids or state.active_zone_count:
                changes["active_room_ids"] = []
                changes["active_room_names"] = ""
                changes["active_zone_count"] = 0

        if work_status.HasField("upgrading"):
            changes["upgrading"] = (work_status.upgrading.state != 0)
            _track_field(state, changes, "upgrading")

        if work_status.HasField("mapping"):
            changes["mapping_state"] = int(work_status.mapping.state)
            changes["mapping_mode"] = int(work_status.mapping.mode)
            _track_field(state, changes, "mapping_state")

        if work_status.HasField("relocating"):
            changes["relocating"] = (work_status.relocating.state != 0)
            _track_field(state, changes, "relocating")

        if work_status.HasField("roller_brush_cleaning"):
            changes["roller_brush_cleaning"] = (work_status.roller_brush_cleaning.state != 0)
            _track_field(state, changes, "roller_brush_cleaning")

        if work_status.HasField("breakpoint"):
            changes["breakpoint_available"] = (work_status.breakpoint.state != 0)
            _track_field(state, changes, "breakpoint_available")

        if work_status.HasField("station"):
            if work_status.station.HasField("dust_collection_system"):
                changes["station_work_status"] = int(work_status.station.dust_collection_system.state)
            else:
                changes["station_work_status"] = 0
            _track_field(state, changes, "station_work_status")

        if work_status.HasField("cruisiing"):
            changes["cruise_state"] = int(work_status.cruisiing.state)
            changes["cruise_mode"] = int(work_status.cruisiing.mode)
            _track_field(state, changes, "cruise_state")

        if work_status.HasField("smart_follow"):
            changes["smart_follow_state"] = int(work_status.smart_follow.state)
            changes["smart_follow_mode"] = int(work_status.smart_follow.mode)
            changes["smart_follow_elapsed"] = work_status.smart_follow.elapsed_time
            changes["smart_follow_area"] = work_status.smart_follow.area
            _track_field(state, changes, "smart_follow_state")

    except Exception as e:
        _LOGGER.warning("Error parsing Work Status: %s", e, exc_info=True)


def _process_play_pause(
    state: VacuumState, dps: dict[str, Any], changes: dict[str, Any],
    dps_map: dict[str, str],
) -> None:
    """Process Play/Pause DPS (152) - extract active cleaning targets."""
    if dps_map["PLAY_PAUSE"] not in dps:
        return

    value = dps[dps_map["PLAY_PAUSE"]]
    try:
        mode_ctrl = decode(ModeCtrlRequest, value)
        _LOGGER.debug("Decoded ModeCtrlRequest: %s", mode_ctrl)

        if mode_ctrl.HasField("select_rooms_clean"):
            room_ids = [r.id for r in mode_ctrl.select_rooms_clean.rooms]
            if not room_ids:
                _LOGGER.debug(
                    "Ignoring START_SELECT_ROOMS_CLEAN without room IDs; preserving existing active targets."
                )
                return
            changes["active_room_ids"] = room_ids
            room_lookup = {
                r["id"]: r.get("name", f"Room {r['id']}") for r in state.rooms
            }
            names = [room_lookup.get(rid, f"Room {rid}") for rid in room_ids]
            changes["active_room_names"] = ", ".join(names)
            changes["active_zone_count"] = 0
            changes["current_scene_id"] = 0
            changes["current_scene_name"] = None
            _track_field(state, changes, "active_room_ids")

        elif mode_ctrl.HasField("select_zones_clean"):
            changes["active_zone_count"] = len(mode_ctrl.select_zones_clean.zones)
            changes["active_room_ids"] = []
            changes["active_room_names"] = ""
            changes["current_scene_id"] = 0
            changes["current_scene_name"] = None
            _track_field(state, changes, "active_room_ids")

        # Scene: intentionally skipped (already tracked via WorkStatus.current_scene)
        # Control commands (pause/resume/stop): no Param oneof, naturally ignored

    except Exception as e:
        _LOGGER.warning("Error parsing Play/Pause DPS: %s", e, exc_info=True)


def _truncate_value(value: Any, max_len: int = 200) -> str:
    """Format a DPS value for logging, preserving full base64 up to max_len."""
    if value is None:
        return "None"
    s = str(value)
    if len(s) <= max_len:
        return s
    return f"{s[:max_len]}... ({len(s)} chars)"


def _catalog_summary(key: str, dps_catalog: dict[str, dict[str, Any]] | None) -> str:
    """Build a one-line catalog summary for debug logging."""
    if not dps_catalog or key not in dps_catalog:
        return "catalog=N/A"
    entry = dps_catalog[key]
    parts = [
        f"code={entry.get('code', '?')}",
        f"type={entry.get('data_type', '?')}",
        f"mode={entry.get('mode', '?')}",
    ]
    prop = entry.get("property", "{}")
    if prop and prop != "{}":
        parts.append(f"property={prop}")
    desc = entry.get("desc", "")
    if desc:
        parts.append(f"desc={desc}")
    return " | ".join(parts)


def _process_other_dps(
    state: VacuumState, dps: dict[str, Any], changes: dict[str, Any],
    dps_map: dict[str, str],
    catalog_types: dict[str, str] | None = None,
    dps_catalog: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Process other DPS items."""
    for key, value in dps.items():
        if key in (
            dps_map["WORK_STATUS"],
            dps_map["STATION_STATUS"],
            dps_map["PLAY_PAUSE"],
        ):
            continue

        try:
            if key == dps_map["BATTERY_LEVEL"]:
                changes["battery_level"] = int(value)
                new_dynamic = dict(changes.get("dynamic_values", state.dynamic_values))
                new_dynamic[key] = int(value)
                changes["dynamic_values"] = new_dynamic
                _track_field(state, changes, "battery_level")

            elif key == dps_map["CLEAN_SPEED"]:
                mapped = _map_clean_speed(value)
                changes["fan_speed"] = mapped
                new_dynamic = dict(changes.get("dynamic_values", state.dynamic_values))
                new_dynamic[key] = int(value)
                changes["dynamic_values"] = new_dynamic
                _track_field(state, changes, "fan_speed")

            elif key == dps_map["ERROR_CODE"]:
                error_proto = decode(ErrorCode, value)
                _LOGGER.debug("Decoded ErrorCode: %s", error_proto)
                all_codes = list(error_proto.error) + list(error_proto.warn)
                changes["error_codes_all"] = all_codes
                changes["error_messages_all"] = [
                    EUFY_CLEAN_ERROR_CODES.get(c, f"Unknown ({c})") for c in all_codes
                ]
                if all_codes:
                    code = all_codes[0]
                    changes["error_code"] = code
                    changes["error_message"] = EUFY_CLEAN_ERROR_CODES.get(
                        code, f"Unknown ({code})"
                    )
                else:
                    changes["error_code"] = 0
                    changes["error_message"] = ""

            elif key == dps_map.get("TOAST", "178"):
                try:
                    prompt = decode(PromptCode, value)
                    _LOGGER.debug("Decoded PromptCode (DPS 178): %s", prompt)
                    codes = list(prompt.value)
                    changes["notification_codes"] = codes
                    if codes:
                        first_code = codes[0]
                        changes["notification_message"] = EUFY_CLEAN_PROMPT_CODES.get(
                            first_code, f"Notification {first_code}"
                        )
                    else:
                        changes["notification_message"] = ""
                    if prompt.last_time:
                        changes["notification_time"] = prompt.last_time
                    _track_field(state, changes, "notification")
                except Exception as e:
                    _LOGGER.debug("DPS 178: PromptCode decode failed: %s", e)

            elif key == dps_map["ACCESSORIES_STATUS"]:
                _LOGGER.debug("Received ACCESSORIES_STATUS: %s", value)
                changes["accessories"] = _parse_accessories(state.accessories, value)
                _track_field(state, changes, "accessories")
                try:
                    _cr = decode(ConsumableResponse, value)
                    if _cr.HasField("runtime") and _cr.runtime.last_time:
                        changes["consumable_last_time"] = _cr.runtime.last_time
                        _track_field(state, changes, "consumable_last_time")
                except Exception:
                    pass

            elif key == dps_map["CLEANING_STATISTICS"]:
                stats = decode(CleanStatistics, value)
                _LOGGER.debug("Decoded CleanStatistics: %s", stats)
                if stats.HasField("single"):
                    changes["cleaning_time"] = stats.single.clean_duration
                    changes["cleaning_area"] = stats.single.clean_area
                    _track_field(state, changes, "cleaning_stats")

                if stats.HasField("total"):
                    changes["total_cleaning_time"] = stats.total.clean_duration
                    changes["total_cleaning_area"] = stats.total.clean_area
                    changes["total_cleaning_count"] = stats.total.clean_count
                    _track_field(state, changes, "total_stats")

                if stats.HasField("user_total"):
                    changes["user_total_cleaning_time"] = stats.user_total.clean_duration
                    changes["user_total_cleaning_area"] = stats.user_total.clean_area
                    changes["user_total_cleaning_count"] = stats.user_total.clean_count
                    _track_field(state, changes, "user_total_stats")

            elif key == dps_map["SCENE_INFO"]:
                _LOGGER.debug("Received SCENE_INFO: %s", value)
                changes["scenes"] = _parse_scene_info(value)

            elif key == dps_map["TIMING"]:
                _process_timer_response(state, value, changes)

            elif key == dps_map["RESERVED2"]:
                _LOGGER.debug("Received RESERVED2: %s", value)
                map_info = _parse_map_data(value)
                if map_info:
                    changes["map_id"] = map_info.get("map_id", 0)
                    changes["rooms"] = map_info.get("rooms", [])
                    _track_field(state, changes, "map_id")

            elif key == dps_map["CLEANING_PARAMETERS"]:
                _LOGGER.debug("Received CLEANING_PARAMETERS: %s", value)
                _process_cleaning_parameters(state, value, changes)

            elif key == dps_map["FIND_ROBOT"]:
                parsed = str(value).lower() == "true"
                changes["find_robot"] = parsed
                new_dynamic = dict(changes.get("dynamic_values", state.dynamic_values))
                new_dynamic[key] = parsed
                changes["dynamic_values"] = new_dynamic

            elif key == dps_map["APP_DEV_INFO"]:
                info = decode(DeviceInfo, value)
                _LOGGER.debug("Decoded DeviceInfo: %s", info)
                if info.device_mac:
                    changes["device_mac"] = info.device_mac
                if info.wifi_name:
                    changes["wifi_ssid"] = info.wifi_name
                    _track_field(state, changes, "wifi_ssid")
                if info.wifi_ip:
                    changes["wifi_ip"] = info.wifi_ip
                    _track_field(state, changes, "wifi_ip")
                if info.software:
                    changes["firmware_version"] = info.software
                    _track_field(state, changes, "firmware_version")
                if info.hardware:
                    changes["hardware_version"] = info.hardware
                    _track_field(state, changes, "hardware_version")
                if info.product_name:
                    changes["product_name"] = info.product_name
                if info.video_sn:
                    changes["video_sn"] = info.video_sn
                if info.HasField("station"):
                    if info.station.software:
                        changes["station_firmware"] = info.station.software
                    if info.station.hardware:
                        changes["station_hardware"] = info.station.hardware
                if info.last_user_id:
                    _LOGGER.debug("Device last_user_id: %s", info.last_user_id)

            elif key == dps_map["MULTI_MAP_MANAGE"]:
                if value is None:
                    _LOGGER.debug("DPS 172: None value (initial state)")
                else:
                    _LOGGER.debug("Received MULTI_MAP_MANAGE (DPS 172): %.100s", value)
                    _parse_multi_map_response(value)

            elif key == dps_map["UNSETTING"]:
                settings = decode(UnisettingResponse, value)
                _LOGGER.debug("Decoded UnisettingResponse: %s", settings)
                changes["wifi_signal"] = (settings.ap_signal_strength / 2) - 100
                _track_field(state, changes, "wifi_signal")
                if settings.HasField("children_lock"):
                    changes["child_lock"] = settings.children_lock.value
                    _track_field(state, changes, "child_lock")

                # Switch fields (proto wrapper: Switch.value -> bool)
                for field_name in (
                    "ai_see", "pet_mode_sw", "poop_avoidance_sw",
                    "live_photo_sw", "deep_mop_corner_sw", "smart_follow_sw",
                    "cruise_continue_sw", "multi_map_sw",
                    "suggest_restricted_zone_sw", "water_level_sw",
                ):
                    try:
                        if settings.HasField(field_name):
                            changes[field_name] = getattr(settings, field_name).value
                            _track_field(state, changes, field_name)
                    except Exception:
                        _LOGGER.debug("Error parsing unisetting field %s", field_name, exc_info=True)

                # Numerical field
                try:
                    if settings.HasField("dust_full_remind"):
                        changes["dust_full_remind"] = settings.dust_full_remind.value
                        _track_field(state, changes, "dust_full_remind")
                except Exception:
                    _LOGGER.debug("Error parsing dust_full_remind", exc_info=True)

                # Unistate sub-fields
                try:
                    if settings.HasField("unistate"):
                        uni = settings.unistate
                        if uni.HasField("mop_state"):
                            changes["mop_state"] = uni.mop_state.value
                            _track_field(state, changes, "mop_state")
                        if uni.HasField("mop_holder_state_l"):
                            changes["mop_holder_state_l"] = uni.mop_holder_state_l.value
                            _track_field(state, changes, "mop_holder_state_l")
                        if uni.HasField("mop_holder_state_r"):
                            changes["mop_holder_state_r"] = uni.mop_holder_state_r.value
                            _track_field(state, changes, "mop_holder_state_r")
                        if uni.HasField("map_valid"):
                            changes["map_valid"] = uni.map_valid.value
                            _track_field(state, changes, "map_valid")
                        if uni.HasField("live_map"):
                            changes["live_map_state_bits"] = uni.live_map.state_bits
                            _track_field(state, changes, "live_map_state_bits")
                        if uni.clean_strategy_version:
                            changes["clean_strategy_version"] = uni.clean_strategy_version
                            _track_field(state, changes, "clean_strategy_version")
                        if uni.HasField("custom_clean_mode"):
                            changes["custom_clean_mode"] = uni.custom_clean_mode.value
                            _track_field(state, changes, "custom_clean_mode")
                except Exception:
                    _LOGGER.debug("Error parsing unistate", exc_info=True)

                # WiFi data
                try:
                    if settings.HasField("wifi_data") and settings.wifi_data.ap:
                        ap = settings.wifi_data.ap[0]
                        if ap.ssid:
                            changes["wifi_ap_ssid"] = ap.ssid
                            _track_field(state, changes, "wifi_ap_ssid")
                        if ap.frequency:
                            changes["wifi_frequency"] = int(ap.frequency)
                            _track_field(state, changes, "wifi_frequency")
                        if ap.HasField("connection"):
                            changes["wifi_connection_result"] = int(ap.connection.result)
                            changes["wifi_connection_timestamp"] = ap.connection.timestamp
                            _track_field(state, changes, "wifi_connection_result")
                            _track_field(state, changes, "wifi_connection_timestamp")
                except Exception:
                    _LOGGER.debug("Error parsing wifi_data", exc_info=True)

            elif key == dps_map["UNDISTURBED"]:
                undisturbed = decode(UndisturbedResponse, value)
                _LOGGER.debug("Decoded UndisturbedResponse: %s", undisturbed)
                if undisturbed.HasField("undisturbed"):
                    changes["dnd_enabled"] = undisturbed.undisturbed.sw.value
                    if undisturbed.undisturbed.HasField("begin"):
                        changes["dnd_start_hour"] = undisturbed.undisturbed.begin.hour
                        changes["dnd_start_minute"] = (
                            undisturbed.undisturbed.begin.minute
                        )
                    if undisturbed.undisturbed.HasField("end"):
                        changes["dnd_end_hour"] = undisturbed.undisturbed.end.hour
                        changes["dnd_end_minute"] = undisturbed.undisturbed.end.minute
                    _track_field(state, changes, "do_not_disturb")

            elif key == dps_map.get("MEDIA_MANAGER"):
                if value is not None:
                    _process_media_manager(state, value, changes)

            elif key == DPS_ROBOT_TELEMETRY:
                pos = _parse_robot_telemetry(value)
                _LOGGER.debug(
                    "DPS 179 telemetry: parsed=%s, raw_b64=%.60s...",
                    pos,
                    value,
                )
                if pos:
                    raw_x, raw_y = pos["x"], pos["y"]
                    changes["robot_position_x"] = raw_x
                    changes["robot_position_y"] = raw_y
                    _track_field(state, changes, "robot_position")

                _parse_analysis_response(state, value, changes)

            elif key == dps_map.get("BOOST_IQ"):
                if isinstance(value, bool):
                    changes["boost_iq"] = value
                    new_dynamic = dict(changes.get("dynamic_values", state.dynamic_values))
                    new_dynamic[key] = value
                    changes["dynamic_values"] = new_dynamic
                    _track_field(state, changes, "boost_iq")

            elif key == dps_map.get("VOLUME"):
                if isinstance(value, (int, float)):
                    vol = int(value)
                    changes["volume"] = vol
                    new_dynamic = dict(changes.get("dynamic_values", state.dynamic_values))
                    new_dynamic[key] = vol
                    changes["dynamic_values"] = new_dynamic
                    _track_field(state, changes, "volume")

            elif key not in HANDLED_DPS_IDS and key not in KNOWN_UNPROCESSED_DPS:
                if catalog_types and key in catalog_types:
                    dtype = catalog_types[key]
                    if dtype == "Bool":
                        parsed_val = str(value).lower() == "true" if isinstance(value, str) else bool(value)
                        new_dynamic = dict(changes.get("dynamic_values", state.dynamic_values))
                        new_dynamic[key] = parsed_val
                        changes["dynamic_values"] = new_dynamic
                    elif dtype == "Value":
                        try:
                            parsed_val = int(value) if isinstance(value, str) else value
                            new_dynamic = dict(changes.get("dynamic_values", state.dynamic_values))
                            new_dynamic[key] = parsed_val
                            changes["dynamic_values"] = new_dynamic
                        except (ValueError, TypeError):
                            pass
                    elif dtype == "Enum":
                        try:
                            parsed_val = int(value)
                        except (ValueError, TypeError):
                            parsed_val = value
                        new_dynamic = dict(changes.get("dynamic_values", state.dynamic_values))
                        new_dynamic[key] = parsed_val
                        changes["dynamic_values"] = new_dynamic
                else:
                    _LOGGER.debug(
                        "UNKNOWN_DPS | key=%s | value=%s | value_type=%s | %s",
                        key,
                        _truncate_value(value),
                        type(value).__name__,
                        _catalog_summary(key, dps_catalog),
                    )

            elif key in KNOWN_UNPROCESSED_DPS:
                _LOGGER.debug(
                    "KNOWN_UNPROCESSED_DPS | key=%s | value=%s | value_type=%s | %s",
                    key,
                    _truncate_value(value),
                    type(value).__name__,
                    _catalog_summary(key, dps_catalog),
                )

            else:
                _LOGGER.debug(
                    "UNHANDLED_DPS | key=%s | value=%s | value_type=%s | in_handled=%s | %s",
                    key,
                    _truncate_value(value),
                    type(value).__name__,
                    key in HANDLED_DPS_IDS,
                    _catalog_summary(key, dps_catalog),
                )

        except Exception as e:
            _LOGGER.warning("Error parsing DPS %s: %s", key, e, exc_info=True)


def _map_task_status(status: WorkStatus, dock_status: str | None = None) -> str:
    """Map WorkStatus to detailed task status."""
    s = status.state

    # Check for specific Wash/Dry states first (usually inside Cleaning state 5)
    if status.HasField("go_wash"):
        # GoWash.Mode: NAVIGATION=0, WASHING=1, DRYING=2
        gw_mode = status.go_wash.mode
        if gw_mode == 2:
            return "Completed"
        if gw_mode == 1:
            return "Washing Mop"
        if gw_mode == 0 and s == 5:
            return "Returning to Wash"

    # Check for Breakpoint (Recharge & Resume)
    # Usually State 7 (Returning) or 3 (Charging)
    is_resumable = False
    if status.HasField("breakpoint") and status.breakpoint.state == 0:
        is_resumable = True

    if s == 3:  # Charging
        if is_resumable:
            return "Charging (Resume)"

        # Check if this is a mid-cleaning wash pause vs post-cleaning
        # If cleaning field exists with PAUSED state while dock is washing,
        # this is a mid-cleaning pause, not task completion
        if status.HasField("cleaning") and status.cleaning.state == 1:  # PAUSED
            if dock_status in (
                "Washing",
                "Adding clean water",
                "Recycling waste water",
            ):
                return "Washing Mop"
            return "Paused"

        # If not resumable and cleaning field is absent, the task is complete
        if status.HasField("station") and status.station.HasField(
            "dust_collection_system"
        ):
            return "Emptying Dust"
        return "Completed"

    if s == 7:  # Returning / Go Home
        # Distinguish between "Finished" and "Recharge needed"
        # However, GoHome mode 0 is "COMPLETE_TASK" and 1 is "COLLECT_DUST"
        if is_resumable:
            return "Returning to Charge"
        if status.HasField("go_home"):
            gh_mode = status.go_home.mode
            if gh_mode == 1:
                return "Returning to Empty"
        return "Returning"

    if s == 5:  # Cleaning
        if (
            status.HasField("cleaning")
            and status.cleaning.state == 1  # PAUSED
            and not status.HasField("go_wash")
        ):
            return "Paused"
        return "Cleaning"

    if s == 4:
        return "Mapping"

    if s == 2:
        return "Error"

    if s == 6:
        return "Remote Control"

    if s == 15:  # Stop / Pause?
        return "Paused"

    # Fallback mappings from basic map
    return _map_work_status(status).title()


def _map_work_status(status: WorkStatus) -> str:
    """Map WorkStatus protobuf to activity string."""
    s = status.state
    if s in (0, 1):  # 0=Standby, 1=Sleep
        return "idle"
    if s == 2:  # Fault
        return "error"
    if s == 3:  # Charging
        return "docked"
    if s == 4:  # FAST_MAPPING
        return "cleaning"
    if s == 5:  # Active clean / station wash+dry
        # go_wash.mode: 0=NAVIGATION, 1=WASHING, 2=DRYING
        # When washing or drying (modes 1, 2), the vacuum is physically docked at the station
        # Users expect "docked" status during station-based activities, not "cleaning"
        # "cleaning" implies the device is moving around cleaning floors
        # This aligns with HA's vacuum state model where "docked" includes station activities
        if status.HasField("go_wash") and status.go_wash.mode in (1, 2):
            return "docked"
        if status.HasField("station") and status.station.HasField(
            "washing_drying_system"
        ):
            return "docked"
        # User-initiated pause: cleaning sub-state is PAUSED and robot is NOT
        # navigating back to the dock for a wash (go_wash absent).
        if (
            status.HasField("cleaning")
            and status.cleaning.state == 1  # PAUSED
            and not status.HasField("go_wash")
        ):
            return "paused"
        return "cleaning"
    if s == 6:  # Active clean (alternate)
        return "cleaning"
    if s == 7:  # Go Home
        return "returning"
    if s == 8:  # Active clean (alternate / cruising)
        return "cleaning"
    if s == 15:  # Paused
        return "paused"

    return "idle"


def _map_trigger_source(value: int) -> str:
    """Map Trigger.Source to string.

    0: UNKNOWN
    1: APP
    2: KEY
    3: TIMING
    4: ROBOT
    5: REMOTE_CTRL
    """
    return TRIGGER_SOURCE_NAMES.get(TriggerSource(value), "unknown")


def _map_clean_speed(value: Any) -> str:
    """Map clean speed value to string."""
    try:
        if isinstance(value, str) and value.isdigit():
            idx = int(value)
        elif isinstance(value, int):
            idx = value
        else:
            return str(value)

        if 0 <= idx < len(EUFY_CLEAN_NOVEL_CLEAN_SPEED):
            return EUFY_CLEAN_NOVEL_CLEAN_SPEED[idx].value
    except Exception as e:
        _LOGGER.debug("Error mapping clean speed: %s", e)
    return "Standard"


def _map_dock_status(value: StationResponse) -> str:
    """Map StationResponse to status string."""
    try:
        status = value.status
        _LOGGER.debug(
            "Dock status raw: state=%s, collecting_dust=%s, clear_water_adding=%s, "
            "waste_water_recycling=%s, disinfectant_making=%s, cutting_hair=%s",
            status.state,
            status.collecting_dust,
            status.clear_water_adding,
            status.waste_water_recycling,
            status.disinfectant_making,
            status.cutting_hair,
        )

        if status.collecting_dust:
            return "Emptying dust"
        if status.clear_water_adding:
            return "Adding clean water"
        if status.waste_water_recycling:
            return "Recycling waste water"
        if status.disinfectant_making:
            return "Making disinfectant"
        if status.cutting_hair:
            return "Cutting hair"

        state = status.state
        state_name = StationResponse.StationStatus.State.Name(state)
        state_string = state_name.strip().lower().replace("_", " ")
        return state_string[:1].upper() + state_string[1:]
    except Exception as e:
        _LOGGER.debug("Error mapping dock status: %s", e)
        return "Unknown"


def _parse_scene_info(value: Any) -> list[dict[str, Any]]:
    """Parse SceneResponse from DPS."""
    try:
        scene_response = decode(SceneResponse, value, has_length=True)
        _LOGGER.debug("Decoded SceneResponse: %s", scene_response)
        if not scene_response or not scene_response.infos:
            return []

        scenes = []
        for scene_info in scene_response.infos:
            if scene_info.name and scene_info.valid:
                scenes.append(
                    {
                        "id": scene_info.id.value if scene_info.HasField("id") else 0,
                        "name": scene_info.name,
                        "type": scene_info.type,
                    }
                )
        return scenes
    except Exception as e:
        _LOGGER.debug("Error parsing scene info: %s | Raw: %s", e, value)
        return []


def _deduplicate_room_names(rooms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure room names are unique by appending a suffix to duplicates.

    e.g. two rooms named "Kitchen" become "Kitchen" and "Kitchen (2)".
    """
    names = [room["name"] for room in rooms]
    deduped = deduplicate_names(names)
    return [{**room, "name": name} for room, name in zip(rooms, deduped)]


def _parse_map_data(value: Any) -> dict[str, Any] | None:
    """Parse Map Data (Universal or RoomParams) from DPS."""
    # UniversalDataResponse
    try:
        universal_data = decode(UniversalDataResponse, value, has_length=True)
        if universal_data:
            _LOGGER.debug("Decoded UniversalDataResponse: %s", universal_data)
        if universal_data and (
            universal_data.cur_map_room.map_id or universal_data.cur_map_room.data
        ):
            rooms = []
            for r in universal_data.cur_map_room.data:
                name = (r.name or "").strip() or f"Room {r.id}"
                rooms.append({"id": r.id, "name": name})
            return {
                "map_id": universal_data.cur_map_room.map_id,
                "rooms": _deduplicate_room_names(rooms),
            }
    except Exception as e:
        _LOGGER.debug("UniversalDataResponse parse failed: %s", e)

    # RoomParams
    try:
        room_params = decode(RoomParams, value, has_length=True)
        if room_params:
            _LOGGER.debug("Decoded RoomParams: %s", room_params)
        if room_params and (room_params.map_id or room_params.rooms):
            rooms = []
            for rm in room_params.rooms:
                name = (rm.name or "").strip() or f"Room {rm.id}"
                rooms.append({"id": rm.id, "name": name})
            return {
                "map_id": room_params.map_id,
                "rooms": _deduplicate_room_names(rooms),
            }
    except Exception as e:
        _LOGGER.debug("RoomParams parse failed: %s", e)

    _LOGGER.debug("Failed to parse map data. Raw: %s", value)
    return None


def _parse_multi_map_response(value: Any) -> dict[str, Any] | None:
    """Parse MultiMapsManageResponse from DPS 172.

    Note: MAP_GET_ALL/MAP_GET_ONE responses with pixel data are only
    delivered via P2P, not cloud MQTT. This handler logs the response
    metadata for diagnostics but currently cannot extract pixel data.
    """
    try:
        resp = decode(MultiMapsManageResponse, value)
        _LOGGER.debug(
            "Decoded MultiMapsManageResponse: method=%s, result=%s",
            resp.method,
            resp.result,
        )
        return None
    except Exception as e:
        _LOGGER.debug("Error parsing TimerInfo: %s", e)
        return None


def _process_media_manager(
    state: VacuumState, value: Any, changes: dict[str, Any]
) -> None:
    try:
        resp = decode(MediaManagerResponse, value)
        _LOGGER.debug("Decoded MediaManagerResponse: %s", resp)

        if resp.HasField("status"):
            changes["media_recording"] = resp.status.state == 1
            changes["media_storage_state"] = MEDIA_STORAGE_STATE_NAMES.get(
                int(resp.status.storage), "Normal"
            )
            changes["media_total_space"] = resp.status.total_space
            changes["media_photo_space"] = resp.status.photo_space
            changes["media_video_space"] = resp.status.video_space
            _track_field(state, changes, "media_status")

        if resp.HasField("setting") and resp.setting.HasField("record"):
            res_val = int(resp.setting.record.resolution)
            changes["media_recording_resolution"] = MEDIA_RESOLUTION_NAMES.get(
                res_val, "720p"
            )
            _track_field(state, changes, "media_recording_resolution")

        if resp.HasField("control") and resp.control.HasField("file_info"):
            changes["media_last_capture_path"] = resp.control.file_info.filepath
            changes["media_last_capture_id"] = resp.control.file_info.id
            _track_field(state, changes, "media_last_capture")

    except Exception as e:
        _LOGGER.warning("Error parsing MediaManager (DPS 174): %s", e, exc_info=True)


def _parse_accessories(current_state: AccessoryState, value: Any) -> AccessoryState:
    """Parse ConsumableResponse from DPS."""
    try:
        response = decode(ConsumableResponse, value)
        _LOGGER.debug("Decoded ConsumableResponse: %s", response)
        if not response.HasField("runtime"):
            return current_state

        runtime = response.runtime
        changes: dict[str, Any] = {}

        if runtime.HasField("filter_mesh"):
            changes["filter_usage"] = runtime.filter_mesh.duration
        if runtime.HasField("rolling_brush"):
            changes["main_brush_usage"] = runtime.rolling_brush.duration
        if runtime.HasField("side_brush"):
            changes["side_brush_usage"] = runtime.side_brush.duration
        if runtime.HasField("sensor"):
            changes["sensor_usage"] = runtime.sensor.duration
        if runtime.HasField("scrape"):
            changes["scrape_usage"] = runtime.scrape.duration
        if runtime.HasField("mop"):
            changes["mop_usage"] = runtime.mop.duration
        if runtime.HasField("dustbag"):
            changes["dustbag_usage"] = runtime.dustbag.duration
        if runtime.HasField("dirty_watertank"):
            changes["dirty_watertank_usage"] = runtime.dirty_watertank.duration
        if runtime.HasField("dirty_waterfilter"):
            changes["dirty_waterfilter_usage"] = runtime.dirty_waterfilter.duration

        return replace(current_state, **changes)

    except Exception as e:
        _LOGGER.debug("Error parsing accessory info: %s", e)
        return current_state


def _process_cleaning_parameters(
    state: VacuumState, value: Any, changes: dict[str, Any]
) -> None:
    """Process Cleaning Parameters DPS (154)."""
    # Try decoding as Response first, then Request
    clean_param = None
    try:
        response = decode(CleanParamResponse, value, has_length=True)
        if response and response.HasField("clean_param"):
            clean_param = response.clean_param
        elif response and response.HasField("running_clean_param"):
            clean_param = response.running_clean_param
        elif response and response.HasField("area_clean_param"):
            clean_param = response.area_clean_param
    except Exception as e:
        _LOGGER.debug("Failed to decode CleanParamResponse from DPS 154: %s", e)

    if not clean_param:
        try:
            request = decode(CleanParamRequest, value, has_length=True)
            if request and request.HasField("clean_param"):
                clean_param = request.clean_param
            elif request and request.HasField("area_clean_param"):
                clean_param = request.area_clean_param
        except Exception as e:
            _LOGGER.debug("Failed to decode CleanParamRequest from DPS 154: %s", e)

    if not clean_param:
        _LOGGER.debug("Could not decode Cleaning Parameters from DPS 154")
        return

    # Extract Cleaning Mode
    if clean_param.HasField("clean_type"):
        mode_val = clean_param.clean_type.value
        changes["cleaning_mode"] = CLEANING_MODE_NAMES.get(
            CleaningMode(mode_val), "Vacuum"
        )
        _track_field(state, changes, "cleaning_mode")

    # Extract Fan Speed (available on newer devices in DPS 154)
    if clean_param.HasField("fan"):
        fan_val = clean_param.fan.suction
        changes["fan_speed"] = FAN_SUCTION_NAMES.get(fan_val, "Standard")
        _track_field(state, changes, "fan_speed")
        _LOGGER.debug(
            "DPS 154: Extracted fan speed %s (value: %s)", changes["fan_speed"], fan_val
        )

    # Extract Mop Water Level
    if clean_param.HasField("mop_mode"):
        level_val = clean_param.mop_mode.level
        changes["mop_water_level"] = MOP_WATER_LEVEL_NAMES.get(
            MopWaterLevel(level_val), "Medium"
        )
        _track_field(state, changes, "mop_water_level")
        _LOGGER.debug(
            "DPS 154: Extracted mop water level %s (value: %s)",
            changes["mop_water_level"],
            level_val,
        )
    else:
        _LOGGER.debug("DPS 154: mop_mode not present in cleaning parameters")

    # Extract Corner Cleaning Mode
    if clean_param.HasField("mop_mode"):
        corner_val = clean_param.mop_mode.corner_clean
        changes["corner_cleaning"] = CORNER_CLEANING_NAMES.get(corner_val, "Normal")
        _track_field(state, changes, "corner_cleaning")
        _LOGGER.debug(
            "DPS 154: Extracted corner cleaning %s (value: %s)",
            changes["corner_cleaning"],
            corner_val,
        )

    # Extract Cleaning Intensity
    if clean_param.HasField("clean_extent"):
        extent_val = clean_param.clean_extent.value
        changes["cleaning_intensity"] = CLEANING_INTENSITY_NAMES.get(
            extent_val, "Normal"
        )
        _track_field(state, changes, "cleaning_intensity")
        _LOGGER.debug(
            "DPS 154: Extracted cleaning intensity %s (value: %s)",
            changes["cleaning_intensity"],
            extent_val,
        )

    # Extract Carpet Strategy
    if clean_param.HasField("clean_carpet"):
        carpet_val = clean_param.clean_carpet.strategy
        changes["carpet_strategy"] = CARPET_STRATEGY_NAMES.get(carpet_val, "Auto Raise")
        _track_field(state, changes, "carpet_strategy")
        _LOGGER.debug(
            "DPS 154: Extracted carpet strategy %s (value: %s)",
            changes["carpet_strategy"],
            carpet_val,
        )

    # Extract Smart Mode Switch
    if clean_param.HasField("smart_mode_sw"):
        changes["smart_mode"] = clean_param.smart_mode_sw.value
        _track_field(state, changes, "smart_mode")
        _LOGGER.debug("DPS 154: Extracted smart mode %s", changes["smart_mode"])

    if clean_param.clean_times:
        changes["clean_times"] = clean_param.clean_times
        _track_field(state, changes, "clean_times")

    if _LOGGER.isEnabledFor(logging.DEBUG):
        tracked_fields = {
            "cleaning_mode",
            "fan_speed",
            "mop_water_level",
            "corner_cleaning",
            "cleaning_intensity",
            "carpet_strategy",
            "smart_mode",
        }
        field_count = sum(1 for k in changes if k in tracked_fields)
        _LOGGER.debug(
            "DPS 154: Successfully processed cleaning parameters - extracted %d fields",
            field_count,
        )


def _parse_analysis_response(
    state: VacuumState, value: str, changes: dict[str, Any]
) -> None:
    """Try to decode DPS 179 as AnalysisResponse for battery_info and internal_status."""
    try:
        analysis = decode(AnalysisResponse, value)
    except Exception:
        _LOGGER.debug("DPS 179: AnalysisResponse decode failed, skipping")
        return

    if analysis.HasField("internal_status"):
        status = analysis.internal_status
        if status.robotapp_state:
            changes["robotapp_state"] = status.robotapp_state
            _track_field(state, changes, "robotapp_state")
        if status.motion_state:
            changes["motion_state"] = status.motion_state
            _track_field(state, changes, "motion_state")

    if analysis.HasField("statistics") and analysis.statistics.HasField("battery_info"):
        bat = analysis.statistics.battery_info
        if bat.real_level:
            changes["battery_real_level"] = bat.real_level
            _track_field(state, changes, "battery_real_level")
        if bat.voltage:
            changes["battery_voltage"] = bat.voltage
            _track_field(state, changes, "battery_voltage")
        if bat.current:
            changes["battery_current"] = bat.current
            _track_field(state, changes, "battery_current")
        if bat.temperature:
            changes["battery_temperature"] = round(bat.temperature[0] / 1000.0, 1)
            _track_field(state, changes, "battery_temperature")

    if analysis.HasField("statistics"):
        stats = analysis.statistics

        if stats.HasField("clean"):
            c = stats.clean
            changes["last_clean_area"] = c.clean_area
            changes["last_clean_time"] = c.clean_time
            changes["last_clean_mode"] = int(c.mode)
            changes["last_clean_start"] = c.start_time
            changes["last_clean_end"] = c.end_time
            _track_field(state, changes, "last_clean_stats")

        if stats.HasField("gohome"):
            gh = stats.gohome
            changes["last_gohome_result"] = gh.result
            changes["last_gohome_fail_code"] = int(gh.fail_code)
            changes["last_gohome_start"] = gh.start_time
            changes["last_gohome_end"] = gh.end_time
            _track_field(state, changes, "last_gohome_stats")

        if stats.HasField("ctrl_event"):
            ce = stats.ctrl_event
            changes["ctrl_event_type"] = int(ce.type)
            changes["ctrl_event_source"] = int(ce.source)
            changes["ctrl_event_timestamp"] = ce.timestamp
            _track_field(state, changes, "ctrl_event")

        if stats.HasField("relocate"):
            _LOGGER.debug("DPS 179: relocate record present")
        if stats.HasField("collect"):
            _LOGGER.debug("DPS 179: collect record present")


def _process_timer_response(
    state: VacuumState, value: Any, changes: dict[str, Any]
) -> None:
    try:
        timer_resp = decode(TimerResponse, value)
        _LOGGER.debug(
            "Decoded TimerResponse: method=%s, timers=%d",
            timer_resp.method,
            len(timer_resp.timers),
        )

        schedules = []
        for timer in timer_resp.timers:
            schedule = _parse_timer_info(timer)
            if schedule:
                schedules.append(schedule)

        changes["schedules"] = schedules
        _track_field(state, changes, "schedules")
    except Exception as e:
        _LOGGER.warning("Error parsing Timer Response: %s", e, exc_info=True)


def _parse_timer_info(timer: Any) -> dict[str, Any] | None:
    try:
        if not timer.HasField("id"):
            return None

        schedule: dict[str, Any] = {"id": timer.id.value}

        if timer.HasField("status"):
            schedule["enabled"] = timer.status.opened
            schedule["valid"] = timer.status.valid
        else:
            schedule["enabled"] = False
            schedule["valid"] = False

        if not timer.HasField("desc"):
            return None

        desc = timer.desc
        schedule["trigger"] = "cycle" if desc.trigger == 1 else "single"

        if desc.HasField("timing"):
            schedule["hour"] = desc.timing.hours
            schedule["minute"] = desc.timing.minutes
        else:
            schedule["hour"] = 0
            schedule["minute"] = 0

        schedule["week_bits"] = desc.cycle.week_bits if desc.HasField("cycle") else 0

        if timer.HasField("action"):
            action = timer.action
            action_type = int(action.type)
            schedule["action_type"] = action_type
            schedule["action_label"] = SCHEDULE_ACTION_NAMES.get(
                action_type, f"Schedule {action_type}"
            )
            if (
                action.HasField("sche_scene_clean")
                and action.sche_scene_clean.scene_name
            ):
                schedule["action_label"] = (
                    f"Scene: {action.sche_scene_clean.scene_name}"
                )
        else:
            schedule["action_type"] = 0
            schedule["action_label"] = "Auto Clean"

        return schedule
    except Exception as e:
        _LOGGER.debug("Error parsing TimerInfo: %s", e)
        return None
