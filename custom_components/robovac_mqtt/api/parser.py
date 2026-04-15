from __future__ import annotations

import base64
import logging
from dataclasses import replace
from typing import Any, cast

from google.protobuf.json_format import MessageToDict

from ..const import (
    CARPET_STRATEGY_NAMES,
    CHARGING_STATE_NAMES,
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
    GO_WASH_MODE_NAMES,
    GO_WASH_STATE_NAMES,
    HANDLED_DPS_IDS,
    KNOWN_UNPROCESSED_DPS,
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
from ..proto.cloud.analysis_pb2 import AnalysisResponse
from ..proto.cloud.app_device_info_pb2 import DeviceInfo
from ..proto.cloud.clean_param_pb2 import CleanParamRequest, CleanParamResponse
from ..proto.cloud.clean_statistics_pb2 import CleanStatistics
from ..proto.cloud.consumable_pb2 import ConsumableResponse
from ..proto.cloud.control_pb2 import ModeCtrlRequest
from ..proto.cloud.error_code_pb2 import ErrorCode, PromptCode
from ..proto.cloud.map_edit_pb2 import MapEditRequest
from ..proto.cloud.media_manager_pb2 import MediaManagerResponse
from ..proto.cloud.multi_maps_pb2 import MultiMapsManageResponse
from ..proto.cloud.scene_pb2 import SceneResponse
from ..proto.cloud.station_pb2 import StationResponse
from ..proto.cloud.stream_pb2 import RoomParams
from ..proto.cloud.timing_pb2 import TimerResponse
from ..proto.cloud.undisturbed_pb2 import UndisturbedResponse
from ..proto.cloud.unisetting_pb2 import UnisettingResponse
from ..proto.cloud.universal_data_pb2 import UniversalDataResponse
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


# -- Proto novelty detection --------------------------------------------------
# Logs new field paths and unknown wire tags ONCE per runtime, per DPS key.
# This catches: (a) known-schema fields the parser doesn't extract,
#               (b) wire-level tags not in our .proto definitions.
_seen_field_shapes: dict[str, set[str]] = {}  # "dps_key" -> set of field paths
_seen_wire_tags: dict[str, set[int]] = {}  # "dps_key" -> set of known+unknown tags
_seen_scalar_values: dict[str, set[str]] = (
    {}
)  # "dps_key" -> set of "type:value" strings
_seen_telemetry_tags: dict[str, set[int]] = {}
_seen_recursive_tags: dict[str, set[str]] = {}  # "dps_key:path" -> set of unknown tags
_novelty_dirty = False  # Set True when any cache grows; coordinator checks and saves


def get_novelty_caches() -> dict[str, Any]:
    return {
        "field_shapes": {k: sorted(v) for k, v in _seen_field_shapes.items()},
        "wire_tags": {k: sorted(v) for k, v in _seen_wire_tags.items()},
        "scalar_values": {k: sorted(v) for k, v in _seen_scalar_values.items()},
        "telemetry_tags": {k: sorted(v) for k, v in _seen_telemetry_tags.items()},
        "recursive_tags": {k: sorted(v) for k, v in _seen_recursive_tags.items()},
    }


def load_novelty_caches(data: dict[str, Any]) -> None:
    global _novelty_dirty
    _seen_field_shapes.update(
        {k: set(v) for k, v in data.get("field_shapes", {}).items()}
    )
    _seen_wire_tags.update({k: set(v) for k, v in data.get("wire_tags", {}).items()})
    _seen_scalar_values.update(
        {k: set(v) for k, v in data.get("scalar_values", {}).items()}
    )
    _seen_telemetry_tags.update(
        {k: set(v) for k, v in data.get("telemetry_tags", {}).items()}
    )
    _seen_recursive_tags.update(
        {k: set(v) for k, v in data.get("recursive_tags", {}).items()}
    )
    _novelty_dirty = False


def is_novelty_dirty() -> bool:
    return _novelty_dirty


def clear_novelty_dirty() -> None:
    global _novelty_dirty
    _novelty_dirty = False


def _log_scalar_novelty(dps_key: str, value: Any) -> None:
    sig = f"{type(value).__name__}:{value}"
    prev = _seen_scalar_values.get(dps_key, set())
    if sig not in prev:
        global _novelty_dirty
        _LOGGER.debug(
            "SCALAR_NOVELTY | dps=%s | value=%s | type=%s",
            dps_key,
            value,
            type(value).__name__,
        )
        _seen_scalar_values[dps_key] = prev | {sig}
        _novelty_dirty = True


def _flatten_proto_paths(d: dict[str, object], prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k
        paths.add(path)
        if isinstance(v, dict):
            paths |= _flatten_proto_paths(v, path)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    paths |= _flatten_proto_paths(item, path)
    return paths


def _listfields_paths(msg: Any, prefix: str = "") -> set[str]:
    """Walk proto via ListFields() to catch explicitly-set default values."""
    from google.protobuf.descriptor import FieldDescriptor

    paths: set[str] = set()
    for fd, val in msg.ListFields():
        path = f"{prefix}.{fd.name}" if prefix else fd.name
        paths.add(path)
        if fd.type == FieldDescriptor.TYPE_MESSAGE:
            if fd.label == FieldDescriptor.LABEL_REPEATED:
                for item in val:
                    paths |= _listfields_paths(item, path)
            else:
                paths |= _listfields_paths(val, path)
    return paths


def _extract_wire_tags(
    raw_bytes: bytes,
) -> tuple[set[int], dict[int, bytes], dict[int, tuple[int, Any]]]:
    """Extract field numbers, length-delimited raw bytes, and per-field wire details."""
    tags: set[int] = set()
    ld_fields: dict[int, bytes] = {}  # field_num -> raw bytes (for recursion)
    field_details: dict[int, tuple[int, Any]] = {}  # field_num -> (wire_type, value)
    i = 0
    while i < len(raw_bytes):
        tag, i = _decode_varint(raw_bytes, i)
        fn, wt = tag >> 3, tag & 7
        if fn == 0:
            break
        tags.add(fn)
        if wt == 0:  # varint
            val, i = _decode_varint(raw_bytes, i)
            field_details[fn] = (0, val)
        elif wt == 2:  # length-delimited
            blen, i = _decode_varint(raw_bytes, i)
            data = raw_bytes[i : i + blen]
            ld_fields[fn] = data
            field_details[fn] = (2, data)
            i += blen
        elif wt == 5:  # 32-bit fixed
            field_details[fn] = (5, raw_bytes[i : i + 4])
            i += 4
        elif wt == 1:  # 64-bit fixed
            field_details[fn] = (1, raw_bytes[i : i + 8])
            i += 8
        else:
            break
    return tags, ld_fields, field_details


_WIRE_TYPE_NAMES = {0: "varint", 1: "fixed64", 2: "bytes", 5: "fixed32"}


def _format_unknown_field(wt: int, val: Any) -> str:
    if wt == 0:
        return f"varint={val}"
    if wt == 2:
        hexval = val.hex()[:80]
        try:
            s = val.decode("utf-8")
            if all(32 <= c < 127 for c in val):
                return f'string[{len(val)}]="{s}"'
        except (UnicodeDecodeError, ValueError):
            pass
        return f"bytes[{len(val)}]={hexval}"
    if wt == 5:
        return f"fixed32={int.from_bytes(val, 'little')}"
    if wt == 1:
        return f"fixed64={int.from_bytes(val, 'little')}"
    return f"wire{wt}=?"


def _scan_unknown_tags_recursive(
    dps_key: str,
    proto_msg: Any,
    raw_bytes: bytes,
    path: str = "",
) -> None:
    """Scan for unknown wire tags at this level and recurse into known sub-messages."""
    from google.protobuf.descriptor import FieldDescriptor

    wire_tags, ld_fields, field_details = _extract_wire_tags(raw_bytes)
    known_nums = set(proto_msg.DESCRIPTOR.fields_by_number.keys())
    unknown = wire_tags - known_nums

    cache_key = f"{dps_key}:{path}" if path else dps_key
    prev = _seen_recursive_tags.get(cache_key, set())
    new_unknown = {str(t) for t in unknown} - prev
    if new_unknown:
        label = f"{type(proto_msg).__name__}" + (f".{path}" if path else "")
        details = []
        for t in sorted(int(t) for t in new_unknown):
            wt, val = field_details.get(t, (-1, None))
            details.append(f"field={t} {_format_unknown_field(wt, val)}")
        _LOGGER.warning(
            "PROTO_UNKNOWN_TAGS | dps=%s | location=%s | fields: %s",
            dps_key,
            label,
            "; ".join(details),
        )
        _seen_recursive_tags[cache_key] = prev | new_unknown
        global _novelty_dirty
        _novelty_dirty = True
    elif unknown:
        label = f"{type(proto_msg).__name__}" + (f".{path}" if path else "")
        _LOGGER.debug(
            "PROTO_UNKNOWN_TAGS_REPEAT | dps=%s | location=%s | tag_count=%d",
            dps_key,
            label,
            len(unknown),
        )

    for fn, raw_sub in ld_fields.items():
        fd = proto_msg.DESCRIPTOR.fields_by_number.get(fn)
        if (
            fd
            and fd.type == FieldDescriptor.TYPE_MESSAGE
            and fd.label != FieldDescriptor.LABEL_REPEATED
        ):
            sub_msg = getattr(proto_msg, fd.name, None)
            if sub_msg is not None:
                sub_path = f"{path}.{fd.name}" if path else fd.name
                _scan_unknown_tags_recursive(dps_key, sub_msg, raw_sub, sub_path)


def _log_proto_novelty(
    dps_key: str,
    proto_msg: Any,
    raw_b64: str,
    has_length: bool = True,
) -> None:
    try:
        # Presence-aware field path detection via ListFields()
        paths = _listfields_paths(proto_msg)
        # Also get MessageToDict paths (catches map fields, oneof display names)
        d = MessageToDict(proto_msg, preserving_proto_field_name=True)
        paths |= _flatten_proto_paths(d)

        cache_key = dps_key
        prev = _seen_field_shapes.get(cache_key, set())
        new_paths = paths - prev
        if new_paths:
            _LOGGER.debug(
                "PROTO_NOVELTY | dps=%s | type=%s | new_field_paths=%s",
                dps_key,
                type(proto_msg).__name__,
                sorted(new_paths),
            )
            global _novelty_dirty
            _novelty_dirty = True
        _seen_field_shapes[cache_key] = prev | paths

        # Recursive wire tag scan for unknown fields at all nesting levels
        raw = base64.b64decode(raw_b64)
        if has_length and raw:
            _, pos = _decode_varint(raw, 0)
            raw = raw[pos:]
        _scan_unknown_tags_recursive(dps_key, proto_msg, raw)
    except Exception:
        _LOGGER.warning(
            "Proto novelty detection failed for dps=%s", dps_key, exc_info=True
        )


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
    _log_raw_telemetry_novelty(outer, sub, inner)
    if 4 not in inner or 5 not in inner:
        return None
    return {"x": inner[4], "y": inner[5]}


def _log_raw_telemetry_novelty(
    outer: dict[int, Any],
    sub: dict[int, Any],
    inner: dict[int, Any],
) -> None:
    for level_name, fields in [("outer", outer), ("sub", sub), ("inner", inner)]:
        cache_key = f"179_telemetry_{level_name}"
        tags = set(fields.keys())
        prev = _seen_telemetry_tags.get(cache_key, set())
        new_tags = tags - prev
        if new_tags:
            _LOGGER.debug(
                "TELEMETRY_NOVELTY | level=%s | new_tags=%s | all_tags=%s",
                level_name,
                sorted(new_tags),
                sorted(tags),
            )
            _seen_telemetry_tags[cache_key] = prev | tags
            global _novelty_dirty
            _novelty_dirty = True


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

    return replace(state, **changes), changes


def _process_station_status(
    state: VacuumState,
    dps: dict[str, Any],
    changes: dict[str, Any],
    dps_map: dict[str, str],
) -> None:
    """Process Station Status DPS."""
    if dps_map["STATION_STATUS"] not in dps:
        return

    value = dps[dps_map["STATION_STATUS"]]
    try:
        station = decode(StationResponse, value)
        _log_proto_novelty("173", station, value)
        new_dock_status = _map_dock_status(station)
        # Debouncing is handled in coordinator, not here
        changes["dock_status"] = new_dock_status
        _track_field(state, changes, "dock_status")

        if station.HasField("clean_water"):
            changes["station_clean_water"] = station.clean_water.value
            _track_field(state, changes, "station_clean_water")

        if station.HasField("status"):
            changes["dock_connected"] = station.status.connected
            _track_field(state, changes, "dock_connected")

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
    state: VacuumState,
    dps: dict[str, Any],
    changes: dict[str, Any],
    dps_map: dict[str, str],
) -> None:
    """Process Work Status DPS."""
    if dps_map["WORK_STATUS"] not in dps:
        return

    value = dps[dps_map["WORK_STATUS"]]
    try:
        work_status = decode(WorkStatus, value)
        _log_proto_novelty("153", work_status, value)
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

        if work_status.HasField("charging"):
            changes["charging_state"] = CHARGING_STATE_NAMES.get(
                int(work_status.charging.state), ""
            )
            _track_field(state, changes, "charging_state")
        elif state.charging_state:
            changes["charging_state"] = ""

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
                _LOGGER.debug("Trigger source inferred from mode: %s", trigger_source)

        changes["trigger_source"] = trigger_source
        if trigger_source == "unknown" and changes.get("activity") in (
            "docked",
            "idle",
        ):
            changes["trigger_source"] = "none"

        # Extract Work Mode
        if work_status.HasField("mode"):
            mode_val = work_status.mode.value
            changes["work_mode"] = WORK_MODE_NAMES.get(mode_val, "unknown")
            _track_field(state, changes, "work_mode")
        elif state.work_mode == "unknown" and changes.get("activity") == "cleaning":
            # If we don't know the mode yet but we are cleaning, default to Auto
            changes["work_mode"] = "Auto"
        elif changes.get("activity") not in ("cleaning", "returning"):
            new_mode = (
                "Standby"
                if changes.get("activity") in ("docked", "idle")
                else "unknown"
            )
            if state.work_mode != new_mode:
                changes["work_mode"] = new_mode

        # Fallback/Override if cleaning.scheduled_task is explicit
        if work_status.HasField("cleaning") and work_status.cleaning.scheduled_task:
            changes["trigger_source"] = "schedule"

        # Update dock_status from WorkStatus.
        # go_wash.mode is the authoritative signal for wash/dry cycle state.
        # Station sub-fields (washing_drying_system, water_injection_system)
        # report sub-phases within that cycle and must not overwrite the
        # primary dock status when go_wash is active.
        is_go_wash_active = work_status.HasField(
            "go_wash"
        ) and work_status.go_wash.mode in (1, 2)

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

            if st.HasField("water_tank_state"):
                changes["water_tank_clear_adding"] = (
                    st.water_tank_state.clear_water_adding
                )
                changes["water_tank_waste_recycling"] = (
                    st.water_tank_state.waste_water_recycling
                )
                _track_field(state, changes, "water_tank_state")

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

        if work_status.HasField("go_wash"):
            gw = work_status.go_wash
            changes["go_wash_state"] = GO_WASH_STATE_NAMES.get(int(gw.state), "")
            changes["go_wash_mode"] = GO_WASH_MODE_NAMES.get(int(gw.mode), "")
            _track_field(state, changes, "go_wash_state")
        elif state.go_wash_state:
            changes["go_wash_state"] = ""
            changes["go_wash_mode"] = ""

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
            changes["upgrading"] = work_status.upgrading.state != 0
            _track_field(state, changes, "upgrading")

        if work_status.HasField("mapping"):
            changes["mapping_state"] = int(work_status.mapping.state)
            changes["mapping_mode"] = int(work_status.mapping.mode)
            _track_field(state, changes, "mapping_state")

        if work_status.HasField("relocating"):
            changes["relocating"] = work_status.relocating.state != 0
            _track_field(state, changes, "relocating")

        if work_status.HasField("roller_brush_cleaning"):
            changes["roller_brush_cleaning"] = (
                work_status.roller_brush_cleaning.state != 0
            )
            _track_field(state, changes, "roller_brush_cleaning")

        if work_status.HasField("breakpoint"):
            changes["breakpoint_available"] = work_status.breakpoint.state != 0
            _track_field(state, changes, "breakpoint_available")

        if work_status.HasField("station"):
            if work_status.station.HasField("dust_collection_system"):
                changes["station_work_status"] = int(
                    work_status.station.dust_collection_system.state
                )
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
    state: VacuumState,
    dps: dict[str, Any],
    changes: dict[str, Any],
    dps_map: dict[str, str],
) -> None:
    """Process Play/Pause DPS (152) - extract active cleaning targets."""
    if dps_map["PLAY_PAUSE"] not in dps:
        return

    value = dps[dps_map["PLAY_PAUSE"]]
    try:
        mode_ctrl = decode(ModeCtrlRequest, value)
        _log_proto_novelty("152", mode_ctrl, value)

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
    state: VacuumState,
    dps: dict[str, Any],
    changes: dict[str, Any],
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
                _log_scalar_novelty("163", value)
                new_dynamic = dict(changes.get("dynamic_values", state.dynamic_values))
                new_dynamic[key] = int(value)
                changes["dynamic_values"] = new_dynamic
                _track_field(state, changes, "battery_level")

            elif key == dps_map["POWER"]:
                parsed = (
                    str(value).lower() == "true"
                    if isinstance(value, str)
                    else bool(value)
                )
                changes["power"] = parsed
                _log_scalar_novelty("151", value)
                new_dynamic = dict(changes.get("dynamic_values", state.dynamic_values))
                new_dynamic[key] = parsed
                changes["dynamic_values"] = new_dynamic
                _track_field(state, changes, "power")

            elif key == dps_map["CLEAN_SPEED"]:
                mapped = _map_clean_speed(value)
                changes["fan_speed"] = mapped
                _log_scalar_novelty("158", value)
                new_dynamic = dict(changes.get("dynamic_values", state.dynamic_values))
                new_dynamic[key] = int(value)
                changes["dynamic_values"] = new_dynamic
                _track_field(state, changes, "fan_speed")

            elif key == dps_map["ERROR_CODE"]:
                error_proto = decode(ErrorCode, value)
                _log_proto_novelty("177", error_proto, value)
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
                    _log_proto_novelty("178", prompt, value)
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
                changes["accessories"] = _parse_accessories(state.accessories, value)
                _track_field(state, changes, "accessories")
                try:
                    _cr = decode(ConsumableResponse, value)
                    _log_proto_novelty("168", _cr, value)
                    if _cr.HasField("runtime") and _cr.runtime.last_time:
                        changes["consumable_last_time"] = _cr.runtime.last_time
                        _track_field(state, changes, "consumable_last_time")
                except Exception:
                    _LOGGER.warning(
                        "Failed to parse consumable runtime from DPS %s",
                        key,
                        exc_info=True,
                    )

            elif key == dps_map["CLEANING_STATISTICS"]:
                stats = decode(CleanStatistics, value)
                _log_proto_novelty("167", stats, value)
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
                    changes["user_total_cleaning_time"] = (
                        stats.user_total.clean_duration
                    )
                    changes["user_total_cleaning_area"] = stats.user_total.clean_area
                    changes["user_total_cleaning_count"] = stats.user_total.clean_count
                    _track_field(state, changes, "user_total_stats")

            elif key == dps_map["SCENE_INFO"]:
                changes["scenes"] = _parse_scene_info(value)

            elif key == dps_map["TIMING"]:
                _process_timer_response(state, value, changes)

            elif key == dps_map["RESERVED2"]:
                map_info = _parse_map_data(value)
                if map_info:
                    changes["map_id"] = map_info.get("map_id", 0)
                    changes["rooms"] = map_info.get("rooms", [])
                    _track_field(state, changes, "map_id")

            elif key == dps_map["CLEANING_PARAMETERS"]:
                _process_cleaning_parameters(state, value, changes)

            elif key == dps_map["FIND_ROBOT"]:
                parsed = str(value).lower() == "true"
                changes["find_robot"] = parsed
                _log_scalar_novelty("160", value)
                new_dynamic = dict(changes.get("dynamic_values", state.dynamic_values))
                new_dynamic[key] = parsed
                changes["dynamic_values"] = new_dynamic

            elif key == dps_map["APP_DEV_INFO"]:
                info = decode(DeviceInfo, value)
                _log_proto_novelty("169", info, value)
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
                ota_channel = getattr(cast(Any, info), "ota_channel", "")
                if ota_channel:
                    changes["ota_channel"] = ota_channel
                    _track_field(state, changes, "ota_channel")
                if info.video_sn:
                    changes["video_sn"] = info.video_sn
                if info.HasField("station"):
                    if info.station.software:
                        changes["station_firmware"] = info.station.software
                    if info.station.hardware:
                        changes["station_hardware"] = info.station.hardware
            elif key == dps_map["MAP_EDIT_REQUEST"]:
                map_edit = _parse_map_edit(value)
                if map_edit:
                    changes.update(map_edit)
                    _track_field(state, changes, "map_edit_method")

            elif key == dps_map.get("MULTI_MAP_CTRL", "171"):
                multi_map_ctrl = _parse_multi_map_ctrl(value)
                if multi_map_ctrl:
                    changes.update(multi_map_ctrl)
                    _track_field(state, changes, "multi_map_ctrl")
            elif key == dps_map["MULTI_MAP_MANAGE"]:
                if value is None:
                    _LOGGER.debug("DPS 172: None value (initial state)")
                else:
                    multi_map = _parse_multi_map_response(value)
                    if multi_map:
                        changes.update(multi_map)
                        _track_field(state, changes, "multi_map")

            elif key == dps_map["UNSETTING"]:
                settings = decode(UnisettingResponse, value)
                _log_proto_novelty("176", settings, value)
                changes["wifi_signal"] = (settings.ap_signal_strength / 2) - 100
                _track_field(state, changes, "wifi_signal")
                if settings.HasField("children_lock"):
                    changes["child_lock"] = settings.children_lock.value
                    _track_field(state, changes, "child_lock")

                # Switch fields (proto wrapper: Switch.value -> bool)
                for field_name in (
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
                ):
                    try:
                        if settings.HasField(field_name):
                            changes[field_name] = getattr(settings, field_name).value
                            _track_field(state, changes, field_name)
                    except Exception:
                        _LOGGER.warning(
                            "Error parsing unisetting field %s",
                            field_name,
                            exc_info=True,
                        )

                # Numerical field
                try:
                    if settings.HasField("dust_full_remind"):
                        changes["dust_full_remind"] = settings.dust_full_remind.value
                        _track_field(state, changes, "dust_full_remind")
                except Exception:
                    _LOGGER.warning("Error parsing dust_full_remind", exc_info=True)

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
                            changes["clean_strategy_version"] = (
                                uni.clean_strategy_version
                            )
                            _track_field(state, changes, "clean_strategy_version")
                        if uni.HasField("custom_clean_mode"):
                            changes["custom_clean_mode"] = uni.custom_clean_mode.value
                            _track_field(state, changes, "custom_clean_mode")
                except Exception:
                    _LOGGER.warning("Error parsing unistate", exc_info=True)

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
                            changes["wifi_connection_result"] = int(
                                ap.connection.result
                            )
                            changes["wifi_connection_timestamp"] = (
                                ap.connection.timestamp
                            )
                            _track_field(state, changes, "wifi_connection_result")
                            _track_field(state, changes, "wifi_connection_timestamp")
                except Exception:
                    _LOGGER.warning("Error parsing wifi_data", exc_info=True)

            elif key == dps_map["UNDISTURBED"]:
                undisturbed = decode(UndisturbedResponse, value)
                _log_proto_novelty("157", undisturbed, value)
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
                if pos:
                    raw_x, raw_y = pos["x"], pos["y"]
                    changes["robot_position_x"] = raw_x
                    changes["robot_position_y"] = raw_y
                    _track_field(state, changes, "robot_position")

                _parse_analysis_response(state, value, changes)

            elif key == dps_map.get("BOOST_IQ"):
                if isinstance(value, bool):
                    changes["boost_iq"] = value
                    _log_scalar_novelty("159", value)
                    new_dynamic = dict(
                        changes.get("dynamic_values", state.dynamic_values)
                    )
                    new_dynamic[key] = value
                    changes["dynamic_values"] = new_dynamic
                    _track_field(state, changes, "boost_iq")

            elif key == dps_map.get("VOLUME"):
                if isinstance(value, (int, float)):
                    vol = int(value)
                    changes["volume"] = vol
                    _log_scalar_novelty("161", value)
                    new_dynamic = dict(
                        changes.get("dynamic_values", state.dynamic_values)
                    )
                    new_dynamic[key] = vol
                    changes["dynamic_values"] = new_dynamic
                    _track_field(state, changes, "volume")

            elif key not in HANDLED_DPS_IDS and key not in KNOWN_UNPROCESSED_DPS:
                if catalog_types and key in catalog_types:
                    dtype = catalog_types[key]
                    new_dynamic = dict(
                        changes.get("dynamic_values", state.dynamic_values)
                    )
                    if dtype == "Bool":
                        new_dynamic[key] = (
                            str(value).lower() == "true"
                            if isinstance(value, str)
                            else bool(value)
                        )
                    elif dtype == "Value":
                        try:
                            new_dynamic[key] = (
                                int(value) if isinstance(value, str) else value
                            )
                        except (ValueError, TypeError):
                            pass
                    elif dtype == "Enum":
                        try:
                            new_dynamic[key] = int(value)
                        except (ValueError, TypeError):
                            new_dynamic[key] = value
                    changes["dynamic_values"] = new_dynamic
                    _track_field(state, changes, f"dynamic_{key}")
                else:
                    _LOGGER.debug(
                        "UNKNOWN_DPS | key=%s | value=%s | value_type=%s | %s",
                        key,
                        _truncate_value(value),
                        type(value).__name__,
                        _catalog_summary(key, dps_catalog),
                    )

            elif key in KNOWN_UNPROCESSED_DPS:
                cat_type = catalog_types.get(key, "") if catalog_types else ""
                if cat_type == "Raw" and isinstance(value, str) and value:
                    try:
                        raw_bytes = base64.b64decode(value)
                        if raw_bytes:
                            try:
                                size_raw: int
                                pos_raw: int
                                size_raw, pos_raw = _decode_varint(raw_bytes, 0)
                                size_index: int = size_raw
                                start_index: int = pos_raw
                                if start_index + size_index == len(raw_bytes):
                                    raw_bytes = raw_bytes[start_index:]
                            except Exception:
                                pass
                        hex_dump = (
                            raw_bytes.hex()
                            if len(raw_bytes) <= 64
                            else raw_bytes[:64].hex() + f"...({len(raw_bytes)}b)"
                        )
                        _LOGGER.debug(
                            "KNOWN_UNPROCESSED_DPS | key=%s | value=%s | hex=%s | %s",
                            key,
                            _truncate_value(value),
                            hex_dump,
                            _catalog_summary(key, dps_catalog),
                        )
                    except Exception:
                        _LOGGER.debug(
                            "KNOWN_UNPROCESSED_DPS | key=%s | value=%s | value_type=%s | %s",
                            key,
                            _truncate_value(value),
                            type(value).__name__,
                            _catalog_summary(key, dps_catalog),
                        )
                else:
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
        state_name = str(StationResponse.StationStatus.State.Name(state))
        state_string = state_name.strip().lower().replace("_", " ")
        return state_string[:1].upper() + state_string[1:]
    except Exception as e:
        _LOGGER.debug("Error mapping dock status: %s", e)
        return "Unknown"


