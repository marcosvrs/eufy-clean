# Removed: test_vacuum_properties — covered by tests/integration/test_entity_vacuum.py
# Removed: test_vacuum_attributes — covered by tests/integration/test_entity_vacuum.py
# Removed: test_vacuum_commands — covered by tests/integration/test_entity_vacuum.py
# Removed: test_set_fan_speed — covered by tests/integration/test_entity_vacuum.py
# Removed: test_async_send_command_raw — covered by tests/integration/test_entity_vacuum.py
# Removed: test_room_clean_applies_user_preferences — covered by tests/integration/test_entity_vacuum.py
# Removed: test_room_clean_with_explicit_params_overrides_preferences — covered by tests/integration/test_entity_vacuum.py
# Removed: test_mqtt_malformed_message_does_not_crash — covered by tests/integration/test_edge_cases.py
# Removed: test_app_segment_clean_command — covered by tests/integration/test_entity_vacuum.py
# Removed: test_app_segment_clean_invalid_ids — covered by tests/integration/test_entity_vacuum.py
# Removed: test_async_clean_segments_empty_list — covered by tests/integration/test_entity_vacuum.py
# All tests in this file were REDUNDANT per tests/integration/AUDIT.md (Task 12/15 integration coverage).

from custom_components.robovac_mqtt.vacuum import RoboVacMQTTEntity


def test_vacuum_unrecorded_attributes():
    assert "rooms" in RoboVacMQTTEntity._unrecorded_attributes
    assert "segments" in RoboVacMQTTEntity._unrecorded_attributes
