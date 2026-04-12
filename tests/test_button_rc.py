import asyncio
from unittest.mock import MagicMock

from custom_components.robovac_mqtt.api.commands import build_command
from custom_components.robovac_mqtt.button import RCDirectionButton, RCModeButton
from custom_components.robovac_mqtt.const import (
    AUTO_ENTITY_OVERRIDES,
    HANDLED_DPS_IDS,
)
from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator
from custom_components.robovac_mqtt.models import VacuumState


def _mock_coordinator() -> MagicMock:
    c = MagicMock(spec=EufyCleanCoordinator)
    c.device_id = "test_device"
    c.device_info = MagicMock()
    c.data = VacuumState()
    c.last_update_success = True
    c.dps_map = {"REMOTE_CTRL": "155", "PLAY_PAUSE": "152"}
    return c


def test_dps_155_in_handled_ids() -> None:
    assert "155" in HANDLED_DPS_IDS


def test_remote_ctrl_not_in_auto_entity_overrides() -> None:
    assert "remote_ctrl" not in AUTO_ENTITY_OVERRIDES


def test_rc_direction_button_unique_id() -> None:
    entity = RCDirectionButton(_mock_coordinator(), "Forward")
    assert entity.unique_id == "test_device_rc_forward"


def test_rc_direction_button_all_directions() -> None:
    coord = _mock_coordinator()
    for direction in ("Forward", "Back", "Left", "Right", "Brake"):
        entity = RCDirectionButton(coord, direction)
        assert entity.unique_id == f"test_device_rc_{direction.lower()}"
        assert entity.name == f"RC {direction}"


def test_rc_direction_button_sends_generic_command() -> None:
    coordinator = _mock_coordinator()
    entity = RCDirectionButton(coordinator, "Forward")

    async def _send_command(command: dict[str, object]) -> None:
        coordinator.sent_command = command

    entity.coordinator.async_send_command = _send_command
    asyncio.run(entity.async_press())

    assert coordinator.sent_command == {"155": "Forward"}


def test_rc_mode_button_enter() -> None:
    entity = RCModeButton(_mock_coordinator(), enter=True)
    assert entity.unique_id == "test_device_rc_enter"
    assert entity._attr_translation_key == "rc_enter"


def test_rc_mode_button_exit() -> None:
    entity = RCModeButton(_mock_coordinator(), enter=False)
    assert entity.unique_id == "test_device_rc_exit"
    assert entity._attr_translation_key == "rc_exit"


def test_rc_mode_enter_sends_start_rc() -> None:
    coordinator = _mock_coordinator()
    entity = RCModeButton(coordinator, enter=True)

    async def _send_command(command: dict[str, object]) -> None:
        coordinator.sent_command = command

    entity.coordinator.async_send_command = _send_command
    asyncio.run(entity.async_press())

    assert "152" in coordinator.sent_command


def test_rc_mode_exit_sends_stop_rc() -> None:
    coordinator = _mock_coordinator()
    entity = RCModeButton(coordinator, enter=False)

    async def _send_command(command: dict[str, object]) -> None:
        coordinator.sent_command = command

    entity.coordinator.async_send_command = _send_command
    asyncio.run(entity.async_press())

    assert "152" in coordinator.sent_command


def test_build_command_start_rc() -> None:
    result = build_command("start_rc")
    assert "152" in result


def test_build_command_stop_rc() -> None:
    result = build_command("stop_rc")
    assert "152" in result


def test_all_rc_entities_hidden_by_default() -> None:
    coord = _mock_coordinator()
    entities = []
    for direction in ("Forward", "Back", "Left", "Right", "Brake"):
        entities.append(RCDirectionButton(coord, direction))
    entities.append(RCModeButton(coord, enter=True))
    entities.append(RCModeButton(coord, enter=False))

    assert len(entities) == 7
    for entity in entities:
        assert entity.entity_registry_visible_default is False