def _parse_scene_info(value: Any) -> list[dict[str, Any]]:
    """Parse SceneResponse from DPS."""
    try:
        scene_response = decode(SceneResponse, value, has_length=True)
        _log_proto_novelty("180", scene_response, value)
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
        _log_proto_novelty("165", universal_data, value)
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
        _log_proto_novelty("165", room_params, value)
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
        _log_proto_novelty("172", resp, value)
        method_enum = MultiMapsManageResponse.DESCRIPTOR.fields_by_name[
            "method"
        ].enum_type
        method_name = (
            method_enum.values_by_number.get(int(resp.method)) if method_enum else None
        )
        result_enum = MultiMapsManageResponse.DESCRIPTOR.fields_by_name[
            "result"
        ].enum_type
        result_name = (
            result_enum.values_by_number.get(int(resp.result)) if result_enum else None
        )

        parsed: dict[str, Any] = {
            "multi_map_method": (
                method_name.name if method_name else str(int(resp.method))
            ),
            "multi_map_result": (
                result_name.name if result_name else str(int(resp.result))
            ),
            "multi_map_seq": resp.seq,
        }

        if resp.HasField("map_infos"):
            parsed["multi_map_selected_id"] = resp.map_infos.map_id
            parsed["multi_map_name"] = resp.map_infos.name

        if resp.HasField("complete_maps"):
            parsed["multi_map_count"] = len(resp.complete_maps.complete_map)
            if (
                not parsed.get("multi_map_selected_id")
                and resp.complete_maps.complete_map
            ):
                parsed["multi_map_selected_id"] = resp.complete_maps.complete_map[
                    0
                ].map_id
                parsed["multi_map_name"] = resp.complete_maps.complete_map[0].name

        return parsed
    except Exception as e:
        _LOGGER.debug("Error parsing MultiMapsManageResponse: %s", e)
        return None


