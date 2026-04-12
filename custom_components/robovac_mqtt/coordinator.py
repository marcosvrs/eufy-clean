from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, replace
from datetime import timedelta
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api.client import EufyCleanClient
from .api.cloud import EufyLogin
from .api.parser import (
    clear_novelty_dirty,
    get_novelty_caches,
    is_novelty_dirty,
    load_novelty_caches,
    update_state,
)
from .const import (
    DEFAULT_DPS_MAP,
    DOMAIN,
    build_dps_map_from_catalog,
    supported_dps_from_catalog,
)
from .models import CleaningSession, VacuumState
from .typing_defs import EufyCleanConfigEntry, EufyDeviceInfo

_LOGGER = logging.getLogger(__name__)

_ACTIVE_SESSION_STATUSES = frozenset(
    {
        "Cleaning",
        "Returning to Wash",
        "Paused",
        "Washing Mop",
        "Emptying Dust",
        "Returning",
        "Returning to Empty",
        "Adding clean water",
        "Recycling waste water",
    }
)

_DOCK_VISIT_STATUSES = frozenset(
    {
        "Returning to Wash",
        "Returning to Empty",
    }
)


class EufyCleanCoordinator(DataUpdateCoordinator[VacuumState]):
    """Coordinator to manage Eufy Clean device connection and state."""

    @callback
    def async_set_updated_data(self, data: VacuumState) -> None:
        """Update data and notify listeners without noisy debug logging."""
        self._async_unsub_refresh()
        self._debounced_refresh.async_cancel()
        self.data = data
        self.last_update_success = True
        if self._listeners:
            self._schedule_refresh()
        self.async_update_listeners()

    def __init__(
        self,
        hass: HomeAssistant,
        eufy_login: EufyLogin,
        device_info: EufyDeviceInfo,
        config_entry: EufyCleanConfigEntry | None = None,
    ) -> None:
        """Initialize coordinator."""
        self.device_id = device_info["deviceId"]
        self.device_model = device_info["deviceModel"]
        self.device_name = device_info["deviceName"]
        self.serial_number = device_info.get("deviceId")  # Usually deviceId is SN
        self.firmware_version = device_info.get("softVersion")
        self._raw_device_info = device_info
        self.eufy_login = eufy_login

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{self.device_name}",
        )

        self.client: EufyCleanClient | None = None
        self.data = VacuumState()
        self.last_update_success = True
        self._dock_idle_cancel: CALLBACK_TYPE | None = (
            None  # Timer for dock IDLE debounce
        )
        self._segment_update_cancel: CALLBACK_TYPE | None = (
            None  # Timer for segment updates debounce
        )
        self._catalog_refresh_cancel: CALLBACK_TYPE | None = None
        self._timer_inquiry_cancel: CALLBACK_TYPE | None = None
        self._enable_new_entities_cancel: CALLBACK_TYPE | None = None
        self._current_session: CleaningSession | None = None
        self._cleaning_history: list[dict[str, object]] = []
        self._prev_task_status: str = ""
        self._store_lock = asyncio.Lock()
        self._pending_dock_status: str | None = None
        self.last_seen_segments: list[dict[str, Any]] | None = None
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.{self.device_id}")

        catalog = device_info.get("dps_catalog", [])
        self._raw_catalog: list[dict[str, object]] = catalog
        if catalog:
            self.dps_map: dict[str, str] = build_dps_map_from_catalog(catalog)
            _LOGGER.info(
                "Built dynamic DPS map for %s from cloud catalog (%d entries)",
                self.device_name,
                len(catalog),
            )
        else:
            self.dps_map = dict(DEFAULT_DPS_MAP)
            _LOGGER.debug(
                "Using default DPS map for %s — no catalog yet", self.device_name
            )
        self.supported_dps: frozenset[str] = supported_dps_from_catalog(catalog)
        self.dps_catalog: dict[str, dict[str, object]] = (
            {str(item.get("dp_id", "")): item for item in catalog} if catalog else {}
        )
        self.catalog_types: dict[str, str] = (
            {
                str(item.get("dp_id", "")): str(item.get("data_type", ""))
                for item in catalog
            }
            if catalog
            else {}
        )

        self._initial_dps = device_info.get("dps")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        fw = (
            self.data.firmware_version
            if self.data.firmware_version
            else self._raw_device_info.get("softVersion")
        )
        info = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=self.device_name,
            manufacturer="Eufy",
            model=self.device_model,
            serial_number=self.serial_number,
            sw_version=fw,
        )
        # Add MAC address from DPS 169 DeviceInfo if available
        if mac := self.data.device_mac:
            info["connections"] = {(CONNECTION_NETWORK_MAC, format_mac(mac))}
        return info

    @property
    def cleaning_history(self) -> list[dict[str, object]]:
        """Return list of past cleaning sessions."""
        return self._cleaning_history

    @property
    def current_cleaning_session(self) -> CleaningSession | None:
        """Return the in-progress cleaning session, or None."""
        return self._current_session

    async def initialize(self) -> None:
        """Initialize connection to the device."""
        try:
            if not self.eufy_login.mqtt_credentials:
                await self.eufy_login.checkLogin()

            creds = self.eufy_login.mqtt_credentials
            if not creds:
                raise UpdateFailed("Failed to retrieve MQTT credentials")

            self.client = EufyCleanClient(
                device_id=self.device_id,
                user_id=creds["user_id"],
                app_name=creds["app_name"],
                thing_name=creds["thing_name"],
                access_key="",  # Unused
                ticket="",  # Unused
                openudid=self.eufy_login.openudid,
                certificate_pem=creds["certificate_pem"],
                private_key=creds["private_key"],
                device_model=self.device_model,
                endpoint=creds["endpoint_addr"],
            )

            self.client.set_on_message(self._handle_mqtt_message)
            self.client.set_on_disconnect(self._on_mqtt_disconnect)
            self.client.set_on_connect(self._on_mqtt_reconnect)
            await self.async_load_storage()

            if self._initial_dps:
                self.data, _ = update_state(
                    self.data,
                    self._initial_dps,
                    dps_map=self.dps_map,
                    catalog_types=self.catalog_types,
                    dps_catalog=self.dps_catalog,
                )
                self._initial_dps = None
                self._prev_task_status = self.data.task_status

            await self.client.connect()

            self._enable_new_entities_cancel = async_call_later(
                self.hass, 2.0, self._async_enable_new_entities_cb
            )

            if self._raw_catalog:
                async with self._store_lock:
                    existing = await self._store.async_load() or {}
                    existing["dps_catalog"] = self._raw_catalog
                    await self._store.async_save(existing)

            self._catalog_refresh_cancel = async_track_time_interval(
                self.hass,
                self._async_refresh_catalog,
                timedelta(hours=24),
            )

            if "TIMING" in self.supported_dps:
                self._timer_inquiry_cancel = async_call_later(
                    self.hass, 5.0, self._async_request_schedules
                )

        except Exception as e:
            _LOGGER.error(
                "Failed to initialize coordinator for %s: %s", self.device_name, e
            )
            raise

    @callback
    def _on_mqtt_disconnect(self) -> None:
        """Handle MQTT disconnect and mark entities unavailable."""
        _LOGGER.warning("MQTT disconnected for %s; marking device unavailable", self.device_name)
        self.async_set_update_error(ConnectionError("MQTT disconnected"))

    @callback
    def _on_mqtt_reconnect(self) -> None:
        """Handle MQTT reconnect and restore entity availability."""
        _LOGGER.info("MQTT reconnected for %s; restoring device availability", self.device_name)
        self.async_set_updated_data(self.data)

    @callback
    def _handle_mqtt_message(self, payload: bytes) -> None:
        """Handle incoming MQTT message bytes."""
        try:
            # Parse MQTT wrapper and extract DPS data
            parsed = json.loads(payload.decode())
            payload_data = parsed.get("payload", {})
            # Payload can be a nested JSON string or a dict
            if isinstance(payload_data, str):
                payload_data = json.loads(payload_data)

            # Filter non-DPS protocol messages (cloud handshake/sync)
            protocol = payload_data.get("protocol")
            if protocol in (4, 5, 7):
                return

            if dps := payload_data.get("data"):
                # Calculate new state based on connection
                new_state, changes = update_state(
                    self.data,
                    dps,
                    dps_map=self.dps_map,
                    catalog_types=self.catalog_types,
                    dps_catalog=self.dps_catalog,
                )

                # Only consider debounce if dock_status was explicitly set in this message
                # This prevents messages without dock info (like DPS 154) from
                # incorrectly resetting the debounce timer
                if "dock_status" in changes:
                    new_dock = changes["dock_status"]

                    # Determine the status we are currently "heading towards"
                    target_dock = (
                        self._pending_dock_status
                        if self._pending_dock_status
                        else self.data.dock_status
                    )

                    # If the reported dock status differs from our target,
                    # restart the debounce timer
                    if new_dock != target_dock:
                        _LOGGER.debug(
                            "Dock status change: %s -> %s (committed: %s). Restarting debounce.",
                            target_dock,
                            new_dock,
                            self.data.dock_status,
                        )
                        if self._dock_idle_cancel:
                            self._dock_idle_cancel()

                        self._pending_dock_status = new_dock
                        self._dock_idle_cancel = async_call_later(
                            self.hass, 2.0, self._async_commit_dock_status
                        )

                # Always update the rest of the state immediately
                # But force dock_status to remain at the currently visible value
                # until the timer fires
                effective_current_status = self.data.dock_status
                state_to_publish = replace(
                    new_state, dock_status=effective_current_status
                )

                if any(
                    key in changes
                    for key in (
                        "ctrl_event_type",
                        "ctrl_event_source",
                        "ctrl_event_timestamp",
                    )
                ):
                    self.hass.bus.async_fire(
                        "robovac_mqtt_ctrl_event",
                        {
                            "device_id": self.device_id,
                            "event_type": state_to_publish.ctrl_event_type,
                            "event_source": state_to_publish.ctrl_event_source,
                            "timestamp": state_to_publish.ctrl_event_timestamp,
                        },
                    )

                self.async_set_updated_data(state_to_publish)

                # Track cleaning sessions
                if "task_status" in changes:
                    self._track_cleaning_session(state_to_publish)

                # Auto-enable entities when device reports new fields
                if "received_fields" in changes:
                    self._async_enable_new_entities(state_to_publish)

                # Check for segment changes if rooms were updated (debounced)
                if "rooms" in changes:
                    if self._segment_update_cancel:
                        self._segment_update_cancel()
                    self._segment_update_cancel = async_call_later(
                        self.hass, 2.0, self._async_commit_segment_changes
                    )

                if is_novelty_dirty():
                    self.hass.async_create_task(self._async_save_novelty())

        except Exception as e:
            _LOGGER.warning("Error handling MQTT message: %s", e)

    @callback
    def _async_enable_new_entities(self, state: VacuumState) -> None:
        """Enable entities disabled by integration when the device reports new fields."""
        ent_reg = er.async_get(self.hass)
        dev_reg = dr.async_get(self.hass)

        device_entry = dev_reg.async_get_device(identifiers={(DOMAIN, self.device_id)})
        if not device_entry:
            return

        received = state.received_fields
        for entity_entry in er.async_entries_for_device(
            ent_reg, device_entry.id, include_disabled_entities=True
        ):
            if (
                entity_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
                and entity_entry.unique_id.partition("_")[2] in received
            ):
                ent_reg.async_update_entity(entity_entry.entity_id, disabled_by=None)
                _LOGGER.info(
                    "Auto-enabled %s (device reported new data)",
                    entity_entry.entity_id,
                )

    @callback
    def _async_enable_new_entities_cb(self, _now: Any) -> None:
        self._enable_new_entities_cancel = None
        self._async_enable_new_entities(self.data)

    @callback
    def _async_commit_dock_status(self, _now: Any) -> None:
        """Commit the pending dock status."""
        self._dock_idle_cancel = None
        final_dock = self._pending_dock_status
        self._pending_dock_status = None

        if final_dock is None:
            _LOGGER.warning("Pending dock status was None when timer fired!")
            return

        # Apply the final dock status to the current data
        committed_state = replace(self.data, dock_status=final_dock)
        self.async_set_updated_data(committed_state)

    @callback
    def _async_commit_segment_changes(self, _now: Any) -> None:
        """Commit segment changes."""
        self._segment_update_cancel = None
        async_dispatcher_send(self.hass, f"{DOMAIN}_{self.device_id}_rooms_updated")

    @callback
    def _track_cleaning_session(self, state: VacuumState) -> None:
        """Track cleaning session start/end based on task_status transitions."""
        new_status = state.task_status
        prev_status = self._prev_task_status
        self._prev_task_status = new_status

        if new_status == "Cleaning" and prev_status not in _ACTIVE_SESSION_STATUSES:
            self._current_session = CleaningSession(
                start_time=dt_util.utcnow().isoformat(),
                trigger_source=state.trigger_source,
                rooms=(
                    [n.strip() for n in state.active_room_names.split(",") if n.strip()]
                    if state.active_room_names
                    else []
                ),
                scene_name=state.current_scene_name,
                fan_speed=state.fan_speed,
                work_mode=state.work_mode,
            )
            _LOGGER.debug("Cleaning session started: trigger=%s", state.trigger_source)
            return

        if self._current_session is None:
            return

        if new_status in _DOCK_VISIT_STATUSES and prev_status != new_status:
            self._current_session.dock_visits += 1
            return

        if new_status == "Completed":
            self._current_session.end_time = dt_util.utcnow().isoformat()
            self._current_session.duration_seconds = state.cleaning_time
            self._current_session.area_m2 = state.cleaning_area
            self._current_session.error_message = state.error_message or ""
            self._current_session.completed = True
            _LOGGER.info(
                "Cleaning session completed: %ds, %dm², %d dock visits",
                state.cleaning_time,
                state.cleaning_area,
                self._current_session.dock_visits,
            )
            self._cleaning_history.append(asdict(self._current_session))
            max_history = self.config_entry.options.get("max_cleaning_history", 100) if self.config_entry else 100
            self._cleaning_history = self._cleaning_history[-max_history:]
            self._current_session = None
            self.hass.async_create_task(self._async_save_cleaning_history())
            return

        if new_status not in _ACTIVE_SESSION_STATUSES and new_status not in (
            "",
            "unavailable",
        ):
            self._current_session.end_time = dt_util.utcnow().isoformat()
            self._current_session.duration_seconds = state.cleaning_time
            self._current_session.area_m2 = state.cleaning_area
            self._current_session.error_message = state.error_message or ""
            self._current_session.completed = False
            _LOGGER.warning(
                "Cleaning session aborted (status=%s): %ds, %dm²",
                new_status,
                state.cleaning_time,
                state.cleaning_area,
            )
            self._cleaning_history.append(asdict(self._current_session))
            max_history = self.config_entry.options.get("max_cleaning_history", 100) if self.config_entry else 100
            self._cleaning_history = self._cleaning_history[-max_history:]
            self._current_session = None
            self.hass.async_create_task(self._async_save_cleaning_history())

    async def _async_save_cleaning_history(self) -> None:
        """Persist cleaning history to store."""
        try:
            async with self._store_lock:
                existing = await self._store.async_load() or {}
                existing["cleaning_history"] = self._cleaning_history
                await self._store.async_save(existing)
        except Exception:
            _LOGGER.exception(
                "Failed to save cleaning history for %s", self.device_name
            )

    def async_shutdown_timers(self) -> None:
        """Cancel active debounce timers (call before teardown)."""
        if self._dock_idle_cancel:
            self._dock_idle_cancel()
            self._dock_idle_cancel = None
        if self._segment_update_cancel:
            self._segment_update_cancel()
            self._segment_update_cancel = None
        if self._catalog_refresh_cancel:
            self._catalog_refresh_cancel()
            self._catalog_refresh_cancel = None
        if self._timer_inquiry_cancel:
            self._timer_inquiry_cancel()
            self._timer_inquiry_cancel = None
        if self._enable_new_entities_cancel:
            self._enable_new_entities_cancel()
            self._enable_new_entities_cancel = None

    @callback
    def _async_request_schedules(self, _now: Any) -> None:
        self._timer_inquiry_cancel = None
        self.hass.async_create_task(self._async_send_timer_inquiry())

    async def _async_send_timer_inquiry(self) -> None:
        from .api.commands import build_command

        cmd = build_command("timer_inquiry", dps_map=self.dps_map)
        if cmd:
            await self.async_send_command(cmd)

    @callback
    def set_active_cleaning_targets(
        self,
        room_ids: list[int] | None = None,
        zone_count: int = 0,
    ) -> None:
        """Set active cleaning targets on state (called when HA sends commands)."""
        rooms = self.data.rooms
        if room_ids:
            room_lookup = {r["id"]: r.get("name", f"Room {r['id']}") for r in rooms}
            names = [room_lookup.get(rid, f"Room {rid}") for rid in room_ids]
            new_state = replace(
                self.data,
                active_room_ids=room_ids,
                active_room_names=", ".join(names),
                active_zone_count=0,
                current_scene_id=0,
                current_scene_name=None,
                received_fields=self.data.received_fields | {"active_room_ids"},
            )
        else:
            new_state = replace(
                self.data,
                active_room_ids=[],
                active_room_names="",
                active_zone_count=zone_count,
                current_scene_id=0,
                current_scene_name=None,
                received_fields=self.data.received_fields | {"active_room_ids"},
            )
        self.async_set_updated_data(new_state)

    @callback
    def set_active_scene(self, scene_id: int, scene_name: str | None) -> None:
        """Set the active cleaning scene on state."""
        new_state = replace(
            self.data,
            current_scene_id=scene_id,
            current_scene_name=scene_name,
            active_room_ids=[],
            active_room_names="",
            active_zone_count=0,
        )
        self.async_set_updated_data(new_state)

    async def async_send_command(self, command_dict: dict[str, Any]) -> None:
        """Send command to device."""
        if self.client:
            await self.client.send_command(command_dict)
        else:
            _LOGGER.warning("Cannot send command: no MQTT client available")

    async def _async_update_data(self) -> VacuumState:
        """Fetch data from API endpoint.

        For this integration, we rely on push updates.
        This method is called by RequestRefresh or polling.
        We can potentially fetch HTTP state here if needed as fallback.
        For now, just return current state.
        """
        return self.data

    async def async_load_storage(self) -> None:
        """Load data from storage."""
        if data := await self._store.async_load():
            self.last_seen_segments = data.get("last_seen_segments")

            if not self._raw_catalog:
                stored_catalog = data.get("dps_catalog")
                if stored_catalog:
                    self._raw_catalog = stored_catalog
                    self.dps_map = build_dps_map_from_catalog(stored_catalog)
                    self.supported_dps = supported_dps_from_catalog(stored_catalog)
                    self.dps_catalog = {
                        str(item.get("dp_id", "")): item for item in stored_catalog
                    }
                    self.catalog_types = {
                        str(item.get("dp_id", "")): item.get("data_type", "")
                        for item in stored_catalog
                    }
                    _LOGGER.info(
                        "Loaded stored DPS catalog for %s (%d entries)",
                        self.device_name,
                        len(stored_catalog),
                    )

            if novelty := data.get("novelty_caches"):
                load_novelty_caches(novelty)

            raw_history = data.get("cleaning_history", [])
            if not isinstance(raw_history, list):
                _LOGGER.warning(
                    "Cleaning history for %s is corrupted (type=%s), resetting",
                    self.device_name,
                    type(raw_history).__name__,
                )
                self._cleaning_history = []
            else:
                valid = []
                for entry in raw_history:
                    if (
                        isinstance(entry, dict)
                        and entry.get("start_time")
                        and "completed" in entry
                    ):
                        valid.append(entry)
                    else:
                        _LOGGER.warning(
                            "Dropping malformed cleaning history entry for %s: %s",
                            self.device_name,
                            entry,
                        )
                self._cleaning_history = valid
            max_history = self.config_entry.options.get("max_cleaning_history", 100) if self.config_entry else 100
            self._cleaning_history = self._cleaning_history[-max_history:]
            _LOGGER.debug(
                "Loaded %d cleaning history records for %s",
                len(self._cleaning_history),
                self.device_name,
            )

    async def _async_save_novelty(self) -> None:
        async with self._store_lock:
            existing = await self._store.async_load() or {}
            existing["novelty_caches"] = get_novelty_caches()
            await self._store.async_save(existing)
        clear_novelty_dirty()

    async def async_save_segments(self, segments_payload: list[dict[str, Any]]) -> None:
        """Save segments to storage."""
        self.last_seen_segments = segments_payload
        async with self._store_lock:
            existing = await self._store.async_load() or {}
            existing["last_seen_segments"] = segments_payload
            if self._raw_catalog:
                existing["dps_catalog"] = self._raw_catalog
            await self._store.async_save(existing)

    async def _async_refresh_catalog(self, _now: Any) -> None:
        """Periodically refresh the DPS catalog from the cloud (every 24h)."""
        try:
            new_catalog = await self.eufy_login.eufyApi.get_product_data_points(
                self.device_model
            )
            if new_catalog and new_catalog != self._raw_catalog:
                self._raw_catalog = new_catalog
                self.dps_map = build_dps_map_from_catalog(new_catalog)
                self.supported_dps = supported_dps_from_catalog(new_catalog)
                self.dps_catalog = {
                    str(item.get("dp_id", "")): item for item in new_catalog
                }
                self.catalog_types = {
                    str(item.get("dp_id", "")): item.get("data_type", "")
                    for item in new_catalog
                }
                async with self._store_lock:
                    existing = await self._store.async_load() or {}
                    existing["dps_catalog"] = new_catalog
                    await self._store.async_save(existing)
                _LOGGER.info(
                    "DPS catalog refreshed for %s (%d entries). "
                    "Changes take effect on next restart.",
                    self.device_name,
                    len(new_catalog),
                )
        except Exception as exc:
            _LOGGER.warning(
                "DPS catalog refresh failed for %s: %s", self.device_name, exc
            )
