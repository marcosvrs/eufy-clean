import enum
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock homeassistant.components.stream before importing camera module.
# The stream component imports numpy which has broken C-extensions in this env.
if "homeassistant.components.stream" not in sys.modules:

    class _Orientation(enum.IntEnum):
        NO_TRANSFORM = 0

    _stream_mock = MagicMock()
    _stream_mock.Orientation = _Orientation
    sys.modules["homeassistant.components.stream"] = _stream_mock
    sys.modules["homeassistant.components.stream.core"] = MagicMock()

from custom_components.robovac_mqtt.camera import RoboVacMapCamera  # noqa: E402
from custom_components.robovac_mqtt.coordinator import EufyCleanCoordinator  # noqa: E402
from custom_components.robovac_mqtt.models import VacuumState  # noqa: E402


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock(spec=EufyCleanCoordinator)
    coordinator.data = VacuumState()
    coordinator.device_id = "test_device"
    coordinator.device_name = "Test Vacuum"
    coordinator.device_model = "T2276"
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def camera(mock_coordinator):
    cam = RoboVacMapCamera(mock_coordinator)
    cam.async_write_ha_state = MagicMock()
    return cam


class TestCameraInit:
    def test_unique_id(self, camera):
        assert camera._attr_unique_id == "test_device_map_camera"

    def test_entity_name(self, camera):
        assert camera._attr_name == "Map"

    def test_content_type(self, camera):
        assert camera._attr_content_type == "image/png"

    def test_not_recording(self, camera):
        assert camera._attr_is_recording is False

    def test_not_streaming(self, camera):
        assert camera._attr_is_streaming is False

    def test_empty_path_on_init(self, camera):
        assert camera._path == []

    def test_last_activity_idle_on_init(self, camera):
        assert camera._last_activity == "idle"


class TestCameraImage:
    @pytest.mark.asyncio
    async def test_returns_png_bytes_when_empty(self, camera):
        result = await camera.async_camera_image()
        assert result is not None
        assert result[:4] == b"\x89PNG"

    @pytest.mark.asyncio
    async def test_returns_png_with_path(self, camera):
        camera._path = [(100, 200), (150, 250), (200, 300)]
        result = await camera.async_camera_image()
        assert result is not None
        assert result[:4] == b"\x89PNG"

    @pytest.mark.asyncio
    async def test_passes_rooms_to_renderer(self, camera, mock_coordinator):
        rooms = [{"id": 1, "name": "Kitchen"}, {"id": 2, "name": "Hall"}]
        mock_coordinator.data = VacuumState(rooms=rooms)
        camera._path = [(100, 200)]
        result = await camera.async_camera_image()
        assert result is not None
        assert result[:4] == b"\x89PNG"

    @pytest.mark.asyncio
    async def test_passes_dock_position_when_path_has_points(self, camera, mock_coordinator):
        camera._path = [(100, 200), (150, 250)]
        camera._dock_position = (100, 200)

        with patch("custom_components.robovac_mqtt.camera.render_path") as mock_render:
            mock_render.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
            result = await camera.async_camera_image()

        assert result is not None
        mock_render.assert_called_once_with(
            positions=[(100, 200), (150, 250)],
            dock_position=(100, 200),
            rooms=None,
        )

    @pytest.mark.asyncio
    async def test_passes_none_rooms_when_empty(self, camera, mock_coordinator):
        mock_coordinator.data = VacuumState(rooms=[])
        result = await camera.async_camera_image()
        assert result is not None