def _parse_map_edit(value: Any) -> dict[str, Any] | None:
    """Parse MapEditRequest echo from DPS 170."""
    try:
        request = decode(MapEditRequest, value)
        _log_proto_novelty("170", request, value)
        method_enum = MapEditRequest.DESCRIPTOR.fields_by_name["method"].enum_type
        method_name = (
            method_enum.values_by_number.get(int(request.method))
            if method_enum
            else None
        )
        return {
            "map_edit_method": (
                method_name.name if method_name else str(int(request.method))
            ),
            "map_edit_seq": request.seq,
            "map_edit_map_id": request.map_id,
        }
    except Exception as e:
        _LOGGER.debug("Error parsing MapEditRequest: %s", e)
        return None


def _parse_multi_map_ctrl(value: Any) -> dict[str, Any] | None:
    """Parse raw DPS 171 multi-map control echo.

    No proto definition is available in this repo, so keep a minimal
    schema-free parse of the leading varint fields for diagnostics.
    """
    if not isinstance(value, str) or not value:
        return None

    try:
        raw = base64.b64decode(value)
        if raw:
            _, pos = _decode_varint(raw, 0)
            if pos <= len(raw):
                raw = raw[pos:]
        fields = _decode_raw_varints(raw)
        parsed: dict[str, Any] = {}
        method = fields.get(1)
        seq = fields.get(2)
        if isinstance(method, int):
            parsed["multi_map_ctrl_method"] = method
        if isinstance(seq, int):
            parsed["multi_map_ctrl_seq"] = seq
        return parsed or None
    except Exception as e:
        _LOGGER.debug("Error parsing raw multi-map ctrl DPS 171: %s", e)
        return None


