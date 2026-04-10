from __future__ import annotations

import asyncio
import datetime as dt
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator
from custom_components.robovac_mqtt.models import VacuumState

UTC = dt.timezone.utc


def _ts(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value).astimezone(UTC)


def _state(task_status: str, **overrides) -> VacuumState:
    base = {
        "task_status": task_status,
        "trigger_source": "app",
        "fan_speed": "Max",
        "work_mode": "vacuum_mop",
    }
    base.update(overrides)
    return VacuumState(**base)


def _track_sequence(
    coordinator: EufyCleanCoordinator,
    sequence: list[tuple[str, dict]],
) -> None:
    for status, overrides in sequence:
        coordinator._track_cleaning_session(_state(status, **overrides))


@pytest.fixture
def coordinator() -> EufyCleanCoordinator:
    hass = MagicMock()
    hass.async_create_task = lambda coro: coro.close()

    login = MagicMock()
    login.openudid = "test-openudid"

    device_info = {
        "deviceId": "AMP96Z0E21600132",
        "deviceModel": "T2351",
        "deviceName": "Robovac",
    }

    coordinator = EufyCleanCoordinator(hass, login, device_info)
    coordinator._store = SimpleNamespace(
        async_load=AsyncMock(return_value={}),
        async_save=AsyncMock(),
    )
    return coordinator


def test_session_completes_with_mid_clean_washes_and_dock_visits(
    coordinator: EufyCleanCoordinator,
) -> None:
    """Normal scheduled clean with pre-wash, mid-clean dock visits, and post-complete dock ops."""
    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-04T05:30:06+00:00"),
            _ts("2026-04-04T06:46:49+00:00"),
        ],
    ):
        _track_sequence(
            coordinator,
            [
                (
                    "Cleaning",
                    {
                        "trigger_source": "schedule",
                        "current_scene_name": "Daily",
                        "active_room_names": "",
                        "fan_speed": "Max",
                        "work_mode": "vacuum_mop",
                    },
                ),
                ("Washing Mop", {}),
                ("Cleaning", {}),
                ("Returning to Wash", {}),
                ("Paused", {}),
                ("Washing Mop", {}),
                ("Cleaning", {}),
                ("Returning to Wash", {}),
                ("Returning", {}),
                ("Completed", {"cleaning_time": 3240, "cleaning_area": 26}),
                ("Emptying Dust", {}),
                ("Completed", {"cleaning_time": 3240, "cleaning_area": 26}),
                ("Washing Mop", {}),
                ("Completed", {"cleaning_time": 3240, "cleaning_area": 26}),
            ],
        )

    assert coordinator.current_cleaning_session is None
    assert len(coordinator.cleaning_history) == 1

    entry = coordinator.cleaning_history[0]
    assert entry["start_time"] == "2026-04-04T05:30:06+00:00"
    assert entry["end_time"] == "2026-04-04T06:46:49+00:00"
    assert entry["trigger_source"] == "schedule"
    assert entry["scene_name"] == "Daily"
    assert entry["rooms"] == []
    assert entry["fan_speed"] == "Max"
    assert entry["work_mode"] == "vacuum_mop"
    assert entry["dock_visits"] == 2
    assert entry["duration_seconds"] == 3240
    assert entry["area_m2"] == 26
    assert entry["completed"] is True


def test_manual_room_clean_tracks_unicode_room_names_and_zero_dock_visits(
    coordinator: EufyCleanCoordinator,
) -> None:
    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-05T09:05:55+00:00"),
            _ts("2026-04-05T09:14:49+00:00"),
        ],
    ):
        _track_sequence(
            coordinator,
            [
                (
                    "Cleaning",
                    {
                        "trigger_source": "app",
                        "active_room_names": "Küche, Sala ❤️, Niño,  , ",
                        "fan_speed": "Turbo",
                        "work_mode": "Room",
                    },
                ),
                ("Returning", {}),
                ("Completed", {"cleaning_time": 534, "cleaning_area": 12}),
            ],
        )

    entry = coordinator.cleaning_history[0]
    assert entry["trigger_source"] == "app"
    assert entry["rooms"] == ["Küche", "Sala ❤️", "Niño"]
    assert entry["fan_speed"] == "Turbo"
    assert entry["work_mode"] == "Room"
    assert entry["dock_visits"] == 0
    assert entry["completed"] is True


