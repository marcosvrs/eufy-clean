from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import EntityCategory

from custom_components.robovac_mqtt.binary_sensor import (
    async_setup_entry as binary_sensor_setup,
)
from custom_components.robovac_mqtt.button import async_setup_entry as button_setup
from custom_components.robovac_mqtt.const import DOMAIN
from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator
from custom_components.robovac_mqtt.models import EufyCleanData
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.sensor import async_setup_entry as sensor_setup
from custom_components.robovac_mqtt.switch import async_setup_entry as switch_setup

EXPECTED_SENSOR_SUFFIXES = {
    "error_message",
    "task_status",
    "work_mode",
    "active_cleaning_target",
    "robot_position_x",
    "robot_position_y",
    "robotapp_state",
    "motion_state",
    "battery_level",
    "battery_real_level",
    "battery_voltage",
    "battery_current",
    "battery_temperature",
    "battery_show_level",
    "charging_state",
    "go_wash_state",
    "go_wash_mode",
    "mapping_state",
    "mapping_mode",
    "cruise_state",
    "cruise_mode",
    "smart_follow_state",
    "station_work_status",
    "dust_collect_start_time",
    "last_notification",
    "cleaning_time",
    "cleaning_area",
    "total_cleaning_time",
    "total_cleaning_area",
    "total_cleaning_count",
    "user_total_cleaning_time",
    "user_total_cleaning_area",
    "user_total_cleaning_count",
    "water_level",
    "waste_water_level",
    "dock_status",
    "active_map",
    "wifi_signal",
    "clean_strategy_version",
    "live_map_state_bits",
    "wifi_frequency",
    "wifi_connection_result",
    "wifi_connection_timestamp",
    "wifi_ssid",
    "wifi_ip",
    "ota_channel",
    "last_capture",
    "filter_remaining",
    "main_brush_remaining",
    "side_brush_remaining",
    "sensor_remaining",
    "scrape_remaining",
    "mop_remaining",
    "dustbag_usage",
    "dirty_watertank_usage",
    "dirty_waterfilter_usage",
    "accessory_12_usage",
    "accessory_13_usage",
    "accessory_15_usage",
    "accessory_19_usage",
}

EXPECTED_BINARY_SENSOR_SUFFIXES = {
    "charging",
    "upgrading",
    "relocating",
    "breakpoint_available",
    "roller_brush_cleaning",
    "water_tank_clear_adding",
    "water_tank_waste_recycling",
    "dock_connected",
    "dust_collect_result",
    "mop_holder_l",
    "mop_holder_r",
    "map_valid",
    "live_map",
    "mop_state",
}

EXPECTED_SWITCH_SUFFIXES = {
    "auto_empty",
    "auto_wash",
    "do_not_disturb",
    "child_lock",
    "ai_see",
    "pet_mode_sw",
    "poop_avoidance_sw",
    "live_photo_sw",
    "deep_mop_corner_sw",
    "smart_follow_sw",
    "cruise_continue_sw",
    "multi_map_sw",
    "suggest_restricted_zone_sw",
    "water_level_sw",
    "smart_mode",
    "media_recording",
}

EXPECTED_BUTTON_SUFFIXES = {
    "_dry_mop",
    "_wash_mop",
    "_empty_dust_bin",
    "_stop_dry_mop",
    "_reset_filter",
    "_reset_main_brush",
    "_reset_side_brush",
    "_reset_sensors",
    "_reset_scrape",
    "_reset_mop",
    "_stop_return",
    "_map_then_clean",
    "_global_cruise",
    "_stop_smart_follow",
    "_restart",
    "_resume_from_breakpoint",
    "_media_capture",
    "_rc_forward",
    "_rc_back",
    "_rc_left",
    "_rc_right",
    "_rc_brake",
    "_rc_enter",
    "_rc_exit",
}


def _snapshot_entries(
    suffixes: Iterable[str],
    *,
    enabled: bool,
    visible: bool = False,
    category: EntityCategory | None,
) -> dict[str, tuple[bool, bool, str | None]]:
    category_value = category.value if category else None
    return {suffix: (enabled, visible, category_value) for suffix in suffixes}


EXPECTED_SENSOR_METADATA = {
    **_snapshot_entries(
        {"error_message", "task_status", "work_mode"},
        enabled=True,
        category=EntityCategory.DIAGNOSTIC,
    ),
    **_snapshot_entries(
        {"battery_level"},
        enabled=True,
        category=None,
    ),
    **_snapshot_entries(
        EXPECTED_SENSOR_SUFFIXES
        - {
            "error_message",
            "task_status",
            "work_mode",
            "battery_level",
            "water_level",
            "waste_water_level",
            "dock_status",
        },
        enabled=False,
        category=EntityCategory.DIAGNOSTIC,
    ),
    **_snapshot_entries(
        {
            "water_level",
            "waste_water_level",
            "dock_status",
        },
        enabled=False,
        category=None,
    ),
}

EXPECTED_BINARY_SENSOR_METADATA = {
    **_snapshot_entries({"charging"}, enabled=True, category=None),
    **_snapshot_entries(
        EXPECTED_BINARY_SENSOR_SUFFIXES - {"charging"},
        enabled=False,
        category=EntityCategory.DIAGNOSTIC,
    ),
}

