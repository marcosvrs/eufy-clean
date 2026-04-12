from __future__ import annotations

import asyncio
import json
import logging
import os
import ssl
import tempfile
import time
from collections.abc import Callable
from typing import Any

import aiomqtt

_LOGGER = logging.getLogger(__name__)


class EufyCleanClient:
    """Handles low-level MQTT connectivity and protocol transport."""

    def __init__(
        self,
        device_id: str,
        user_id: str,
        app_name: str,
        thing_name: str,
        access_key: str,
        ticket: str,
        openudid: str,
        certificate_pem: str,
        private_key: str,
        device_model: str,
        endpoint: str,
    ) -> None:
        self.device_id = device_id
        self.user_id = user_id
        self.app_name = app_name
        self.thing_name = thing_name
        self.openudid = openudid
        self.certificate_pem = certificate_pem
        self.private_key = private_key
        self.device_model = device_model
        self.endpoint = endpoint

        self._client: aiomqtt.Client | None = None
        self._cert_path: str | None = None
        self._key_path: str | None = None
        self._client_id: str | None = None
        self._on_message_callback: Callable[[bytes], None] | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._connected = False
        self._connected_event = asyncio.Event()
        self._shutdown = False
        self._on_disconnect_callback: Callable[[], None] | None = None
        self._on_connect_callback: Callable[[], None] | None = None

        del access_key
        del ticket

    @property
    def connected(self) -> bool:
        """Return whether the MQTT client is connected."""
        return self._connected

    def set_on_message(self, callback: Callable[[bytes], None]) -> None:
        """Set callback for incoming raw MQTT payloads."""
        self._on_message_callback = callback

    def set_on_disconnect(self, callback: Callable[[], None]) -> None:
        """Set callback for disconnect events."""
        self._on_disconnect_callback = callback

    def set_on_connect(self, callback: Callable[[], None]) -> None:
        """Set callback for connect events."""
        self._on_connect_callback = callback

    def _write_cert_files(self) -> tuple[str, str]:
        """Write certificate and key to temp files."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem") as f:
            f.write(self.certificate_pem)
            cert_path = f.name

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".key") as f:
            f.write(self.private_key)
            key_path = f.name

        os.chmod(key_path, 0o600)
        return cert_path, key_path

    def _cleanup_cert_files(self) -> None:
        """Remove temporary certificate files."""
        for path_attr in ("_cert_path", "_key_path"):
            path = getattr(self, path_attr)
            if path:
                try:
                    os.unlink(path)
                except OSError as err:
                    _LOGGER.warning("Failed to delete %s: %s", path, err)
                setattr(self, path_attr, None)

    def _build_tls_params(self) -> aiomqtt.TLSParameters:
        """Build TLS parameters for aiomqtt connection."""
        self._cert_path, self._key_path = self._write_cert_files()
        return aiomqtt.TLSParameters(
            certfile=self._cert_path,
            keyfile=self._key_path,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )

    async def send_command(self, data_payload: dict[str, Any]) -> None:
        """Send a formatted command to the device."""
        if not self._connected:
            try:
                await asyncio.wait_for(self._connected_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                _LOGGER.error("Cannot send command: MQTT not connected (timeout)")
                return

        if not self._client:
            _LOGGER.error("Cannot send command: MQTT client not available")
            return

        try:
            timestamp = int(time.time() * 1000)
            payload = json.dumps(
                {
                    "account_id": self.user_id,
                    "data": data_payload,
                    "device_sn": self.device_id,
                    "protocol": 2,
                    "t": timestamp,
                }
            )

            client_id = (
                self._client_id
                or f"android-{self.app_name}-eufy_android_{self.openudid}_{self.user_id}"
            )

            mqtt_val = {
                "head": {
                    "client_id": client_id,
                    "cmd": 65537,
                    "cmd_status": 2,
                    "msg_seq": 1,
                    "seed": "",
                    "sess_id": client_id,
                    "sign_code": 0,
                    "timestamp": timestamp,
                    "version": "1.0.0.1",
                },
                "payload": payload,
            }

            topic = f"cmd/eufy_home/{self.device_model}/{self.device_id}/req"
            _LOGGER.debug("Sending command to %s: %s", topic, data_payload)
            await self.send_bytes(topic, json.dumps(mqtt_val).encode())
        except Exception as err:
            _LOGGER.error("Error sending command: %s", err)

    async def connect(self) -> None:
        """Start the MQTT listener task with auto-reconnect."""
        self._shutdown = False
        self._connected = False
        self._connected_event.clear()
        self._client_id = (
            f"android-{self.app_name}-eufy_android_{self.openudid}_{self.user_id}"
            f"-{int(time.time() * 1000)}"
        )

        if self._listener_task:
            await self.disconnect()
            self._shutdown = False
            self._connected = False
            self._connected_event.clear()

        self._listener_task = asyncio.create_task(self._run_listener())
        try:
            await asyncio.wait_for(self._connected_event.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            _LOGGER.error("Initial MQTT connection timed out after 30s")
            raise

    async def _run_listener(self) -> None:
        """Long-lived task: connect, listen, reconnect on failure."""
        response_topic = f"cmd/eufy_home/{self.device_model}/{self.device_id}/res"
        tls_params = self._build_tls_params()

        try:
            while True:
                if self._shutdown:
                    break
                try:
                    async with aiomqtt.Client(
                        hostname=self.endpoint,
                        port=8883,
                        tls_params=tls_params,
                        identifier=self._client_id,
                        username=self.thing_name,
                    ) as client:
                        self._client = client
                        self._connected = True
                        self._connected_event.set()
                        _LOGGER.info("Connected to MQTT broker at %s", self.endpoint)
                        if self._on_connect_callback:
                            self._on_connect_callback()

                        await client.subscribe(response_topic)
                        _LOGGER.debug("Subscribed to %s", response_topic)

                        async for message in client.messages:
                            if self._on_message_callback:
                                try:
                                    self._on_message_callback(bytes(message.payload))
                                except Exception:
                                    _LOGGER.exception("Error handling MQTT message")

                        self._mark_disconnected("MQTT message stream ended")
                except aiomqtt.MqttError as err:
                    self._mark_disconnected(
                        f"MQTT disconnected: {err} — reconnecting in 5s..."
                    )
                    await asyncio.sleep(5)
                except Exception as err:
                    self._mark_disconnected(
                        f"Unexpected MQTT error: {err} — reconnecting in 10s...",
                        unexpected=True,
                    )
                    await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise
        finally:
            self._client = None
            self._connected = False
            self._connected_event.clear()
            self._cleanup_cert_files()

    def _mark_disconnected(self, message: str, unexpected: bool = False) -> None:
        """Clear connection state and notify listeners if needed."""
        was_connected = self._connected
        self._connected = False
        self._connected_event.clear()
        self._client = None

        if was_connected:
            if unexpected:
                _LOGGER.error(message)
            else:
                _LOGGER.warning(message)
            if self._on_disconnect_callback:
                self._on_disconnect_callback()
        elif unexpected:
            _LOGGER.error(message)
        else:
            _LOGGER.debug(message)

    async def disconnect(self) -> None:
        """Disconnect and clean up."""
        self._shutdown = True
        self._connected = False
        self._connected_event.clear()

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        self._client = None
        self._cleanup_cert_files()

    async def send_bytes(self, topic: str, payload: bytes) -> None:
        """Send raw bytes to the device."""
        if not self._connected:
            try:
                await asyncio.wait_for(self._connected_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                _LOGGER.error("Cannot send message: MQTT not connected (timeout)")
                return

        if not self._client:
            _LOGGER.error("Cannot send message: MQTT client not connected")
            return

        await self._client.publish(topic, payload)
