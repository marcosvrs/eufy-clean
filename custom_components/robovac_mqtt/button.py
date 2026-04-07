from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api.commands import build_command
from .const import DOMAIN
from .coordinator import EufyCleanCoordinator
from .proto.cloud.consumable_pb2 import ConsumableRequest

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup button entities."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: list[EufyCleanCoordinator] = data["coordinators"]

    entities = []

    for coordinator in coordinators:
        _LOGGER.debug("Adding buttons for %s", coordinator.device_name)

        if "STATION_STATUS" in coordinator.supported_dps:
            entities.extend(
                [
                    RoboVacButton(coordinator, "Dry Mop", "_dry_mop", "go_dry"),
                    RoboVacButton(coordinator, "Wash Mop", "_wash_mop", "go_selfcleaning"),
                    RoboVacButton(
                        coordinator, "Empty Dust Bin", "_empty_dust_bin", "collect_dust"
                    ),
                    RoboVacButton(coordinator, "Stop Dry Mop", "_stop_dry_mop", "stop_dry"),
                ]
            )

        # Accessory Reset Buttons
        if "ACCESSORIES_STATUS" in coordinator.supported_dps:
            accessories = [
                (
                    "Reset Filter",
                    "_reset_filter",
                    ConsumableRequest.FILTER_MESH,
                    "mdi:air-filter",
                ),
                (
                    "Reset Rolling Brush",
                    "_reset_main_brush",
                    ConsumableRequest.ROLLING_BRUSH,
                    "mdi:broom",
                ),
                (
                    "Reset Side Brush",
                    "_reset_side_brush",
                    ConsumableRequest.SIDE_BRUSH,
                    "mdi:broom",
                ),
                (
                    "Reset Sensors",
                    "_reset_sensors",
                    ConsumableRequest.SENSOR,
                    "mdi:eye-outline",
                ),
                (
                    "Reset Cleaning Tray",
                    "_reset_scrape",
                    ConsumableRequest.SCRAPE,
                    "mdi:wiper",
                ),
                ("Reset Mopping Cloth", "_reset_mop", ConsumableRequest.MOP, "mdi:water"),
            ]

            for name, suffix, reset_type, icon in accessories:
                entities.append(
                    RoboVacButton(
                        coordinator,
                        name,
                        suffix,
                        "reset_accessory",
                        icon,
                        category=EntityCategory.CONFIG,
                        reset_type=reset_type,
                    )
                )

        entities.extend(
            [
                RoboVacButton(
                    coordinator, "Stop Return", "_stop_return", "stop_gohome",
                    "mdi:home-off",
                ),
                RoboVacButton(
                    coordinator, "Map Then Clean", "_map_then_clean",
                    "mapping_then_clean", "mdi:map-plus",
                ),
                RoboVacButton(
                    coordinator, "Global Cruise", "_global_cruise",
                    "start_global_cruise", "mdi:map-marker-path",
                ),
                RoboVacButton(
                    coordinator, "Stop Smart Follow", "_stop_smart_follow",
                    "stop_smart_follow", "mdi:walk",
                ),
            ]
        )

        entities.append(
            RestartButton(coordinator)
        )
        entities.append(ResumeFromBreakpointButton(coordinator))

        if "MEDIA_MANAGER" in coordinator.supported_dps:
            entities.append(
                RoboVacButton(
                    coordinator, "Capture Photo", "_media_capture",
                    "media_capture", "mdi:camera",
                )
            )

        for direction in ("Forward", "Back", "Left", "Right", "Brake"):
            entities.append(RCDirectionButton(coordinator, direction))
        entities.append(RCModeButton(coordinator, enter=True))
        entities.append(RCModeButton(coordinator, enter=False))

    async_add_entities(entities)


class RoboVacButton(CoordinatorEntity[EufyCleanCoordinator], ButtonEntity):
    """Eufy Clean Button Entity."""

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        name_suffix: str,
        id_suffix: str,
        command: str,
        icon: str | None = None,
        category: EntityCategory | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize button."""
        super().__init__(coordinator)
        self._command = command
        self._command_kwargs = kwargs
        self._attr_unique_id = f"{coordinator.device_id}{id_suffix}"

        # Use Home Assistant standard naming
        self._attr_has_entity_name = True
        self._attr_name = name_suffix

        self._attr_device_info = coordinator.device_info
        self._attr_entity_category = category
        if icon:
            self._attr_icon = icon
        self._attr_entity_registry_visible_default = False

    async def async_press(self) -> None:
        """Press the button."""
        cmd = build_command(self._command, **self._command_kwargs)
        await self.coordinator.async_send_command(cmd)


class RestartButton(CoordinatorEntity[EufyCleanCoordinator], ButtonEntity):

    def __init__(self, coordinator: EufyCleanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.device_id}_restart"
        self._attr_name = "Restart"
        self._attr_icon = "mdi:restart"
        self._attr_device_info = coordinator.device_info
        self._attr_entity_category = None
        self._attr_entity_registry_visible_default = False

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(
            build_command("generic", dp_id=self.coordinator.dps_map.get("POWER", "151"), value=False)
        )


class ResumeFromBreakpointButton(CoordinatorEntity[EufyCleanCoordinator], ButtonEntity):

    def __init__(self, coordinator: EufyCleanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.device_id}_resume_from_breakpoint"
        self._attr_name = "Resume from Breakpoint"
        self._attr_icon = "mdi:play-circle"
        self._attr_device_info = coordinator.device_info
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_visible_default = False

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(
            build_command("generic", dp_id=self.coordinator.dps_map.get("PAUSE_JOB", "156"), value=True)
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
        await self.coordinator.async_send_command(build_command(self._cmd))
