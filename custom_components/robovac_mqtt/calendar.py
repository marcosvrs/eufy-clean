from __future__ import annotations

import datetime as dt
import logging
import time
from typing import Any

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEntityFeature,
    CalendarEvent,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api.commands import build_command
from .const import DOMAIN
from .coordinator import EufyCleanCoordinator

_LOGGER = logging.getLogger(__name__)

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
            "user_tz": _local_tz_offset_seconds(),
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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: list[EufyCleanCoordinator] = data["coordinators"]

    entities = []
    for coordinator in coordinators:
        if "TIMING" in coordinator.supported_dps:
            entities.append(EufyCleanCalendar(coordinator))

    async_add_entities(entities)


class EufyCleanCalendar(CoordinatorEntity[EufyCleanCoordinator], CalendarEntity):

    _attr_supported_features = (
        CalendarEntityFeature.CREATE_EVENT
        | CalendarEntityFeature.DELETE_EVENT
        | CalendarEntityFeature.UPDATE_EVENT
    )

    def __init__(self, coordinator: EufyCleanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_cleaning_schedule"
        self._attr_has_entity_name = True
        self._attr_name = "Cleaning Schedule"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        return (
            super().available
            and "schedules" in self.coordinator.data.received_fields
        )

    @property
    def event(self) -> CalendarEvent | None:
        now = dt_util.now()
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
        tz = dt_util.get_default_time_zone()
        events: list[CalendarEvent] = []
        for schedule in self.coordinator.data.schedules:
            if not schedule.get("enabled") or not schedule.get("valid"):
                continue
            events.extend(_expand_schedule(schedule, start, end, tz))
        events.sort(key=lambda e: e.start)
        return events


def _expand_schedule(
    schedule: dict[str, Any],
    start: dt.datetime,
    end: dt.datetime,
    tz: dt.tzinfo,
) -> list[CalendarEvent]:
    hour = schedule.get("hour", 0)
    minute = schedule.get("minute", 0)
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
        event_start = dt.datetime.combine(
            current, dt.time(hour, minute), tzinfo=tz
        )
        if event_start < start:
            event_start += dt.timedelta(days=1)
        event_end = event_start + _EVENT_DURATION
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
