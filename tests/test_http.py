"""Tests for the Eufy HTTP client."""

# pyright: reportAny=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnusedCallResult=false

from __future__ import annotations

import aiohttp
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.robovac_mqtt.api.http import (
    _REQUEST_TIMEOUT,
    EufyAuthError,
    EufyConnectionError,
    EufyHTTPClient,
)


def _make_client() -> EufyHTTPClient:
    """Create an EufyHTTPClient with dummy credentials."""
    return EufyHTTPClient(
        username="test@example.com",
        password="secret",
        openudid="abc123",
    )


def _mock_aiohttp_session(mock_response: AsyncMock) -> MagicMock:
    """Build a mock aiohttp.ClientSession that yields *mock_response* for any request."""
    # The inner context manager (session.post(...)) must be a non-async MagicMock
    # so that `async with session.post(...)` works without awaiting post() first.
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_response)
    ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.close = AsyncMock()
    mock_session.post.return_value = ctx
    mock_session.get.return_value = ctx

    return mock_session


def _make_injected_session(mock_response: AsyncMock) -> MagicMock:
    """Build an injected session compatible with _session_ctx()."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_response)
    ctx.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock(spec=aiohttp.ClientSession)
    session.post.return_value = ctx
    session.get.return_value = ctx
    session.close = AsyncMock()
    return session


# --- None-guard tests (no HTTP calls) ---


@pytest.mark.asyncio
async def test_get_user_info_returns_none_without_session():
    """get_user_info() should return None when session is not set."""
    client = _make_client()
    assert client.session is None
    result = await client.get_user_info()
    assert result is None


@pytest.mark.asyncio
async def test_get_device_list_returns_empty_without_user_info():
    """get_device_list() should return [] when user_info is not set."""
    client = _make_client()
    assert client.user_info is None
    result = await client.get_device_list()
    assert result == []


@pytest.mark.asyncio
async def test_get_product_data_points_returns_empty_without_user_info():
    client = _make_client()
    assert client.user_info is None
    with patch("aiohttp.ClientSession") as mock_session:
        result = await client.get_product_data_points("T2351")

    mock_session.assert_not_called()
    assert result == []


@pytest.mark.asyncio
async def test_eufy_login_json_parse_exception_logs_debug(caplog):
    """eufy_login() logs debug and raises when JSON parsing fails."""
    client = _make_client()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.side_effect = Exception("json decode error")
    mock_response.text = AsyncMock(return_value="bad json")

    with patch(
        "aiohttp.ClientSession", return_value=_mock_aiohttp_session(mock_response)
    ):
        with caplog.at_level(
            logging.DEBUG, logger="custom_components.robovac_mqtt.api.http"
        ):
            with pytest.raises(EufyConnectionError, match="Login failed: 200"):
                await client.eufy_login()

    assert "Failed to parse login response as JSON" in caplog.text


@pytest.mark.asyncio
async def test_get_device_list_non_200_logs_warning(caplog):
    """get_device_list() logs warning when response status is not 200."""
    client = _make_client()
    client.user_info = {"user_center_token": "tok", "gtoken": "g"}
    mock_response = AsyncMock()
    mock_response.status = 503
    mock_response.json = AsyncMock(return_value={})

    with patch(
        "aiohttp.ClientSession", return_value=_mock_aiohttp_session(mock_response)
    ):
        with caplog.at_level(
            logging.WARNING, logger="custom_components.robovac_mqtt.api.http"
        ):
            result = await client.get_device_list()

    assert result == []
    assert "get_device_list failed" in caplog.text
    assert "503" in caplog.text


@pytest.mark.asyncio
async def test_get_product_data_points_none_user_info_logs_warning(caplog):
    """get_product_data_points() logs warning when user_info is None."""
    client = _make_client()
    assert client.user_info is None

    with caplog.at_level(
        logging.WARNING, logger="custom_components.robovac_mqtt.api.http"
    ):
        result = await client.get_product_data_points("T2261")

    assert result == []
    assert "Cannot get product data points" in caplog.text


@pytest.mark.asyncio
async def test_get_cloud_device_list_non_200_logs_warning(caplog):
    """get_cloud_device_list() logs warning when response status is not 200."""
    client = _make_client()
    client.session = {"access_token": "token123"}
    mock_response = AsyncMock()
    mock_response.status = 503
    mock_response.json = AsyncMock(return_value={})

    with patch(
        "aiohttp.ClientSession", return_value=_mock_aiohttp_session(mock_response)
    ):
        with caplog.at_level(
            logging.WARNING, logger="custom_components.robovac_mqtt.api.http"
        ):
            result = await client.get_cloud_device_list()

    assert result == []
    assert "get_cloud_device_list failed" in caplog.text
    assert "503" in caplog.text


@pytest.mark.asyncio
async def test_get_cloud_device_list_raises_auth_error_on_401():
    """get_cloud_device_list() raises auth error for expired credentials."""
    client = _make_client()
    client.session = {"access_token": "token123"}
    mock_response = AsyncMock()
    mock_response.status = 401
    mock_response.json = AsyncMock(return_value={})

    with patch(
        "aiohttp.ClientSession", return_value=_mock_aiohttp_session(mock_response)
    ):
        with pytest.raises(EufyAuthError, match="Authentication failed"):
            await client.get_cloud_device_list()


@pytest.mark.asyncio
async def test_get_mqtt_credentials_non_200_logs_warning(caplog):
    """get_mqtt_credentials() logs warning when response status is not 200."""
    client = _make_client()
    client.user_info = {"user_center_token": "tok", "gtoken": "g"}
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.json = AsyncMock(return_value={})

    with patch(
        "aiohttp.ClientSession", return_value=_mock_aiohttp_session(mock_response)
    ):
        with caplog.at_level(
            logging.WARNING, logger="custom_components.robovac_mqtt.api.http"
        ):
            result = await client.get_mqtt_credentials()

    assert result is None
    assert "get_mqtt_credentials failed" in caplog.text
    assert "500" in caplog.text


@pytest.mark.asyncio
async def test_get_cloud_device_list_returns_empty_without_session():
    """get_cloud_device_list() should return [] when session is not set."""
    client = _make_client()
    assert client.session is None
    result = await client.get_cloud_device_list()
    assert result == []


@pytest.mark.asyncio
async def test_get_mqtt_credentials_returns_none_without_user_info():
    """get_mqtt_credentials() should return None when user_info is not set."""
    client = _make_client()
    assert client.user_info is None
    result = await client.get_mqtt_credentials()
    assert result is None


# --- Mocked HTTP tests ---


@pytest.mark.asyncio
async def test_login_returns_empty_on_failed_login():
    """login() should raise auth errors on invalid credentials."""
    mock_response = AsyncMock()
    mock_response.status = 401
    mock_response.json = AsyncMock(return_value=None)
    mock_response.text = AsyncMock(return_value="Unauthorized")

    mock_session = _mock_aiohttp_session(mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        client = _make_client()
        with pytest.raises(EufyAuthError, match="Invalid credentials"):
            await client.login()


@pytest.mark.asyncio
async def test_login_validate_only():
    """login(validate_only=True) should return the session without calling get_user_info."""
    login_response_data = {
        "access_token": "tok_abc",
        "user_id": "u1",
    }

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=login_response_data)

    mock_session = _mock_aiohttp_session(mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        client = _make_client()

        with patch.object(client, "get_user_info", new_callable=AsyncMock) as mock_gui:
            result = await client.login(validate_only=True)

        # Should contain session data
        assert "session" in result
        assert result["session"]["access_token"] == "tok_abc"

        # get_user_info must NOT have been called
        mock_gui.assert_not_called()


@pytest.mark.asyncio
async def test_get_product_data_points_returns_data_on_success():
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "data": {
                "data_point_list": [
                    {"dp_id": 158, "code": "suction_level"},
                ]
            }
        }
    )

    mock_session = _mock_aiohttp_session(mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        client = _make_client()
        client.user_info = {"user_center_token": "tok", "gtoken": "g"}
        result = await client.get_product_data_points("T2351")

    assert result == [{"dp_id": 158, "code": "suction_level"}]


@pytest.mark.asyncio
async def test_get_product_data_points_returns_empty_on_failure():
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.json = AsyncMock(return_value={})

    mock_session = _mock_aiohttp_session(mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        client = _make_client()
        client.user_info = {"user_center_token": "tok", "gtoken": "g"}
        result = await client.get_product_data_points("T2351")

    assert result == []


@pytest.mark.asyncio
async def test_get_product_data_points_returns_empty_on_exception():
    with patch("aiohttp.ClientSession", side_effect=RuntimeError("boom")):
        client = _make_client()
        client.user_info = {"user_center_token": "tok", "gtoken": "g"}
        result = await client.get_product_data_points("T2351")

    assert result == []


# --- Configuration test ---


def test_request_timeout_is_configured():
    """_REQUEST_TIMEOUT should exist and have a 30-second total."""
    assert _REQUEST_TIMEOUT is not None
    assert _REQUEST_TIMEOUT.total == 30


@pytest.mark.asyncio
async def test_login_uses_injected_session_without_creating_client_session():
    """Injected sessions are reused instead of constructing a new ClientSession."""
    login_response = AsyncMock()
    login_response.status = 200
    login_response.json = AsyncMock(return_value={"access_token": "tok"})

    user_response = AsyncMock()
    user_response.status = 200
    user_response.json = AsyncMock(
        return_value={"user_center_id": "user123", "user_center_token": "uctok"}
    )

    mqtt_response = AsyncMock()
    mqtt_response.status = 200
    mqtt_response.json = AsyncMock(
        return_value={"data": {"endpoint": "mqtt.example.com"}}
    )

    injected_session = _make_injected_session(login_response)
    injected_session.get.return_value = _make_injected_session(
        user_response
    ).get.return_value
    injected_session.post.side_effect = [
        _make_injected_session(login_response).post.return_value,
        _make_injected_session(mqtt_response).post.return_value,
    ]

    client = EufyHTTPClient(
        username="test@example.com",
        password="secret",
        openudid="abc123",
        session=injected_session,
    )

    with patch("aiohttp.ClientSession") as mock_client_session:
        result = await client.login()

    mock_client_session.assert_not_called()
    injected_session.close.assert_not_awaited()
    assert result["session"]["access_token"] == "tok"
    assert result["mqtt"] == {"endpoint": "mqtt.example.com"}


@pytest.mark.asyncio
async def test_session_ctx_closes_owned_session_only():
    """Temporary sessions are closed, injected sessions are left open."""
    client = _make_client()
    owned_session = _make_injected_session(AsyncMock())

    with patch("aiohttp.ClientSession", return_value=owned_session):
        async with client._session_ctx() as session:
            assert session is owned_session

    owned_session.close.assert_awaited_once()

    injected_session = _make_injected_session(AsyncMock())
    injected_client = EufyHTTPClient(
        username="test@example.com",
        password="secret",
        openudid="abc123",
        session=injected_session,
    )

    async with injected_client._session_ctx() as session:
        assert session is injected_session

    injected_session.close.assert_not_awaited()
