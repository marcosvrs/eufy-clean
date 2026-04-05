# Removed: test_scene_select_entity_mocked — covered by tests/integration/test_entity_controls.py

from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.work_status_pb2 import WorkStatus
from custom_components.robovac_mqtt.utils import encode_message


def test_scene_parsing_logic():
    """Test extracting scene info from WorkStatus proto."""
    ws = WorkStatus()
    ws.current_scene.id = 8
    ws.current_scene.name = "Hallway test"

    encoded = encode_message(ws)
    mock_dps = {DPS_MAP["WORK_STATUS"]: encoded}

    state_obj = VacuumState()
    _, changes = update_state(state_obj, mock_dps)

    assert changes.get("current_scene_id") == 8
    assert changes.get("current_scene_name") == "Hallway test"


def test_scene_parsing_partial_update():
    """Test response when WorkStatus partial update (omitted fields) arrives."""
    ws = WorkStatus()

    encoded = encode_message(ws)
    mock_dps = {DPS_MAP["WORK_STATUS"]: encoded}

    state_obj = VacuumState()
    state_obj.current_scene_id = 9
    state_obj.current_scene_name = "Old"

    _, changes = update_state(state_obj, mock_dps)

    assert "current_scene_id" not in changes
    assert "current_scene_name" not in changes


def test_scene_parsing_explicit_clear_mode():
    """Test clearing scene when Mode changes to Auto."""
    ws = WorkStatus()
    ws.mode.value = 0

    encoded = encode_message(ws)
    mock_dps = {DPS_MAP["WORK_STATUS"]: encoded}

    state_obj = VacuumState()
    state_obj.current_scene_id = 9

    _, changes = update_state(state_obj, mock_dps)

    assert changes.get("current_scene_id") == 0
    assert changes.get("current_scene_name") is None


def test_scene_parsing_explicit_clear_state():
    """Test clearing scene when State changes to Charging."""
    ws = WorkStatus()
    ws.state = 3

    encoded = encode_message(ws)
    mock_dps = {DPS_MAP["WORK_STATUS"]: encoded}

    state_obj = VacuumState()
    state_obj.current_scene_id = 9

    _, changes = update_state(state_obj, mock_dps)

    assert changes.get("current_scene_id") == 0
    assert changes.get("current_scene_name") is None
