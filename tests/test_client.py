"""Unit tests for the MQTT client (api/client.py)."""

# pyright: reportAny=false, reportPrivateUsage=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUnannotatedClassAttribute=false, reportUnknownParameterType=false

import asyncio
import os
from collections.abc import AsyncIterator
from types import SimpleNamespace
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import aiomqtt
import pytest

from custom_components.robovac_mqtt.api.client import EufyCleanClient


def _make_client() -> EufyCleanClient:
    """Create a EufyCleanClient instance for testing."""
    return EufyCleanClient(
        device_id="TEST123",
        user_id="user1",
        app_name="eufy_home",
        thing_name="thing1",
        access_key="",
        ticket="",
        openudid="abc123",
        certificate_pem="cert",
        private_key="key",
        device_model="T2320",
        endpoint="mqtt.example.com",
    )


class _FakeMessages:
    """Async iterable wrapper for fake MQTT messages."""

    def __init__(self, payloads: list[bytes]) -> None:
        self._payloads = payloads

    def __aiter__(self) -> AsyncIterator[SimpleNamespace]:
        return self._iterator()

    async def _iterator(self) -> AsyncIterator[SimpleNamespace]:
        for payload in self._payloads:
            yield SimpleNamespace(payload=payload)


class _FakeAiomqttClient:
    """Minimal aiomqtt client context manager for listener tests."""

    def __init__(self, payloads: list[bytes] | None = None) -> None:
        self.payloads = payloads or []
        self.messages = _FakeMessages(self.payloads)
        self.subscribe = AsyncMock()
        self.publish = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_send_command_not_connected_times_out() -> None:
    """send_command exits when MQTT does not reconnect in time."""
    client = _make_client()

    await client.send_command({"test": "value"})


@pytest.mark.asyncio
async def test_send_command_connected_publishes_expected_payload() -> None:
    """send_command publishes to the expected topic and payload shape."""
    client = _make_client()
    client._connected = True
    client._connected_event.set()
    client._client_id = "client-123"
    client._client = MagicMock()
    client._client.publish = AsyncMock()

    await client.send_command({"test": "value"})

    client._client.publish.assert_awaited_once()
    topic, payload = client._client.publish.await_args.args
    assert topic == "cmd/eufy_home/T2320/TEST123/req"
    assert b'"client_id": "client-123"' in payload
    assert b'\\"device_sn\\": \\"TEST123\\"' in payload
    assert b'\\"test\\": \\"value\\"' in payload


@pytest.mark.asyncio
async def test_send_bytes_not_connected_times_out() -> None:
    """send_bytes exits when MQTT does not reconnect in time."""
    client = _make_client()

    await client.send_bytes("topic", b"payload")


def test_mark_disconnected_calls_callback_only_after_connection() -> None:
    """Disconnect callback is only fired after an established connection."""
    client = _make_client()
    callback = MagicMock()
    client.set_on_disconnect(callback)

    client._mark_disconnected("first")
    callback.assert_not_called()

    client._connected = True
    client._connected_event.set()
    client._client = MagicMock()

    client._mark_disconnected("second")

    callback.assert_called_once()
    assert not client._connected
    assert client._client is None
    assert not client._connected_event.is_set()


def test_build_tls_params_writes_temp_files() -> None:
    """TLS parameters reuse temp cert and key files."""
    client = _make_client()

    tls_params = client._build_tls_params()

    assert tls_params.certfile == client._cert_path
    assert tls_params.keyfile == client._key_path
    assert client._cert_path is not None
    assert client._key_path is not None
    assert os.path.exists(client._cert_path)
    assert os.path.exists(client._key_path)

    client._cleanup_cert_files()


@pytest.mark.asyncio
async def test_disconnect_cleans_temp_files_and_cancels_listener() -> None:
    """disconnect removes temp files and cancels active listener task."""
    client = _make_client()

    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem")
    key_fd, key_path = tempfile.mkstemp(suffix=".key")
    os.close(cert_fd)
    os.close(key_fd)

    client._cert_path = cert_path
    client._key_path = key_path

    async def _sleep_forever() -> None:
        await asyncio.sleep(3600)

    client._listener_task = asyncio.create_task(_sleep_forever())

    await client.disconnect()

    assert client._listener_task is None
    assert client._client is None
    assert not client._connected
    assert not client._connected_event.is_set()
    assert not os.path.exists(cert_path)
    assert not os.path.exists(key_path)
    assert client._cert_path is None
    assert client._key_path is None


