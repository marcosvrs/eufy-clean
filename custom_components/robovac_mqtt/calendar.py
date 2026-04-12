from __future__ import annotations

import datetime as dt
import logging
import time
from datetime import datetime as dt_datetime
from typing import Any

from homeassistant.components import calendar as calendar_component
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .typing_defs import EufyCleanConfigEntry
from .api.commands import build_command
from .const import DOMAIN
from .coordinator import EufyCleanCoordinator

PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)

_CALENDAR_ENTITY_FEATURE = getattr(calendar_component, "CalendarEntityFeature")

_EVENT_DURATION = dt.timedelta(minutes=30)

# Proto week_bits: bit0=Sun, bit1=Mon, ..., bit6=Sat
# Python weekday(): 0=Mon, 1=Tue, ..., 6=Sun
# Conversion: proto_bit = (python_weekday + 1) % 7
_PROTO_DAY_NAMES = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")

# Python weekday (Mon=0) -> proto bit index (Sun=0)
_PY_WEEKDAY_TO_PROTO_BIT = [1, 2, 3, 4, 5, 6, 0]


def _weekday_label(week_bits: int) -> str:
    if week_bits == 0x7F:
        return "Every day"
    return ", ".join(
        _PROTO_DAY_NAMES[bit] for bit in range(7) if week_bits & (1 << bit)
    )


def _rrule_to_week_bits(rrule: str) -> int | None:
    """Convert an RRULE BYDAY string to proto week_bits, or None for one-time."""
    if not rrule:
        return None
    byday_map = {"SU": 0, "MO": 1, "TU": 2, "WE": 3, "TH": 4, "FR": 5, "SA": 6}
    bits = 0
    for part in rrule.split(";"):
        if part.startswith("BYDAY="):
            for day_code in part[6:].split(","):
                bit = byday_map.get(day_code.strip().upper())
                if bit is not None:
                    bits |= 1 << bit
    return bits if bits else None


def _week_bits_to_rrule(week_bits: int) -> str:
    """Convert proto week_bits to an RRULE BYDAY string."""
    day_codes = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"]
    days = [day_codes[bit] for bit in range(7) if week_bits & (1 << bit)]
    if not days:
        return ""
    return f"FREQ=WEEKLY;BYDAY={','.join(days)}"


def _local_tz_offset_seconds() -> int:
    """Return the current local UTC offset in seconds (positive = east of UTC)."""
    now = dt_util.now()
    offset = now.utcoffset()
    return int(offset.total_seconds()) if offset else 0


def _is_dst() -> bool:
    """Return True if local timezone is currently in DST."""
    return bool(time.daylight and time.localtime().tm_isdst > 0)


def _build_timer_info_from_event(
    event: dict[str, Any],
    timer_id: int | None = None,
) -> dict[str, Any]:
    start = event.get("dtstart", event.get("start"))
    if isinstance(start, dt.datetime):
        hour = start.hour
        minute = start.minute
    elif isinstance(start, dt.date):
        hour = 0
        minute = 0
    else:
        hour = 0
        minute = 0

    rrule = event.get("rrule", "")
    week_bits = _rrule_to_week_bits(rrule)
    is_cycle = week_bits is not None

    if not is_cycle and isinstance(start, dt.datetime):
        proto_bit = _PY_WEEKDAY_TO_PROTO_BIT[start.weekday()]
        week_bits = 1 << proto_bit

    info: dict[str, Any] = {}
    if timer_id is not None:
        info["id"] = {"value": timer_id}

    info["status"] = {"valid": True, "opened": True}
    info["desc"] = {
        "trigger": 1 if is_cycle else 0,
        "timing": {
            "user_tz": _local_tz_offset_seconds() & 0xFFFFFFFF,
            "summer": _is_dst(),
            "hours": hour,
            "minutes": minute,
        },
    }
    if is_cycle and week_bits:
        info["desc"]["cycle"] = {"week_bits": week_bits}

    info["action"] = {"type": 0, "sche_auto_clean": {"mode": 0}}

    return info


def _find_schedule_by_uid(
    schedules: list[dict[str, Any]], uid: str
) -> dict[str, Any] | None:
    try:
        timer_id = int(uid)
    except (ValueError, TypeError):
        return None
    for s in schedules:
        if s.get("id") == timer_id:
            return s
    return None


