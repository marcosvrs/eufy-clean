from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .api.cloud import EufyLogin
    from .coordinator import EufyCleanCoordinator


class EufyDeviceInfo(TypedDict, total=False):
    """Known cloud/device fields used by the integration."""

    deviceId: str
    deviceModel: str
    deviceName: str
    deviceModelName: str
    invalid: bool
    apiType: str
    mqtt: bool
    dps: dict[str, Any]  # justified: DPS payload is device/proto-driven
    softVersion: str
    dps_catalog: list[dict[str, object]]


class MqttCredentials(TypedDict):
    """MQTT credentials returned by the Eufy cloud API."""

    user_id: str
    app_name: str
    thing_name: str
    certificate_pem: str
    private_key: str
    endpoint_addr: str


type CoordinatorMap = dict[str, EufyCleanCoordinator]


class EufyCleanRuntimeData(TypedDict):
    """Typed view of runtime data if needed outside dataclass usage."""

    coordinators: CoordinatorMap
    cloud: EufyLogin


type EufyCleanConfigEntry = ConfigEntry["EufyCleanData"]


if TYPE_CHECKING:
    from .models import EufyCleanData
