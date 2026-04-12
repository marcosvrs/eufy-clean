"""Unit tests for button entities."""

# pyright: reportAny=false

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.robovac_mqtt.button import (
    RCModeButton,
    RestartButton,
    ResumeFromBreakpointButton,
    RoboVacButton,
)
from custom_components.robovac_mqtt.descriptions.button import (
    RoboVacButtonDescription,
    RoboVacResetButtonDescription,
)
from custom_components.robovac_mqtt.models import VacuumState


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock coordinator for button tests."""
    coordinator = MagicMock()
    coordinator.device_id = "test_id"
    coordinator.device_name = "Test Vac"
    coordinator.device_info = {"identifiers": {("robovac_mqtt", "test_id")}}
    coordinator.dps_map = {}
    coordinator.data = VacuumState()
    coordinator.async_send_command = AsyncMock()
    coordinator.last_update_success = True
    return coordinator


@pytest.mark.asyncio
async def test_reset_button_builds_reset_accessory_command(mock_coordinator: MagicMock):
    """Reset buttons send the reset_accessory command with the consumable type."""
    description = RoboVacResetButtonDescription(
        key="reset_filter",
        consumable_type=7,
        icon="mdi:air-filter",
    )
    entity = RoboVacButton(mock_coordinator, description)

    with patch("custom_components.robovac_mqtt.button.build_command") as mock_build:
        mock_build.return_value = {"168": "payload"}

        await entity.async_press()

    mock_build.assert_called_once_with(
        "reset_accessory",
        dps_map=mock_coordinator.dps_map,
        reset_type=7,
    )
    mock_coordinator.async_send_command.assert_awaited_once_with({"168": "payload"})


@pytest.mark.asyncio
async def test_restart_button_uses_power_dps_fallback(mock_coordinator: MagicMock):
    """Restart button falls back to DPS 151 when POWER is absent."""
    entity = RestartButton(mock_coordinator)

    with patch("custom_components.robovac_mqtt.button.build_command") as mock_build:
        mock_build.return_value = {"151": False}

        await entity.async_press()

    mock_build.assert_called_once_with("generic", dp_id="151", value=False)
    mock_coordinator.async_send_command.assert_awaited_once_with({"151": False})


@pytest.mark.asyncio
async def test_resume_from_breakpoint_button_uses_pause_job_fallback(
    mock_coordinator: MagicMock,
):
    """Resume-from-breakpoint button falls back to DPS 156 when missing."""
    entity = ResumeFromBreakpointButton(mock_coordinator)

    with patch("custom_components.robovac_mqtt.button.build_command") as mock_build:
        mock_build.return_value = {"156": True}

        await entity.async_press()

    mock_build.assert_called_once_with("generic", dp_id="156", value=True)
    mock_coordinator.async_send_command.assert_awaited_once_with({"156": True})


@pytest.mark.asyncio
async def test_rc_mode_exit_button_sends_stop_rc(mock_coordinator: MagicMock):
    """Exit RC mode button sends the stop_rc command."""
    entity = RCModeButton(mock_coordinator, enter=False)

    with patch("custom_components.robovac_mqtt.button.build_command") as mock_build:
        mock_build.return_value = {"155": "stop"}

        await entity.async_press()

    mock_build.assert_called_once_with("stop_rc", dps_map=mock_coordinator.dps_map)
    mock_coordinator.async_send_command.assert_awaited_once_with({"155": "stop"})


@pytest.mark.asyncio
async def test_generic_button_forwards_description_command(mock_coordinator: MagicMock):
    """Generic button descriptions pass their command through unchanged."""
    description = RoboVacButtonDescription(key="stop_return", command="stop_gohome")
    entity = RoboVacButton(mock_coordinator, description)

    with patch("custom_components.robovac_mqtt.button.build_command") as mock_build:
        mock_build.return_value = {"173": "payload"}

        await entity.async_press()

    mock_build.assert_called_once_with("stop_gohome", dps_map=mock_coordinator.dps_map)
    mock_coordinator.async_send_command.assert_awaited_once_with({"173": "payload"})