def _estimate_duration(
    history: list[dict[str, Any]],
    trigger_source: str | None = None,
    scene_name: str | None = None,
    default_minutes: int = 30,
) -> int:
    """Estimate cleaning duration from last 10 matching completed sessions.

    Filters by trigger_source and scene_name to avoid mixing scheduled
    whole-house cleans with short manual room cleans.  Excludes aborted sessions.
    """
    candidates = [
        s
        for s in history
        if s.get("completed")
        and s.get("duration_seconds", 0) > 0
        and (trigger_source is None or s.get("trigger_source") == trigger_source)
        and (scene_name is None or s.get("scene_name") == scene_name)
    ]
    if not candidates:
        # Fall back to all completed sessions if no exact match
        candidates = [
            s
            for s in history
            if s.get("completed") and s.get("duration_seconds", 0) > 0
        ]
    if not candidates:
        return default_minutes
    recent = candidates[-10:]
    avg_seconds = sum(s["duration_seconds"] for s in recent) / len(recent)
    return max(10, int(avg_seconds / 60))


def _session_summary(session: dict[str, Any]) -> str:
    """Build calendar event summary from a cleaning session record."""
    trigger = session.get("trigger_source", "unknown")
    duration_min = session.get("duration_seconds", 0) // 60
    area = session.get("area_m2", 0)
    scene = session.get("scene_name")
    rooms = session.get("rooms", [])
    icon = "\U0001f5d3\ufe0f" if trigger == "schedule" else "\U0001f9f9"
    if scene:
        label = scene
    elif rooms:
        label = ", ".join(rooms[:3])
        if len(rooms) > 3:
            label += f" +{len(rooms) - 3}"
    elif trigger == "schedule":
        label = "Scheduled Clean"
    else:
        label = "Manual Clean"
    return f"{icon} {label} ({duration_min} min, {area}m\u00b2)"


def _session_description(session: dict[str, Any]) -> str:
    """Build calendar event description from a cleaning session record."""
    parts = []
    trigger = session.get("trigger_source", "unknown")
    parts.append(f"Trigger: {trigger.title()}")
    rooms = session.get("rooms", [])
    if rooms:
        parts.append(f"Rooms: {', '.join(rooms)}")
    fan = session.get("fan_speed", "")
    mode = session.get("work_mode", "")
    if fan or mode:
        parts.append(f"Fan: {fan} | Mode: {mode}")
    dock_visits = session.get("dock_visits", 0)
    if dock_visits > 0:
        parts.append(f"Dock visits: {dock_visits} (wash/empty)")
    error = session.get("error_message", "")
    if error:
        parts.append(f"Error: {error}")
    if not session.get("completed"):
        parts.append("\u26a0\ufe0f Session did not complete")
    return "\n".join(parts)


def _expand_schedule_future(
    schedule: dict[str, Any],
    start: dt.datetime,
    end: dt.datetime,
    tz: dt.tzinfo,
    est_duration: dt.timedelta,
) -> list[CalendarEvent]:
    """Expand scheduled events into the FUTURE only."""
    hour = schedule.get("hour", 0)
    minute = schedule.get("minute", 0)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        _LOGGER.warning(
            "Skipping schedule with invalid time: hour=%s, minute=%s",
            hour,
            minute,
        )
        return []
    summary_base = schedule.get("action_label", "Scheduled Clean")
    uid = str(schedule.get("id", ""))
    est_min = int(est_duration.total_seconds() / 60)
    events: list[CalendarEvent] = []
    current = start.date()
    end_date = end.date()
    if schedule.get("trigger") == "cycle":
        week_bits = schedule.get("week_bits", 0)
        rrule = _week_bits_to_rrule(week_bits)
        while current <= end_date:
            proto_bit = (current.weekday() + 1) % 7
            if week_bits & (1 << proto_bit):
                event_start = dt.datetime.combine(
                    current, dt.time(hour, minute), tzinfo=tz
                )
                event_end = event_start + est_duration
                if event_end > start and event_start < end:
                    events.append(
                        CalendarEvent(
                            start=event_start,
                            end=event_end,
                            summary=f"\U0001f4c5 {summary_base} (est. ~{est_min} min)",
                            description=_weekday_label(week_bits),
                            uid=uid,
                            rrule=rrule,
                            recurrence_id=current.isoformat(),
                        )
                    )
            current += dt.timedelta(days=1)
    else:
        event_start = dt.datetime.combine(current, dt.time(hour, minute), tzinfo=tz)
        if event_start < start:
            event_start += dt.timedelta(days=1)
        event_end = event_start + est_duration
        if event_end > start and event_start < end:
            events.append(
                CalendarEvent(
                    start=event_start,
                    end=event_end,
                    summary=f"\U0001f4c5 {summary_base} (est. ~{est_min} min)",
                    description="One-time",
                    uid=uid,
                )
            )
    return events


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EufyCleanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entities: list[CalendarEntity] = []
    for coordinator in config_entry.runtime_data.coordinators.values():
        if "TIMING" in coordinator.supported_dps:
            entities.append(EufyCleanCalendar(coordinator))

    async_add_entities(entities)


