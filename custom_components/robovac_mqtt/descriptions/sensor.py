from __future__ import annotations

# pyright: reportMissingImports=false

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
)

from ..const import ACCESSORY_MAX_LIFE
from ..models import VacuumState

if TYPE_CHECKING:
    from ..coordinator import EufyCleanCoordinator


@dataclass(frozen=True, kw_only=True)
class RoboVacSensorDescription(SensorEntityDescription):
    value_fn: Callable[[VacuumState], Any] = field(default=lambda s: None)
    exists_fn: Callable[[EufyCleanCoordinator], bool] = field(default=lambda c: True)
    availability_fn: Callable[[VacuumState], bool] | None = None
    extra_state_attributes_fn: Callable[[VacuumState], dict[str, Any]] | None = None
    enabled_default: bool = True


def _make_accessory_remaining_desc(
    attr: str, name: str, icon: str
) -> RoboVacSensorDescription:
    key = attr.replace("_usage", "_remaining")
    max_life = ACCESSORY_MAX_LIFE.get(attr, 0)
    return RoboVacSensorDescription(
        key=key,
        name=name,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="h",
        state_class=SensorStateClass.MEASUREMENT,
        icon=icon,
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "ACCESSORIES_STATUS" in c.supported_dps,
        value_fn=lambda s, a=attr, m=max_life: max(0, m - (getattr(s.accessories, a) or 0)),
        extra_state_attributes_fn=lambda s, a=attr, m=max_life: {
            "usage_hours": getattr(s.accessories, a) or 0,
            "total_life_hours": m,
        },
        availability_fn=lambda s: "accessories" in s.received_fields,
    )


def _make_consumable_usage_desc(
    attr: str, name: str, icon: str
) -> RoboVacSensorDescription:
    return RoboVacSensorDescription(
        key=attr,
        name=name,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="h",
        state_class=SensorStateClass.MEASUREMENT,
        icon=icon,
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "ACCESSORIES_STATUS" in c.supported_dps,
        value_fn=lambda s, a=attr: getattr(s.accessories, a) or 0,
        availability_fn=lambda s: "accessories" in s.received_fields,
    )


