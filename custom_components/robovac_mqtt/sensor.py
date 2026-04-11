from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .__init__ import EufyCleanConfigEntry
from .auto_entities import get_auto_sensors
from .const import DOMAIN
from .coordinator import EufyCleanCoordinator
from .descriptions.sensor import SENSOR_DESCRIPTIONS, RoboVacSensorDescription
from .models import VacuumState

PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)


def _active_rooms_value(state: VacuumState) -> str | None:
    """Return a display label for the current active cleaning target."""
    if state.active_room_names:
        return state.active_room_names
    if state.current_scene_name:
        return state.current_scene_name
    if state.active_zone_count:
        suffix = "" if state.active_zone_count == 1 else "s"
        return f"{state.active_zone_count} zone{suffix}"
    return None


def _active_rooms_available(state: VacuumState) -> bool:
    """Return whether any active cleaning target is currently known."""
    return bool(
        state.active_room_ids
        or state.current_scene_id
        or state.current_scene_name
        or state.active_zone_count
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EufyCleanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from descriptions."""
    entities: list[SensorEntity] = []
    for coordinator in config_entry.runtime_data.coordinators.values():
        _LOGGER.debug("Adding sensors for %s", coordinator.device_name)
        entities.extend(
            RoboVacSensor(coordinator, description)
            for description in SENSOR_DESCRIPTIONS
            if description.exists_fn(coordinator)
        )
        entities.extend(get_auto_sensors(coordinator))
    async_add_entities(entities)


class RoboVacSensor(CoordinatorEntity[EufyCleanCoordinator], SensorEntity):
    """Eufy Clean Sensor Entity."""

    _attr_has_entity_name = True
    _attr_entity_registry_visible_default = False

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        description: RoboVacSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"
        self._attr_name = description.name
        self._attr_device_info = coordinator.device_info
        self._attr_entity_registry_enabled_default = (
            description.availability_fn is None and description.enabled_default
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not super().available:
            return False
        if self.entity_description.availability_fn is not None:
            return self.entity_description.availability_fn(self.coordinator.data)
        return True

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return entity specific state attributes."""
        fn = self.entity_description.extra_state_attributes_fn
        if fn:
            return fn(self.coordinator.data)
        return None