class EufyCleanCalendar(CoordinatorEntity[EufyCleanCoordinator], CalendarEntity):

    _attr_supported_features = (
        _CALENDAR_ENTITY_FEATURE.CREATE_EVENT
        | _CALENDAR_ENTITY_FEATURE.DELETE_EVENT
        | _CALENDAR_ENTITY_FEATURE.UPDATE_EVENT
    )

    def __init__(self, coordinator: EufyCleanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_cleaning_schedule"
        self._attr_has_entity_name = True
        self._attr_translation_key = "cleaning_schedule"
        self._attr_device_info = coordinator.device_info
        self._attr_entity_registry_enabled_default = True
        self._attr_entity_registry_visible_default = True

    @property
    def available(self) -> bool:
        return (
            super().available and "schedules" in self.coordinator.data.received_fields
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming or current event."""
        now = dt_util.now()
        current = self.coordinator.current_cleaning_session
        if current is not None:
            tz = dt_util.get_default_time_zone()
            try:
                ev_start = dt_datetime.fromisoformat(current.start_time).astimezone(tz)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Current cleaning session has invalid start_time: %s",
                    current.start_time,
                )
                ev_start = now
            elapsed_min = max(0, int((now - ev_start).total_seconds() / 60))
            return CalendarEvent(
                start=ev_start,
                end=max(ev_start, now),
                summary=f"\U0001f504 Cleaning in progress ({elapsed_min} min)...",
                description=f"Trigger: {current.trigger_source.title()}",
            )
        end = now + dt.timedelta(days=7)
        events = self._expand_events(now, end)
        for ev in events:
            if ev.end > now:
                return ev
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: dt.datetime,
        end_date: dt.datetime,
    ) -> list[CalendarEvent]:
        return self._expand_events(start_date, end_date)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        schedules = self.coordinator.data.schedules
        return {
            "schedule_count": len(schedules),
            "enabled_count": sum(1 for s in schedules if s.get("enabled")),
        }

    async def async_create_event(self, **kwargs: Any) -> None:
        timer_info = _build_timer_info_from_event(kwargs)
        cmd = build_command(
            "timer_add",
            dps_map=self.coordinator.dps_map,
            timer_info=timer_info,
        )
        await self.coordinator.async_send_command(cmd)
        await self._async_refresh_schedules()

    async def async_delete_event(
        self,
        uid: str,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        if not uid.isdigit():
            _LOGGER.warning("Skipping delete for non-numeric timer uid: %s", uid)
            return
        timer_id = int(uid)
        cmd = build_command(
            "timer_delete",
            dps_map=self.coordinator.dps_map,
            timer_id=timer_id,
        )
        await self.coordinator.async_send_command(cmd)
        await self._async_refresh_schedules()

    async def async_update_event(
        self,
        uid: str,
        event: dict[str, Any],
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        if not uid.isdigit():
            _LOGGER.warning("Skipping update for non-numeric timer uid: %s", uid)
            return
        timer_id = int(uid)
        timer_info = _build_timer_info_from_event(event, timer_id=timer_id)
        cmd = build_command(
            "timer_modify",
            dps_map=self.coordinator.dps_map,
            timer_info=timer_info,
        )
        await self.coordinator.async_send_command(cmd)
        await self._async_refresh_schedules()

    async def _async_refresh_schedules(self) -> None:
        cmd = build_command("timer_inquiry", dps_map=self.coordinator.dps_map)
        await self.coordinator.async_send_command(cmd)

    def _expand_events(
        self, start: dt.datetime, end: dt.datetime
    ) -> list[CalendarEvent]:
        """Expand events from history (past), live state (now), and schedule (future)."""
        tz = dt_util.get_default_time_zone()
        now = dt_util.now()
        events: list[CalendarEvent] = []

        # 1. PAST: cleaning sessions from history
        for session in self.coordinator.cleaning_history:
            ev = self._session_to_event(session, tz, start, end)
            if ev:
                events.append(ev)

        # 2. CURRENT: in-progress cleaning session
        current = self.coordinator.current_cleaning_session
        if current is not None:
            try:
                ev_start = dt_datetime.fromisoformat(current.start_time).astimezone(tz)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Current cleaning session has invalid start_time: %s",
                    current.start_time,
                )
                ev_start = now
            ev_end = max(ev_start, now)
            if ev_end > start and ev_start < end:
                elapsed_min = max(0, int((now - ev_start).total_seconds() / 60))
                events.append(
                    CalendarEvent(
                        start=ev_start,
                        end=ev_end,
                        summary=f"\U0001f504 Cleaning in progress ({elapsed_min} min)...",
                        description=f"Trigger: {current.trigger_source.title()}\nDock visits: {current.dock_visits}",
                        uid="current",
                    )
                )

        # 3. FUTURE: scheduled events with estimated duration
        for schedule in self.coordinator.data.schedules:
            if not schedule.get("enabled") or not schedule.get("valid"):
                continue
            est_minutes = _estimate_duration(
                self.coordinator.cleaning_history,
                trigger_source="schedule",
            )
            est_duration = dt.timedelta(minutes=est_minutes)
            for sched_ev in _expand_schedule_future(
                schedule, now, end, tz, est_duration
            ):
                events.append(sched_ev)

        events.sort(key=lambda e: e.start)
        _LOGGER.debug(
            "Calendar expanded %d events (history=%d, schedules=%d)",
            len(events),
            len(self.coordinator.cleaning_history),
            len(self.coordinator.data.schedules),
        )
        return events

    @staticmethod
    def _session_to_event(
        session: dict[str, Any],
        tz: dt.tzinfo,
        range_start: dt.datetime,
        range_end: dt.datetime,
    ) -> CalendarEvent | None:
        """Convert a cleaning session dict to a CalendarEvent if in range."""
        start_str = session.get("start_time", "")
        end_str = session.get("end_time")
        if not start_str or not end_str:
            return None
        try:
            ev_start = dt_datetime.fromisoformat(start_str).astimezone(tz)
            ev_end = dt_datetime.fromisoformat(end_str).astimezone(tz)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Skipping cleaning session with invalid timestamps: start=%s, end=%s",
                start_str,
                end_str,
            )
            return None
        if ev_end < ev_start:
            _LOGGER.warning(
                "Skipping cleaning session with reversed timestamps: start=%s, end=%s",
                start_str,
                end_str,
            )
            return None
        if ev_end <= range_start or ev_start >= range_end:
            return None
        return CalendarEvent(
            start=ev_start,
            end=ev_end,
            summary=_session_summary(session),
            description=_session_description(session),
            uid=f"session_{start_str}",
        )


def _expand_schedule(
    schedule: dict[str, Any],
    start: dt.datetime,
    end: dt.datetime,
    tz: dt.tzinfo,
) -> list[CalendarEvent]:
    hour = schedule.get("hour", 0)
    minute = schedule.get("minute", 0)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        _LOGGER.warning(
            "Skipping schedule with invalid time: hour=%s, minute=%s",
            hour,
            minute,
        )
        return []
    summary = schedule.get("action_label", "Scheduled Clean")
    uid = str(schedule.get("id", ""))
    events: list[CalendarEvent] = []

    current = start.date()
    end_date = end.date()

    if schedule.get("trigger") == "cycle":
        week_bits = schedule.get("week_bits", 0)
        description = _weekday_label(week_bits)
        rrule = _week_bits_to_rrule(week_bits)
        while current <= end_date:
            proto_bit = (current.weekday() + 1) % 7
            if week_bits & (1 << proto_bit):
                event_start = dt.datetime.combine(
                    current, dt.time(hour, minute), tzinfo=tz
                )
                event_end = event_start + _EVENT_DURATION
                if event_end > start and event_start < end:
                    events.append(
                        CalendarEvent(
                            start=event_start,
                            end=event_end,
                            summary=summary,
                            description=description,
                            uid=uid,
                            rrule=rrule,
                            recurrence_id=current.isoformat(),
                        )
                    )
            current += dt.timedelta(days=1)
    else:
        event_start = dt.datetime.combine(current, dt.time(hour, minute), tzinfo=tz)
        if event_start < start:
            event_start += dt.timedelta(days=1)
        event_end = max(event_start, event_start + _EVENT_DURATION)
        if event_end > start and event_start < end:
            events.append(
                CalendarEvent(
                    start=event_start,
                    end=event_end,
                    summary=summary,
                    description="One-time",
                    uid=uid,
                )
            )

    return events
