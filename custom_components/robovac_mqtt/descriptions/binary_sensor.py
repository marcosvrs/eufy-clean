from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

from ..models import VacuumState

# pyright: reportMissingImports=false


if TYPE_CHECKING:
    from ..coordinator import EufyCleanCoordinator


@dataclass(frozen=True, kw_only=True)
class RoboVacBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[VacuumState], bool | None] = field(default=lambda s: None)
    exists_fn: Callable[[EufyCleanCoordinator], bool] = field(default=lambda c: True)
    availability_fn: Callable[[VacuumState], bool] | None = None


BINARY_SENSOR_DESCRIPTIONS: tuple[RoboVacBinarySensorDescription, ...] = (
    RoboVacBinarySensorDescription(
        key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        entity_category=None,
        value_fn=lambda s: s.charging,
    ),
    RoboVacBinarySensorDescription(
        key="upgrading",
        icon="mdi:update",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.upgrading,
        availability_fn=lambda s: "upgrading" in s.received_fields,
    ),
    RoboVacBinarySensorDescription(
        key="relocating",
        icon="mdi:crosshairs-gps",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.relocating,
        availability_fn=lambda s: "relocating" in s.received_fields,
    ),
    RoboVacBinarySensorDescription(
        key="breakpoint_available",
        icon="mdi:map-marker-check",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.breakpoint_available,
        availability_fn=lambda s: "breakpoint_available" in s.received_fields,
    ),
    RoboVacBinarySensorDescription(
        key="roller_brush_cleaning",
        icon="mdi:brush",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.roller_brush_cleaning,
        availability_fn=lambda s: "roller_brush_cleaning" in s.received_fields,
    ),
    RoboVacBinarySensorDescription(
        key="water_tank_clear_adding",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.water_tank_clear_adding,
        availability_fn=lambda s: "water_tank_state" in s.received_fields,
    ),
    RoboVacBinarySensorDescription(
        key="water_tank_waste_recycling",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.water_tank_waste_recycling,
        availability_fn=lambda s: "water_tank_state" in s.received_fields,
    ),
    RoboVacBinarySensorDescription(
        key="dock_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.dock_connected,
        availability_fn=lambda s: "dock_connected" in s.received_fields,
    ),
    RoboVacBinarySensorDescription(
        key="dust_collect_result",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.dust_collect_result,
        availability_fn=lambda s: "dust_collect_stats" in s.received_fields,
    ),
    RoboVacBinarySensorDescription(
        key="mop_holder_l",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "UNSETTING" in c.supported_dps,
        value_fn=lambda s: s.mop_holder_state_l,
        availability_fn=lambda s: "mop_holder_state_l" in s.received_fields,
    ),
    RoboVacBinarySensorDescription(
        key="mop_holder_r",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "UNSETTING" in c.supported_dps,
        value_fn=lambda s: s.mop_holder_state_r,
        availability_fn=lambda s: "mop_holder_state_r" in s.received_fields,
    ),
    RoboVacBinarySensorDescription(
        key="map_valid",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "UNSETTING" in c.supported_dps,
        value_fn=lambda s: s.map_valid,
        availability_fn=lambda s: "map_valid" in s.received_fields,
    ),
    RoboVacBinarySensorDescription(
        key="live_map",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "UNSETTING" in c.supported_dps,
        value_fn=lambda s: bool(s.live_map_state_bits),
        availability_fn=lambda s: "live_map_state_bits" in s.received_fields,
    ),
    RoboVacBinarySensorDescription(
        key="mop_state",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "UNSETTING" in c.supported_dps,
        value_fn=lambda s: s.mop_state,
        availability_fn=lambda s: "mop_state" in s.received_fields,
    ),
)

assert len(BINARY_SENSOR_DESCRIPTIONS) == 14