EXPECTED_SWITCH_METADATA = {
    **_snapshot_entries(
        {"auto_empty", "auto_wash"},
        enabled=True,
        category=EntityCategory.CONFIG,
    ),
    **_snapshot_entries(
        EXPECTED_SWITCH_SUFFIXES - {"auto_empty", "auto_wash"},
        enabled=False,
        category=EntityCategory.CONFIG,
    ),
}

EXPECTED_BUTTON_METADATA = {
    **_snapshot_entries(
        {
            "_reset_filter",
            "_reset_main_brush",
            "_reset_side_brush",
            "_reset_sensors",
            "_reset_scrape",
            "_reset_mop",
            "_restart",
            "_rc_forward",
            "_rc_back",
            "_rc_left",
            "_rc_right",
            "_rc_brake",
            "_rc_enter",
            "_rc_exit",
        },
        enabled=True,
        category=EntityCategory.CONFIG,
    ),
    **_snapshot_entries(
        EXPECTED_BUTTON_SUFFIXES
        - {
            "_reset_filter",
            "_reset_main_brush",
            "_reset_side_brush",
            "_reset_sensors",
            "_reset_scrape",
            "_reset_mop",
            "_restart",
            "_rc_forward",
            "_rc_back",
            "_rc_left",
            "_rc_right",
            "_rc_brake",
            "_rc_enter",
            "_rc_exit",
        },
        enabled=True,
        category=None,
    ),
}


@pytest.fixture
def mock_coordinator() -> MagicMock:
    coordinator = MagicMock(spec=EufyCleanCoordinator)
    coordinator.device_id = "test_device"
    coordinator.device_name = "Test Device"
    coordinator.device_model = "T2351"
    coordinator.device_info = MagicMock()
    coordinator.last_update_success = True
    coordinator.dps_map = {}
    coordinator.supported_dps = frozenset(
        {
            "CLEANING_STATISTICS",
            "STATION_STATUS",
            "MULTI_MAP_MANAGE",
            "UNSETTING",
            "APP_DEV_INFO",
            "MEDIA_MANAGER",
            "ACCESSORIES_STATUS",
            "UNDISTURBED",
        }
    )
    coordinator.data = VacuumState(
        received_fields={
            "robot_position",
            "robotapp_state",
            "motion_state",
            "battery_real_level",
            "battery_voltage",
            "battery_current",
            "battery_temperature",
            "battery_show_level",
            "charging_state",
            "go_wash_state",
            "go_wash_mode",
            "mapping_state",
            "cruise_state",
            "cruise_mode",
            "smart_follow_state",
            "station_work_status",
            "cleaning_stats",
            "total_stats",
            "user_total_stats",
            "station_clean_water",
            "dock_status",
            "map_id",
            "wifi_signal",
            "mop_state",
            "clean_strategy_version",
            "live_map_state_bits",
            "wifi_frequency",
            "wifi_connection_result",
            "wifi_connection_timestamp",
            "wifi_ssid",
            "wifi_ip",
            "ota_channel",
            "dust_collect_stats",
            "media_last_capture",
            "accessories",
            "notification",
            "water_tank_state",
            "dock_connected",
            "upgrading",
            "relocating",
            "breakpoint_available",
            "roller_brush_cleaning",
            "mop_holder_state_l",
            "mop_holder_state_r",
            "map_valid",
            "child_lock",
            "smart_mode",
            "media_status",
            "do_not_disturb",
        }
    )
    return coordinator


@pytest.fixture
def mock_hass_data(mock_coordinator: MagicMock) -> tuple[MagicMock, MagicMock]:
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.runtime_data = EufyCleanData(
        coordinators={mock_coordinator.device_id: mock_coordinator}, cloud=MagicMock()
    )
    return hass, entry


def _sensor_suffix(entity: Any, device_id: str) -> str:
    return entity.unique_id.removeprefix(f"{device_id}_")


def _button_suffix(entity: Any, device_id: str) -> str:
    return entity.unique_id[len(device_id) :]


def _metadata(entity: Any) -> tuple[bool, bool, str | None]:
    category = entity.entity_category
    return (
        entity.entity_registry_enabled_default,
        entity.entity_registry_visible_default,
        category.value if category else None,
    )


def _assert_snapshot(
    entities: list[Any],
    *,
    expected_count: int,
    expected_suffixes: set[str],
    suffix_extractor: Callable[[Any, str], str],
    metadata_map: dict[str, tuple[bool, bool, str | None]],
    device_id: str,
) -> None:
    actual = {
        suffix_extractor(entity, device_id): _metadata(entity) for entity in entities
    }
    actual_suffixes = set(actual)
    assert len(entities) == expected_count, (
        f"Expected {expected_count} entities, got {len(entities)}: "
        f"{sorted(actual_suffixes.symmetric_difference(expected_suffixes))}"
    )
    assert actual_suffixes == expected_suffixes, (
        "Diff: " f"{sorted(actual_suffixes.symmetric_difference(expected_suffixes))}"
    )
    assert actual == metadata_map


