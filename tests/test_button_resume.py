from unittest.mock import MagicMock

from custom_components.robovac_mqtt.api.commands import build_command
from custom_components.robovac_mqtt.button import ResumeFromBreakpointButton
from custom_components.robovac_mqtt.const import HANDLED_DPS_IDS
from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator
from custom_components.robovac_mqtt.models import VacuumState


def _mock_coordinator() -> MagicMock:
    coordinator = MagicMock(spec=EufyCleanCoordinator)
    coordinator.device_id = "test_device"
    coordinator.device_info = MagicMock()
    coordinator.data = VacuumState()
    coordinator.last_update_success = True
    coordinator.dps_map = {"PAUSE_JOB": "156"}
    return coordinator


def test_dps_156_in_handled_ids() -> None:
    assert "156" in HANDLED_DPS_IDS


def test_resume_button_class_exists() -> None:
    entity = ResumeFromBreakpointButton(_mock_coordinator())

    assert entity.unique_id == "test_device_resume_from_breakpoint"
    assert entity.entity_registry_visible_default is False


def test_resume_button_sends_correct_command() -> None:
    coordinator = _mock_coordinator()
    entity = ResumeFromBreakpointButton(coordinator)

    async def _send_command(command: dict[str, object]) -> None:
        coordinator.sent_command = command

    entity.coordinator.async_send_command = _send_command

    import asyncio

    asyncio.run(entity.async_press())

    assert coordinator.sent_command["156"] is not None


def test_resume_button_command_matches_generic_pause_job() -> None:
    assert build_command("generic", dp_id="156", value=True)["156"]