def _process_media_manager(
    state: VacuumState, value: Any, changes: dict[str, Any]
) -> None:
    try:
        resp = decode(MediaManagerResponse, value)
        _log_proto_novelty("174", resp, value)

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
        _log_proto_novelty("168", response, value)
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

        runtime_any = cast(Any, runtime)
        if runtime.HasField("accessory_12"):
            changes["accessory_12_usage"] = runtime_any.accessory_12.duration
        if runtime.HasField("accessory_13"):
            changes["accessory_13_usage"] = runtime_any.accessory_13.duration
        if runtime.HasField("accessory_15"):
            changes["accessory_15_usage"] = runtime_any.accessory_15.duration
        if runtime.HasField("accessory_19"):
            changes["accessory_19_usage"] = runtime_any.accessory_19.duration

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
        _log_proto_novelty("154", response, value)
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
            _log_proto_novelty("154", request, value)
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

    # Extract Mop Water Level
    if clean_param.HasField("mop_mode"):
        level_val = clean_param.mop_mode.level
        changes["mop_water_level"] = MOP_WATER_LEVEL_NAMES.get(
            MopWaterLevel(level_val), "Medium"
        )
        _track_field(state, changes, "mop_water_level")
    else:
        pass

    # Extract Corner Cleaning Mode
    if clean_param.HasField("mop_mode"):
        corner_val = clean_param.mop_mode.corner_clean
        changes["corner_cleaning"] = CORNER_CLEANING_NAMES.get(corner_val, "Normal")
        _track_field(state, changes, "corner_cleaning")

    # Extract Cleaning Intensity
    if clean_param.HasField("clean_extent"):
        extent_val = clean_param.clean_extent.value
        changes["cleaning_intensity"] = CLEANING_INTENSITY_NAMES.get(
            extent_val, "Normal"
        )
        _track_field(state, changes, "cleaning_intensity")

    # Extract Carpet Strategy
    if clean_param.HasField("clean_carpet"):
        carpet_val = clean_param.clean_carpet.strategy
        changes["carpet_strategy"] = CARPET_STRATEGY_NAMES.get(carpet_val, "Auto Raise")
        _track_field(state, changes, "carpet_strategy")

    # Extract Smart Mode Switch
    if clean_param.HasField("smart_mode_sw"):
        changes["smart_mode"] = clean_param.smart_mode_sw.value
        _track_field(state, changes, "smart_mode")
    if clean_param.clean_times:
        changes["clean_times"] = clean_param.clean_times
        _track_field(state, changes, "clean_times")


