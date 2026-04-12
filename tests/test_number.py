"""Unit tests for number entities."""

# pyright: reportAny=false, reportUnknownParameterType=false, reportMissingTypeArgument=false, reportUnknownArgumentType=false, reportIndexIssue=false

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.number import DockNumberEntity, UnisettingNumber


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock coordinator for number tests."""
    coordinator = MagicMock()
    coordinator.device_id = "test_id"
    coordinator.device_name = "Test Vac"
    coordinator.device_info = {"identifiers": {("robovac_mqtt", "test_id")}}
    coordinator.dps_map = {}
    coordinator.data = VacuumState(
        dock_auto_cfg={"wash": {"wash_freq": {"time_or_area": {"value": 15}}}},
        received_fields={"dust_full_remind"},
        dust_full_remind=10,
    )
    coordinator.async_send_command = AsyncMock()
    coordinator.last_update_success = True
    return coordinator


def _wash_freq_getter(cfg: dict[str, Any]) -> float:
    return cfg["wash"]["wash_freq"]["time_or_area"]["value"]


def _wash_freq_setter(cfg: dict[str, Any], value: float) -> None:
    cfg["wash"]["wash_freq"]["time_or_area"]["value"] = int(value)


@pytest.mark.asyncio
async def test_dock_number_native_value_returns_none_on_getter_error(
    mock_coordinator: MagicMock,
):
    """Dock number returns None instead of raising on malformed config."""
    entity = DockNumberEntity(
        mock_coordinator,
        "wash_frequency_value",
        15,
        25,
        1,
        lambda cfg: cfg["missing"]["value"],
        _wash_freq_setter,
    )
    entity._attr_translation_key = None
    entity._attr_name = "Wash Frequency Value"

    assert entity.native_value is None


@pytest.mark.asyncio
async def test_dock_number_set_value_preserves_existing_config(mock_coordinator: MagicMock):
    """Updating the number deep-copies dock config before mutation."""
    original_cfg = {
        "wash": {"wash_freq": {"time_or_area": {"value": 15}}},
        "collectdust_v2": {"sw": {"value": True}},
    }
    mock_coordinator.data = VacuumState(dock_auto_cfg=original_cfg)
    entity = DockNumberEntity(
        mock_coordinator,
        "wash_frequency_value",
        15,
        25,
        1,
        _wash_freq_getter,
        _wash_freq_setter,
    )

    with patch("custom_components.robovac_mqtt.number.build_command") as mock_build:
        mock_build.return_value = {"173": "payload"}

        await entity.async_set_native_value(25)

    cfg = mock_build.call_args.kwargs["cfg"]
    assert cfg["wash"]["wash_freq"]["time_or_area"]["value"] == 25
    assert cfg["collectdust_v2"]["sw"]["value"] is True
    assert original_cfg["wash"]["wash_freq"]["time_or_area"]["value"] == 15


@pytest.mark.asyncio
async def test_dock_number_accepts_minimum_boundary_value(mock_coordinator: MagicMock):
    """Dock number forwards the configured minimum boundary unchanged."""
    entity = DockNumberEntity(
        mock_coordinator,
        "wash_frequency_value",
        15,
        25,
        1,
        _wash_freq_getter,
        _wash_freq_setter,
    )

    with patch("custom_components.robovac_mqtt.number.build_command") as mock_build:
        mock_build.return_value = {"173": "payload"}

        await entity.async_set_native_value(entity.native_min_value)

    cfg = mock_build.call_args.kwargs["cfg"]
    assert cfg["wash"]["wash_freq"]["time_or_area"]["value"] == 15


@pytest.mark.asyncio
async def test_unisetting_number_available_only_after_field_received(
    mock_coordinator: MagicMock,
):
    """Unisetting numbers are unavailable until their field has been observed."""
    mock_coordinator.data = VacuumState(received_fields=set())
    entity = UnisettingNumber(mock_coordinator, "dust_full_remind", 0, 100, 1)

    assert entity.available is False

    mock_coordinator.data.received_fields.add("dust_full_remind")
    assert entity.available is True


@pytest.mark.asyncio
async def test_unisetting_number_casts_float_to_int_when_sending(
    mock_coordinator: MagicMock,
):
    """Unisetting numbers cast Home Assistant float payloads to ints."""
    entity = UnisettingNumber(mock_coordinator, "dust_full_remind", 0, 100, 1)

    with patch("custom_components.robovac_mqtt.number.build_command") as mock_build:
        mock_build.return_value = {"176": "payload"}

        await entity.async_set_native_value(42.9)

    mock_build.assert_called_once_with(
        "set_unisetting",
        dps_map=mock_coordinator.dps_map,
        field="dust_full_remind",
        value=42,
        current_state=mock_coordinator.data,
    )
