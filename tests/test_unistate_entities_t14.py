from unittest.mock import MagicMock

import pytest

from custom_components.robovac_mqtt.binary_sensor import RoboVacBinarySensor
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


def _coord_with_fields(mock_coordinator, fields, **state_kwargs):
    mock_coordinator.data = VacuumState(received_fields=set(fields), **state_kwargs)
    return mock_coordinator


UNISTATE_SENSOR_FIELDS = ["mop_state", "clean_strategy_version"]

UNISTATE_BINARY_SENSOR_FIELDS = [
    "mop_holder_state_l",
    "mop_holder_state_r",
    "map_valid",
]


class TestUnistateSensors:
    def test_mop_state_available(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"mop_state"})
        sensor = RoboVacSensor(
            mock_coordinator,
            "mop_state",
            "Mop State",
            lambda s: s.mop_state,
            availability_fn=lambda s: "mop_state" in s.received_fields,
        )
        assert sensor.available is True

    def test_mop_state_unavailable(self, mock_coordinator):
        sensor = RoboVacSensor(
            mock_coordinator,
            "mop_state",
            "Mop State",
            lambda s: s.mop_state,
            availability_fn=lambda s: "mop_state" in s.received_fields,
        )
        assert sensor.available is False

    def test_mop_state_value(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"mop_state"}, mop_state=True)
        sensor = RoboVacSensor(
            mock_coordinator,
            "mop_state",
            "Mop State",
            lambda s: s.mop_state,
            availability_fn=lambda s: "mop_state" in s.received_fields,
        )
        assert sensor.native_value is True

    def test_clean_strategy_version_available(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"clean_strategy_version"})
        sensor = RoboVacSensor(
            mock_coordinator,
            "clean_strategy_version",
            "Clean Strategy Version",
            lambda s: s.clean_strategy_version,
            availability_fn=lambda s: "clean_strategy_version" in s.received_fields,
        )
        assert sensor.available is True

    def test_clean_strategy_version_value(self, mock_coordinator):
        _coord_with_fields(
            mock_coordinator, {"clean_strategy_version"}, clean_strategy_version=42
        )
        sensor = RoboVacSensor(
            mock_coordinator,
            "clean_strategy_version",
            "Clean Strategy Version",
            lambda s: s.clean_strategy_version,
            availability_fn=lambda s: "clean_strategy_version" in s.received_fields,
        )
        assert sensor.native_value == 42


class TestUnistateBinarySensors:
    def test_mop_holder_left_available(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"mop_holder_state_l"})
        bs = RoboVacBinarySensor(
            mock_coordinator,
            "mop_holder_l",
            "Mop Holder Left",
            lambda s: s.mop_holder_state_l,
            availability_fn=lambda s: "mop_holder_state_l" in s.received_fields,
        )
        assert bs.available is True

    def test_mop_holder_left_unavailable(self, mock_coordinator):
        bs = RoboVacBinarySensor(
            mock_coordinator,
            "mop_holder_l",
            "Mop Holder Left",
            lambda s: s.mop_holder_state_l,
            availability_fn=lambda s: "mop_holder_state_l" in s.received_fields,
        )
        assert bs.available is False

    def test_mop_holder_left_default_false(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"mop_holder_state_l"})
        bs = RoboVacBinarySensor(
            mock_coordinator,
            "mop_holder_l",
            "Mop Holder Left",
            lambda s: s.mop_holder_state_l,
            availability_fn=lambda s: "mop_holder_state_l" in s.received_fields,
        )
        assert bs.is_on is False

    def test_mop_holder_right_available(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"mop_holder_state_r"})
        bs = RoboVacBinarySensor(
            mock_coordinator,
            "mop_holder_r",
            "Mop Holder Right",
            lambda s: s.mop_holder_state_r,
            availability_fn=lambda s: "mop_holder_state_r" in s.received_fields,
        )
        assert bs.available is True

    def test_map_valid_available(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"map_valid"})
        bs = RoboVacBinarySensor(
            mock_coordinator,
            "map_valid",
            "Map Valid",
            lambda s: s.map_valid,
            availability_fn=lambda s: "map_valid" in s.received_fields,
        )
        assert bs.available is True

    def test_map_valid_true(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, {"map_valid"}, map_valid=True)
        bs = RoboVacBinarySensor(
            mock_coordinator,
            "map_valid",
            "Map Valid",
            lambda s: s.map_valid,
            availability_fn=lambda s: "map_valid" in s.received_fields,
        )
        assert bs.is_on is True

    def test_loop_lambda_capture(self, mock_coordinator):
        _coord_with_fields(mock_coordinator, UNISTATE_BINARY_SENSOR_FIELDS)
        sensors = []
        for id_suffix, name, bs_field in [
            ("mop_holder_l", "Mop Holder Left", "mop_holder_state_l"),
            ("mop_holder_r", "Mop Holder Right", "mop_holder_state_r"),
            ("map_valid", "Map Valid", "map_valid"),
        ]:
            sensors.append(
                RoboVacBinarySensor(
                    mock_coordinator,
                    id_suffix,
                    name,
                    lambda s, f=bs_field: getattr(s, f, False),
                    availability_fn=lambda s, f=bs_field: f in s.received_fields,
                )
            )
        for sensor in sensors:
            assert sensor.available is True
            assert sensor.is_on is False


class TestVacuumStateUnistateFields:
    @pytest.mark.parametrize(
        "field", UNISTATE_SENSOR_FIELDS + UNISTATE_BINARY_SENSOR_FIELDS
    )
    def test_field_exists_on_vacuum_state(self, field):
        s = VacuumState()
        assert hasattr(s, field), f"VacuumState missing field: {field}"
