"""Unit tests for the FindRobot switch entity."""

# Removed: test_find_robot_entity — covered by tests/integration/test_entity_controls.py
# Removed: test_find_robot_turn_on_off — covered by tests/integration/test_entity_controls.py
# Removed: test_child_lock_switch_turn_on_off — covered by tests/integration/test_entity_controls.py
# Removed: test_child_lock_switch_unavailable_without_field — covered by tests/integration/test_entity_controls.py
# Removed: test_do_not_disturb_switch_turn_on_off — covered by tests/integration/test_entity_controls.py
# Removed: test_dock_switches — covered by tests/integration/test_entity_controls.py
# Removed: test_dock_switch_deepcopy_no_mutation — covered by tests/integration/test_entity_controls.py
# Removed: test_dock_switch_unavailable_no_cfg — covered by tests/integration/test_entity_controls.py

from custom_components.robovac_mqtt.switch import set_wash_cfg


def test_set_wash_cfg_writes_string_values():
    """Test set_wash_cfg writes STANDARD/CLOSE strings, not integers."""
    cfg = {}
    set_wash_cfg(cfg, True)
    assert cfg["wash"]["cfg"] == "STANDARD"
    set_wash_cfg(cfg, False)
    assert cfg["wash"]["cfg"] == "CLOSE"
