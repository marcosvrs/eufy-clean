"""Tests for UnisettingSwitch, UnisettingNumber, and build_set_unisetting_command."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.robovac_mqtt.api.commands import (
    _UNISETTING_SWITCH_FIELDS,
    build_command,
    build_set_unisetting_command,
)
from custom_components.robovac_mqtt.const import DPS_MAP
from custom_components.robovac_mqtt.descriptions.switch import (
    RoboVacUnisettingSwitchDescription,
)
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.number import UnisettingNumber
from custom_components.robovac_mqtt.proto.cloud.unisetting_pb2 import UnisettingRequest
from custom_components.robovac_mqtt.switch import UnisettingSwitch
from custom_components.robovac_mqtt.utils import decode


def _mock_coordinator(received=None):
    c = MagicMock()
    c.device_id = "test"
    c.device_info = MagicMock()
    state = VacuumState()
    if received:
        state = VacuumState(received_fields=set(received))
    c.data = state
    c.last_update_success = True
    c.supported_dps = {"UNSETTING"}
    c.dps_map = {"UNSETTING": "176"}
    return c


class TestBuildSetUnisettingCommand:

    def test_returns_dps_176_key(self):
        state = VacuumState()
        result = build_set_unisetting_command("pet_mode_sw", True, state)
        assert DPS_MAP["UNSETTING"] in result

    def test_build_command_dispatcher(self):
        state = VacuumState()
        result = build_command(
            "set_unisetting", field="ai_see", value=True, current_state=state
        )
        assert DPS_MAP["UNSETTING"] in result

    def test_read_modify_write_preserves_existing_state(self):
        state = VacuumState(
            child_lock=True,
            ai_see=True,
            pet_mode_sw=True,
            dust_full_remind=42,
        )
        result = build_set_unisetting_command("water_level_sw", True, state)
        decoded = decode(UnisettingRequest, result[DPS_MAP["UNSETTING"]])

        assert decoded.children_lock.value is True
        assert decoded.ai_see.value is True
        assert decoded.pet_mode_sw.value is True
        assert decoded.water_level_sw.value is True
        assert decoded.dust_full_remind.value == 42

    def test_overrides_target_switch(self):
        state = VacuumState(pet_mode_sw=False)
        result = build_set_unisetting_command("pet_mode_sw", True, state)
        decoded = decode(UnisettingRequest, result[DPS_MAP["UNSETTING"]])
        assert decoded.pet_mode_sw.value is True

    def test_overrides_dust_full_remind(self):
        state = VacuumState(dust_full_remind=10)
        result = build_set_unisetting_command("dust_full_remind", 75, state)
        decoded = decode(UnisettingRequest, result[DPS_MAP["UNSETTING"]])
        assert decoded.dust_full_remind.value == 75

    def test_all_ten_switch_fields_included(self):
        state = VacuumState()
        result = build_set_unisetting_command("ai_see", True, state)
        decoded = decode(UnisettingRequest, result[DPS_MAP["UNSETTING"]])

        for field in _UNISETTING_SWITCH_FIELDS:
            assert hasattr(decoded, field)


def _sw_desc(field_name, name, icon):
    return RoboVacUnisettingSwitchDescription(
        field_name=field_name, name=name, icon=icon
    )


class TestUnisettingSwitch:

    def test_is_on_reads_from_coordinator(self):
        coord = _mock_coordinator(received=["pet_mode_sw"])
        coord.data = VacuumState(pet_mode_sw=True, received_fields={"pet_mode_sw"})
        sw = UnisettingSwitch(coord, _sw_desc("pet_mode_sw", "Pet Mode", "mdi:paw"))
        assert sw.is_on is True

    def test_is_on_false(self):
        coord = _mock_coordinator(received=["ai_see"])
        sw = UnisettingSwitch(coord, _sw_desc("ai_see", "AI See", "mdi:eye"))
        assert sw.is_on is False

    def test_available_requires_received_field(self):
        coord = _mock_coordinator(received=[])
        sw = UnisettingSwitch(coord, _sw_desc("ai_see", "AI See", "mdi:eye"))
        assert sw.available is False

    def test_available_when_field_received(self):
        coord = _mock_coordinator(received=["ai_see"])
        sw = UnisettingSwitch(coord, _sw_desc("ai_see", "AI See", "mdi:eye"))
        assert sw.available is True

    def test_unique_id(self):
        coord = _mock_coordinator()
        sw = UnisettingSwitch(coord, _sw_desc("pet_mode_sw", "Pet Mode", "mdi:paw"))
        assert sw._attr_unique_id == "test_pet_mode_sw"

    def test_entity_category_config(self):
        from homeassistant.const import EntityCategory

        coord = _mock_coordinator()
        sw = UnisettingSwitch(coord, _sw_desc("ai_see", "AI See", "mdi:eye"))
        assert sw._attr_entity_category == EntityCategory.CONFIG

    def test_visible_default_false(self):
        coord = _mock_coordinator()
        sw = UnisettingSwitch(coord, _sw_desc("ai_see", "AI See", "mdi:eye"))
        assert sw._attr_entity_registry_visible_default is False

    @pytest.mark.asyncio
    async def test_turn_on_sends_command(self):
        coord = _mock_coordinator(received=["pet_mode_sw"])
        coord.async_send_command = AsyncMock()
        sw = UnisettingSwitch(coord, _sw_desc("pet_mode_sw", "Pet Mode", "mdi:paw"))
        await sw.async_turn_on()
        coord.async_send_command.assert_called_once()
        sent = coord.async_send_command.call_args[0][0]
        assert DPS_MAP["UNSETTING"] in sent

    @pytest.mark.asyncio
    async def test_turn_off_sends_command(self):
        coord = _mock_coordinator(received=["pet_mode_sw"])
        coord.async_send_command = AsyncMock()
        sw = UnisettingSwitch(coord, _sw_desc("pet_mode_sw", "Pet Mode", "mdi:paw"))
        await sw.async_turn_off()
        coord.async_send_command.assert_called_once()


class TestUnisettingNumber:

    def test_native_value_reads_from_coordinator(self):
        coord = _mock_coordinator(received=["dust_full_remind"])
        coord.data = VacuumState(
            dust_full_remind=42, received_fields={"dust_full_remind"}
        )
        num = UnisettingNumber(coord, "dust_full_remind", "Dust Full Remind", 0, 100)
        assert num.native_value == 42.0

    def test_native_value_none_when_missing(self):
        coord = _mock_coordinator()
        num = UnisettingNumber(coord, "dust_full_remind", "Dust Full Remind", 0, 100)
        assert num.native_value == 0.0

    def test_available_requires_received_field(self):
        coord = _mock_coordinator(received=[])
        num = UnisettingNumber(coord, "dust_full_remind", "Dust Full Remind", 0, 100)
        assert num.available is False

    def test_available_when_field_received(self):
        coord = _mock_coordinator(received=["dust_full_remind"])
        num = UnisettingNumber(coord, "dust_full_remind", "Dust Full Remind", 0, 100)
        assert num.available is True

    def test_entity_category_config(self):
        from homeassistant.const import EntityCategory

        coord = _mock_coordinator()
        num = UnisettingNumber(coord, "dust_full_remind", "Dust Full Remind", 0, 100)
        assert num._attr_entity_category == EntityCategory.CONFIG

    def test_visible_default_false(self):
        coord = _mock_coordinator()
        num = UnisettingNumber(coord, "dust_full_remind", "Dust Full Remind", 0, 100)
        assert num._attr_entity_registry_visible_default is False

    @pytest.mark.asyncio
    async def test_set_value_sends_command(self):
        coord = _mock_coordinator(received=["dust_full_remind"])
        coord.async_send_command = AsyncMock()
        num = UnisettingNumber(coord, "dust_full_remind", "Dust Full Remind", 0, 100)
        await num.async_set_native_value(75)
        coord.async_send_command.assert_called_once()
        sent = coord.async_send_command.call_args[0][0]
        assert DPS_MAP["UNSETTING"] in sent
