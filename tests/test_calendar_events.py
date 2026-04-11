from __future__ import annotations

import datetime as dt
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import custom_components.robovac_mqtt.calendar as calendar_mod
from custom_components.robovac_mqtt.calendar import (
    EufyCleanCalendar,
    _estimate_duration,
    _expand_schedule_future,
    _session_description,
    _session_summary,
)
from custom_components.robovac_mqtt.models import CleaningSession

UTC = dt.timezone.utc


def _freeze_time(
    monkeypatch: pytest.MonkeyPatch,
    now: dt.datetime,
    tz: dt.tzinfo = UTC,
) -> None:
    monkeypatch.setattr(calendar_mod.dt_util, "now", lambda: now)
    def get_tz():
        return tz

    def clear_cache() -> None:
        return None

    get_tz.cache_clear = clear_cache  # satisfy HA teardown expectation
    monkeypatch.setattr(calendar_mod.dt_util, "get_default_time_zone", get_tz)


def _calendar(
    cleaning_history: list[dict] | None = None,
    current_session: CleaningSession | None = None,
    schedules: list[dict] | None = None,
) -> EufyCleanCalendar:
    entity = object.__new__(EufyCleanCalendar)
    entity.coordinator = SimpleNamespace(
        cleaning_history=cleaning_history or [],
        current_cleaning_session=current_session,
        data=SimpleNamespace(schedules=schedules or []),
    )
    return entity


def _session(
    start_time: str | None,
    end_time: str | None,
    **overrides,
) -> dict:
    base = {
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": 1800,
        "area_m2": 24,
        "trigger_source": "schedule",
        "rooms": [],
        "scene_name": "Daily",
        "fan_speed": "Max",
        "work_mode": "vacuum_mop",
        "dock_visits": 0,
        "error_message": "",
        "completed": True,
    }
    base.update(overrides)
    return base


def _history_entry(
    minutes: int,
    *,
    completed: bool = True,
    trigger_source: str = "schedule",
    scene_name: str | None = None,
) -> dict:
    return {
        "duration_seconds": minutes * 60,
        "completed": completed,
        "trigger_source": trigger_source,
        "scene_name": scene_name,
    }


def test_expand_events_returns_empty_for_empty_history_and_schedules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = dt.datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    _freeze_time(monkeypatch, now)

    calendar = _calendar()

    assert (
        calendar._expand_events(now - dt.timedelta(days=1), now + dt.timedelta(days=1))
        == []
    )


def test_expand_events_returns_all_supplied_history_entries_even_above_retention_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = dt.datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    _freeze_time(monkeypatch, now)

    history = [
        _session(
            f"2026-04-{(i % 28) + 1:02d}T{10}:00:00+00:00",
            f"2026-04-{(i % 28) + 1:02d}T{11}:00:00+00:00",
            scene_name=f"Run {i}",
        )
        for i in range(101)
    ]

    calendar = _calendar(cleaning_history=history)
    events = calendar._expand_events(
        dt.datetime(2026, 4, 1, 0, 0, tzinfo=UTC),
        dt.datetime(2026, 5, 15, 0, 0, tzinfo=UTC),
    )

    assert len(events) == 101


def test_session_to_event_skips_missing_start_or_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = dt.datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    _freeze_time(monkeypatch, now)

    calendar = _calendar()
    range_start = now - dt.timedelta(days=1)
    range_end = now + dt.timedelta(days=1)

    assert (
        calendar._session_to_event(
            _session(None, "2026-04-10T10:30:00+00:00"),
            UTC,
            range_start,
            range_end,
        )
        is None
    )
    assert (
        calendar._session_to_event(
            _session("2026-04-10T10:00:00+00:00", None),
            UTC,
            range_start,
            range_end,
        )
        is None
    )


def test_session_to_event_skips_malformed_timestamps_with_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    now = dt.datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    _freeze_time(monkeypatch, now)

    calendar = _calendar()
    event = calendar._session_to_event(
        _session("not-an-iso-date", "2026-04-10T10:30:00+00:00"),
        UTC,
        now - dt.timedelta(days=1),
        now + dt.timedelta(days=1),
    )

    assert event is None
    assert "Skipping cleaning session with invalid timestamps" in caplog.text


