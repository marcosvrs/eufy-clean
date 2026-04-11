from custom_components.robovac_mqtt.const import HANDLED_DPS_IDS, KNOWN_UNPROCESSED_DPS
from custom_components.robovac_mqtt.models import VacuumState


def test_178_not_in_unprocessed():
    assert "178" not in KNOWN_UNPROCESSED_DPS


def test_178_in_handled():
    assert "178" in HANDLED_DPS_IDS


def test_notification_fields_exist():
    s = VacuumState()
    assert s.notification_codes == []
    assert s.notification_message == ""
    assert s.notification_time == 0
