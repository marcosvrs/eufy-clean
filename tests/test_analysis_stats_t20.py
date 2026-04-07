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
    ]:
        assert hasattr(s, field), f"Missing: {field}"
