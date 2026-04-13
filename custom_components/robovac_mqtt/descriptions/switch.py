from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class RoboVacUnisettingSwitchDescription:
    field_name: str
    icon: str


UNISETTING_SWITCH_DESCRIPTIONS: tuple[RoboVacUnisettingSwitchDescription, ...] = (
    RoboVacUnisettingSwitchDescription(field_name="ai_see", icon="mdi:eye"),
    RoboVacUnisettingSwitchDescription(field_name="pet_mode_sw", icon="mdi:paw"),
    RoboVacUnisettingSwitchDescription(
        field_name="poop_avoidance_sw",
        icon="mdi:emoticon-poop",
    ),
    RoboVacUnisettingSwitchDescription(field_name="live_photo_sw", icon="mdi:camera"),
    RoboVacUnisettingSwitchDescription(
        field_name="deep_mop_corner_sw",
        icon="mdi:broom",
    ),
    RoboVacUnisettingSwitchDescription(
        field_name="smart_follow_sw",
        icon="mdi:motion-sensor",
    ),
    RoboVacUnisettingSwitchDescription(
        field_name="cruise_continue_sw", icon="mdi:refresh"
    ),
    RoboVacUnisettingSwitchDescription(field_name="multi_map_sw", icon="mdi:map-plus"),
    RoboVacUnisettingSwitchDescription(
        field_name="suggest_restricted_zone_sw",
        icon="mdi:map-marker-off",
    ),
    RoboVacUnisettingSwitchDescription(
        field_name="water_level_sw",
        icon="mdi:water-check",
    ),
)

assert len(UNISETTING_SWITCH_DESCRIPTIONS) == 10
