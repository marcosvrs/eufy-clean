from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .auto_entities import get_auto_sensors
from .const import ACCESSORY_MAX_LIFE, DOMAIN
from .coordinator import EufyCleanCoordinator, VacuumState

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
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensor entities."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: list[EufyCleanCoordinator] = data["coordinators"]

    entities = []

    for coordinator in coordinators:
        _LOGGER.debug("Adding sensors for %s", coordinator.device_name)

        # Core sensors — always created
        entities.append(
            RoboVacSensor(
                coordinator,
                "error_message",
                "Error Message",
                lambda s: s.error_message,
                device_class=None,
                unit=None,
                state_class=None,
                icon="mdi:alert-circle-outline",
                category=EntityCategory.DIAGNOSTIC,
                extra_state_attributes_fn=lambda s: {
                    "all_codes": s.error_codes_all,
                    "all_messages": s.error_messages_all,
                },
            )
        )

        entities.append(
            RoboVacSensor(
                coordinator,
                "task_status",
                "Task Status",
                lambda s: s.task_status,
                device_class=None,
                unit=None,
                state_class=None,
                icon="mdi:robot-vacuum",
                category=EntityCategory.DIAGNOSTIC,
            )
        )

        entities.append(
            RoboVacSensor(
                coordinator,
                "work_mode",
                "Work Mode",
                lambda s: s.work_mode,
                device_class=None,
                unit=None,
                state_class=None,
                icon="mdi:cog-outline",
                category=EntityCategory.DIAGNOSTIC,
            )
        )

        entities.append(
                RoboVacSensor(
                    coordinator,
                    "active_cleaning_target",
                "Active Cleaning Target",
                _active_rooms_value,
                device_class=None,
                unit=None,
                state_class=None,
                icon="mdi:floor-plan",
                category=EntityCategory.DIAGNOSTIC,
                    availability_fn=_active_rooms_available,
                    enabled_default=True,
                    extra_state_attributes_fn=lambda s: {
                        "room_ids": s.active_room_ids,
                        "scene_id": s.current_scene_id,
                    "scene_name": s.current_scene_name,
                    "zone_count": s.active_zone_count,
                },
            )
        )

        entities.append(
            RoboVacSensor(
                coordinator,
                "robot_position_x",
                "Robot Position X (raw)",
                lambda s: s.robot_position_x,
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:crosshairs-gps",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "robot_position" in s.received_fields,
            )
        )

        entities.append(
            RoboVacSensor(
                coordinator,
                "robot_position_y",
                "Robot Position Y (raw)",
                lambda s: s.robot_position_y,
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:crosshairs-gps",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "robot_position" in s.received_fields,
            )
        )

        # Analysis diagnostics (DPS 179 AnalysisResponse)
        entities.extend([
            RoboVacSensor(
                coordinator,
                "robotapp_state",
                "Robot App State",
                lambda s: s.robotapp_state or None,
                icon="mdi:state-machine",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "robotapp_state" in s.received_fields,
            ),
            RoboVacSensor(
                coordinator,
                "motion_state",
                "Motion State",
                lambda s: s.motion_state or None,
                icon="mdi:motion",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "motion_state" in s.received_fields,
            ),
            RoboVacSensor(
                coordinator,
                "battery_real_level",
                "Battery Real Level",
                lambda s: s.battery_real_level,
                unit=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:battery-heart-variant",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "battery_real_level" in s.received_fields,
            ),
            RoboVacSensor(
                coordinator,
                "battery_voltage",
                "Battery Voltage",
                lambda s: s.battery_voltage,
                unit="mV",
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:flash-triangle-outline",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "battery_voltage" in s.received_fields,
            ),
            RoboVacSensor(
                coordinator,
                "battery_current",
                "Battery Current",
                lambda s: s.battery_current,
                unit="mA",
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:current-dc",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "battery_current" in s.received_fields,
            ),
            RoboVacSensor(
                coordinator,
                "battery_temperature",
                "Battery Temperature",
                lambda s: s.battery_temperature,
                device_class=SensorDeviceClass.TEMPERATURE,
                unit="°C",
                state_class=SensorStateClass.MEASUREMENT,
                icon="mdi:thermometer",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "battery_temperature" in s.received_fields,
                suggested_display_precision=1,
            ),
        ])

        # WorkStatus extended sensors (T9, gated by received_fields)
        entities.extend([
            RoboVacSensor(
                coordinator,
                "mapping_state",
                "Mapping State",
                lambda s: s.mapping_state,
                icon="mdi:map",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "mapping_state" in s.received_fields,
            ),
            RoboVacSensor(
                coordinator,
                "mapping_mode",
                "Mapping Mode",
                lambda s: s.mapping_mode,
                icon="mdi:map-clock",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "mapping_state" in s.received_fields,
            ),
            RoboVacSensor(
                coordinator,
                "cruise_state",
                "Cruise State",
                lambda s: s.cruise_state,
                icon="mdi:navigation",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "cruise_state" in s.received_fields,
            ),
            RoboVacSensor(
                coordinator,
                "cruise_mode",
                "Cruise Mode",
                lambda s: s.cruise_mode,
                icon="mdi:navigation-variant",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "cruise_state" in s.received_fields,
            ),
            RoboVacSensor(
                coordinator,
                "smart_follow_state",
                "Smart Follow State",
                lambda s: s.smart_follow_state,
                icon="mdi:motion-sensor",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "smart_follow_state" in s.received_fields,
            ),
            RoboVacSensor(
                coordinator,
                "station_work_status",
                "Station Work Status",
                lambda s: s.station_work_status,
                icon="mdi:robot-vacuum",
                category=EntityCategory.DIAGNOSTIC,
                availability_fn=lambda s: "station_work_status" in s.received_fields,
            ),
        ])

        # Cleaning statistics sensors
        if "CLEANING_STATISTICS" in coordinator.supported_dps:
            entities.append(
                RoboVacSensor(
                    coordinator,
                    "cleaning_time",
                    "Cleaning Time",
                    lambda s: s.cleaning_time,
                    device_class=SensorDeviceClass.DURATION,
                    unit="s",
                    state_class=SensorStateClass.MEASUREMENT,
                    icon="mdi:clock-outline",
                    availability_fn=lambda s: "cleaning_stats" in s.received_fields,
                )
            )

            entities.append(
                RoboVacSensor(
                    coordinator,
                    "cleaning_area",
                    "Cleaning Area",
                    lambda s: s.cleaning_area,
                    device_class=None,
                    unit="m²",
                    state_class=SensorStateClass.MEASUREMENT,
                    icon="mdi:floor-plan",
                    availability_fn=lambda s: "cleaning_stats" in s.received_fields,
                )
            )

            entities.extend([
                RoboVacSensor(
                    coordinator,
                    "total_cleaning_time",
                    "Total Cleaning Time",
                    lambda s: s.total_cleaning_time,
                    unit="s",
                    icon="mdi:timer",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "total_stats" in s.received_fields,
                ),
                RoboVacSensor(
                    coordinator,
                    "total_cleaning_area",
                    "Total Cleaning Area",
                    lambda s: s.total_cleaning_area,
                    unit="m²",
                    icon="mdi:floor-plan",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "total_stats" in s.received_fields,
                ),
                RoboVacSensor(
                    coordinator,
                    "total_cleaning_count",
                    "Total Cleaning Count",
                    lambda s: s.total_cleaning_count,
                    icon="mdi:counter",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "total_stats" in s.received_fields,
                ),
                RoboVacSensor(
                    coordinator,
                    "user_total_cleaning_time",
                    "User Total Cleaning Time",
                    lambda s: s.user_total_cleaning_time,
                    unit="s",
                    icon="mdi:timer-outline",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "user_total_stats" in s.received_fields,
                ),
                RoboVacSensor(
                    coordinator,
                    "user_total_cleaning_area",
                    "User Total Cleaning Area",
                    lambda s: s.user_total_cleaning_area,
                    unit="m²",
                    icon="mdi:floor-plan",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "user_total_stats" in s.received_fields,
                ),
                RoboVacSensor(
                    coordinator,
                    "user_total_cleaning_count",
                    "User Total Cleaning Count",
                    lambda s: s.user_total_cleaning_count,
                    icon="mdi:counter",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "user_total_stats" in s.received_fields,
                ),
            ])

        # Station/dock sensors
        if "STATION_STATUS" in coordinator.supported_dps:
            entities.append(
                RoboVacSensor(
                    coordinator,
                    "water_level",
                    "Water Level",
                    lambda s: s.station_clean_water,
                    device_class=None,
                    unit=PERCENTAGE,
                    state_class=SensorStateClass.MEASUREMENT,
                    availability_fn=lambda s: "station_clean_water"
                    in s.received_fields,
                )
            )

            entities.append(
                RoboVacSensor(
                    coordinator,
                    "waste_water_level",
                    "Waste Water Level",
                    lambda s: s.station_waste_water,
                    device_class=None,
                    unit=PERCENTAGE,
                    state_class=SensorStateClass.MEASUREMENT,
                    icon="mdi:water-minus",
                    availability_fn=lambda s: "dock_status" in s.received_fields,
                )
            )

            entities.append(
                RoboVacSensor(
                    coordinator,
                    "dock_status",
                    "Dock Status",
                    lambda s: s.dock_status,
                    device_class=None,
                    unit=None,
                    state_class=None,
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "dock_status" in s.received_fields,
                )
            )

        # Active map sensor
        if "MULTI_MAP_MANAGE" in coordinator.supported_dps:
            entities.append(
                RoboVacSensor(
                    coordinator,
                    "active_map",
                    "Active Map",
                    lambda s: s.map_id,
                    device_class=None,
                    unit=None,
                    state_class=None,
                    icon="mdi:map-marker-path",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "map_id" in s.received_fields,
                )
            )

        # WiFi/signal sensors
        if "UNSETTING" in coordinator.supported_dps:
            entities.append(
                RoboVacSensor(
                    coordinator,
                    "wifi_signal",
                    "WiFi Signal Strength",
                    lambda s: s.wifi_signal,
                    device_class=SensorDeviceClass.SIGNAL_STRENGTH,
                    unit=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
                    state_class=SensorStateClass.MEASUREMENT,
                    icon="mdi:wifi",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "wifi_signal" in s.received_fields,
                )
            )

            # Unistate sensors (T14)
            entities.extend([
                RoboVacSensor(
                    coordinator,
                    "mop_state",
                    "Mop State",
                    lambda s: s.mop_state,
                    icon="mdi:mop",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "mop_state" in s.received_fields,
                ),
                RoboVacSensor(
                    coordinator,
                    "clean_strategy_version",
                    "Clean Strategy Version",
                    lambda s: s.clean_strategy_version,
                    icon="mdi:strategy",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "clean_strategy_version" in s.received_fields,
                ),
                RoboVacSensor(
                    coordinator,
                    "live_map_state_bits",
                    "Live Map State",
                    lambda s: s.live_map_state_bits,
                    icon="mdi:map-clock",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "live_map_state_bits" in s.received_fields,
                ),
            ])

            # WiFi data sensors (T15)
            entities.extend([
                RoboVacSensor(
                    coordinator,
                    "wifi_frequency",
                    "WiFi Frequency",
                    lambda s: "5 GHz" if s.wifi_frequency == 1 else "2.4 GHz" if s.wifi_frequency == 0 else str(s.wifi_frequency),
                    icon="mdi:wifi",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "wifi_frequency" in s.received_fields,
                ),
                RoboVacSensor(
                    coordinator,
                    "wifi_connection_result",
                    "WiFi Connection Result",
                    lambda s: "OK" if s.wifi_connection_result == 0 else "Password Error" if s.wifi_connection_result == 1 else str(s.wifi_connection_result),
                    icon="mdi:wifi-check",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "wifi_connection_result" in s.received_fields,
                ),
                RoboVacSensor(
                    coordinator,
                    "wifi_connection_timestamp",
                    "WiFi Connection Timestamp",
                    lambda s: s.wifi_connection_timestamp,
                    icon="mdi:clock-outline",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "wifi_connection_timestamp" in s.received_fields,
                ),
            ])

        # App/device info sensors
        if "APP_DEV_INFO" in coordinator.supported_dps:
            entities.append(
                RoboVacSensor(
                    coordinator,
                    "wifi_ssid",
                    "WiFi SSID",
                    lambda s: s.wifi_ssid or None,
                    icon="mdi:wifi",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "wifi_ssid" in s.received_fields,
                )
            )

            entities.append(
                RoboVacSensor(
                    coordinator,
                    "wifi_ip",
                    "IP Address",
                    lambda s: s.wifi_ip or None,
                    icon="mdi:ip-network",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "wifi_ip" in s.received_fields,
                )
            )

        if "MEDIA_MANAGER" in coordinator.supported_dps:
            entities.append(
                RoboVacSensor(
                    coordinator,
                    "last_capture",
                    "Last Capture",
                    lambda s: s.media_last_capture_path or None,
                    icon="mdi:camera",
                    category=EntityCategory.DIAGNOSTIC,
                    availability_fn=lambda s: "media_last_capture" in s.received_fields,
                )
            )

        # Accessory sensors
        if "ACCESSORIES_STATUS" in coordinator.supported_dps:
            accessories = [
                ("filter_usage", "Filter Remaining", "mdi:air-filter"),
                ("main_brush_usage", "Rolling Brush Remaining", "mdi:broom"),
                ("side_brush_usage", "Side Brush Remaining", "mdi:broom"),
                ("sensor_usage", "Sensor Remaining", "mdi:eye-outline"),
                ("scrape_usage", "Cleaning Tray Remaining", "mdi:wiper"),
                ("mop_usage", "Mopping Cloth Remaining", "mdi:water"),
            ]

            for attr, name, icon in accessories:
                def get_accessory_remaining(
                    state: VacuumState, a: str = attr
                ) -> int:
                    usage = getattr(state.accessories, a) or 0
                    max_life = ACCESSORY_MAX_LIFE.get(a, 0)
                    return max(0, max_life - usage)

                max_life_val = ACCESSORY_MAX_LIFE.get(attr, 0)

                def get_attributes(
                    state: VacuumState, a: str = attr, m: int = max_life_val
                ) -> dict[str, Any]:
                    usage = getattr(state.accessories, a) or 0
                    return {
                        "usage_hours": usage,
                        "total_life_hours": m,
                    }

                entities.append(
                    RoboVacSensor(
                        coordinator,
                        attr.replace("_usage", "_remaining"),
                        name,
                        get_accessory_remaining,
                        device_class=SensorDeviceClass.DURATION,
                        unit="h",
                        state_class=SensorStateClass.MEASUREMENT,
                        icon=icon,
                        category=EntityCategory.DIAGNOSTIC,
                        extra_state_attributes_fn=get_attributes,
                        availability_fn=lambda s: "accessories"
                        in s.received_fields,
                    )
                )

            consumables = [
                ("dustbag_usage", "Dustbag Usage", "mdi:delete"),
                (
                    "dirty_watertank_usage",
                    "Waste Water Tank Usage",
                    "mdi:water-alert",
                ),
                (
                    "dirty_waterfilter_usage",
                    "Water Filter Usage",
                    "mdi:water-check",
                ),
            ]

            for attr, name, icon in consumables:
                entities.append(
                    RoboVacSensor(
                        coordinator,
                        attr,
                        name,
                        lambda s, a=attr: getattr(s.accessories, a) or 0,
                        device_class=SensorDeviceClass.DURATION,
                        unit="h",
                        state_class=SensorStateClass.MEASUREMENT,
                        icon=icon,
                        category=EntityCategory.DIAGNOSTIC,
                        availability_fn=lambda s: "accessories"
                        in s.received_fields,
                    )
                )

        entities.append(
            RoboVacSensor(
                coordinator,
                "last_notification",
                "Last Notification",
                lambda s: s.notification_message or None,
                icon="mdi:bell",
                category=EntityCategory.DIAGNOSTIC,
                extra_state_attributes_fn=lambda s: {"codes": s.notification_codes},
                availability_fn=lambda s: "notification" in s.received_fields,
            )
        )

        # Auto-generated sensors from DPS catalog
        entities.extend(get_auto_sensors(coordinator))

    async_add_entities(entities)


