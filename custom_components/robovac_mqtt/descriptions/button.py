from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.const import EntityCategory

from ..proto.cloud.consumable_pb2 import ConsumableRequest

# pyright: reportMissingImports=false


if TYPE_CHECKING:
    from ..coordinator import EufyCleanCoordinator


@dataclass(frozen=True, kw_only=True)
class RoboVacButtonDescription:
    key: str
    command: str
    icon: str | None = None
    exists_fn: Callable[[EufyCleanCoordinator], bool] = field(default=lambda c: True)
    entity_category: EntityCategory | None = None


@dataclass(frozen=True, kw_only=True)
class RoboVacResetButtonDescription:
    key: str
    consumable_type: int
    icon: str
    exists_fn: Callable[[EufyCleanCoordinator], bool] = field(default=lambda c: True)
    entity_category: EntityCategory | None = EntityCategory.CONFIG


DOCK_BUTTON_DESCRIPTIONS: tuple[RoboVacButtonDescription, ...] = (
    RoboVacButtonDescription(
        key="dry_mop",
        command="go_dry",
        exists_fn=lambda c: "STATION_STATUS" in c.supported_dps,
    ),
    RoboVacButtonDescription(
        key="wash_mop",
        command="go_selfcleaning",
        exists_fn=lambda c: "STATION_STATUS" in c.supported_dps,
    ),
    RoboVacButtonDescription(
        key="empty_dust_bin",
        command="collect_dust",
        exists_fn=lambda c: "STATION_STATUS" in c.supported_dps,
    ),
    RoboVacButtonDescription(
        key="stop_dry_mop",
        command="stop_dry",
        exists_fn=lambda c: "STATION_STATUS" in c.supported_dps,
    ),
)

GENERIC_BUTTON_DESCRIPTIONS: tuple[RoboVacButtonDescription, ...] = (
    RoboVacButtonDescription(
        key="stop_return",
        command="stop_gohome",
        icon="mdi:home-off",
    ),
    RoboVacButtonDescription(
        key="map_then_clean",
        command="mapping_then_clean",
        icon="mdi:map-plus",
    ),
    RoboVacButtonDescription(
        key="global_cruise",
        command="start_global_cruise",
        icon="mdi:map-marker-path",
    ),
    RoboVacButtonDescription(
        key="stop_smart_follow",
        command="stop_smart_follow",
        icon="mdi:walk",
    ),
)

RESET_BUTTON_DESCRIPTIONS: tuple[RoboVacResetButtonDescription, ...] = (
    RoboVacResetButtonDescription(
        key="reset_filter",
        consumable_type=ConsumableRequest.FILTER_MESH,
        icon="mdi:air-filter",
        exists_fn=lambda c: "ACCESSORIES_STATUS" in c.supported_dps,
    ),
    RoboVacResetButtonDescription(
        key="reset_main_brush",
        consumable_type=ConsumableRequest.ROLLING_BRUSH,
        icon="mdi:broom",
        exists_fn=lambda c: "ACCESSORIES_STATUS" in c.supported_dps,
    ),
    RoboVacResetButtonDescription(
        key="reset_side_brush",
        consumable_type=ConsumableRequest.SIDE_BRUSH,
        icon="mdi:broom",
        exists_fn=lambda c: "ACCESSORIES_STATUS" in c.supported_dps,
    ),
    RoboVacResetButtonDescription(
        key="reset_sensors",
        consumable_type=ConsumableRequest.SENSOR,
        icon="mdi:eye-outline",
        exists_fn=lambda c: "ACCESSORIES_STATUS" in c.supported_dps,
    ),
    RoboVacResetButtonDescription(
        key="reset_scrape",
        consumable_type=ConsumableRequest.SCRAPE,
        icon="mdi:wiper",
        exists_fn=lambda c: "ACCESSORIES_STATUS" in c.supported_dps,
    ),
    RoboVacResetButtonDescription(
        key="reset_mop",
        consumable_type=ConsumableRequest.MOP,
        icon="mdi:water",
        exists_fn=lambda c: "ACCESSORIES_STATUS" in c.supported_dps,
    ),
)

MEDIA_BUTTON_DESCRIPTIONS: tuple[RoboVacButtonDescription, ...] = (
    RoboVacButtonDescription(
        key="media_capture",
        command="media_capture",
        icon="mdi:camera",
        exists_fn=lambda c: "MEDIA_MANAGER" in c.supported_dps,
    ),
)

assert (
    len(DOCK_BUTTON_DESCRIPTIONS)
    + len(GENERIC_BUTTON_DESCRIPTIONS)
    + len(RESET_BUTTON_DESCRIPTIONS)
    + len(MEDIA_BUTTON_DESCRIPTIONS)
    == 15
)
