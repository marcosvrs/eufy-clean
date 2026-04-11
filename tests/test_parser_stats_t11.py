from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DEFAULT_DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.clean_statistics_pb2 import (
    CleanStatistics,
)
from custom_components.robovac_mqtt.utils import encode_message


def _make_dps(stats: CleanStatistics) -> dict:
    return {DEFAULT_DPS_MAP["CLEANING_STATISTICS"]: encode_message(stats)}


def test_total_stats_parsed():
    stats = CleanStatistics(
        total=CleanStatistics.Total(
            clean_duration=3600,
            clean_area=50,
            clean_count=10,
        )
    )
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(stats))

    assert new_state.total_cleaning_time == 3600
    assert new_state.total_cleaning_area == 50
    assert new_state.total_cleaning_count == 10
    assert "total_stats" in new_state.received_fields


def test_user_total_stats_parsed():
    stats = CleanStatistics(
        user_total=CleanStatistics.Total(
            clean_duration=1800,
            clean_area=25,
            clean_count=5,
        )
    )
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(stats))

    assert new_state.user_total_cleaning_time == 1800
    assert new_state.user_total_cleaning_area == 25
    assert new_state.user_total_cleaning_count == 5
    assert "user_total_stats" in new_state.received_fields


def test_existing_single_stats_still_work():
    stats = CleanStatistics(
        single=CleanStatistics.Single(
            clean_duration=600,
            clean_area=10,
        )
    )
    state = VacuumState()
    new_state, _ = update_state(state, _make_dps(stats))

    assert new_state.cleaning_time == 600
    assert new_state.cleaning_area == 10
