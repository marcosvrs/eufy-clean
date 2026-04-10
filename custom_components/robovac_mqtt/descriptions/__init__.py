"""EntityDescription dataclasses for robovac_mqtt platforms."""

from .binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    RoboVacBinarySensorDescription,
)
from .button import (
    DOCK_BUTTON_DESCRIPTIONS,
    GENERIC_BUTTON_DESCRIPTIONS,
    MEDIA_BUTTON_DESCRIPTIONS,
    RESET_BUTTON_DESCRIPTIONS,
    RoboVacButtonDescription,
    RoboVacResetButtonDescription,
)
from .sensor import SENSOR_DESCRIPTIONS, RoboVacSensorDescription
from .switch import (
    UNISETTING_SWITCH_DESCRIPTIONS,
    RoboVacUnisettingSwitchDescription,
)

__all__ = [
    "BINARY_SENSOR_DESCRIPTIONS",
    "DOCK_BUTTON_DESCRIPTIONS",
    "GENERIC_BUTTON_DESCRIPTIONS",
    "MEDIA_BUTTON_DESCRIPTIONS",
    "RESET_BUTTON_DESCRIPTIONS",
    "SENSOR_DESCRIPTIONS",
    "UNISETTING_SWITCH_DESCRIPTIONS",
    "RoboVacBinarySensorDescription",
    "RoboVacButtonDescription",
    "RoboVacResetButtonDescription",
    "RoboVacSensorDescription",
    "RoboVacUnisettingSwitchDescription",
]
