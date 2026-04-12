"""Unit tests for do-not-disturb time entities."""

# pyright: reportAny=false

from __future__ import annotations

from datetime import time as dt_time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.time import (
    DoNotDisturbEndTimeEntity,
    DoNotDisturbStartTimeEntity,
)


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock coordinator for time tests."""
    coordinator = MagicMock()
    coordinator.device_id = "test_id"
    coordinator.device_name = "Test Vac"
    coordinator.device_info = {"identifiers": {("robovac_mqtt", "test_id")}}
    coordinator.data = VacuumState(received_fields={"do_not_disturb"})
    coordinator.async_send_command = AsyncMock()
    coordinator.async_set_updated_data = MagicMock()
    coordinator.last_update_success = True
    return coordinator


@pytest.mark.asyncio
async def test_dnd_start_time_parses_midnight(mock_coordinator: MagicMock):
    """Start entity returns 00:00 correctly."""
    mock_coordinator.data = VacuumState(
        dnd_start_hour=0,
        dnd_start_minute=0,
        received_fields={"do_not_disturb"},
    )
    entity = DoNotDisturbStartTimeEntity(mock_coordinator)

    assert entity.native_value == dt_time(0, 0)


@pytest.mark.asyncio
async def test_dnd_end_time_parses_last_minute_of_day(mock_coordinator: MagicMock):
    """End entity returns 23:59 correctly."""
    mock_coordinator.data = VacuumState(
        dnd_end_hour=23,
        dnd_end_minute=59,
        received_fields={"do_not_disturb"},
    )
    entity = DoNotDisturbEndTimeEntity(mock_coordinator)

    assert entity.native_value == dt_time(23, 59)


@pytest.mark.asyncio
async def test_dnd_start_time_update_preserves_end_schedule(mock_coordinator: MagicMock):
    """Updating start time keeps the existing end time in the outgoing command."""
    entity = DoNotDisturbStartTimeEntity(mock_coordinator)

    with patch("custom_components.robovac_mqtt.time.build_command") as mock_build:
        mock_build.return_value = {"157": "payload"}

        await entity.async_set_value(dt_time(6, 45))

    mock_build.assert_called_once_with(
        "set_do_not_disturb",
        active=mock_coordinator.data.dnd_enabled,
        begin_hour=6,
        begin_minute=45,
        end_hour=mock_coordinator.data.dnd_end_hour,
        end_minute=mock_coordinator.data.dnd_end_minute,
    )
    updated_state = mock_coordinator.async_set_updated_data.call_args.args[0]
    assert updated_state.dnd_start_hour == 6
    assert updated_state.dnd_start_minute == 45
    assert updated_state.dnd_end_hour == mock_coordinator.data.dnd_end_hour


@pytest.mark.asyncio
async def test_dnd_end_time_update_preserves_start_schedule(mock_coordinator: MagicMock):
    """Updating end time keeps the existing start time in the outgoing command."""
    entity = DoNotDisturbEndTimeEntity(mock_coordinator)

    with patch("custom_components.robovac_mqtt.time.build_command") as mock_build:
        mock_build.return_value = {"157": "payload"}

        await entity.async_set_value(dt_time(7, 30))

    mock_build.assert_called_once_with(
        "set_do_not_disturb",
        active=mock_coordinator.data.dnd_enabled,
        begin_hour=mock_coordinator.data.dnd_start_hour,
        begin_minute=mock_coordinator.data.dnd_start_minute,
        end_hour=7,
        end_minute=30,
    )
    updated_state = mock_coordinator.async_set_updated_data.call_args.args[0]
    assert updated_state.dnd_end_hour == 7
    assert updated_state.dnd_end_minute == 30


@pytest.mark.asyncio
async def test_dnd_time_unavailable_without_received_marker(mock_coordinator: MagicMock):
    """DND time entities stay unavailable until the field has been reported."""
    mock_coordinator.data = VacuumState(received_fields=set())
    entity = DoNotDisturbStartTimeEntity(mock_coordinator)

    assert entity.available is False
