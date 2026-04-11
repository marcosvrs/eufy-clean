from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EufyCleanCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up event entities."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: list[EufyCleanCoordinator] = data["coordinators"]
    async_add_entities(
        RoboVacNotificationEvent(coordinator) for coordinator in coordinators
    )


class RoboVacNotificationEvent(CoordinatorEntity[EufyCleanCoordinator], EventEntity):
    """Event entity for transient toast notifications."""

    _attr_has_entity_name = True
    _attr_name = "Notification Event"
    _attr_event_types = ["notification"]
    _attr_entity_registry_enabled_default = False
    _attr_entity_registry_visible_default = False

    def __init__(self, coordinator: EufyCleanCoordinator) -> None:
        """Initialize the event entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_notification_event"
        self._attr_device_info = coordinator.device_info
        self._last_notification_key: tuple[str, int, tuple[int, ...]] | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fire event when a new notification arrives."""
        data = self.coordinator.data
        new_key = (
            data.notification_message,
            data.notification_time,
            tuple(data.notification_codes),
        )
        if data.notification_message and new_key != self._last_notification_key:
            self._trigger_event(
                "notification",
                {
                    "code": data.notification_codes,
                    "message": data.notification_message,
                    "timestamp": data.notification_time,
                },
            )
            self._last_notification_key = new_key
        super()._handle_coordinator_update()
