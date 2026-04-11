from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DEFAULT_DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState


def test_analysis_stats_fields_exist():
    s = VacuumState()
    for field in [
        "last_clean_area",
        "last_clean_time",
        "last_clean_mode",
        "last_gohome_result",
        "last_gohome_fail_code",
        "ctrl_event_type",
        "ctrl_event_source",
        "ctrl_event_timestamp",
        "battery_discharge_curve",
    ]:
        assert hasattr(s, field), f"Missing: {field}"


def test_battery_discharge_curve_parsed():
    """DPS 179 with battery_curve field 16 populates battery_discharge_curve."""
    b64 = "GRIXggEUEhIKENYHzwfCB7cHrQelB54HmAc="
    state = VacuumState()
    dps_key = DEFAULT_DPS_MAP.get("ANALYSIS", "179")
    new_state, changes = update_state(state, {dps_key: b64})
    assert new_state.battery_discharge_curve == [
        98.2,
        97.5,
        96.2,
        95.1,
        94.1,
        93.3,
        92.6,
        92.0,
    ]


def test_battery_discharge_curve_empty_without_field():
    """DPS 179 without battery_curve keeps empty list."""
    state = VacuumState()
    assert state.battery_discharge_curve == []