@pytest.mark.xfail(
    reason="active_room_names is comma-delimited and cannot preserve commas inside room names",
    strict=False,
)
def test_room_names_with_embedded_commas_should_not_split(
    coordinator: EufyCleanCoordinator,
) -> None:
    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-05T11:00:00+00:00"),
            _ts("2026-04-05T11:05:00+00:00"),
        ],
    ):
        _track_sequence(
            coordinator,
            [
                (
                    "Cleaning",
                    {
                        "active_room_names": "Hall, East, Kitchen",
                    },
                ),
                ("Completed", {"cleaning_time": 300, "cleaning_area": 5}),
            ],
        )

    assert coordinator.cleaning_history[0]["rooms"] == ["Hall, East", "Kitchen"]


def test_error_aborts_session_and_followup_idle_does_not_duplicate_history(
    coordinator: EufyCleanCoordinator,
) -> None:
    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-05T12:09:57+00:00"),
            _ts("2026-04-05T12:12:35+00:00"),
        ],
    ):
        _track_sequence(
            coordinator,
            [
                ("Cleaning", {"active_room_names": "Kitchen"}),
                (
                    "Error",
                    {
                        "cleaning_time": 158,
                        "cleaning_area": 7,
                        "error_message": "WHEEL STUCK",
                    },
                ),
                ("Idle", {"cleaning_time": 158, "cleaning_area": 7}),
            ],
        )

    assert coordinator.current_cleaning_session is None
    assert len(coordinator.cleaning_history) == 1

    entry = coordinator.cleaning_history[0]
    assert entry["completed"] is False
    assert entry["error_message"] == "WHEEL STUCK"
    assert entry["duration_seconds"] == 158
    assert entry["area_m2"] == 7


def test_idle_abort_when_user_stops_mid_clean(
    coordinator: EufyCleanCoordinator,
) -> None:
    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-06T12:35:45+00:00"),
            _ts("2026-04-06T12:44:44+00:00"),
        ],
    ):
        _track_sequence(
            coordinator,
            [
                ("Cleaning", {"trigger_source": "app"}),
                ("Returning", {}),
                ("Idle", {"cleaning_time": 499, "cleaning_area": 8}),
            ],
        )

    assert len(coordinator.cleaning_history) == 1
    assert coordinator.cleaning_history[0]["completed"] is False


def test_unavailable_does_not_abort_session(
    coordinator: EufyCleanCoordinator,
) -> None:
    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-06T13:14:12+00:00"),
            _ts("2026-04-06T13:18:46+00:00"),
        ],
    ):
        _track_sequence(
            coordinator,
            [
                ("Cleaning", {"trigger_source": "schedule"}),
                ("unavailable", {}),
                ("unavailable", {}),
                ("Completed", {"cleaning_time": 274, "cleaning_area": 9}),
            ],
        )

    assert len(coordinator.cleaning_history) == 1
    assert coordinator.cleaning_history[0]["completed"] is True


def test_repeated_status_bursts_do_not_duplicate_dock_visits_or_sessions(
    coordinator: EufyCleanCoordinator,
) -> None:
    sequence: list[tuple[str, dict]] = []
    sequence.extend([("Cleaning", {})] * 20)
    sequence.extend([("Returning to Wash", {})] * 20)
    sequence.extend([("Cleaning", {})] * 20)
    sequence.extend([("Completed", {"cleaning_time": 600, "cleaning_area": 10})] * 20)

    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-07T05:30:02+00:00"),
            _ts("2026-04-07T06:27:35+00:00"),
        ],
    ):
        _track_sequence(coordinator, sequence)

    assert len(coordinator.cleaning_history) == 1
    assert coordinator.cleaning_history[0]["dock_visits"] == 1


def test_returning_without_prior_cleaning_does_not_start_session(
    coordinator: EufyCleanCoordinator,
) -> None:
    _track_sequence(
        coordinator,
        [
            ("Returning", {}),
            ("Completed", {"cleaning_time": 60, "cleaning_area": 1}),
        ],
    )

    assert coordinator.current_cleaning_session is None
    assert coordinator.cleaning_history == []


@pytest.mark.parametrize(
    "status",
    [
        "Mapping",
        "Remote Control",
        "Returning",
        "Returning to Empty",
        "Returning to Charge",
        "Charging (Resume)",
        "Idle",
    ],
)
def test_non_cleaning_status_does_not_start_new_session(
    coordinator: EufyCleanCoordinator,
    status: str,
) -> None:
    coordinator._track_cleaning_session(_state(status))
    assert coordinator.current_cleaning_session is None
    assert coordinator.cleaning_history == []


