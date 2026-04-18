from __future__ import annotations

import copy
import logging
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api.commands import build_command
from .auto_entities import get_auto_switches
from .coordinator import EufyCleanCoordinator
from .descriptions.switch import (
    UNISETTING_SWITCH_DESCRIPTIONS,
    RoboVacUnisettingSwitchDescription,
)
from .typing_defs import EufyCleanConfigEntry

PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EufyCleanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup switch entities."""
    entities: list[SwitchEntity] = []

    for coordinator in config_entry.runtime_data.coordinators.values():
        _LOGGER.debug("Adding switch entities for %s", coordinator.device_name)

        if "STATION_STATUS" in coordinator.supported_dps:
            entities.append(
                DockSwitchEntity(
                    coordinator,
                    "auto_empty",
                    lambda cfg: cfg.get("collectdust_v2", {})
                    .get("sw", {})
                    .get("value", False),
                    set_collect_dust,
                    icon="mdi:delete-restore",
                )
            )

            entities.append(
                DockSwitchEntity(
                    coordinator,
                    "auto_wash",
                    lambda cfg: cfg.get("wash", {}).get("cfg", "CLOSE") == "STANDARD",
                    set_wash_cfg,
                    icon="mdi:water-sync",
                )
            )

        if "UNDISTURBED" in coordinator.supported_dps:
            entities.append(DoNotDisturbSwitchEntity(coordinator))

        if "UNSETTING" in coordinator.supported_dps:
            entities.append(ChildLockSwitchEntity(coordinator))
            entities.extend(
                UnisettingSwitch(coordinator, description)
                for description in UNISETTING_SWITCH_DESCRIPTIONS
            )

        entities.append(SmartModeSwitchEntity(coordinator))

        if "MEDIA_MANAGER" in coordinator.supported_dps:
            entities.append(MediaRecordingSwitchEntity(coordinator))

        entities.extend(get_auto_switches(coordinator))

        for schedule in coordinator.data.schedules:
            entities.append(ScheduleSwitchEntity(coordinator, schedule))

    async_add_entities(entities)


def set_collect_dust(cfg: dict[str, Any], val: bool) -> None:
    """Helper to set collect dust state in config dict."""
    if "collectdust_v2" not in cfg:
        cfg["collectdust_v2"] = {"sw": {"value": val}}
    else:
        if "sw" not in cfg["collectdust_v2"]:
            cfg["collectdust_v2"]["sw"] = {"value": val}
        else:
            cfg["collectdust_v2"]["sw"]["value"] = val


def set_wash_cfg(cfg: dict[str, Any], val: bool) -> None:
    """Helper to set wash state in config dict."""
    if "wash" not in cfg:
        cfg["wash"] = {"cfg": "STANDARD" if val else "CLOSE"}
    else:
        cfg["wash"]["cfg"] = "STANDARD" if val else "CLOSE"


def _current_dnd_schedule(coordinator: EufyCleanCoordinator) -> dict[str, int | bool]:
    """Return the current Do Not Disturb schedule from coordinator state."""
    data = coordinator.data
    return {
        "active": data.dnd_enabled,
        "begin_hour": data.dnd_start_hour,
        "begin_minute": data.dnd_start_minute,
        "end_hour": data.dnd_end_hour,
        "end_minute": data.dnd_end_minute,
    }


class DockSwitchEntity(CoordinatorEntity[EufyCleanCoordinator], SwitchEntity):
    """Switch for Dock/Station settings."""

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        id_suffix: str,
        getter: Callable[[dict[str, Any]], bool],
        setter: Callable[[dict[str, Any], bool], None],
        icon: str | None = None,
    ) -> None:
        """Initialize the dock switch entity."""
        super().__init__(coordinator)
        self._id_suffix = id_suffix
        self._getter = getter
        self._setter = setter
        self._attr_unique_id = f"{coordinator.device_id}_{id_suffix}"
        self._attr_has_entity_name = True
        self._attr_translation_key = id_suffix
        self._attr_entity_category = EntityCategory.CONFIG
        if icon:
            self._attr_icon = icon

        self._attr_device_info = coordinator.device_info
        self._attr_entity_registry_visible_default = False

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        cfg = self.coordinator.data.dock_auto_cfg
        if not cfg:
            return None
        try:
            return self._getter(cfg)
        except Exception as e:
            _LOGGER.debug("Error getting switch state for %s: %s", self._id_suffix, e)
            return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._set_state(False)

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return super().available and bool(self.coordinator.data.dock_auto_cfg)

    async def _set_state(self, state: bool) -> None:
        """Send command to update config."""
        cfg = copy.deepcopy(self.coordinator.data.dock_auto_cfg)
        self._setter(cfg, state)

        command = build_command(
            "set_auto_cfg", dps_map=self.coordinator.dps_map, cfg=cfg
        )
        await self.coordinator.async_send_command(command)


class ChildLockSwitchEntity(CoordinatorEntity[EufyCleanCoordinator], SwitchEntity):
    """Switch for the device child lock setting."""

    def __init__(self, coordinator: EufyCleanCoordinator) -> None:
        """Initialize the child lock switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_child_lock"
        self._attr_has_entity_name = True
        self._attr_translation_key = "child_lock"
        self._attr_icon = "mdi:lock-outline"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = coordinator.device_info
        self._attr_entity_registry_enabled_default = False
        self._attr_entity_registry_visible_default = False

    @property
    def is_on(self) -> bool | None:
        """Return true if child lock is enabled."""
        return self.coordinator.data.child_lock

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return (
            super().available and "child_lock" in self.coordinator.data.received_fields
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable child lock."""
        await self._set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable child lock."""
        await self._set_state(False)

    async def _set_state(self, state: bool) -> None:
        """Send child lock command and optimistically update state."""
        command = build_command("set_child_lock", active=state)
        await self.coordinator.async_send_command(command)
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, child_lock=state)
        )


