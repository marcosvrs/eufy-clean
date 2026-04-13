from custom_components.robovac_mqtt.descriptions.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
)
from custom_components.robovac_mqtt.descriptions.button import (
    DOCK_BUTTON_DESCRIPTIONS,
    GENERIC_BUTTON_DESCRIPTIONS,
    MEDIA_BUTTON_DESCRIPTIONS,
    RESET_BUTTON_DESCRIPTIONS,
)
from custom_components.robovac_mqtt.descriptions.sensor import SENSOR_DESCRIPTIONS
from custom_components.robovac_mqtt.descriptions.switch import (
    UNISETTING_SWITCH_DESCRIPTIONS,
)


def test_sensor_description_count():
    assert len(SENSOR_DESCRIPTIONS) == 61


def test_sensor_description_keys_unique():
    keys = [d.key for d in SENSOR_DESCRIPTIONS]
    assert len(keys) == len(set(keys)), "Duplicate sensor description keys"


def test_sensor_description_keys_non_empty():
    assert all(d.key for d in SENSOR_DESCRIPTIONS)


def test_binary_sensor_description_count():
    assert len(BINARY_SENSOR_DESCRIPTIONS) == 15


def test_binary_sensor_description_keys_unique():
    keys = [d.key for d in BINARY_SENSOR_DESCRIPTIONS]
    assert len(keys) == len(set(keys)), "Duplicate binary sensor description keys"


def test_unisetting_switch_description_count():
    assert len(UNISETTING_SWITCH_DESCRIPTIONS) == 10


def test_button_description_counts():
    assert len(DOCK_BUTTON_DESCRIPTIONS) == 4
    assert len(GENERIC_BUTTON_DESCRIPTIONS) == 4
    assert len(RESET_BUTTON_DESCRIPTIONS) == 6
    assert len(MEDIA_BUTTON_DESCRIPTIONS) == 1
    total = (
        len(DOCK_BUTTON_DESCRIPTIONS)
        + len(GENERIC_BUTTON_DESCRIPTIONS)
        + len(RESET_BUTTON_DESCRIPTIONS)
        + len(MEDIA_BUTTON_DESCRIPTIONS)
    )
    assert total == 15


def test_near_duplicate_sensors_disabled_by_default():
    desc_by_key = {d.key: d for d in SENSOR_DESCRIPTIONS}
    assert not desc_by_key["battery_show_level"].enabled_default
    assert not desc_by_key["user_total_cleaning_time"].enabled_default
    assert not desc_by_key["user_total_cleaning_area"].enabled_default
    assert not desc_by_key["user_total_cleaning_count"].enabled_default
