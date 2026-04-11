"""Integration tests for the robovac_mqtt config flow using real HA runtime."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.robovac_mqtt.const import DOMAIN, VACS


@pytest.fixture
def mock_eufy_http_login():
    with patch("custom_components.robovac_mqtt.config_flow.EufyHTTPClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.login = AsyncMock(return_value={"session": "valid-session-token"})
        mock_cls.return_value = mock_instance
        yield mock_cls, mock_instance


async def test_config_flow_happy_path(
    hass: HomeAssistant, mock_eufy_http_login
) -> None:
    """Valid credentials produce a config entry with correct data."""
    mock_cls, mock_instance = mock_eufy_http_login

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch("custom_components.robovac_mqtt.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "user@example.com", CONF_PASSWORD: "s3cret"},
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "user@example.com"

    entry_data = result["result"].data
    assert entry_data[CONF_USERNAME] == "user@example.com"
    assert entry_data[CONF_PASSWORD] == "s3cret"
    assert entry_data[VACS] == {}

    mock_cls.assert_called_once()
    call_args = mock_cls.call_args
    assert call_args[0][0] == "user@example.com"
    assert call_args[0][1] == "s3cret"
    mock_instance.login.assert_awaited_once_with(validate_only=True)


async def test_config_flow_login_failure(hass: HomeAssistant) -> None:
    """Login raises exception — form shown again with 'unknown' error."""
    with patch("custom_components.robovac_mqtt.config_flow.EufyHTTPClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.login = AsyncMock(side_effect=ConnectionError("Network error"))
        mock_cls.return_value = mock_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "bad@example.com", CONF_PASSWORD: "badpass"},
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "unknown"}


async def test_config_flow_invalid_auth(hass: HomeAssistant) -> None:
    """Login returns no session — form shown with 'invalid_auth' error."""
    with patch("custom_components.robovac_mqtt.config_flow.EufyHTTPClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.login = AsyncMock(return_value={"error": "invalid credentials"})
        mock_cls.return_value = mock_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "wrong@example.com", CONF_PASSWORD: "wrongpass"},
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "invalid_auth"}


async def test_config_flow_duplicate_entry(
    hass: HomeAssistant, mock_eufy_http_login
) -> None:
    """Existing entry with same email aborts with 'already_configured'."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id="existing@example.com",
        data={
            CONF_USERNAME: "existing@example.com",
            CONF_PASSWORD: "oldpass",
            VACS: {},
        },
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: "existing@example.com", CONF_PASSWORD: "newpass"},
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_config_flow_reconfigure(
    hass: HomeAssistant, mock_eufy_http_login
) -> None:
    """Reconfigure flow updates password when username matches."""
    _, mock_instance = mock_eufy_http_login

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="reconfig@example.com",
        data={
            CONF_USERNAME: "reconfig@example.com",
            CONF_PASSWORD: "oldpassword",
            VACS: {},
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.robovac_mqtt.async_setup_entry", return_value=True):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: "reconfig@example.com", CONF_PASSWORD: "newpassword"},
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_PASSWORD] == "newpassword"
    assert entry.data[CONF_USERNAME] == "reconfig@example.com"


async def test_config_flow_reconfigure_username_mismatch(
    hass: HomeAssistant,
) -> None:
    """Reconfigure with different username shows form with username_mismatch error."""
    with patch("custom_components.robovac_mqtt.config_flow.EufyHTTPClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.login = AsyncMock(return_value={"session": "valid-session-token"})
        mock_cls.return_value = mock_instance

        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id="original@example.com",
            data={
                CONF_USERNAME: "original@example.com",
                CONF_PASSWORD: "pass",
                VACS: {},
            },
        )
        entry.add_to_hass(hass)

        with patch(
            "custom_components.robovac_mqtt.async_setup_entry", return_value=True
        ):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "different@example.com", CONF_PASSWORD: "newpass"},
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        assert result["errors"] == {CONF_USERNAME: "username_mismatch"}