class TestPathAccumulation:
    def test_accumulates_position_during_cleaning(self, camera, mock_coordinator):
        mock_coordinator.data = VacuumState(
            activity="cleaning",
            robot_position_x=100,
            robot_position_y=200,
            received_fields={"robot_position"},
        )
        camera._handle_coordinator_update()
        assert camera._path == [(100, 200)]

    def test_accumulates_position_during_returning(self, camera, mock_coordinator):
        camera._last_activity = "cleaning"
        mock_coordinator.data = VacuumState(
            activity="returning",
            robot_position_x=50,
            robot_position_y=60,
            received_fields={"robot_position"},
        )
        camera._handle_coordinator_update()
        assert camera._path == [(50, 60)]

    def test_skips_zero_zero_position(self, camera, mock_coordinator):
        mock_coordinator.data = VacuumState(
            activity="cleaning",
            robot_position_x=0,
            robot_position_y=0,
            received_fields={"robot_position"},
        )
        camera._handle_coordinator_update()
        assert camera._path == []

    def test_skips_duplicate_position(self, camera, mock_coordinator):
        camera._path = [(100, 200)]
        mock_coordinator.data = VacuumState(
            activity="cleaning",
            robot_position_x=100,
            robot_position_y=200,
            received_fields={"robot_position"},
        )
        camera._handle_coordinator_update()
        assert camera._path == [(100, 200)]

    def test_does_not_accumulate_when_docked(self, camera, mock_coordinator):
        mock_coordinator.data = VacuumState(
            activity="docked",
            robot_position_x=100,
            robot_position_y=200,
            received_fields={"robot_position"},
        )
        camera._handle_coordinator_update()
        assert camera._path == []

    def test_does_not_accumulate_when_idle(self, camera, mock_coordinator):
        mock_coordinator.data = VacuumState(
            activity="idle",
            robot_position_x=100,
            robot_position_y=200,
            received_fields={"robot_position"},
        )
        camera._handle_coordinator_update()
        assert camera._path == []

    def test_does_not_accumulate_without_received_fields(
        self, camera, mock_coordinator
    ):
        mock_coordinator.data = VacuumState(
            activity="cleaning",
            robot_position_x=100,
            robot_position_y=200,
        )
        camera._handle_coordinator_update()
        assert camera._path == []

    def test_multiple_updates_accumulate(self, camera, mock_coordinator):
        for x, y in [(100, 200), (110, 210), (120, 220)]:
            mock_coordinator.data = VacuumState(
                activity="cleaning",
                robot_position_x=x,
                robot_position_y=y,
                received_fields={"robot_position"},
            )
            camera._handle_coordinator_update()
        assert camera._path == [(100, 200), (110, 210), (120, 220)]


class TestPathReset:
    def test_resets_on_idle_to_cleaning(self, camera, mock_coordinator):
        camera._path = [(10, 20), (30, 40)]
        camera._last_activity = "idle"
        mock_coordinator.data = VacuumState(
            activity="cleaning",
            robot_position_x=100,
            robot_position_y=200,
            received_fields={"robot_position"},
        )
        camera._handle_coordinator_update()
        assert camera._path == [(100, 200)]

    def test_resets_on_docked_to_cleaning(self, camera, mock_coordinator):
        camera._path = [(10, 20)]
        camera._last_activity = "docked"
        mock_coordinator.data = VacuumState(
            activity="cleaning",
            robot_position_x=50,
            robot_position_y=60,
            received_fields={"robot_position"},
        )
        camera._handle_coordinator_update()
        assert camera._path == [(50, 60)]

    def test_resets_on_error_to_cleaning(self, camera, mock_coordinator):
        camera._path = [(10, 20)]
        camera._last_activity = "error"
        mock_coordinator.data = VacuumState(
            activity="cleaning",
            robot_position_x=50,
            robot_position_y=60,
            received_fields={"robot_position"},
        )
        camera._handle_coordinator_update()
        assert camera._path == [(50, 60)]

    def test_no_reset_on_cleaning_to_cleaning(self, camera, mock_coordinator):
        camera._path = [(10, 20)]
        camera._last_activity = "cleaning"
        mock_coordinator.data = VacuumState(
            activity="cleaning",
            robot_position_x=50,
            robot_position_y=60,
            received_fields={"robot_position"},
        )
        camera._handle_coordinator_update()
        assert camera._path == [(10, 20), (50, 60)]

    def test_no_reset_on_paused_to_cleaning(self, camera, mock_coordinator):
        camera._path = [(10, 20)]
        camera._last_activity = "paused"
        mock_coordinator.data = VacuumState(
            activity="cleaning",
            robot_position_x=50,
            robot_position_y=60,
            received_fields={"robot_position"},
        )
        camera._handle_coordinator_update()
        assert camera._path == [(10, 20), (50, 60)]

    def test_no_reset_on_returning_to_cleaning(self, camera, mock_coordinator):
        camera._path = [(10, 20)]
        camera._last_activity = "returning"
        mock_coordinator.data = VacuumState(
            activity="cleaning",
            robot_position_x=50,
            robot_position_y=60,
            received_fields={"robot_position"},
        )
        camera._handle_coordinator_update()
        assert camera._path == [(10, 20), (50, 60)]

    def test_updates_last_activity(self, camera, mock_coordinator):
        mock_coordinator.data = VacuumState(activity="cleaning")
        camera._handle_coordinator_update()
        assert camera._last_activity == "cleaning"

        mock_coordinator.data = VacuumState(activity="returning")
        camera._handle_coordinator_update()
        assert camera._last_activity == "returning"

        mock_coordinator.data = VacuumState(activity="docked")
        camera._handle_coordinator_update()
        assert camera._last_activity == "docked"
