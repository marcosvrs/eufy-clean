from __future__ import annotations

import logging
from typing import Any

import aiohttp

from ..const import DEFAULT_DPS_MAP
from ..typing_defs import EufyDeviceInfo, MqttCredentials
from .http import EufyHTTPClient

_LOGGER = logging.getLogger(__name__)


class EufyLoginError(Exception):
    """Eufy Login Error."""


class EufyLogin:
    def __init__(
        self,
        username: str,
        password: str,
        openudid: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.eufyApi = EufyHTTPClient(username, password, openudid, session=session)
        self.username = username
        self.password = password
        self.openudid = openudid
        self.mqtt_credentials: MqttCredentials | None = None
        self.mqtt_devices: list[EufyDeviceInfo] = []
        self.eufy_api_devices: list[dict[str, Any]] = []

    async def init(self) -> None:
        await self.login({"mqtt": True})
        await self.getDevices()

    async def login(self, config: dict[str, bool]) -> None:
        if not config["mqtt"]:
            raise EufyLoginError("MQTT login is required")

        eufy_login = await self.eufyApi.login()

        if not eufy_login:
            raise EufyLoginError("Login failed")

        self.mqtt_credentials = eufy_login["mqtt"]

    async def checkLogin(self) -> None:
        if not self.mqtt_credentials:
            await self.login({"mqtt": True})

    async def getDevices(self) -> None:
        self.eufy_api_devices = await self.eufyApi.get_cloud_device_list()
        raw_devices = await self.eufyApi.get_device_list()

        product_codes: set[str] = set()
        device_models: dict[str, str] = {}
        for device in raw_devices:
            model_info = self.findModel(device["device_sn"])
            if not model_info["invalid"]:
                code = model_info["deviceModel"]
                if code:
                    product_codes.add(code)
                    device_models[device["device_sn"]] = code

        catalogs: dict[str, list[dict[str, Any]]] = {}
        for code in product_codes:
            try:
                catalogs[code] = await self.eufyApi.get_product_data_points(code)
            except Exception as exc:
                _LOGGER.debug("Unexpected error fetching catalog for %s: %s", code, exc)
                catalogs[code] = []

        devices: list[EufyDeviceInfo] = []
        for device in raw_devices:
            sn = device["device_sn"]
            model_info = self.findModel(sn)
            product_code = device_models.get(sn, "")
            devices.append(
                {
                    **model_info,
                    "apiType": self.checkApiType(device.get("dps", {})),
                    "mqtt": True,
                    "dps": device.get("dps", {}),
                    "softVersion": device.get("main_sw_version")
                    or device.get("soft_version")
                    or "",
                    "dps_catalog": catalogs.get(product_code, []),
                }
            )

        self.mqtt_devices = [d for d in devices if not d["invalid"]]

    async def getMqttDevice(self, deviceId: str) -> dict[str, Any] | None:
        devices = await self.eufyApi.get_device_list()
        return next((d for d in devices if d.get("device_sn") == deviceId), None)

    @staticmethod
    def checkApiType(dps: dict[str, Any]) -> str:
        if any(k in dps for k in DEFAULT_DPS_MAP.values()):
            return "novel"
        return "legacy"

    def findModel(self, deviceId: str) -> EufyDeviceInfo:
        device = next((d for d in self.eufy_api_devices if d["id"] == deviceId), None)

        if device:
            product = device.get("product", {})
            product_code = product.get("product_code", "") if isinstance(product, dict) else ""
            product_name = product.get("name") if isinstance(product, dict) else None
            device_name = device.get("alias_name") or device.get("device_name") or device.get("name")
            return {
                "deviceId": deviceId,
                "deviceModel": str(product_code)[:5] or str(device.get("device_model", ""))[:5],
                "deviceName": str(device_name or ""),
                "deviceModelName": str(product_name or ""),
                "invalid": False,
            }

        return {
            "deviceId": deviceId,
            "deviceModel": "",
            "deviceName": "",
            "deviceModelName": "",
            "invalid": True,
        }