def test_session_to_event_should_skip_reversed_timestamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = dt.datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    _freeze_time(monkeypatch, now)

    calendar = _calendar()
    event = calendar._session_to_event(
        _session("2026-04-10T10:00:00+00:00", "2026-04-10T09:00:00+00:00"),
        UTC,
        now - dt.timedelta(days=1),
        now + dt.timedelta(days=1),
    )

    assert event is None


def test_expand_events_includes_current_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = dt.datetime(2026, 4, 10, 6, 0, tzinfo=UTC)
    _freeze_time(monkeypatch, now)

    calendar = _calendar(
        current_session=CleaningSession(
            start_time="2026-04-10T05:30:00+00:00",
            trigger_source="schedule",
            dock_visits=2,
        )
    )

    events = calendar._expand_events(
        now - dt.timedelta(hours=1),
        now + dt.timedelta(hours=1),
    )

    assert len(events) == 1
    assert "Cleaning in progress (30 min)" in events[0].summary
    assert "Trigger: Schedule" in events[0].description
    assert "Dock visits: 2" in events[0].description


def test_current_session_with_future_start_should_clamp_elapsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = dt.datetime(2026, 4, 10, 6, 0, tzinfo=UTC)
    _freeze_time(monkeypatch, now)

    calendar = _calendar(
        current_session=CleaningSession(
            start_time="2026-04-10T06:05:00+00:00",
            trigger_source="app",
        )
    )

    event = calendar.event
    assert event is not None
    assert "0 min" in event.summary
    assert event.start <= event.end


def test_expand_schedule_future_with_zero_week_bits_returns_empty() -> None:
    events = _expand_schedule_future(
        {
            "id": 1,
            "trigger": "cycle",
            "week_bits": 0,
            "hour": 9,
            "minute": 0,
            "action_label": "Scheduled Clean",
        },
        dt.datetime(2026, 4, 10, 0, 0, tzinfo=UTC),
        dt.datetime(2026, 4, 11, 0, 0, tzinfo=UTC),
        UTC,
        dt.timedelta(minutes=30),
    )

    assert events == []


@pytest.mark.parametrize(
    ("hour", "minute"),
    [
        (25, 0),
        (10, 61),
    ],
)
def test_expand_schedule_future_should_skip_invalid_times(
    hour: int,
    minute: int,
) -> None:
    events = _expand_schedule_future(
        {
            "id": 1,
            "trigger": "single",
            "hour": hour,
            "minute": minute,
            "action_label": "Scheduled Clean",
        },
        dt.datetime(2026, 4, 10, 0, 0, tzinfo=UTC),
        dt.datetime(2026, 4, 11, 0, 0, tzinfo=UTC),
        UTC,
        dt.timedelta(minutes=30),
    )

    assert events == []


@pytest.mark.xfail(
    reason="DST transition times are not normalized/disambiguated explicitly",
    strict=False,
)
@pytest.mark.parametrize(
    ("day_start", "hour", "minute", "expected_hour", "expected_fold"),
    [
        (
            dt.datetime(2026, 3, 8, 0, 0, tzinfo=ZoneInfo("America/New_York")),
            2,
            30,
            3,
            0,
        ),
        (
            dt.datetime(2026, 11, 1, 0, 0, tzinfo=ZoneInfo("America/New_York")),
            1,
            30,
            1,
            1,
        ),
    ],
)
def test_expand_schedule_future_should_handle_dst_transitions(
    day_start: dt.datetime,
    hour: int,
    minute: int,
    expected_hour: int,
    expected_fold: int,
) -> None:
    tz = day_start.tzinfo
    assert tz is not None

    events = _expand_schedule_future(
        {
            "id": 7,
            "trigger": "single",
            "hour": hour,
            "minute": minute,
            "action_label": "DST Clean",
        },
        day_start,
        day_start + dt.timedelta(days=1),
        tz,
        dt.timedelta(minutes=30),
    )

    assert len(events) == 1
    assert events[0].start.hour == expected_hour
    assert events[0].start.fold == expected_fold