class RoboVacSensor(CoordinatorEntity[EufyCleanCoordinator], SensorEntity):
    """Eufy Clean Sensor Entity."""

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        id_suffix: str,
        name_suffix: str,
        value_fn: Callable[[VacuumState], Any],
        device_class: SensorDeviceClass | None = None,
        unit: str | None = None,
        state_class: SensorStateClass | None = None,
        icon: str | None = None,
        category: EntityCategory | None = EntityCategory.DIAGNOSTIC,
        extra_state_attributes_fn: (
            Callable[[VacuumState], dict[str, Any]] | None
        ) = None,
        availability_fn: Callable[[VacuumState], bool] | None = None,
        enabled_default: bool = True,
        suggested_display_precision: int | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._value_fn = value_fn
        self._extra_attrs_fn = extra_state_attributes_fn
        self._availability_fn = availability_fn
        self._attr_unique_id = f"{coordinator.device_id}_{id_suffix}"

        # Use Home Assistant standard naming
        # This will prefix the device name to the entity name if the
        # device name is not in the entity name
        # Result: sensor.robovac_water_level (Safer, avoids collisions)
        self._attr_has_entity_name = True
        self._attr_name = name_suffix
        self._enabled_default = enabled_default
        self._attr_entity_registry_visible_default = False

        self._attr_device_info = coordinator.device_info

        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = category
        if icon:
            self._attr_icon = icon
        if suggested_display_precision is not None:
            self._attr_suggested_display_precision = suggested_display_precision

    @property
    def entity_registry_enabled_default(self) -> bool:
        if self._availability_fn is not None:
            return False
        return self._enabled_default

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        Checks coordinator availability and optional custom availability function.
        """
        if not super().available:
            return False
        if self._availability_fn is not None:
            return self._availability_fn(self.coordinator.data)
        return True

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self._value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return entity specific state attributes."""
        if self._extra_attrs_fn:
            return self._extra_attrs_fn(self.coordinator.data)
        return None