def _parse_analysis_response(
    state: VacuumState, value: str, changes: dict[str, Any]
) -> None:
    """Try to decode DPS 179 as AnalysisResponse for battery_info and internal_status."""
    try:
        analysis = decode(AnalysisResponse, value)
        _log_proto_novelty("179", analysis, value)
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
        # Guard: the device periodically sends a "heartbeat" analysis message
        # with ALL battery fields zeroed out, immediately followed by a real
        # message with actual values. Accepting the zeroed message causes the
        # battery sensors to flicker 0→real→0→real every ~10 seconds, which
        # floods any below-threshold automations.  Discard when all key
        # indicators are simultaneously zero (real_level, voltage, current).
        _is_empty_heartbeat = (
            bat.real_level == 0 and bat.voltage == 0 and bat.current == 0
        )
        if not _is_empty_heartbeat:
            if bat.real_level is not None:
                changes["battery_real_level"] = bat.real_level
                _track_field(state, changes, "battery_real_level")
            if bat.voltage is not None:
                changes["battery_voltage"] = bat.voltage
                _track_field(state, changes, "battery_voltage")
            if bat.current is not None:
                changes["battery_current"] = bat.current
                _track_field(state, changes, "battery_current")
            if bat.temperature:
                changes["battery_temperature"] = round(bat.temperature[0] / 1000.0, 1)
                _track_field(state, changes, "battery_temperature")
            if bat.show_level is not None:
                changes["battery_show_level"] = bat.show_level
                _track_field(state, changes, "battery_show_level")
            if bat.update_time:
                changes["battery_update_time"] = bat.update_time
                _track_field(state, changes, "battery_update_time")

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

        if stats.HasField("collect"):
            col = stats.collect
            changes["dust_collect_result"] = bool(col.result)
            changes["dust_collect_start_time"] = col.start_time
            _track_field(state, changes, "dust_collect_stats")

        if stats.HasField("ctrl_event"):
            ce = stats.ctrl_event
            changes["ctrl_event_type"] = int(ce.type)
            changes["ctrl_event_source"] = int(ce.source)
            changes["ctrl_event_timestamp"] = ce.timestamp
            _track_field(state, changes, "ctrl_event")

        if stats.HasField("battery_curve") and stats.battery_curve.HasField(
            "discharge"
        ):
            readings = [v / 10.0 for v in stats.battery_curve.discharge.values]
            if readings:
                changes["battery_discharge_curve"] = readings
                _track_field(state, changes, "battery_discharge_curve")


def _process_timer_response(
    state: VacuumState, value: Any, changes: dict[str, Any]
) -> None:
    try:
        timer_resp = decode(TimerResponse, value)
        _log_proto_novelty("164", timer_resp, value)

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