@pytest.mark.parametrize("work_mode", ["Spot", "Zone"])
def test_spot_and_zone_modes_start_sessions(
    coordinator: EufyCleanCoordinator,
    work_mode: str,
) -> None:
    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-08T10:00:00+00:00"),
            _ts("2026-04-08T10:07:00+00:00"),
        ],
    ):
        _track_sequence(
            coordinator,
            [
                ("Cleaning", {"work_mode": work_mode, "trigger_source": "app"}),
                ("Completed", {"cleaning_time": 420, "cleaning_area": 6}),
            ],
        )

    assert coordinator.cleaning_history[0]["work_mode"] == work_mode


def test_unknown_trigger_and_zero_stats_are_still_persisted(
    coordinator: EufyCleanCoordinator,
) -> None:
    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-08T11:00:00+00:00"),
            _ts("2026-04-08T11:01:00+00:00"),
        ],
    ):
        _track_sequence(
            coordinator,
            [
                ("Cleaning", {"trigger_source": "unknown"}),
                ("Completed", {"cleaning_time": 0, "cleaning_area": 0}),
            ],
        )

    entry = coordinator.cleaning_history[0]
    assert entry["trigger_source"] == "unknown"
    assert entry["duration_seconds"] == 0
    assert entry["area_m2"] == 0
    assert entry["completed"] is True


def test_back_to_back_cleans_create_two_sessions(
    coordinator: EufyCleanCoordinator,
) -> None:
    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-08T12:00:00+00:00"),
            _ts("2026-04-08T12:10:00+00:00"),
            _ts("2026-04-08T12:10:05+00:00"),
            _ts("2026-04-08T12:25:00+00:00"),
        ],
    ):
        _track_sequence(
            coordinator,
            [
                ("Cleaning", {"trigger_source": "schedule"}),
                ("Completed", {"cleaning_time": 600, "cleaning_area": 11}),
                ("Cleaning", {"trigger_source": "app"}),
                ("Completed", {"cleaning_time": 895, "cleaning_area": 14}),
            ],
        )

    assert len(coordinator.cleaning_history) == 2
    assert coordinator.cleaning_history[0]["trigger_source"] == "schedule"
    assert coordinator.cleaning_history[1]["trigger_source"] == "app"


def test_error_then_resume_creates_second_session_not_continuation(
    coordinator: EufyCleanCoordinator,
) -> None:
    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-09T08:00:00+00:00"),
            _ts("2026-04-09T08:12:00+00:00"),
            _ts("2026-04-09T08:20:00+00:00"),
            _ts("2026-04-09T08:40:00+00:00"),
        ],
    ):
        _track_sequence(
            coordinator,
            [
                ("Cleaning", {"trigger_source": "app"}),
                ("Error", {"cleaning_time": 720, "cleaning_area": 10}),
                ("Paused", {}),
                ("Charging (Resume)", {}),
                ("Cleaning", {"trigger_source": "app"}),
                ("Returning", {}),
                ("Completed", {"cleaning_time": 1200, "cleaning_area": 19}),
            ],
        )

    assert len(coordinator.cleaning_history) == 2
    assert coordinator.cleaning_history[0]["completed"] is False
    assert coordinator.cleaning_history[1]["completed"] is True


def test_cleaning_session_survives_mqtt_gap_when_process_state_is_kept(
    coordinator: EufyCleanCoordinator,
) -> None:
    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-09T09:00:00+00:00"),
            _ts("2026-04-09T09:30:00+00:00"),
        ],
    ):
        _track_sequence(
            coordinator,
            [
                ("Cleaning", {"trigger_source": "schedule"}),
                ("Cleaning", {}),
                ("Returning", {}),
                ("Completed", {"cleaning_time": 1800, "cleaning_area": 20}),
            ],
        )

    assert len(coordinator.cleaning_history) == 1
    assert coordinator.cleaning_history[0]["completed"] is True


