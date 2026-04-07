"""Auto-generated HA entities from the device DPS catalog."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import AUTO_ENTITY_OVERRIDES, HANDLED_DPS_IDS, KNOWN_UNPROCESSED_DPS
from .coordinator import EufyCleanCoordinator

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class _AutoEntityBase(CoordinatorEntity[EufyCleanCoordinator]):
    """Base class for auto-generated entities."""

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        dp_id: str,
        cloud_code: str,
        override: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._dp_id = dp_id
        self._cloud_code = cloud_code
        self._attr_has_entity_name = True
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.device_id}_{cloud_code}"
        self._attr_name = override.get("name", cloud_code.replace("_", " ").title())
        # entity_category: None value in override → PRIMARY (no category).
        # Missing key → CONFIG (default).
        if "entity_category" in override:
            cat = override["entity_category"]
            if cat is not None:
                self._attr_entity_category = cat
            # else: leave unset → defaults to None (primary entity)
        else:
            self._attr_entity_category = EntityCategory.CONFIG
        self._attr_entity_registry_enabled_default = override.get(
            "enabled_default", False
        )
        if icon := override.get("icon"):
            self._attr_icon = icon

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return (
            super().available
            and self._dp_id in self.coordinator.data.dynamic_values
        )


# ---------------------------------------------------------------------------
# Entity classes
# ---------------------------------------------------------------------------


class AutoSwitch(_AutoEntityBase, SwitchEntity):
    """Auto-generated switch for Bool + rw DPS entries."""

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        dp_id: str,
        cloud_code: str,
        override: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, dp_id, cloud_code, override)

    @property
    def is_on(self) -> bool | None:
        """Return current switch state."""
        return self.coordinator.data.dynamic_values.get(self._dp_id, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._set(False)

    async def _set(self, value: bool) -> None:
        from .api.commands import build_command

        await self.coordinator.async_send_command(
            build_command("generic", dp_id=self._dp_id, value=value)
        )
        new_dv = {**self.coordinator.data.dynamic_values, self._dp_id: value}
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, dynamic_values=new_dv)
        )


class AutoBinarySensor(_AutoEntityBase, BinarySensorEntity):
    """Auto-generated binary sensor for Bool + ro DPS entries."""

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        dp_id: str,
        cloud_code: str,
        override: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, dp_id, cloud_code, override)
        if dc := override.get("device_class"):
            self._attr_device_class = dc

    @property
    def is_on(self) -> bool | None:
        """Return current binary sensor state."""
        return self.coordinator.data.dynamic_values.get(self._dp_id, False)


class AutoNumber(_AutoEntityBase, NumberEntity):
    """Auto-generated number for Value + rw DPS entries."""

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        dp_id: str,
        cloud_code: str,
        override: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, dp_id, cloud_code, override)
        self._attr_native_min_value = float(override.get("min", 0))
        self._attr_native_max_value = float(override.get("max", 100))
        self._attr_native_step = float(override.get("step", 1))
        self._attr_mode = NumberMode.SLIDER
        if unit := override.get("unit"):
            self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> float | None:
        """Return current number value."""
        val = self.coordinator.data.dynamic_values.get(self._dp_id)
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""
        int_val = int(value)
        from .api.commands import build_command

        await self.coordinator.async_send_command(
            build_command("generic", dp_id=self._dp_id, value=int_val)
        )
        new_dv = {**self.coordinator.data.dynamic_values, self._dp_id: int_val}
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, dynamic_values=new_dv)
        )


class AutoSensor(_AutoEntityBase, SensorEntity):
    """Auto-generated sensor for Value + ro DPS entries."""

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        dp_id: str,
        cloud_code: str,
        override: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, dp_id, cloud_code, override)
        if dc := override.get("device_class"):
            self._attr_device_class = dc
        if unit := override.get("unit"):
            self._attr_native_unit_of_measurement = unit
        if sc := override.get("state_class"):
            self._attr_state_class = (
                SensorStateClass.MEASUREMENT if sc == "measurement" else sc
            )

    @property
    def native_value(self) -> Any:
        """Return current sensor value."""
        return self.coordinator.data.dynamic_values.get(self._dp_id)


class AutoSelect(_AutoEntityBase, SelectEntity):
    """Auto-generated select for Enum + rw DPS entries with known options."""

    def __init__(
        self,
        coordinator: EufyCleanCoordinator,
        dp_id: str,
        cloud_code: str,
        override: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, dp_id, cloud_code, override)
        self._options_map: dict[int, str] = override.get("options_map", {})
        self._reverse_map: dict[str, int] = {
            v: k for k, v in self._options_map.items()
        }
        self._attr_options = list(self._options_map.values())

    @property
    def current_option(self) -> str | None:
        """Return currently selected option."""
        val = self.coordinator.data.dynamic_values.get(self._dp_id)
        if val is None:
            return None
        return self._options_map.get(int(val))

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        int_val = self._reverse_map.get(option)
        if int_val is None:
            _LOGGER.warning("Unknown option %r for %s", option, self._cloud_code)
            return
        from .api.commands import build_command

        await self.coordinator.async_send_command(
            build_command("generic", dp_id=self._dp_id, value=str(int_val))
        )
        new_dv = {**self.coordinator.data.dynamic_values, self._dp_id: int_val}
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, dynamic_values=new_dv)
        )


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def get_auto_switches(
    coordinator: EufyCleanCoordinator,
) -> list[AutoSwitch]:
    """Create AutoSwitch entities for Bool + rw DPS entries."""
    entities: list[AutoSwitch] = []
    for dp_id_str, entry in coordinator.dps_catalog.items():
        if dp_id_str in HANDLED_DPS_IDS or dp_id_str in KNOWN_UNPROCESSED_DPS:
            continue
        if entry.get("data_type") == "Bool" and entry.get("mode") == "rw":
            code = entry.get("code", f"dps_{dp_id_str}")
            override = AUTO_ENTITY_OVERRIDES.get(code, {})
            entities.append(AutoSwitch(coordinator, dp_id_str, code, override))
    return entities


def get_auto_binary_sensors(
    coordinator: EufyCleanCoordinator,
) -> list[AutoBinarySensor]:
    """Create AutoBinarySensor entities for Bool + ro DPS entries."""
    entities: list[AutoBinarySensor] = []
    for dp_id_str, entry in coordinator.dps_catalog.items():
        if dp_id_str in HANDLED_DPS_IDS or dp_id_str in KNOWN_UNPROCESSED_DPS:
            continue
        if entry.get("data_type") == "Bool" and entry.get("mode") == "ro":
            code = entry.get("code", f"dps_{dp_id_str}")
            override = AUTO_ENTITY_OVERRIDES.get(code, {})
            entities.append(AutoBinarySensor(coordinator, dp_id_str, code, override))
    return entities


def get_auto_numbers(
    coordinator: EufyCleanCoordinator,
) -> list[AutoNumber]:
    """Create AutoNumber entities for Value + rw DPS entries."""
    entities: list[AutoNumber] = []
    for dp_id_str, entry in coordinator.dps_catalog.items():
        if dp_id_str in HANDLED_DPS_IDS or dp_id_str in KNOWN_UNPROCESSED_DPS:
            continue
        if entry.get("data_type") == "Value" and entry.get("mode") == "rw":
            code = entry.get("code", f"dps_{dp_id_str}")
            override = AUTO_ENTITY_OVERRIDES.get(code, {})
            entities.append(AutoNumber(coordinator, dp_id_str, code, override))
    return entities


def get_auto_sensors(
    coordinator: EufyCleanCoordinator,
) -> list[AutoSensor]:
    """Create AutoSensor entities for Value + ro DPS entries."""
    entities: list[AutoSensor] = []
    for dp_id_str, entry in coordinator.dps_catalog.items():
        if dp_id_str in HANDLED_DPS_IDS or dp_id_str in KNOWN_UNPROCESSED_DPS:
            continue
        if entry.get("data_type") == "Value" and entry.get("mode") == "ro":
            code = entry.get("code", f"dps_{dp_id_str}")
            override = AUTO_ENTITY_OVERRIDES.get(code, {})
            entities.append(AutoSensor(coordinator, dp_id_str, code, override))
    return entities


def get_auto_selects(
    coordinator: EufyCleanCoordinator,
) -> list[AutoSelect]:
    """Create AutoSelect entities for Enum + rw DPS entries with known options."""
    entities: list[AutoSelect] = []
    for dp_id_str, entry in coordinator.dps_catalog.items():
        if dp_id_str in HANDLED_DPS_IDS or dp_id_str in KNOWN_UNPROCESSED_DPS:
            continue
        if entry.get("data_type") == "Enum" and entry.get("mode") == "rw":
            code = entry.get("code", f"dps_{dp_id_str}")
            override = AUTO_ENTITY_OVERRIDES.get(code, {})
            if "options_map" not in override:
                continue  # Skip — no known options
            entities.append(AutoSelect(coordinator, dp_id_str, code, override))
    return entities
