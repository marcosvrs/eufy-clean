"""Unit tests for the robovac_mqtt config flow."""

# pyright: reportAny=false, reportExplicitAny=false, reportInvalidCast=false, reportMissingTypeStubs=false, reportTypedDictNotRequiredAccess=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnusedCallResult=false

from __future__ import annotations

from typing import Any, cast
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.robovac_mqtt.const import DOMAIN, VACS


def flow_result(result: ConfigFlowResult) -> dict[str, Any]:
    """Cast flow result for test assertions."""
    return cast(dict[str, Any], result)


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Successful user flow creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result_data = flow_result(result)

    assert result_data["type"] is FlowResultType.FORM
    assert result_data["step_id"] == "user"

    with patch(
        "custom_components.robovac_mqtt.config_flow.ConfigFlow._validate_login",
        return_value={},
    ) as validate_login:
        result = await hass.config_entries.flow.async_configure(
            result_data["flow_id"],
            user_input={CONF_USERNAME: "test@test.com", CONF_PASSWORD: "pass123"},
        )
    result_data = flow_result(result)

    assert result_data["type"] is FlowResultType.CREATE_ENTRY
    assert result_data["title"] == "test@test.com"
    assert result_data["data"] == {
        CONF_USERNAME: "test@test.com",
        CONF_PASSWORD: "pass123",
        VACS: {},
    }
    validate_login.assert_awaited_once_with("test@test.com", "pass123")


async def test_user_flow_auth_failure(hass: HomeAssistant) -> None:
    """Auth failures are surfaced to the user step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result_data = flow_result(result)

    with patch(
        "custom_components.robovac_mqtt.config_flow.ConfigFlow._validate_login",
        return_value={"base": "invalid_auth"},
    ) as validate_login:
        result = await hass.config_entries.flow.async_configure(
            result_data["flow_id"],
            user_input={CONF_USERNAME: "test@test.com", CONF_PASSWORD: "wrong"},
        )
    result_data = flow_result(result)

    assert result_data["type"] is FlowResultType.FORM
    assert result_data["step_id"] == "user"
    assert result_data["errors"] == {"base": "invalid_auth"}
    validate_login.assert_awaited_once_with("test@test.com", "wrong")


async def test_user_flow_network_error(hass: HomeAssistant) -> None:
    """Connection failures are surfaced as cannot_connect."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result_data = flow_result(result)

    with patch(
        "custom_components.robovac_mqtt.config_flow.ConfigFlow._validate_login",
        return_value={"base": "cannot_connect"},
    ) as validate_login:
        result = await hass.config_entries.flow.async_configure(
            result_data["flow_id"],
            user_input={CONF_USERNAME: "test@test.com", CONF_PASSWORD: "pass123"},
        )
    result_data = flow_result(result)

    assert result_data["type"] is FlowResultType.FORM
    assert result_data["step_id"] == "user"
    assert result_data["errors"] == {"base": "cannot_connect"}
    validate_login.assert_awaited_once_with("test@test.com", "pass123")


async def test_user_flow_duplicate(hass: HomeAssistant) -> None:
    """Duplicate user flow aborts before validation."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="duplicate@test.com",
        data={
            CONF_USERNAME: "duplicate@test.com",
            CONF_PASSWORD: "oldpass",
            VACS: {},
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result_data = flow_result(result)

    with patch(
        "custom_components.robovac_mqtt.config_flow.ConfigFlow._validate_login",
        return_value={},
    ) as validate_login:
        result = await hass.config_entries.flow.async_configure(
            result_data["flow_id"],
            user_input={CONF_USERNAME: "duplicate@test.com", CONF_PASSWORD: "newpass"},
        )
    result_data = flow_result(result)

    assert result_data["type"] is FlowResultType.ABORT
    assert result_data["reason"] == "already_configured"
    validate_login.assert_not_called()


async def test_reauth_flow_success(hass: HomeAssistant) -> None:
    """Successful reauth updates the entry password."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="reauth@test.com",
        data={
            CONF_USERNAME: "reauth@test.com",
            CONF_PASSWORD: "oldpass",
            VACS: {},
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": entry.entry_id,
            "unique_id": entry.unique_id,
        },
        data=entry.data,
    )
    result_data = flow_result(result)

    assert result_data["type"] is FlowResultType.FORM
    assert result_data["step_id"] == "reauth_confirm"

    with patch(
        "custom_components.robovac_mqtt.config_flow.ConfigFlow._validate_login",
        return_value={},
    ) as validate_login:
        result = await hass.config_entries.flow.async_configure(
            result_data["flow_id"],
            user_input={CONF_PASSWORD: "newpass"},
        )
        _ = await hass.async_block_till_done()
    result_data = flow_result(result)

    assert result_data["type"] is FlowResultType.ABORT
    assert result_data["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "newpass"
    validate_login.assert_awaited_once_with("reauth@test.com", "newpass")


async def test_reauth_flow_failure(hass: HomeAssistant) -> None:
    """Failed reauth keeps the user on the confirmation step."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="reauth@test.com",
        data={
            CONF_USERNAME: "reauth@test.com",
            CONF_PASSWORD: "oldpass",
            VACS: {},
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": entry.entry_id,
            "unique_id": entry.unique_id,
        },
        data=entry.data,
    )
    result_data = flow_result(result)

    with patch(
        "custom_components.robovac_mqtt.config_flow.ConfigFlow._validate_login",
        return_value={"base": "invalid_auth"},
    ) as validate_login:
        result = await hass.config_entries.flow.async_configure(
            result_data["flow_id"],
            user_input={CONF_PASSWORD: "wrongpass"},
        )
    result_data = flow_result(result)

    assert result_data["type"] is FlowResultType.FORM
    assert result_data["step_id"] == "reauth_confirm"
    assert result_data["errors"] == {"base": "invalid_auth"}
    validate_login.assert_awaited_once_with("reauth@test.com", "wrongpass")


async def test_reconfigure_flow_success(hass: HomeAssistant) -> None:
    """Reconfigure updates the password for the same username."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="reconfigure@test.com",
        data={
            CONF_USERNAME: "reconfigure@test.com",
            CONF_PASSWORD: "oldpass",
            VACS: {},
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    result_data = flow_result(result)

    assert result_data["type"] is FlowResultType.FORM
    assert result_data["step_id"] == "reconfigure"

    with patch(
        "custom_components.robovac_mqtt.config_flow.ConfigFlow._validate_login",
        return_value={},
    ) as validate_login:
        result = await hass.config_entries.flow.async_configure(
            result_data["flow_id"],
            user_input={
                CONF_USERNAME: "reconfigure@test.com",
                CONF_PASSWORD: "newpass",
            },
        )
        _ = await hass.async_block_till_done()
    result_data = flow_result(result)

    assert result_data["type"] is FlowResultType.ABORT
    assert result_data["reason"] == "reconfigure_successful"
    assert entry.data[CONF_PASSWORD] == "newpass"
    validate_login.assert_awaited_once_with("reconfigure@test.com", "newpass")


async def test_options_flow(hass: HomeAssistant) -> None:
    """Options flow updates the max cleaning history setting."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "options@test.com",
            CONF_PASSWORD: "pass123",
            VACS: {},
        },
        options={"max_cleaning_history": 150},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result_data = flow_result(result)

    assert result_data["type"] is FlowResultType.FORM
    assert result_data["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result_data["flow_id"],
        user_input={"max_cleaning_history": 250},
    )
    result_data = flow_result(result)

    assert result_data["type"] is FlowResultType.CREATE_ENTRY
    assert result_data["data"] == {"max_cleaning_history": 250}