SENSOR_DESCRIPTIONS: tuple[RoboVacSensorDescription, ...] = (
    RoboVacSensorDescription(
        key="error_message",
        name="Error Message",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.error_message or None,
        extra_state_attributes_fn=lambda s: {
            "all_codes": s.error_codes_all,
            "all_messages": s.error_messages_all,
        },
    ),
    RoboVacSensorDescription(
        key="task_status",
        name="Task Status",
        icon="mdi:robot-vacuum",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.task_status,
    ),
    RoboVacSensorDescription(
        key="work_mode",
        name="Work Mode",
        icon="mdi:cog-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.work_mode,
    ),
    RoboVacSensorDescription(
        key="active_cleaning_target",
        name="Active Cleaning Target",
        icon="mdi:floor-plan",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.active_room_names
        if s.active_room_names
        else (
            s.current_scene_name
            if s.current_scene_name
            else (
                f"{s.active_zone_count} zone"
                + ("s" if s.active_zone_count != 1 else "")
                if s.active_zone_count
                else None
            )
        ),
        availability_fn=lambda s: bool(
            s.active_room_ids
            or s.current_scene_id
            or s.current_scene_name
            or s.active_zone_count
        ),
        extra_state_attributes_fn=lambda s: {
            "room_ids": s.active_room_ids,
            "scene_id": s.current_scene_id,
            "scene_name": s.current_scene_name,
            "zone_count": s.active_zone_count,
        },
    ),
    RoboVacSensorDescription(
        key="robot_position_x",
        name="Robot Position X (raw)",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:crosshairs-gps",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.robot_position_x,
        availability_fn=lambda s: "robot_position" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="robot_position_y",
        name="Robot Position Y (raw)",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:crosshairs-gps",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.robot_position_y,
        availability_fn=lambda s: "robot_position" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="robotapp_state",
        name="Robot App State",
        icon="mdi:state-machine",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.robotapp_state or None,
        availability_fn=lambda s: "robotapp_state" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="motion_state",
        name="Motion State",
        icon="mdi:motion",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.motion_state or None,
        availability_fn=lambda s: "motion_state" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="battery_real_level",
        name="Battery Real Level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-heart-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.battery_real_level,
        availability_fn=lambda s: "battery_real_level" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="battery_voltage",
        name="Battery Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash-triangle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.battery_voltage,
        availability_fn=lambda s: "battery_voltage" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="battery_current",
        name="Battery Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:current-dc",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.battery_current,
        availability_fn=lambda s: "battery_current" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="battery_temperature",
        name="Battery Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
        value_fn=lambda s: s.battery_temperature,
        availability_fn=lambda s: "battery_temperature" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="battery_show_level",
        name="Battery Display Level",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.battery_show_level,
        availability_fn=lambda s: "battery_show_level" in s.received_fields,
        enabled_default=False,
    ),
    RoboVacSensorDescription(
        key="charging_state",
        name="Charging State",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.charging_state or None,
        availability_fn=lambda s: "charging_state" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="go_wash_state",
        name="Go Wash State",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.go_wash_state or None,
        availability_fn=lambda s: "go_wash_state" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="go_wash_mode",
        name="Go Wash Mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.go_wash_mode or None,
        availability_fn=lambda s: "go_wash_state" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="mapping_state",
        name="Mapping State",
        icon="mdi:map",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.mapping_state,
        availability_fn=lambda s: "mapping_state" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="mapping_mode",
        name="Mapping Mode",
        icon="mdi:map-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.mapping_mode,
        availability_fn=lambda s: "mapping_state" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="cruise_state",
        name="Cruise State",
        icon="mdi:navigation",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.cruise_state,
        availability_fn=lambda s: "cruise_state" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="cruise_mode",
        name="Cruise Mode",
        icon="mdi:navigation-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.cruise_mode,
        availability_fn=lambda s: "cruise_state" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="smart_follow_state",
        name="Smart Follow State",
        icon="mdi:motion-sensor",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.smart_follow_state,
        availability_fn=lambda s: "smart_follow_state" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="station_work_status",
        name="Station Work Status",
        icon="mdi:robot-vacuum",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.station_work_status,
        availability_fn=lambda s: "station_work_status" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="dust_collect_start_time",
        name="Last Dust Collection",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.dust_collect_start_time,
        availability_fn=lambda s: "dust_collect_stats" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="last_notification",
        name="Last Notification",
        icon="mdi:bell",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.notification_message or None,
        extra_state_attributes_fn=lambda s: {"codes": s.notification_codes},
        availability_fn=lambda s: "notification" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="cleaning_time",
        name="Cleaning Time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:clock-outline",
        entity_category=None,
        exists_fn=lambda c: "CLEANING_STATISTICS" in c.supported_dps,
        value_fn=lambda s: s.cleaning_time,
        availability_fn=lambda s: "cleaning_stats" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="cleaning_area",
        name="Cleaning Area",
        native_unit_of_measurement="m²",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:floor-plan",
        entity_category=None,
        exists_fn=lambda c: "CLEANING_STATISTICS" in c.supported_dps,
        value_fn=lambda s: s.cleaning_area,
        availability_fn=lambda s: "cleaning_stats" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="total_cleaning_time",
        name="Total Cleaning Time",
        native_unit_of_measurement="s",
        icon="mdi:timer",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "CLEANING_STATISTICS" in c.supported_dps,
        value_fn=lambda s: s.total_cleaning_time,
        availability_fn=lambda s: "total_stats" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="total_cleaning_area",
        name="Total Cleaning Area",
        native_unit_of_measurement="m²",
        icon="mdi:floor-plan",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "CLEANING_STATISTICS" in c.supported_dps,
        value_fn=lambda s: s.total_cleaning_area,
        availability_fn=lambda s: "total_stats" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="total_cleaning_count",
        name="Total Cleaning Count",
        icon="mdi:counter",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "CLEANING_STATISTICS" in c.supported_dps,
        value_fn=lambda s: s.total_cleaning_count,
        availability_fn=lambda s: "total_stats" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="user_total_cleaning_time",
        name="User Total Cleaning Time",
        native_unit_of_measurement="s",
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "CLEANING_STATISTICS" in c.supported_dps,
        value_fn=lambda s: s.user_total_cleaning_time,
        availability_fn=lambda s: "user_total_stats" in s.received_fields,
        enabled_default=False,
    ),
    RoboVacSensorDescription(
        key="user_total_cleaning_area",
        name="User Total Cleaning Area",
        native_unit_of_measurement="m²",
        icon="mdi:floor-plan",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "CLEANING_STATISTICS" in c.supported_dps,
        value_fn=lambda s: s.user_total_cleaning_area,
        availability_fn=lambda s: "user_total_stats" in s.received_fields,
        enabled_default=False,
    ),
    RoboVacSensorDescription(
        key="user_total_cleaning_count",
        name="User Total Cleaning Count",
        icon="mdi:counter",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "CLEANING_STATISTICS" in c.supported_dps,
        value_fn=lambda s: s.user_total_cleaning_count,
        availability_fn=lambda s: "user_total_stats" in s.received_fields,
        enabled_default=False,
    ),
    RoboVacSensorDescription(
        key="water_level",
        name="Water Level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=None,
        exists_fn=lambda c: "STATION_STATUS" in c.supported_dps,
        value_fn=lambda s: s.station_clean_water,
        availability_fn=lambda s: "station_clean_water" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="waste_water_level",
        name="Waste Water Level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-minus",
        entity_category=None,
        exists_fn=lambda c: "STATION_STATUS" in c.supported_dps,
        value_fn=lambda s: s.station_waste_water,
        availability_fn=lambda s: "dock_status" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="dock_status",
        name="Dock Status",
        entity_category=None,
        exists_fn=lambda c: "STATION_STATUS" in c.supported_dps,
        value_fn=lambda s: s.dock_status,
        availability_fn=lambda s: "dock_status" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="active_map",
        name="Active Map",
        icon="mdi:map-marker-path",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "MULTI_MAP_MANAGE" in c.supported_dps,
        value_fn=lambda s: s.map_id,
        availability_fn=lambda s: "map_id" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="wifi_signal",
        name="WiFi Signal Strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "UNSETTING" in c.supported_dps,
        value_fn=lambda s: s.wifi_signal,
        availability_fn=lambda s: "wifi_signal" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="mop_state",
        name="Mop State",
        icon="mdi:mop",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "UNSETTING" in c.supported_dps,
        value_fn=lambda s: s.mop_state,
        availability_fn=lambda s: "mop_state" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="clean_strategy_version",
        name="Clean Strategy Version",
        icon="mdi:strategy",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "UNSETTING" in c.supported_dps,
        value_fn=lambda s: s.clean_strategy_version,
        availability_fn=lambda s: "clean_strategy_version" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="live_map_state_bits",
        name="Live Map State",
        icon="mdi:map-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "UNSETTING" in c.supported_dps,
        value_fn=lambda s: s.live_map_state_bits,
        availability_fn=lambda s: "live_map_state_bits" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="wifi_frequency",
        name="WiFi Frequency",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "UNSETTING" in c.supported_dps,
        value_fn=lambda s: "5 GHz"
        if s.wifi_frequency == 1
        else "2.4 GHz"
        if s.wifi_frequency == 0
        else str(s.wifi_frequency),
        availability_fn=lambda s: "wifi_frequency" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="wifi_connection_result",
        name="WiFi Connection Result",
        icon="mdi:wifi-check",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "UNSETTING" in c.supported_dps,
        value_fn=lambda s: "OK"
        if s.wifi_connection_result == 0
        else "Password Error"
        if s.wifi_connection_result == 1
        else str(s.wifi_connection_result),
        availability_fn=lambda s: "wifi_connection_result" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="wifi_connection_timestamp",
        name="WiFi Connection Timestamp",
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "UNSETTING" in c.supported_dps,
        value_fn=lambda s: s.wifi_connection_timestamp,
        availability_fn=lambda s: "wifi_connection_timestamp" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="wifi_ssid",
        name="WiFi SSID",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "APP_DEV_INFO" in c.supported_dps,
        value_fn=lambda s: s.wifi_ssid or None,
        availability_fn=lambda s: "wifi_ssid" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="wifi_ip",
        name="IP Address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "APP_DEV_INFO" in c.supported_dps,
        value_fn=lambda s: s.wifi_ip or None,
        availability_fn=lambda s: "wifi_ip" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="ota_channel",
        name="OTA Channel",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "APP_DEV_INFO" in c.supported_dps,
        value_fn=lambda s: s.ota_channel or None,
        availability_fn=lambda s: "ota_channel" in s.received_fields,
    ),
    RoboVacSensorDescription(
        key="last_capture",
        name="Last Capture",
        icon="mdi:camera",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda c: "MEDIA_MANAGER" in c.supported_dps,
        value_fn=lambda s: s.media_last_capture_path or None,
        availability_fn=lambda s: "media_last_capture" in s.received_fields,
    ),
    _make_accessory_remaining_desc(
        "filter_usage", "Filter Remaining", "mdi:air-filter"
    ),
    _make_accessory_remaining_desc(
        "main_brush_usage", "Rolling Brush Remaining", "mdi:broom"
    ),
    _make_accessory_remaining_desc(
        "side_brush_usage", "Side Brush Remaining", "mdi:broom"
    ),
    _make_accessory_remaining_desc(
        "sensor_usage", "Sensor Remaining", "mdi:eye-outline"
    ),
    _make_accessory_remaining_desc(
        "scrape_usage", "Cleaning Tray Remaining", "mdi:wiper"
    ),
    _make_accessory_remaining_desc(
        "mop_usage", "Mopping Cloth Remaining", "mdi:water"
    ),
    _make_consumable_usage_desc("dustbag_usage", "Dustbag Usage", "mdi:delete"),
    _make_consumable_usage_desc(
        "dirty_watertank_usage", "Waste Water Tank Usage", "mdi:water-alert"
    ),
    _make_consumable_usage_desc(
        "dirty_waterfilter_usage", "Water Filter Usage", "mdi:water-check"
    ),
    _make_consumable_usage_desc(
        "accessory_12_usage", "Accessory 12 Usage", "mdi:tools"
    ),
    _make_consumable_usage_desc(
        "accessory_13_usage", "Accessory 13 Usage", "mdi:tools"
    ),
    _make_consumable_usage_desc(
        "accessory_15_usage", "Accessory 15 Usage", "mdi:tools"
    ),
    _make_consumable_usage_desc(
        "accessory_19_usage", "Accessory 19 Usage", "mdi:tools"
    ),
)

assert len(SENSOR_DESCRIPTIONS) == 60