class DoNotDisturbSwitchEntity(CoordinatorEntity[EufyCleanCoordinator], SwitchEntity):
    """Switch for the Do Not Disturb schedule."""

    def __init__(self, coordinator: EufyCleanCoordinator) -> None:
        """Initialize the DND switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_do_not_disturb"
        self._attr_has_entity_name = True
        self._attr_translation_key = "do_not_disturb"
        self._attr_icon = "mdi:minus-circle-off-outline"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = coordinator.device_info
        self._attr_entity_registry_enabled_default = False
        self._attr_entity_registry_visible_default = False

    @property
    def is_on(self) -> bool | None:
        """Return true if DND is enabled."""
        return self.coordinator.data.dnd_enabled

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return (
            super().available
            and "do_not_disturb" in self.coordinator.data.received_fields
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the current DND schedule."""
        data = self.coordinator.data
        return {
            "start_time": f"{data.dnd_start_hour:02d}:{data.dnd_start_minute:02d}",
            "end_time": f"{data.dnd_end_hour:02d}:{data.dnd_end_minute:02d}",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable Do Not Disturb."""
        await self._set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable Do Not Disturb."""
        await self._set_state(False)

    async def _set_state(self, state: bool) -> None:
        """Send DND command and optimistically update state."""
        schedule = _current_dnd_schedule(self.coordinator)
        command = build_command(
            "set_do_not_disturb",
            active=state,
            begin_hour=int(schedule["begin_hour"]),
            begin_minute=int(schedule["begin_minute"]),
            end_hour=int(schedule["end_hour"]),
            end_minute=int(schedule["end_minute"]),
        )
        await self.coordinator.async_send_command(command)
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, dnd_enabled=state)
        )


