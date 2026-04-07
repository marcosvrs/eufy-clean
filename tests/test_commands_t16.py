"""Tests for zone_clean, spot_clean, goto_clean command builders."""

from custom_components.robovac_mqtt.api.commands import (
    build_command,
    build_goto_clean_command,
    build_spot_clean_command,
    build_zone_clean_command,
)
from custom_components.robovac_mqtt.const import DPS_MAP, EUFY_CLEAN_CONTROL
from custom_components.robovac_mqtt.proto.cloud.control_pb2 import ModeCtrlRequest
from custom_components.robovac_mqtt.utils import decode


def _decode_mode_ctrl(result: dict) -> ModeCtrlRequest:
    return decode(ModeCtrlRequest, result[DPS_MAP["PLAY_PAUSE"]])


class TestZoneClean:
    def test_basic(self):
        result = build_command(
            "zone_clean", zones=[{"x1": 0, "y1": 0, "x2": 100, "y2": 100}]
        )
        assert DPS_MAP["PLAY_PAUSE"] in result
        msg = _decode_mode_ctrl(result)
        assert msg.method == EUFY_CLEAN_CONTROL.START_SELECT_ZONES_CLEAN
        assert len(msg.select_zones_clean.zones) == 1
        zone = msg.select_zones_clean.zones[0]
        assert zone.quadrangle.p0.x == 0
        assert zone.quadrangle.p0.y == 0
        assert zone.quadrangle.p2.x == 100
        assert zone.quadrangle.p2.y == 100

    def test_multiple_zones(self):
        zones = [
            {"x1": 0, "y1": 0, "x2": 50, "y2": 50},
            {"x1": 60, "y1": 60, "x2": 120, "y2": 120},
        ]
        result = build_command("zone_clean", zones=zones)
        msg = _decode_mode_ctrl(result)
        assert len(msg.select_zones_clean.zones) == 2
        assert msg.select_zones_clean.zones[1].quadrangle.p0.x == 60

    def test_with_map_id(self):
        result = build_command(
            "zone_clean",
            zones=[{"x1": 0, "y1": 0, "x2": 50, "y2": 50}],
            map_id=3,
        )
        msg = _decode_mode_ctrl(result)
        assert msg.select_zones_clean.map_id == 3

    def test_zone_clean_times(self):
        result = build_zone_clean_command(
            zones=[{"x1": 0, "y1": 0, "x2": 50, "y2": 50, "clean_times": 2}]
        )
        msg = _decode_mode_ctrl(result)
        assert msg.select_zones_clean.zones[0].clean_times == 2

    def test_quadrangle_corners(self):
        result = build_zone_clean_command(
            zones=[{"x1": 10, "y1": 20, "x2": 30, "y2": 40}]
        )
        msg = _decode_mode_ctrl(result)
        q = msg.select_zones_clean.zones[0].quadrangle
        assert (q.p0.x, q.p0.y) == (10, 20)
        assert (q.p1.x, q.p1.y) == (30, 20)
        assert (q.p2.x, q.p2.y) == (30, 40)
        assert (q.p3.x, q.p3.y) == (10, 40)


class TestSpotClean:
    def test_basic(self):
        result = build_command("spot_clean")
        assert DPS_MAP["PLAY_PAUSE"] in result
        msg = _decode_mode_ctrl(result)
        assert msg.method == EUFY_CLEAN_CONTROL.START_SPOT_CLEAN
        assert msg.spot_clean.clean_times == 1

    def test_custom_clean_times(self):
        result = build_command("spot_clean", clean_times=3)
        msg = _decode_mode_ctrl(result)
        assert msg.spot_clean.clean_times == 3

    def test_direct_builder(self):
        result = build_spot_clean_command(clean_times=2)
        msg = _decode_mode_ctrl(result)
        assert msg.method == EUFY_CLEAN_CONTROL.START_SPOT_CLEAN
        assert msg.spot_clean.clean_times == 2


class TestGotoClean:
    def test_basic(self):
        result = build_command("goto_clean", x=100, y=200)
        assert DPS_MAP["PLAY_PAUSE"] in result
        msg = _decode_mode_ctrl(result)
        assert msg.method == EUFY_CLEAN_CONTROL.START_GOTO_CLEAN
        assert msg.go_to.destination.x == 100
        assert msg.go_to.destination.y == 200

    def test_with_map_id(self):
        result = build_command("goto_clean", x=50, y=75, map_id=4)
        msg = _decode_mode_ctrl(result)
        assert msg.go_to.map_id == 4

    def test_direct_builder(self):
        result = build_goto_clean_command(x=300, y=400, map_id=2)
        msg = _decode_mode_ctrl(result)
        assert msg.go_to.destination.x == 300
        assert msg.go_to.destination.y == 400
        assert msg.go_to.map_id == 2
