from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

import aiohttp

from ..const import (
    EUFY_API_DEVICE_LIST,
    EUFY_API_DEVICE_V2,
    EUFY_API_LOGIN,
    EUFY_API_MQTT_INFO,
    EUFY_API_PRODUCT_DATA_POINT,
    EUFY_API_USER_INFO,
)

_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)

_LOGGER = logging.getLogger(__name__)


def _as_dict(value: Any) -> dict[str, Any]:
    """Return a JSON object as a typed dict."""
    return cast(dict[str, Any], value)


def _as_list_of_dicts(value: Any) -> list[dict[str, Any]]:
    """Return a JSON array of objects with a typed shape."""
    return cast(list[dict[str, Any]], value)


class EufyCleanError(Exception):
    """Base exception for Eufy Clean API."""


class EufyAuthError(EufyCleanError):
    """Authentication failure — wrong credentials or token expired."""


class EufyConnectionError(EufyCleanError):
    """Network or connection failure — API server unreachable."""


class EufyHTTPClient:
    """HTTP Client for Eufy Authentication and Device Discovery."""

    def __init__(
        self,
        username: str,
        password: str,
        openudid: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.username = username
        self.password = password
        self.openudid = openudid
        self._http_session = session
        self.session: dict[str, Any] | None = None
        self.user_info: dict[str, Any] | None = None

    @asynccontextmanager
    async def _session_ctx(self) -> AsyncIterator[aiohttp.ClientSession]:
        """Yield injected session or a temporary session."""
        session = self._http_session
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT)
        assert session is not None
        try:
            yield session
        finally:
            if own_session:
                await session.close()

    async def login(self, validate_only: bool = False) -> dict[str, Any]:
        """Perform login flow."""
        session = await self.eufy_login()

        if validate_only:
            return {"session": session}

        user = await self.get_user_info()
        mqtt = await self.get_mqtt_credentials()
        return {"session": session, "user": user, "mqtt": mqtt}

    async def eufy_login(self) -> dict[str, Any]:
        """Login to Eufy Cloud."""
        try:
            async with self._session_ctx() as session:
                async with session.post(
                    EUFY_API_LOGIN,
                    headers={
                        "category": "Home",
                        "Accept": "*/*",
                        "openudid": self.openudid,
                        "Content-Type": "application/json",
                        "clientType": "1",
                        "User-Agent": "EufyHome-Android-3.1.3-753",
                        "Connection": "keep-alive",
                    },
                    json={
                        "email": self.username,
                        "password": self.password,
                        "client_id": "eufyhome-app",
                        "client_secret": "GQCpr9dSp3uQpsOMgJ4xQ",
                    },
                ) as response:
                    response_json = None
                    try:
                        response_json = await response.json()
                    except Exception:
                        _LOGGER.warning(
                            "Failed to parse login response as JSON", exc_info=True
                        )

                    if (
                        response.status == 200
                        and response_json
                        and response_json.get("access_token")
                    ):
                        _LOGGER.debug("eufyLogin successful")
                        self.session = _as_dict(response_json)
                        return self.session

                    body = response_json or await response.text()
                    _LOGGER.error("Login failed: %s %s", response.status, body)
                    if response.status in (401, 403):
                        raise EufyAuthError("Invalid credentials")
                    raise EufyConnectionError(f"Login failed: {response.status}")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EufyConnectionError(str(err)) from err

    async def get_user_info(self) -> dict[str, Any] | None:
        """Get User details."""
        if not self.session:
            _LOGGER.warning("get_user_info called without active session")
            return None

        try:
            async with self._session_ctx() as session:
                async with session.get(
                    EUFY_API_USER_INFO,
                    headers={
                        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                        "user-agent": "EufyHome-Android-3.1.3-753",
                        "category": "Home",
                        "token": self.session["access_token"],
                        "openudid": self.openudid,
                        "clienttype": "2",
                    },
                ) as response:
                    if response.status == 200:
                        self.user_info = await response.json()
                        if self.user_info is None or not self.user_info.get(
                            "user_center_id"
                        ):
                            _LOGGER.error("No user_center_id found")
                            return None

                        self.user_info["gtoken"] = hashlib.md5(
                            self.user_info["user_center_id"].encode()
                        ).hexdigest()
                        return self.user_info

                    if response.status in (401, 403):
                        raise EufyAuthError("Authentication failed")

                    _LOGGER.error("get user center info failed")
                    _LOGGER.warning(
                        "get_user_info returning None due to unexpected status %s",
                        response.status,
                    )
                    return None
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EufyConnectionError(str(err)) from err

    async def get_device_list(self) -> list[dict[str, Any]]:
        """Get list of devices."""
        if not self.user_info:
            _LOGGER.error("Cannot get device list: user_info is None")
            return []

        try:
            async with self._session_ctx() as session:
                async with session.post(
                    EUFY_API_DEVICE_LIST,
                    headers={
                        "user-agent": "EufyHome-Android-3.1.3-753",
                        "openudid": self.openudid,
                        "os-version": "Android",
                        "model-type": "PHONE",
                        "app-name": "eufy_home",
                        "x-auth-token": self.user_info["user_center_token"],
                        "gtoken": self.user_info["gtoken"],
                        "content-type": "application/json; charset=UTF-8",
                    },
                    json={"attribute": 3},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        devices = data.get("data", {}).get("devices")
                        if not devices:
                            _LOGGER.warning("get_device_list returned no devices")
                            return []
                        return [device["device"] for device in devices]
                    if response.status in (401, 403):
                        raise EufyAuthError("Authentication failed")
                    _LOGGER.warning(
                        "get_device_list failed: status %s", response.status
                    )
                    return []
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EufyConnectionError(str(err)) from err

    async def get_product_data_points(self, product_code: str) -> list[dict[str, Any]]:
        if not self.user_info:
            _LOGGER.warning("Cannot get product data points: user_info is None")
            return []

        try:
            async with self._session_ctx() as session:
                async with session.post(
                    EUFY_API_PRODUCT_DATA_POINT,
                    headers={
                        "user-agent": "EufyHome-Android-3.1.3-753",
                        "openudid": self.openudid,
                        "os-version": "Android",
                        "model-type": "PHONE",
                        "app-name": "eufy_home",
                        "x-auth-token": self.user_info["user_center_token"],
                        "gtoken": self.user_info["gtoken"],
                        "content-type": "application/json; charset=UTF-8",
                    },
                    json={"product_code": product_code, "code": product_code},
                ) as response:
                    if response.status == 200:
                        data = _as_dict(await response.json())
                        return _as_list_of_dicts(
                            data.get("data", {}).get("data_point_list", [])
                        )
                    if response.status in (401, 403):
                        raise EufyAuthError("Authentication failed")
                    _LOGGER.warning(
                        "get_product_data_points failed for %s: status %s",
                        product_code,
                        response.status,
                    )
                    return []
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise EufyConnectionError(str(exc)) from exc
        except EufyAuthError:
            raise
        except Exception as exc:
            _LOGGER.warning(
                "get_product_data_points failed for %s: %s", product_code, exc
            )
            return []

    async def get_cloud_device_list(self) -> list[dict[str, Any]]:
        """Get cloud device list (V2)."""
        if not self.session:
            _LOGGER.error("Cannot get cloud device list: no session")
            return []

        try:
            async with self._session_ctx() as session:
                async with session.get(
                    EUFY_API_DEVICE_V2,
                    headers={
                        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                        "user-agent": "EufyHome-Android-3.1.3-753",
                        "category": "Home",
                        "token": self.session["access_token"],
                        "openudid": self.openudid,
                        "clienttype": "2",
                    },
                ) as response:
                    if response.status == 200:
                        data = _as_dict(await response.json())
                        return _as_list_of_dicts(data.get("devices", []))
                    if response.status in (401, 403):
                        raise EufyAuthError("Authentication failed")
                    _LOGGER.warning(
                        "get_cloud_device_list failed: status %s", response.status
                    )
                    return []
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EufyConnectionError(str(err)) from err

    async def get_mqtt_credentials(self) -> dict[str, Any] | None:
        """Get MQTT credentials."""
        if not self.user_info:
            _LOGGER.error("Cannot get MQTT credentials: user_info is None")
            return None

        try:
            async with self._session_ctx() as session:
                async with session.post(
                    EUFY_API_MQTT_INFO,
                    headers={
                        "content-type": "application/json",
                        "user-agent": "EufyHome-Android-3.1.3-753",
                        "openudid": self.openudid,
                        "os-version": "Android",
                        "model-type": "PHONE",
                        "app-name": "eufy_home",
                        "x-auth-token": self.user_info["user_center_token"],
                        "gtoken": self.user_info["gtoken"],
                    },
                ) as response:
                    if response.status == 200:
                        data = _as_dict(await response.json()).get("data")
                        if isinstance(data, dict):
                            return _as_dict(data)
                        _LOGGER.warning(
                            "get_mqtt_credentials returned no credential payload"
                        )
                        return None
                    if response.status in (401, 403):
                        raise EufyAuthError("Authentication failed")
                    _LOGGER.warning(
                        "get_mqtt_credentials failed: status %s", response.status
                    )
                    return None
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EufyConnectionError(str(err)) from err