@pytest.mark.xfail(
    reason="current code does not restore _current_session across restart",
    strict=False,
)
def test_restart_during_cleaning_should_resume_existing_session(
    coordinator: EufyCleanCoordinator,
) -> None:
    coordinator._prev_task_status = "Cleaning"

    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[_ts("2026-04-09T10:00:00+00:00")],
    ):
        _track_sequence(
            coordinator,
            [
                ("Cleaning", {"trigger_source": "schedule"}),
                ("Completed", {"cleaning_time": 1200, "cleaning_area": 18}),
            ],
        )

    assert len(coordinator.cleaning_history) == 1


def test_history_is_capped_at_100_entries(
    coordinator: EufyCleanCoordinator,
) -> None:
    coordinator._cleaning_history = [
        {
            "start_time": f"old-{i}",
            "end_time": f"old-end-{i}",
            "duration_seconds": 60,
            "area_m2": 1,
            "trigger_source": "app",
            "rooms": [],
            "scene_name": None,
            "fan_speed": "Standard",
            "work_mode": "Auto",
            "dock_visits": 0,
            "error_message": "",
            "completed": True,
        }
        for i in range(100)
    ]

    with patch(
        "custom_components.robovac_mqtt.coordinator.dt_util.utcnow",
        side_effect=[
            _ts("2026-04-10T05:30:02+00:00"),
            _ts("2026-04-10T06:49:14+00:00"),
        ],
    ):
        _track_sequence(
            coordinator,
            [
                ("Cleaning", {"trigger_source": "schedule"}),
                ("Completed", {"cleaning_time": 3600, "cleaning_area": 28}),
            ],
        )

    assert len(coordinator.cleaning_history) == 100
    assert all(item["start_time"] != "old-0" for item in coordinator.cleaning_history)
    assert coordinator.cleaning_history[-1]["duration_seconds"] == 3600


@pytest.mark.asyncio
async def test_async_load_storage_handles_none_from_store(
    coordinator: EufyCleanCoordinator,
) -> None:
    coordinator._store.async_load = AsyncMock(return_value=None)

    await coordinator.async_load_storage()

    assert coordinator.cleaning_history == []
    assert coordinator.last_seen_segments is None


@pytest.mark.asyncio
async def test_async_load_storage_should_reset_non_list_cleaning_history(
    coordinator: EufyCleanCoordinator,
) -> None:
    coordinator._store.async_load = AsyncMock(return_value={"cleaning_history": "oops"})

    await coordinator.async_load_storage()

    assert coordinator.cleaning_history == []


@pytest.mark.asyncio
async def test_async_load_storage_should_drop_malformed_history_entries(
    coordinator: EufyCleanCoordinator,
) -> None:
    coordinator._store.async_load = AsyncMock(
        return_value={
            "cleaning_history": [
                {"start_time": "2026-04-04T05:30:06+00:00"},
            ]
        }
    )

    await coordinator.async_load_storage()

    assert coordinator.cleaning_history == []


class _CapturingStore:
    def __init__(self) -> None:
        self._data: dict = {}
        self.save_count = 0

    async def async_load(self) -> dict:
        return dict(self._data)

    async def async_save(self, data: dict) -> None:
        self._data = dict(data)
        self.save_count += 1


@pytest.mark.asyncio
async def test_concurrent_saves_preserve_both_cleaning_history_and_novelty(
    coordinator: EufyCleanCoordinator,
) -> None:
    """With asyncio.Lock, serialized saves preserve all data."""
    store = _CapturingStore()
    coordinator._store = store
    coordinator._cleaning_history = [{"start_time": "x"}]

    with patch(
        "custom_components.robovac_mqtt.coordinator.get_novelty_caches",
        return_value={"field_shapes": {}},
    ), patch(
        "custom_components.robovac_mqtt.coordinator.clear_novelty_dirty",
    ):
        await coordinator._async_save_cleaning_history()
        await coordinator._async_save_novelty()

    assert "cleaning_history" in store._data
    assert "novelty_caches" in store._data
    assert store._data["cleaning_history"] == [{"start_time": "x"}]
    assert store.save_count == 2


@pytest.mark.asyncio
async def test_async_save_cleaning_history_logs_and_swallows_store_errors(
    coordinator: EufyCleanCoordinator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    coordinator._cleaning_history = [{"start_time": "2026-04-04T05:30:06+00:00"}]
    coordinator._store.async_load = AsyncMock(return_value={})
    coordinator._store.async_save = AsyncMock(side_effect=OSError("permission denied"))

    await coordinator._async_save_cleaning_history()

    assert "Failed to save cleaning history" in caplog.text
