"""Auto-generated HA entity classes for simple-type DPS from cloud catalog."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import AUTO_ENTITY_OVERRIDES, HANDLED_DPS_IDS, KNOWN_UNPROCESSED_DPS


class _AutoEntityBase(CoordinatorEntity):

    _attr_has_entity_name = True

    def __init__(self, coordinator: Any, dp_id: str, cloud_code: str, override: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._dp_id = dp_id
        self._cloud_code = cloud_code
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.device_id}_{cloud_code}"
        self._attr_name = override.get("name", cloud_code.replace("_", " ").title())
        self._attr_icon = override.get("icon")
        self._attr_entity_registry_enabled_default = override.get("enabled_default", False)
        if "entity_category" in override:
            cat = override["entity_category"]
            if cat is not None:
                self._attr_entity_category = cat
        else:
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self) -> bool:
        return self._dp_id in self.coordinator.data.dynamic_values


class AutoSwitch(_AutoEntityBase, SwitchEntity):

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.dynamic_values.get(self._dp_id, False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command({self._dp_id: True})
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, dynamic_values={**self.coordinator.data.dynamic_values, self._dp_id: True})
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command({self._dp_id: False})
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, dynamic_values={**self.coordinator.data.dynamic_values, self._dp_id: False})
        )


class AutoBinarySensor(_AutoEntityBase, BinarySensorEntity):

    def __init__(self, coordinator: Any, dp_id: str, cloud_code: str, override: dict[str, Any]) -> None:
        super().__init__(coordinator, dp_id, cloud_code, override)
        if dc := override.get("device_class"):
            self._attr_device_class = dc

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.dynamic_values.get(self._dp_id, False))


class AutoSensor(_AutoEntityBase, SensorEntity):

    def __init__(self, coordinator: Any, dp_id: str, cloud_code: str, override: dict[str, Any]) -> None:
        super().__init__(coordinator, dp_id, cloud_code, override)
        if dc := override.get("device_class"):
            self._attr_device_class = dc
        if unit := override.get("unit"):
            self._attr_native_unit_of_measurement = unit
        if sc := override.get("state_class"):
            self._attr_state_class = SensorStateClass.MEASUREMENT if sc == "measurement" else sc

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.dynamic_values.get(self._dp_id)


class AutoNumber(_AutoEntityBase, NumberEntity):

    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: Any, dp_id: str, cloud_code: str, override: dict[str, Any]) -> None:
        super().__init__(coordinator, dp_id, cloud_code, override)
        self._attr_native_min_value = float(override.get("min", 0))
        self._attr_native_max_value = float(override.get("max", 100))
        self._attr_native_step = float(override.get("step", 1))

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.dynamic_values.get(self._dp_id)
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        int_val = int(value)
        await self.coordinator.async_send_command({self._dp_id: int_val})
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, dynamic_values={**self.coordinator.data.dynamic_values, self._dp_id: int_val})
        )


class AutoSelect(_AutoEntityBase, SelectEntity):

    def __init__(self, coordinator: Any, dp_id: str, cloud_code: str, override: dict[str, Any]) -> None:
        super().__init__(coordinator, dp_id, cloud_code, override)
        self._options_map: dict[int, str] = override["options_map"]
        self._reverse_map: dict[str, int] = {v: k for k, v in self._options_map.items()}
        self._attr_options = list(self._options_map.values())

    @property
    def current_option(self) -> str | None:
        val = self.coordinator.data.dynamic_values.get(self._dp_id)
        if val is None:
            return None
        return self._options_map.get(int(val))

    async def async_select_option(self, option: str) -> None:
        int_val = self._reverse_map[option]
        await self.coordinator.async_send_command({self._dp_id: str(int_val)})
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, dynamic_values={**self.coordinator.data.dynamic_values, self._dp_id: int_val})
        )


# ── Factory functions ──────────────────────────────────────────────────────────

def _should_skip(dp_id_str: str, entry: dict[str, Any]) -> bool:
    return (
        dp_id_str in HANDLED_DPS_IDS
        or dp_id_str in KNOWN_UNPROCESSED_DPS
        or entry.get("data_type") in ("Raw", "String")
    )


def get_auto_switches(coordinator: Any) -> list[AutoSwitch]:
    entities: list[AutoSwitch] = []
    for dp_id_str, entry in coordinator.dps_catalog.items():
        if _should_skip(dp_id_str, entry):
            continue
        if entry.get("data_type") == "Bool" and entry.get("mode") in ("rw", "w"):
            code = entry.get("code", f"dps_{dp_id_str}")
            override = AUTO_ENTITY_OVERRIDES.get(code, {})
            entities.append(AutoSwitch(coordinator, dp_id_str, code, override))
    return entities


def get_auto_binary_sensors(coordinator: Any) -> list[AutoBinarySensor]:
    entities: list[AutoBinarySensor] = []
    for dp_id_str, entry in coordinator.dps_catalog.items():
        if _should_skip(dp_id_str, entry):
            continue
        if entry.get("data_type") == "Bool" and entry.get("mode") == "ro":
            code = entry.get("code", f"dps_{dp_id_str}")
            override = AUTO_ENTITY_OVERRIDES.get(code, {})
            entities.append(AutoBinarySensor(coordinator, dp_id_str, code, override))
    return entities


def get_auto_sensors(coordinator: Any) -> list[AutoSensor]:
    entities: list[AutoSensor] = []
    for dp_id_str, entry in coordinator.dps_catalog.items():
        if _should_skip(dp_id_str, entry):
            continue
        if entry.get("data_type") == "Value" and entry.get("mode") == "ro":
            code = entry.get("code", f"dps_{dp_id_str}")
            override = AUTO_ENTITY_OVERRIDES.get(code, {})
            entities.append(AutoSensor(coordinator, dp_id_str, code, override))
    return entities


def get_auto_numbers(coordinator: Any) -> list[AutoNumber]:
    entities: list[AutoNumber] = []
    for dp_id_str, entry in coordinator.dps_catalog.items():
        if _should_skip(dp_id_str, entry):
            continue
        if entry.get("data_type") == "Value" and entry.get("mode") in ("rw", "w"):
            code = entry.get("code", f"dps_{dp_id_str}")
            override = AUTO_ENTITY_OVERRIDES.get(code, {})
            entities.append(AutoNumber(coordinator, dp_id_str, code, override))
    return entities


def get_auto_selects(coordinator: Any) -> list[AutoSelect]:
    entities: list[AutoSelect] = []
    for dp_id_str, entry in coordinator.dps_catalog.items():
        if _should_skip(dp_id_str, entry):
            continue
        if entry.get("data_type") == "Enum" and entry.get("mode") in ("rw", "w"):
            code = entry.get("code", f"dps_{dp_id_str}")
            override = AUTO_ENTITY_OVERRIDES.get(code, {})
            if "options_map" not in override:
                continue
            entities.append(AutoSelect(coordinator, dp_id_str, code, override))
    return entities
