"""Unit tests for binary sensor entities."""

# pyright: reportAny=false, reportArgumentType=false

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.robovac_mqtt.binary_sensor import RoboVacBinarySensor
from custom_components.robovac_mqtt.descriptions.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
)
from custom_components.robovac_mqtt.models import VacuumState


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock coordinator for binary sensor tests."""
    coordinator = MagicMock()
    coordinator.device_id = "test_id"
    coordinator.device_name = "Test Vac"
    coordinator.device_info = {"identifiers": {("robovac_mqtt", "test_id")}}
    coordinator.data = VacuumState()
    coordinator.last_update_success = True
    return coordinator


def _description(key: str):
    return next(desc for desc in BINARY_SENSOR_DESCRIPTIONS if desc.key == key)


@pytest.mark.asyncio
async def test_charging_sensor_propagates_none_state(mock_coordinator: MagicMock):
    """Charging sensor keeps an unknown state when the value is unavailable."""
    mock_coordinator.data = VacuumState(charging=None)  # type: ignore[arg-type]
    entity = RoboVacBinarySensor(mock_coordinator, _description("charging"))

    assert entity.is_on is None


@pytest.mark.asyncio
async def test_live_map_sensor_is_off_when_bits_zero(mock_coordinator: MagicMock):
    """Live map sensor maps zero state bits to False once available."""
    mock_coordinator.data = VacuumState(
        live_map_state_bits=0,
        received_fields={"live_map_state_bits"},
    )
    entity = RoboVacBinarySensor(mock_coordinator, _description("live_map"))

    assert entity.available is True
    assert entity.is_on is False


@pytest.mark.asyncio
async def test_live_map_sensor_unavailable_before_field_received(
    mock_coordinator: MagicMock,
):
    """Availability depends on the received field marker, not stored value alone."""
    mock_coordinator.data = VacuumState(live_map_state_bits=4, received_fields=set())
    entity = RoboVacBinarySensor(mock_coordinator, _description("live_map"))

    assert entity.available is False
    assert entity.is_on is True


@pytest.mark.asyncio
async def test_dust_collect_result_sensor_uses_received_field_gate(
    mock_coordinator: MagicMock,
):
    """Dust collect result stays unavailable until its stats field is received."""
    mock_coordinator.data = VacuumState(dust_collect_result=True, received_fields=set())
    entity = RoboVacBinarySensor(mock_coordinator, _description("dust_collect_result"))

    assert entity.available is False

    mock_coordinator.data.received_fields.add("dust_collect_stats")
    assert entity.available is True
    assert entity.is_on is True