@pytest.mark.asyncio
async def test_connect_starts_listener_and_waits_for_connection() -> None:
    """connect spawns the listener and waits for initial connection."""
    client = _make_client()

    async def _fake_run_listener() -> None:
        client._connected = True
        client._connected_event.set()

    with patch.object(client, "_run_listener", new=AsyncMock(side_effect=_fake_run_listener)):
        await client.connect()

    assert client._listener_task is not None
    await client._listener_task
    assert client._client_id is not None


@pytest.mark.asyncio
async def test_build_tls_params_passes_expected_tls_settings() -> None:
    """TLS parameters use client cert/key with TLS 1.2 required."""
    client = _make_client()

    tls_params = client._build_tls_params()

    assert tls_params.certfile == client._cert_path
    assert tls_params.keyfile == client._key_path
    assert tls_params.cert_reqs is not None
    assert tls_params.tls_version is not None
    client._cleanup_cert_files()


@pytest.mark.asyncio
async def test_run_listener_connects_subscribes_and_receives_messages() -> None:
    """Listener configures aiomqtt, subscribes, and forwards payloads."""
    client = _make_client()
    on_message = MagicMock(side_effect=lambda payload: setattr(client, "_shutdown", True))
    on_connect = MagicMock()
    client.set_on_message(on_message)
    client.set_on_connect(on_connect)

    fake_mqtt_client = _FakeAiomqttClient([b"hello"])

    with (
        patch.object(client, "_build_tls_params", return_value="tls-params"),
        patch("custom_components.robovac_mqtt.api.client.aiomqtt.Client", return_value=fake_mqtt_client) as mock_client,
    ):
        await client._run_listener()

    mock_client.assert_called_once()
    kwargs = mock_client.call_args.kwargs
    assert kwargs["hostname"] == "mqtt.example.com"
    assert kwargs["port"] == 8883
    assert kwargs["tls_params"] == "tls-params"
    assert kwargs["username"] == "thing1"
    fake_mqtt_client.subscribe.assert_awaited_once_with(
        "cmd/eufy_home/T2320/TEST123/res"
    )
    on_connect.assert_called_once()
    on_message.assert_called_once_with(b"hello")


@pytest.mark.asyncio
async def test_send_bytes_publishes_when_connected() -> None:
    """send_bytes publishes directly through the aiomqtt client."""
    client = _make_client()
    mqtt_client = _FakeAiomqttClient()
    client._client = mqtt_client
    client._connected = True
    client._connected_event.set()

    await client.send_bytes("topic/test", b"payload")

    mqtt_client.publish.assert_awaited_once_with("topic/test", b"payload")


@pytest.mark.asyncio
async def test_run_listener_marks_disconnected_and_reconnects_after_mqtt_error() -> None:
    """MQTT errors clear connection state and trigger reconnect delay."""
    client = _make_client()
    client._client_id = "client-123"
    mqtt_error = aiomqtt.MqttError("boom")

    with (
        patch.object(client, "_build_tls_params", return_value="tls-params"),
        patch(
            "custom_components.robovac_mqtt.api.client.aiomqtt.Client",
            side_effect=[mqtt_error, asyncio.CancelledError()],
        ),
        patch("custom_components.robovac_mqtt.api.client.asyncio.sleep", new=AsyncMock()) as mock_sleep,
        patch.object(client, "_mark_disconnected") as mock_mark,
    ):
        with pytest.raises(asyncio.CancelledError):
            await client._run_listener()

    mock_mark.assert_called_once()
    assert "reconnecting in 5s" in mock_mark.call_args.args[0]
    mock_sleep.assert_awaited_once_with(5)


@pytest.mark.asyncio
async def test_connect_times_out_when_initial_connection_never_happens() -> None:
    """connect raises TimeoutError when no connection is established."""
    client = _make_client()

    with patch.object(client, "_run_listener", new=AsyncMock()):
        with pytest.raises(asyncio.TimeoutError):
            await client.connect()
