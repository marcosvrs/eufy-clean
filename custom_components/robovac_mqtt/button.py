from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .__init__ import EufyCleanConfigEntry
from .api.commands import build_command
from .const import DOMAIN
from .coordinator import EufyCleanCoordinator
from .descriptions.button import (
    DOCK_BUTTON_DESCRIPTIONS,
    GENERIC_BUTTON_DESCRIPTIONS,
    MEDIA_BUTTON_DESCRIPTIONS,
    RESET_BUTTON_DESCRIPTIONS,
    RoboVacButtonDescription,
    RoboVacResetButtonDescription,
)

PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EufyCleanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup button entities."""
    entities: list[ButtonEntity] = []

    for coordinator in config_entry.runtime_data.coordinators.values():
        _LOGGER.debug("Adding buttons for %s", coordinator.device_name)

        entities.extend(
            RoboVacButton(coordinator, description)
            for description in DOCK_BUTTON_DESCRIPTIONS
            if description.exists_fn(coordinator)
        )

        entities.extend(
            RoboVacButton(coordinator, description)
            for description in RESET_BUTTON_DESCRIPTIONS
            if description.exists_fn(coordinator)
        )

        entities.extend(
            RoboVacButton(coordinator, description)
            for description in GENERIC_BUTTON_DESCRIPTIONS
            if description.exists_fn(coordinator)
        )

        entities.append(RestartButton(coordinator))
        entities.append(ResumeFromBreakpointButton(coordinator))

        entities.extend(
            RoboVacButton(coordinator, description)
            for description in MEDIA_BUTTON_DESCRIPTIONS
            if description.exists_fn(coordinator)
        )

        for direction in ("Forward", "Back", "Left", "Right", "Brake"):
            entities.append(RCDirectionButton(coordinator, direction))
        entities.append(RCModeButton(coordinator, enter=True))
        entities.append(RCModeButton(coordinator, enter=False))

    async_add_entities(entities)


class RoboVacButton(CoordinatorEntity[EufyCleanCoordinator], ButtonEntity):
    """Eufy Clean Button Entity."""

    _attr_has_entity_name = True
    _attr_entity_registry_visible_default = False

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        description: RoboVacButtonDescription | RoboVacResetButtonDescription,
    ) -> None:
        """Initialize button."""
        super().__init__(coordinator)
        self._description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"
        self._attr_name = description.name
        self._attr_device_info = coordinator.device_info
        self._attr_entity_category = description.entity_category
        if description.icon:
            self._attr_icon = description.icon

    async def async_press(self) -> None:
        """Press the button."""
        if isinstance(self._description, RoboVacResetButtonDescription):
            cmd = build_command(
                "reset_accessory",
                dps_map=self.coordinator.dps_map,
                reset_type=self._description.consumable_type,
            )
        else:
            cmd = build_command(
                self._description.command, dps_map=self.coordinator.dps_map
            )
        await self.coordinator.async_send_command(cmd)


class RestartButton(CoordinatorEntity[EufyCleanCoordinator], ButtonEntity):

    def __init__(self, coordinator: EufyCleanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.device_id}_restart"
        self._attr_name = "Restart"
        self._attr_icon = "mdi:restart"
        self._attr_device_info = coordinator.device_info
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_visible_default = False

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(
            build_command(
                "generic",
                dp_id=self.coordinator.dps_map.get("POWER", "151"),
                value=False,
            )
        )


class ResumeFromBreakpointButton(CoordinatorEntity[EufyCleanCoordinator], ButtonEntity):

    def __init__(self, coordinator: EufyCleanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.device_id}_resume_from_breakpoint"
        self._attr_name = "Resume from Breakpoint"
        self._attr_icon = "mdi:play-circle"
        self._attr_device_info = coordinator.device_info
        self._attr_entity_category = None
        self._attr_entity_registry_visible_default = False

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(
            build_command(
                "generic",
                dp_id=self.coordinator.dps_map.get("PAUSE_JOB", "156"),
                value=True,
            )
        )


_RC_DIRECTION_ICONS = {
    "Forward": "mdi:arrow-up",
    "Back": "mdi:arrow-down",
    "Left": "mdi:arrow-left",
    "Right": "mdi:arrow-right",
    "Brake": "mdi:stop",
}


class RCDirectionButton(CoordinatorEntity[EufyCleanCoordinator], ButtonEntity):

    def __init__(self, coordinator: EufyCleanCoordinator, direction: str) -> None:
        super().__init__(coordinator)
        self._direction = direction
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.device_id}_rc_{direction.lower()}"
        self._attr_name = f"RC {direction}"
        self._attr_icon = _RC_DIRECTION_ICONS.get(direction, "mdi:gamepad")
        self._attr_device_info = coordinator.device_info
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_visible_default = False

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(
            build_command(
                "generic",
                dp_id=self.coordinator.dps_map.get("REMOTE_CTRL", "155"),
                value=self._direction,
            )
        )


class RCModeButton(CoordinatorEntity[EufyCleanCoordinator], ButtonEntity):

    def __init__(self, coordinator: EufyCleanCoordinator, *, enter: bool) -> None:
        super().__init__(coordinator)
        self._enter = enter
        self._attr_has_entity_name = True
        if enter:
            self._attr_unique_id = f"{coordinator.device_id}_rc_enter"
            self._attr_name = "Enter RC Mode"
            self._attr_icon = "mdi:gamepad-variant"
            self._cmd = "start_rc"
        else:
            self._attr_unique_id = f"{coordinator.device_id}_rc_exit"
            self._attr_name = "Exit RC Mode"
            self._attr_icon = "mdi:gamepad-variant-outline"
            self._cmd = "stop_rc"
        self._attr_device_info = coordinator.device_info
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_visible_default = False

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(
            build_command(self._cmd, dps_map=self.coordinator.dps_map)
        )
