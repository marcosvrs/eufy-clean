"""Unit tests for parsing cleaning statistics."""

# Removed: test_cleaning_stats_sensors — covered by tests/integration/test_entity_sensor.py

from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.clean_statistics_pb2 import (
    CleanStatistics,
)
from custom_components.robovac_mqtt.utils import encode_message


def test_parsing_cleaning_stats():
    """Test parsing of CLEANING_STATISTICS DPS."""
    state = VacuumState()

    stats = CleanStatistics()
    stats.single.clean_duration = 2700
    stats.single.clean_area = 50
    stats.total.clean_duration = 60000
    stats.total.clean_area = 1200
    stats.total.clean_count = 25

    encoded_value = encode_message(stats)

    dps = {DPS_MAP["CLEANING_STATISTICS"]: encoded_value}
    new_state, _ = update_state(state, dps)

    assert new_state.cleaning_time == 2700
    assert new_state.cleaning_area == 50