class SmartModeSwitchEntity(CoordinatorEntity[EufyCleanCoordinator], SwitchEntity):
    """Switch for the smart mode cleaning setting."""

    def __init__(self, coordinator: EufyCleanCoordinator) -> None:
        """Initialize the smart mode switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_smart_mode"
        self._attr_has_entity_name = True
        self._attr_translation_key = "smart_mode"
        self._attr_icon = "mdi:brain"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = coordinator.device_info
        self._attr_entity_registry_enabled_default = False
        self._attr_entity_registry_visible_default = False

    @property
    def is_on(self) -> bool | None:
        """Return true if smart mode is enabled."""
        return self.coordinator.data.smart_mode

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return (
            super().available and "smart_mode" in self.coordinator.data.received_fields
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable smart mode."""
        await self._set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable smart mode."""
        await self._set_state(False)

    async def _set_state(self, state: bool) -> None:
        """Send smart mode command and optimistically update state."""
        command = build_command(
            "set_smart_mode", dps_map=self.coordinator.dps_map, active=state
        )
        await self.coordinator.async_send_command(command)
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, smart_mode=state)
        )


class UnisettingSwitch(CoordinatorEntity[EufyCleanCoordinator], SwitchEntity):

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        description: RoboVacUnisettingSwitchDescription,
    ) -> None:
        super().__init__(coordinator)
        self._field_name = description.field_name
        self._attr_unique_id = f"{coordinator.device_id}_{description.field_name}"
        self._attr_has_entity_name = True
        self._attr_translation_key = description.field_name
        self._attr_icon = description.icon
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = coordinator.device_info
        self._attr_entity_registry_enabled_default = False
        self._attr_entity_registry_visible_default = False

    @property
    def is_on(self) -> bool | None:
        return getattr(self.coordinator.data, self._field_name, None)

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._field_name in self.coordinator.data.received_fields
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, value: bool) -> None:
        cmd = build_command(
            "set_unisetting",
            dps_map=self.coordinator.dps_map,
            field=self._field_name,
            value=value,
            current_state=self.coordinator.data,
        )
        await self.coordinator.async_send_command(cmd)


class MediaRecordingSwitchEntity(CoordinatorEntity[EufyCleanCoordinator], SwitchEntity):

    def __init__(self, coordinator: EufyCleanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_media_recording"
        self._attr_has_entity_name = True
        self._attr_translation_key = "media_recording"
        self._attr_icon = "mdi:record-rec"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = coordinator.device_info
        self._attr_entity_registry_enabled_default = False
        self._attr_entity_registry_visible_default = False

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.media_recording

    @property
    def available(self) -> bool:
        return (
            super().available
            and "media_status" in self.coordinator.data.received_fields
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_state(False)

    async def _set_state(self, state: bool) -> None:
        cmd = build_command(
            "media_record", dps_map=self.coordinator.dps_map, start=state
        )
        await self.coordinator.async_send_command(cmd)
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, media_recording=state)
        )


class ScheduleSwitchEntity(CoordinatorEntity[EufyCleanCoordinator], SwitchEntity):

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        schedule: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._schedule_id: int = schedule.get("id", 0)
        label = schedule.get("action_label", f"Schedule {self._schedule_id}")
        self._attr_unique_id = f"{coordinator.device_id}_schedule_{self._schedule_id}"
        self._attr_has_entity_name = True
        self._attr_name = f"Schedule: {label}"
        self._attr_icon = "mdi:calendar-clock"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        for s in self.coordinator.data.schedules:
            if s.get("id") == self._schedule_id:
                return s.get("enabled", False)
        return None

    @property
    def available(self) -> bool:
        return super().available and any(
            s.get("id") == self._schedule_id for s in self.coordinator.data.schedules
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        cmd = build_command(
            "timer_open",
            dps_map=self.coordinator.dps_map,
            timer_id=self._schedule_id,
        )
        await self.coordinator.async_send_command(cmd)

    async def async_turn_off(self, **kwargs: Any) -> None:
        cmd = build_command(
            "timer_close",
            dps_map=self.coordinator.dps_map,
            timer_id=self._schedule_id,
        )
        await self.coordinator.async_send_command(cmd)