@pytest.mark.asyncio
async def test_golden_sensor_unique_ids(
    mock_coordinator: MagicMock, mock_hass_data: tuple[MagicMock, MagicMock]
) -> None:
    hass, entry = mock_hass_data
    captured: list[Any] = []

    with patch(
        "custom_components.robovac_mqtt.sensor.get_auto_sensors", return_value=[]
    ):
        await sensor_setup(
            hass, entry, lambda entities, *args, **kwargs: captured.extend(entities)
        )

    _assert_snapshot(
        captured,
        expected_count=60,
        expected_suffixes=EXPECTED_SENSOR_SUFFIXES,
        suffix_extractor=_sensor_suffix,
        metadata_map=EXPECTED_SENSOR_METADATA,
        device_id=mock_coordinator.device_id,
    )


@pytest.mark.asyncio
async def test_golden_binary_sensor_unique_ids(
    mock_coordinator: MagicMock, mock_hass_data: tuple[MagicMock, MagicMock]
) -> None:
    hass, entry = mock_hass_data
    captured: list[Any] = []

    with patch(
        "custom_components.robovac_mqtt.binary_sensor.get_auto_binary_sensors",
        return_value=[],
    ):
        await binary_sensor_setup(
            hass, entry, lambda entities, *args, **kwargs: captured.extend(entities)
        )

    _assert_snapshot(
        captured,
        expected_count=14,
        expected_suffixes=EXPECTED_BINARY_SENSOR_SUFFIXES,
        suffix_extractor=_sensor_suffix,
        metadata_map=EXPECTED_BINARY_SENSOR_METADATA,
        device_id=mock_coordinator.device_id,
    )


@pytest.mark.asyncio
async def test_golden_switch_unique_ids(
    mock_coordinator: MagicMock, mock_hass_data: tuple[MagicMock, MagicMock]
) -> None:
    hass, entry = mock_hass_data
    captured: list[Any] = []

    with patch(
        "custom_components.robovac_mqtt.switch.get_auto_switches", return_value=[]
    ):
        await switch_setup(
            hass, entry, lambda entities, *args, **kwargs: captured.extend(entities)
        )

    _assert_snapshot(
        captured,
        expected_count=16,
        expected_suffixes=EXPECTED_SWITCH_SUFFIXES,
        suffix_extractor=_sensor_suffix,
        metadata_map=EXPECTED_SWITCH_METADATA,
        device_id=mock_coordinator.device_id,
    )


@pytest.mark.asyncio
async def test_golden_button_unique_ids(
    mock_coordinator: MagicMock, mock_hass_data: tuple[MagicMock, MagicMock]
) -> None:
    hass, entry = mock_hass_data
    captured: list[Any] = []

    await button_setup(
        hass, entry, lambda entities, *args, **kwargs: captured.extend(entities)
    )

    _assert_snapshot(
        captured,
        expected_count=24,
        expected_suffixes=EXPECTED_BUTTON_SUFFIXES,
        suffix_extractor=_button_suffix,
        metadata_map=EXPECTED_BUTTON_METADATA,
        device_id=mock_coordinator.device_id,
    )


@pytest.mark.asyncio
async def test_golden_sensor_enabled_defaults(
    mock_coordinator: MagicMock, mock_hass_data: tuple[MagicMock, MagicMock]
) -> None:
    hass, entry = mock_hass_data
    captured: list[Any] = []

    with patch(
        "custom_components.robovac_mqtt.sensor.get_auto_sensors", return_value=[]
    ):
        await sensor_setup(
            hass, entry, lambda entities, *args, **kwargs: captured.extend(entities)
        )

    by_suffix = {
        _sensor_suffix(entity, mock_coordinator.device_id): entity
        for entity in captured
    }

    assert by_suffix["error_message"].entity_registry_enabled_default is True
    assert by_suffix["task_status"].entity_registry_enabled_default is True
    assert by_suffix["work_mode"].entity_registry_enabled_default is True
    assert by_suffix["active_cleaning_target"].entity_registry_enabled_default is False


@pytest.mark.asyncio
async def test_golden_sensor_snapshot_detects_suffix_change(
    mock_coordinator: MagicMock, mock_hass_data: tuple[MagicMock, MagicMock]
) -> None:
    hass, entry = mock_hass_data
    captured: list[Any] = []

    with patch(
        "custom_components.robovac_mqtt.sensor.get_auto_sensors", return_value=[]
    ):
        await sensor_setup(
            hass, entry, lambda entities, *args, **kwargs: captured.extend(entities)
        )

    tampered = dict(EXPECTED_SENSOR_METADATA)
    tampered["error_message_renamed"] = tampered.pop("error_message")

    with pytest.raises(AssertionError):
        _assert_snapshot(
            captured,
            expected_count=60,
            expected_suffixes=(EXPECTED_SENSOR_SUFFIXES - {"error_message"})
            | {"error_message_renamed"},
            suffix_extractor=_sensor_suffix,
            metadata_map=tampered,
            device_id=mock_coordinator.device_id,
        )
