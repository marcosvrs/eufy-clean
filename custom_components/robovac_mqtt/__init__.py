from __future__ import annotations

import logging
import random
import string
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_time_interval

from .api.cloud import EufyLogin
from .api.http import EufyAuthError, EufyConnectionError
from .const import DOMAIN
from .coordinator import EufyCleanCoordinator
from .models import EufyCleanData
from .typing_defs import EufyCleanConfigEntry

PLATFORMS: list[Platform] = [
    Platform.VACUUM,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.BINARY_SENSOR,
    Platform.TIME,
    Platform.CALENDAR,
    Platform.EVENT,
]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: EufyCleanConfigEntry) -> bool:
    """Initialize the integration."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    # Generate OpenUDID (consistent per session)
    openudid = "".join(random.choices(string.hexdigits, k=32))

    # Initialize Login Controller
    session = async_get_clientsession(hass)
    eufy_login = EufyLogin(username, password, openudid, session=session)
    try:
        await eufy_login.init()
    except EufyAuthError as err:
        raise ConfigEntryAuthFailed from err
    except EufyConnectionError as err:
        raise ConfigEntryNotReady from err
    except Exception as e:
        _LOGGER.error("Failed to initialize Eufy Clean: %s", e)
        raise ConfigEntryNotReady from e

    coordinators: dict[str, EufyCleanCoordinator] = {}

    # Get Devices and create coordinators
    # eufy_login.mqtt_devices populated by init/getDevices
    # mqtt_devices is a list of dicts with device info
    mqtt_devices = eufy_login.mqtt_devices
    is_multi_device = len(mqtt_devices) > 1

    for device_info in mqtt_devices:
        device_id = device_info.get("deviceId")
        if not device_id:
            continue

        _LOGGER.debug(
            "Found device: %s (%s)",
            device_info.get("deviceName", "Unknown"),
            device_id,
        )

        coordinator = EufyCleanCoordinator(hass, eufy_login, device_info, config_entry=entry)
        try:
            await coordinator.initialize()

            # Migrate segments from config entry data to per-device Store.
            # Only migrate if the store is empty and we have a single device
            # to avoid overwriting newer data or assigning to wrong device.
            if last_seen := entry.data.get("last_seen_segments"):
                if is_multi_device:
                    _LOGGER.info(
                        "Skipping migration of last seen segments for %s due to multi-device setup",
                        device_id,
                    )
                elif not coordinator.last_seen_segments:
                    await coordinator.async_save_segments(last_seen)
                    _LOGGER.info(
                        "Migrated last seen segments for %s to persistent storage",
                        device_id,
                    )

            coordinators[device_id] = coordinator
        except Exception as e:
            _LOGGER.warning("Failed to initialize coordinator for %s: %s", device_id, e)

    if not coordinators:
        _LOGGER.warning("No Eufy Clean devices found or initialized.")
        # We generally return True anyway to avoid blocking HA startup,
        # unless critical failure?
        # But if no devices, nothing to do.

    # Check for orphaned devices and log warnings
    current_device_ids = set(coordinators.keys())
    device_registry = dr.async_get(hass)
    registry_devices = dr.async_entries_for_config_entry(
        device_registry, entry.entry_id
    )

    for device_entry in registry_devices:
        # Extract our domain's device ID from identifiers set
        eufy_id = next(
            (id[1] for id in device_entry.identifiers if id[0] == DOMAIN), None
        )

        if eufy_id and eufy_id not in current_device_ids:
            _LOGGER.warning(
                "Device %s (%s) is registered but was not returned by the Eufy API. "
                "It will be shown as unavailable. You can manually remove it if it was deleted from your account.",
                device_entry.name_by_user or device_entry.name,
                eufy_id,
            )

    entry.runtime_data = EufyCleanData(coordinators=coordinators, cloud=eufy_login)

    # Clean up migrated data from config entry (skip for multi-device to avoid
    # deleting data that was intentionally not migrated)
    if "last_seen_segments" in entry.data and not is_multi_device:
        new_data = dict(entry.data)
        new_data.pop("last_seen_segments")
        hass.config_entries.async_update_entry(entry, data=new_data)
        _LOGGER.info(
            "Removed legacy last_seen_segments from config entry %s", entry.entry_id
        )

    entry.async_on_unload(entry.add_update_listener(update_listener))

    entry.async_on_unload(
        async_track_time_interval(
            hass,
            lambda _now: hass.async_create_task(_async_check_new_devices(hass, entry)),
            timedelta(hours=1),
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EufyCleanConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        for coordinator in entry.runtime_data.coordinators.values():
            coordinator.async_shutdown_timers()
            if coordinator.client:
                await coordinator.client.disconnect()

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: EufyCleanConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove a config entry device — only allow if device is not in cloud list."""
    eufy_id = next(
        (identifier[1] for identifier in device_entry.identifiers if identifier[0] == DOMAIN),
        None,
    )
    if not eufy_id:
        return True

    cloud = config_entry.runtime_data.cloud
    if not cloud.mqtt_devices:
        _LOGGER.warning(
            "Cannot verify device %s — cloud device list not loaded. Blocking removal.",
            eufy_id,
        )
        return False

    cloud_ids = {d.get("deviceId") for d in cloud.mqtt_devices}
    if eufy_id in cloud_ids:
        return False

    return True


async def _async_check_new_devices(
    hass: HomeAssistant, entry: EufyCleanConfigEntry
) -> None:
    cloud = entry.runtime_data.cloud
    try:
        await cloud.getDevices()
    except Exception:
        _LOGGER.debug("Periodic device refresh failed", exc_info=True)
        return

    current_ids = set(entry.runtime_data.coordinators.keys())
    cloud_ids = {d.get("deviceId") for d in cloud.mqtt_devices if d.get("deviceId")}

    new_ids = cloud_ids - current_ids
    if new_ids:
        _LOGGER.info("New devices detected: %s — reloading integration", new_ids)
        await hass.config_entries.async_reload(entry.entry_id)


async def update_listener(hass: HomeAssistant, entry: EufyCleanConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
