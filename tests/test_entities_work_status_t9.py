from unittest.mock import MagicMock

import pytest

from custom_components.robovac_mqtt.binary_sensor import RoboVacBinarySensor
from custom_components.robovac_mqtt.descriptions.binary_sensor import (
    RoboVacBinarySensorDescription,
)
from custom_components.robovac_mqtt.descriptions.sensor import RoboVacSensorDescription
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.sensor import RoboVacSensor


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator.device_id = "test_id"
    coordinator.device_name = "Test Vac"
    coordinator.device_model = "T2351"
    coordinator.data = VacuumState()
    coordinator.last_update_success = True
    return coordinator


def _coord_with_fields(mock_coordinator, fields):
    mock_coordinator.data = VacuumState(received_fields=set(fields))
    return mock_coordinator


NEW_SENSOR_FIELDS = [
    "mapping_state",
    "mapping_mode",
    "cruise_state",
    "cruise_mode",
    "smart_follow_state",
    "station_work_status",
]

NEW_BINARY_SENSOR_FIELDS = [
    "upgrading",
    "relocating",
    "breakpoint_available",
    "roller_brush_cleaning",
]


def _sensor_desc(key, name, availability_fn=None):
    return RoboVacSensorDescription(
        key=key,
        name=name,
        value_fn=lambda s, k=key: getattr(s, k),
        availability_fn=availability_fn,
    )


class TestWorkStatusSensors:
    def test_sensor_available_when_field_received(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"mapping_state"})
        sensor = RoboVacSensor(
            mock_coordinator,
            _sensor_desc(
                "mapping_state",
                "Mapping State",
                availability_fn=lambda s: "mapping_state" in s.received_fields,
            ),
        )
        assert sensor.available is True

    def test_sensor_unavailable_when_field_not_received(self, mock_coordinator):
        sensor = RoboVacSensor(
            mock_coordinator,
            _sensor_desc(
                "mapping_state",
                "Mapping State",
                availability_fn=lambda s: "mapping_state" in s.received_fields,
            ),
        )
        assert sensor.available is False

    def test_sensor_returns_value(self, mock_coordinator):
        mock_coordinator.data = VacuumState(
            mapping_state=1, received_fields={"mapping_state"}
        )
        sensor = RoboVacSensor(
            mock_coordinator,
            _sensor_desc(
                "mapping_state",
                "Mapping State",
                availability_fn=lambda s: "mapping_state" in s.received_fields,
            ),
        )
        assert sensor.native_value == 1

    def test_cruise_mode_gated_by_cruise_state(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"cruise_state"})
        sensor = RoboVacSensor(
            mock_coordinator,
            RoboVacSensorDescription(
                key="cruise_mode",
                name="Cruise Mode",
                value_fn=lambda s: s.cruise_mode,
                availability_fn=lambda s: "cruise_state" in s.received_fields,
            ),
        )
        assert sensor.available is True

    def test_mapping_mode_gated_by_mapping_state(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"mapping_state"})
        sensor = RoboVacSensor(
            mock_coordinator,
            RoboVacSensorDescription(
                key="mapping_mode",
                name="Mapping Mode",
                value_fn=lambda s: s.mapping_mode,
                availability_fn=lambda s: "mapping_state" in s.received_fields,
            ),
        )
        assert sensor.available is True


def _bs_desc(key, name, value_fn, availability_fn=None):
    return RoboVacBinarySensorDescription(
        key=key,
        name=name,
        value_fn=value_fn,
        availability_fn=availability_fn,
    )


class TestWorkStatusBinarySensors:
    def test_binary_sensor_available_when_received(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"upgrading"})
        bs = RoboVacBinarySensor(
            mock_coordinator,
            _bs_desc(
                "upgrading",
                "Upgrading",
                lambda s: s.upgrading,
                availability_fn=lambda s: "upgrading" in s.received_fields,
            ),
        )
        assert bs.available is True

    def test_binary_sensor_unavailable_when_not_received(self, mock_coordinator):
        bs = RoboVacBinarySensor(
            mock_coordinator,
            _bs_desc(
                "upgrading",
                "Upgrading",
                lambda s: s.upgrading,
                availability_fn=lambda s: "upgrading" in s.received_fields,
            ),
        )
        assert bs.available is False

    def test_binary_sensor_default_false(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"upgrading"})
        bs = RoboVacBinarySensor(
            mock_coordinator,
            _bs_desc(
                "upgrading",
                "Upgrading",
                lambda s: s.upgrading,
                availability_fn=lambda s: "upgrading" in s.received_fields,
            ),
        )
        assert bs.is_on is False

    def test_loop_lambda_capture(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, NEW_BINARY_SENSOR_FIELDS)
        sensors = []
        for id_suffix, name, bs_field, icon in [
            ("upgrading", "Upgrading", "upgrading", "mdi:update"),
            ("relocating", "Relocating", "relocating", "mdi:crosshairs-gps"),
            (
                "breakpoint_available",
                "Breakpoint Available",
                "breakpoint_available",
                "mdi:map-marker-check",
            ),
            (
                "roller_brush_cleaning",
                "Roller Brush Cleaning",
                "roller_brush_cleaning",
                "mdi:brush",
            ),
        ]:
            sensors.append(
                RoboVacBinarySensor(
                    mock_coordinator,
                    _bs_desc(
                        id_suffix,
                        name,
                        lambda s, f=bs_field: getattr(s, f),
                        availability_fn=lambda s, f=bs_field: f in s.received_fields,
                    ),
                )
            )
        for sensor in sensors:
            assert sensor.available is True
            assert sensor.is_on is False


class TestVacuumStateFields:
    @pytest.mark.parametrize("field", NEW_SENSOR_FIELDS + NEW_BINARY_SENSOR_FIELDS)
    def test_field_exists_on_vacuum_state(self, field):
        s = VacuumState()
        assert hasattr(s, field), f"VacuumState missing field: {field}"
