from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .__init__ import EufyCleanConfigEntry
from .auto_entities import get_auto_binary_sensors
from .const import DOMAIN
from .coordinator import EufyCleanCoordinator
from .descriptions.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    RoboVacBinarySensorDescription,
)

PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EufyCleanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities from descriptions."""
    entities: list[BinarySensorEntity] = []
    for coordinator in config_entry.runtime_data.coordinators.values():
        _LOGGER.debug("Adding binary sensors for %s", coordinator.device_name)
        entities.extend(
            RoboVacBinarySensor(coordinator, description)
            for description in BINARY_SENSOR_DESCRIPTIONS
            if description.exists_fn(coordinator)
        )
        entities.extend(get_auto_binary_sensors(coordinator))
    async_add_entities(entities)


class RoboVacBinarySensor(CoordinatorEntity[EufyCleanCoordinator], BinarySensorEntity):
    """Eufy Clean Binary Sensor Entity."""

    _attr_has_entity_name = True
    _attr_entity_registry_visible_default = False

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        description: RoboVacBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"
        self._attr_translation_key = description.key
        self._attr_device_info = coordinator.device_info
        self._attr_entity_registry_enabled_default = (
            description.availability_fn is None
            and getattr(description, "enabled_default", True)
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
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.value_fn(self.coordinator.data)