def test_expand_events_range_spanning_multiple_months(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = dt.datetime(2026, 1, 31, 9, 0, tzinfo=UTC)
    _freeze_time(monkeypatch, now)

    history = [
        _session(
            "2026-01-31T08:00:00+00:00",
            "2026-01-31T08:45:00+00:00",
            scene_name="History Run",
        )
    ]
    schedules = [
        {
            "id": 1,
            "enabled": True,
            "valid": True,
            "trigger": "cycle",
            "week_bits": 0x7F,
            "hour": 10,
            "minute": 0,
            "action_label": "Daily Auto",
        }
    ]
    calendar = _calendar(cleaning_history=history, schedules=schedules)

    events = calendar._expand_events(
        dt.datetime(2026, 1, 31, 0, 0, tzinfo=UTC),
        dt.datetime(2026, 3, 2, 0, 0, tzinfo=UTC),
    )

    assert events[0].summary.startswith("🗓️ History Run")
    assert any(ev.summary.startswith("📅 Daily Auto") for ev in events)
    assert len(events) > 20


def test_expand_events_one_minute_range_includes_overlapping_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = dt.datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    _freeze_time(monkeypatch, now)

    calendar = _calendar(
        cleaning_history=[
            _session(
                "2026-04-10T10:00:00+00:00",
                "2026-04-10T10:30:00+00:00",
            )
        ]
    )

    events = calendar._expand_events(
        dt.datetime(2026, 4, 10, 10, 15, tzinfo=UTC),
        dt.datetime(2026, 4, 10, 10, 16, tzinfo=UTC),
    )

    assert len(events) == 1


def test_expand_events_invalid_range_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = dt.datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    _freeze_time(monkeypatch, now)

    calendar = _calendar(
        cleaning_history=[
            _session(
                "2026-04-10T10:00:00+00:00",
                "2026-04-10T10:30:00+00:00",
            )
        ],
        schedules=[
            {
                "id": 1,
                "enabled": True,
                "valid": True,
                "trigger": "cycle",
                "week_bits": 0x7F,
                "hour": 13,
                "minute": 0,
                "action_label": "Daily Auto",
            }
        ],
    )

    events = calendar._expand_events(
        dt.datetime(2026, 4, 11, 0, 0, tzinfo=UTC),
        dt.datetime(2026, 4, 10, 0, 0, tzinfo=UTC),
    )

    assert events == []


def test_expand_events_returns_multiple_future_schedules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = dt.datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
    _freeze_time(monkeypatch, now)

    calendar = _calendar(
        cleaning_history=[
            _session(
                "2026-04-09T09:00:00+00:00",
                "2026-04-09T09:45:00+00:00",
                duration_seconds=2700,
            )
        ],
        schedules=[
            {
                "id": 1,
                "enabled": True,
                "valid": True,
                "trigger": "cycle",
                "week_bits": 0x7F,
                "hour": 10,
                "minute": 0,
                "action_label": "Daily Auto",
            },
            {
                "id": 2,
                "enabled": True,
                "valid": True,
                "trigger": "cycle",
                "week_bits": 0x7F,
                "hour": 10,
                "minute": 0,
                "action_label": "Scene: Kitchen",
            },
        ],
    )

    events = calendar._expand_events(
        now,
        now + dt.timedelta(days=1),
    )

    future = [ev for ev in events if ev.summary.startswith("📅")]
    assert len(future) == 2
    assert any("Daily Auto" in ev.summary for ev in future)
    assert any("Scene: Kitchen" in ev.summary for ev in future)


@pytest.mark.parametrize(
    ("history", "trigger_source", "scene_name", "expected_minutes"),
    [
        (
            [
                _history_entry(20, trigger_source="app"),
                _history_entry(40, trigger_source="app"),
            ],
            "schedule",
            None,
            30,
        ),
        (
            [
                _history_entry(20, completed=False, trigger_source="schedule"),
                _history_entry(40, completed=False, trigger_source="schedule"),
            ],
            "schedule",
            None,
            30,
        ),
        (
            [
                _history_entry(1, trigger_source="schedule"),
                _history_entry(240, trigger_source="schedule"),
            ],
            "schedule",
            None,
            120,
        ),
        (
            [_history_entry(17, trigger_source="schedule")],
            "schedule",
            None,
            17,
        ),
        (
            [_history_entry(m, trigger_source="schedule") for m in range(20, 32)],
            "schedule",
            None,
            26,
        ),
        (
            [
                _history_entry(0, trigger_source="schedule"),
                _history_entry(15, trigger_source="schedule"),
            ],
            "schedule",
            None,
            15,
        ),
        (
            [],
            "schedule",
            None,
            30,
        ),
    ],
)
def test_estimate_duration_cases(
    history: list[dict],
    trigger_source: str | None,
    scene_name: str | None,
    expected_minutes: int,
) -> None:
    assert _estimate_duration(history, trigger_source, scene_name) == expected_minutes


def test_estimate_duration_can_match_scene_name() -> None:
    history = [
        _history_entry(20, trigger_source="schedule", scene_name="Daily"),
        _history_entry(60, trigger_source="schedule", scene_name="Deep Clean"),
    ]

    assert (
        _estimate_duration(
            history,
            trigger_source="schedule",
            scene_name="Deep Clean",
        )
        == 60
    )


def test_session_summary_preserves_scene_name_special_characters() -> None:
    summary = _session_summary(
        _session(
            "2026-04-10T10:00:00+00:00",
            "2026-04-10T10:30:00+00:00",
            scene_name="Deep Clean — Küche ❤️ — 这是一个非常长的场景名",
        )
    )

    assert summary.startswith("🗓️ Deep Clean — Küche ❤️")
    assert "30 min" in summary
    assert "24m²" in summary


def test_session_summary_uses_fallback_labels_and_room_truncation() -> None:
    manual = _session_summary(
        _session(
            "2026-04-10T10:00:00+00:00",
            "2026-04-10T10:10:00+00:00",
            trigger_source="app",
            scene_name=None,
            rooms=[],
            duration_seconds=600,
            area_m2=5,
        )
    )
    scheduled = _session_summary(
        _session(
            "2026-04-10T10:00:00+00:00",
            "2026-04-10T10:10:00+00:00",
            trigger_source="schedule",
            scene_name=None,
            rooms=[],
            duration_seconds=600,
            area_m2=5,
        )
    )
    truncated = _session_summary(
        _session(
            "2026-04-10T10:00:00+00:00",
            "2026-04-10T10:30:00+00:00",
            scene_name=None,
            rooms=["Kitchen", "Hall", "Bathroom", "Bedroom", "Office"],
        )
    )

    assert manual.startswith("🧹 Manual Clean")
    assert scheduled.startswith("🗓️ Scheduled Clean")
    assert "Kitchen, Hall, Bathroom +2" in truncated


def test_session_description_omits_empty_error_and_includes_long_error() -> None:
    session = _session(
        "2026-04-10T10:00:00+00:00",
        "2026-04-10T10:30:00+00:00",
        trigger_source="app",
        rooms=["Kitchen", "Hall"],
        fan_speed="Turbo",
        work_mode="Room",
        dock_visits=2,
        error_message="",
        completed=False,
    )
    description = _session_description(session)

    assert "Trigger: App" in description
    assert "Rooms: Kitchen, Hall" in description
    assert "Fan: Turbo | Mode: Room" in description
    assert "Dock visits: 2 (wash/empty)" in description
    assert "Error:" not in description
    assert "⚠️ Session did not complete" in description

    long_error = "E" * 300
    session["error_message"] = long_error
    description = _session_description(session)
    assert f"Error: {long_error}" in description


@pytest.mark.parametrize(
    (
        "label",
        "week_bits",
        "query_start",
        "query_end",
        "expected_count",
        "expected_days",
    ),
    [
        (
            "weekdays_mon_to_fri",
            0x3E,
            dt.datetime(2026, 4, 6, 0, 0, tzinfo=UTC),
            dt.datetime(2026, 4, 13, 0, 0, tzinfo=UTC),
            5,
            {"Mon", "Tue", "Wed", "Thu", "Fri"},
        ),
        (
            "weekends_sat_sun",
            0x41,
            dt.datetime(2026, 4, 6, 0, 0, tzinfo=UTC),
            dt.datetime(2026, 4, 13, 0, 0, tzinfo=UTC),
            2,
            {"Sat", "Sun"},
        ),
        (
            "custom_mon_wed_fri",
            0x2A,
            dt.datetime(2026, 4, 6, 0, 0, tzinfo=UTC),
            dt.datetime(2026, 4, 13, 0, 0, tzinfo=UTC),
            3,
            {"Mon", "Wed", "Fri"},
        ),
        (
            "single_tuesday",
            0x04,
            dt.datetime(2026, 4, 6, 0, 0, tzinfo=UTC),
            dt.datetime(2026, 4, 13, 0, 0, tzinfo=UTC),
            1,
            {"Tue"},
        ),
        (
            "every_day",
            0x7F,
            dt.datetime(2026, 4, 6, 0, 0, tzinfo=UTC),
            dt.datetime(2026, 4, 13, 0, 0, tzinfo=UTC),
            7,
            {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"},
        ),
        (
            "every_other_day_sun_tue_thu_sat",
            0x55,
            dt.datetime(2026, 4, 6, 0, 0, tzinfo=UTC),
            dt.datetime(2026, 4, 13, 0, 0, tzinfo=UTC),
            4,
            {"Sun", "Tue", "Thu", "Sat"},
        ),
    ],
)
def test_expand_schedule_future_week_bits_variations(
    label: str,
    week_bits: int,
    query_start: dt.datetime,
    query_end: dt.datetime,
    expected_count: int,
    expected_days: set[str],
) -> None:
    schedule = {
        "id": 1,
        "trigger": "cycle",
        "week_bits": week_bits,
        "hour": 5,
        "minute": 30,
        "action_label": "Test Clean",
    }
    events = _expand_schedule_future(
        schedule,
        query_start,
        query_end,
        UTC,
        dt.timedelta(minutes=54),
    )

    assert (
        len(events) == expected_count
    ), f"{label}: expected {expected_count}, got {len(events)}"

    actual_days = {ev.start.strftime("%a") for ev in events}
    assert (
        actual_days == expected_days
    ), f"{label}: expected {expected_days}, got {actual_days}"

    for ev in events:
        assert ev.start.hour == 5
        assert ev.start.minute == 30
        assert "Test Clean" in ev.summary
        assert "est. ~54 min" in ev.summary


def test_expand_schedule_future_one_time_schedule() -> None:
    schedule = {
        "id": 99,
        "trigger": "single",
        "hour": 14,
        "minute": 0,
        "action_label": "One-Time Deep Clean",
    }
    start = dt.datetime(2026, 4, 10, 0, 0, tzinfo=UTC)
    end = dt.datetime(2026, 4, 11, 0, 0, tzinfo=UTC)

    events = _expand_schedule_future(
        schedule,
        start,
        end,
        UTC,
        dt.timedelta(minutes=45),
    )

    assert len(events) == 1
    assert events[0].start.hour == 14
    assert events[0].start.minute == 0
    assert "One-Time Deep Clean" in events[0].summary
    assert "est. ~45 min" in events[0].summary
    assert events[0].description == "One-time"


def test_expand_schedule_future_one_time_past_today_skipped() -> None:
    schedule = {
        "id": 99,
        "trigger": "single",
        "hour": 3,
        "minute": 0,
        "action_label": "Early Clean",
    }
    start = dt.datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    end = dt.datetime(2026, 4, 11, 0, 0, tzinfo=UTC)

    events = _expand_schedule_future(
        schedule,
        start,
        end,
        UTC,
        dt.timedelta(minutes=30),
    )

    assert len(events) == 0 or (len(events) == 1 and events[0].start.day == 11)


def test_expand_schedule_future_two_week_span() -> None:
    schedule = {
        "id": 5,
        "trigger": "cycle",
        "week_bits": 0x2A,
        "hour": 9,
        "minute": 15,
        "action_label": "Bi-weekly Rooms",
    }
    start = dt.datetime(2026, 4, 6, 0, 0, tzinfo=UTC)
    end = dt.datetime(2026, 4, 20, 0, 0, tzinfo=UTC)

    events = _expand_schedule_future(
        schedule,
        start,
        end,
        UTC,
        dt.timedelta(minutes=40),
    )

    assert len(events) == 6
    for ev in events:
        assert ev.start.strftime("%a") in {"Mon", "Wed", "Fri"}
