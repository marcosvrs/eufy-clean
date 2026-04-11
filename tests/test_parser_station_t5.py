"""Tests for T5: DPS 173 dirty_level + clean_level parsing."""

from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DEFAULT_DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.station_pb2 import StationResponse
from custom_components.robovac_mqtt.utils import encode_message


def _make_dps(station: StationResponse) -> dict:
    return {DEFAULT_DPS_MAP["STATION_STATUS"]: encode_message(station)}


def test_dirty_level_populates_station_waste_water() -> None:
    """dirty_level on StationResponse should populate station_waste_water."""
    station = StationResponse(dirty_level=StationResponse.WaterLevel.HIGH)
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(station))
    assert new_state.station_waste_water != 0


def test_clean_level_populates_station_clean_level() -> None:
    """clean_level on StationResponse should populate station_clean_level."""
    station = StationResponse(clean_level=StationResponse.WaterLevel.HIGH)
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(station))
    assert new_state.station_clean_level != 0


def test_empty_dirty_level_gives_zero() -> None:
    """A StationResponse with dirty_level=EMPTY gives station_waste_water=0."""
    station = StationResponse(dirty_level=StationResponse.WaterLevel.EMPTY)
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(station))
    assert new_state.station_waste_water == 0


def test_station_clean_level_field_exists() -> None:
    """VacuumState should have station_clean_level field."""
    assert hasattr(VacuumState(), "station_clean_level")
    assert VacuumState().station_clean_level == 0
