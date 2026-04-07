from __future__ import annotations

import logging
from collections.abc import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .auto_entities import get_auto_binary_sensors
from .const import DOMAIN
from .coordinator import EufyCleanCoordinator, VacuumState

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup binary sensor entities."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: list[EufyCleanCoordinator] = data["coordinators"]

    entities = []

    for coordinator in coordinators:
        _LOGGER.debug("Adding binary sensors for %s", coordinator.device_name)

        entities.append(
            RoboVacBinarySensor(
                coordinator,
                "charging",
                "Charging",
                lambda s: s.charging,
                device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            )
        )

        # WorkStatus binary sensors (T9, gated by received_fields)
        for id_suffix, name, bs_field, icon in [
            ("upgrading", "Upgrading", "upgrading", "mdi:update"),
            ("relocating", "Relocating", "relocating", "mdi:crosshairs-gps"),
            ("breakpoint_available", "Breakpoint Available", "breakpoint_available", "mdi:map-marker-check"),
            ("roller_brush_cleaning", "Roller Brush Cleaning", "roller_brush_cleaning", "mdi:brush"),
        ]:
            entities.append(
                RoboVacBinarySensor(
                    coordinator,
                    id_suffix,
                    name,
                    lambda s, f=bs_field: getattr(s, f),
                    availability_fn=lambda s, f=bs_field: f in s.received_fields,
                )
            )

        # Unistate binary sensors (T14)
        if "UNSETTING" in coordinator.supported_dps:
            for id_suffix, name, bs_field in [
                ("mop_holder_l", "Mop Holder Left", "mop_holder_state_l"),
                ("mop_holder_r", "Mop Holder Right", "mop_holder_state_r"),
                ("map_valid", "Map Valid", "map_valid"),
                ("live_map", "Live Map", "live_map_state_bits"),
            ]:
                entities.append(
                    RoboVacBinarySensor(
                        coordinator,
                        id_suffix,
                        name,
                        lambda s, f=bs_field: getattr(s, f, False),
                        availability_fn=lambda s, f=bs_field: f in s.received_fields,
                    )
                )

        entities.extend(get_auto_binary_sensors(coordinator))

    async_add_entities(entities)


class RoboVacBinarySensor(CoordinatorEntity[EufyCleanCoordinator], BinarySensorEntity):
    """Eufy Clean Binary Sensor Entity."""

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        id_suffix: str,
        name_suffix: str,
        value_fn: Callable[[VacuumState], bool],
        device_class: BinarySensorDeviceClass | None = None,
        category: EntityCategory | None = EntityCategory.DIAGNOSTIC,
        availability_fn: Callable[[VacuumState], bool] | None = None,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._value_fn = value_fn
        self._availability_fn = availability_fn
        self._attr_unique_id = f"{coordinator.device_id}_{id_suffix}"
        self._attr_has_entity_name = True
        self._attr_name = name_suffix
        self._attr_device_info = coordinator.device_info
        self._attr_device_class = device_class
        self._attr_entity_category = category
        self._attr_entity_registry_visible_default = False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not super().available:
            return False
        if self._availability_fn is not None:
            return self._availability_fn(self.coordinator.data)
        return True

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._value_fn(self.coordinator.data)
