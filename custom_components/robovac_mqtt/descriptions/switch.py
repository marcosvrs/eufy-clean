from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class RoboVacUnisettingSwitchDescription:
    field_name: str
    name: str
    icon: str


UNISETTING_SWITCH_DESCRIPTIONS: tuple[RoboVacUnisettingSwitchDescription, ...] = (
    RoboVacUnisettingSwitchDescription(
        field_name="ai_see", name="AI See", icon="mdi:eye"
    ),
    RoboVacUnisettingSwitchDescription(
        field_name="pet_mode_sw", name="Pet Mode", icon="mdi:paw"
    ),
    RoboVacUnisettingSwitchDescription(
        field_name="poop_avoidance_sw",
        name="Poop Avoidance",
        icon="mdi:emoticon-poop",
    ),
    RoboVacUnisettingSwitchDescription(
        field_name="live_photo_sw", name="Live Photo", icon="mdi:camera"
    ),
    RoboVacUnisettingSwitchDescription(
        field_name="deep_mop_corner_sw",
        name="Deep Mop Corner",
        icon="mdi:broom",
    ),
    RoboVacUnisettingSwitchDescription(
        field_name="smart_follow_sw",
        name="Smart Follow",
        icon="mdi:motion-sensor",
    ),
    RoboVacUnisettingSwitchDescription(
        field_name="cruise_continue_sw", name="Cruise Continue", icon="mdi:refresh"
    ),
    RoboVacUnisettingSwitchDescription(
        field_name="multi_map_sw", name="Multi Map", icon="mdi:map-plus"
    ),
    RoboVacUnisettingSwitchDescription(
        field_name="suggest_restricted_zone_sw",
        name="Suggest Restricted Zone",
        icon="mdi:map-marker-off",
    ),
    RoboVacUnisettingSwitchDescription(
        field_name="water_level_sw",
        name="Water Level Monitor",
        icon="mdi:water-check",
    ),
)

assert len(UNISETTING_SWITCH_DESCRIPTIONS) == 10
