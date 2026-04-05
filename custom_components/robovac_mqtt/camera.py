from __future__ import annotations

import logging

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.robovac_mqtt.api.map_renderer import render_path
from .const import DOMAIN
from .coordinator import EufyCleanCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the camera platform."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: list[EufyCleanCoordinator] = data["coordinators"]
    async_add_entities(
        [RoboVacMapCamera(coordinator) for coordinator in coordinators]
    )


class RoboVacMapCamera(CoordinatorEntity[EufyCleanCoordinator], Camera):
    """Camera entity showing the vacuum's cleaning path."""

    _attr_content_type = "image/png"
    _attr_has_entity_name = True
    _attr_name = "Map"
    _attr_is_recording = False
    _attr_is_streaming = False

    def __init__(self, coordinator: EufyCleanCoordinator) -> None:
        """Initialize the map camera."""
        CoordinatorEntity.__init__(self, coordinator)  # type: ignore[arg-type]
        Camera.__init__(self)
        self._attr_unique_id = f"{coordinator.device_id}_map_camera"
        self._attr_device_info = coordinator.device_info
        self._path: list[tuple[int, int]] = []
        self._dock_position: tuple[int, int] | None = None
        self._last_activity: str = "idle"

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator — accumulate path."""
        state = self.coordinator.data
        current_activity = state.activity

        if current_activity == "cleaning" and self._last_activity not in (
            "cleaning",
            "paused",
            "returning",
        ):
            self._path = []
            self._dock_position = None
            _LOGGER.debug("Cleaning session started — path reset")

        self._last_activity = current_activity

        if current_activity in ("cleaning", "returning") and (
            "robot_position" in state.received_fields
        ):
            x, y = state.robot_position_x, state.robot_position_y
            if x or y:  # skip (0, 0) as likely uninitialized
                if not self._path or self._path[-1] != (x, y):
                    self._path.append((x, y))
                    if self._dock_position is None:
                        self._dock_position = (x, y)

        super()._handle_coordinator_update()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return PNG bytes of current path map."""
        state = self.coordinator.data
        rooms = state.rooms if state.rooms else None
        return render_path(
            positions=list(self._path),
            dock_position=self._dock_position,
            rooms=rooms,
        )
