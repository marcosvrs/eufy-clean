"""Tests for map_renderer module."""

import pytest
from PIL import Image
import io

from custom_components.robovac_mqtt.api.map_renderer import render_path


class TestRenderPath:
    """Test cases for render_path function."""

    def test_render_returns_png_bytes(self):
        """Test that render_path returns valid PNG bytes."""
        positions = [(0, 0), (100, 0), (100, 100)]
        result = render_path(positions)
        assert isinstance(result, bytes)
        assert result[:4] == b'\x89PNG'  # PNG magic bytes

    def test_render_empty_positions(self):
        """Test that empty positions returns a valid placeholder image."""
        result = render_path([])
        assert isinstance(result, bytes)
        assert result[:4] == b'\x89PNG'

        # Verify it's a valid image
        img = Image.open(io.BytesIO(result))
        assert img.size == (512, 512)

    def test_image_size_512x512(self):
        """Test that output image is 512x512 pixels."""
        positions = [(0, 0), (100, 100), (200, 200)]
        result = render_path(positions)
        img = Image.open(io.BytesIO(result))
        assert img.size == (512, 512)

    def test_dark_background_visible(self):
        """Test that dark background is visible (not all same color)."""
        positions = [(0, 0), (100, 100)]
        result = render_path(positions)
        img = Image.open(io.BytesIO(result))
        pixels = list(img.getdata())

        # Check that we have the dark background color (20, 20, 30)
        bg_color = (20, 20, 30)
        assert bg_color in pixels, "Dark background should be visible"

    def test_path_visible_cyan_pixels(self):
        """Test that path is visible with at least some cyan pixels."""
        positions = [(0, 0), (100, 0), (100, 100), (0, 100)]
        result = render_path(positions)
        img = Image.open(io.BytesIO(result))
        pixels = list(img.getdata())

        # Cyan path color
        path_color = (0, 180, 200)
        assert path_color in pixels, "Cyan path should be visible"

    def test_robot_position_yellow_dot(self):
        """Test that robot position is marked with yellow dot."""
        positions = [(0, 0), (100, 100)]
        result = render_path(positions)
        img = Image.open(io.BytesIO(result))
        pixels = list(img.getdata())

        # Bright yellow robot color
        robot_color = (255, 220, 0)
        assert robot_color in pixels, "Yellow robot position dot should be visible"

    def test_dock_marker_visible(self):
        """Test that dock marker is visible when dock_position provided."""
        positions = [(0, 0), (100, 100)]
        dock_position = (50, 50)
        result = render_path(positions, dock_position=dock_position)
        img = Image.open(io.BytesIO(result))
        pixels = list(img.getdata())

        # Bright green dock color
        dock_color = (0, 200, 100)
        assert dock_color in pixels, "Green dock marker should be visible"

    def test_no_dock_marker_when_none(self):
        """Test that no dock marker appears when dock_position is None."""
        positions = [(0, 0), (100, 100)]
        result = render_path(positions, dock_position=None)
        img = Image.open(io.BytesIO(result))
        pixels = list(img.getdata())

        # Bright green dock color should NOT be present
        dock_color = (0, 200, 100)
        assert dock_color not in pixels, "Green dock marker should NOT be visible"

    def test_room_labels_visible(self):
        """Test that room labels are rendered when rooms provided."""
        positions = [(0, 0), (100, 100)]
        rooms = [{"name": "Kitchen", "id": 1}, {"name": "Living Room", "id": 2}]
        result = render_path(positions, rooms=rooms)
        img = Image.open(io.BytesIO(result))
        pixels = list(img.getdata())

        # PIL's default font uses anti-aliasing, so check for light grayish pixels
        # (values close to 180, 180, 180 due to anti-aliasing)
        has_light_gray = any(
            150 <= r <= 200 and 150 <= g <= 200 and 150 <= b <= 200
            for r, g, b in pixels
        )
        assert has_light_gray, "Room labels should be visible (light gray pixels)"

    def test_coordinate_transform_negative_values(self):
        """Test that negative coordinates are handled correctly."""
        # Coordinates from DPS 179 can be negative (e.g., -8208)
        positions = [(-8000, -5000), (-7000, -4000), (-6000, -3000)]
        result = render_path(positions)
        assert isinstance(result, bytes)
        assert result[:4] == b'\x89PNG'

    def test_coordinate_transform_large_range(self):
        """Test that large coordinate ranges are scaled correctly."""
        # Real DPS 179 coordinates can range from -8208 to 8913
        positions = [(-8208, 0), (8913, 10000), (0, -5000)]
        result = render_path(positions)
        img = Image.open(io.BytesIO(result))
        assert img.size == (512, 512)

    def test_single_point_path(self):
        """Test that a single point path renders correctly."""
        positions = [(100, 100)]
        result = render_path(positions)
        assert isinstance(result, bytes)
        assert result[:4] == b'\x89PNG'

        # Should show robot position
        img = Image.open(io.BytesIO(result))
        pixels = list(img.getdata())
        robot_color = (255, 220, 0)
        assert robot_color in pixels

    def test_custom_image_size(self):
        """Test that custom image_size parameter works."""
        positions = [(0, 0), (100, 100)]
        result = render_path(positions, image_size=256)
        img = Image.open(io.BytesIO(result))
        assert img.size == (256, 256)

    def test_path_with_many_points(self):
        """Test rendering with many position points."""
        # Simulate a cleaning path with 100 points
        positions = [(i * 10, (i % 10) * 100) for i in range(100)]
        result = render_path(positions)
        assert isinstance(result, bytes)
        assert result[:4] == b'\x89PNG'

        img = Image.open(io.BytesIO(result))
        assert img.size == (512, 512)

    def test_vertical_line_path(self):
        """Test that vertical line path renders correctly."""
        positions = [(100, 0), (100, 100), (100, 200), (100, 300)]
        result = render_path(positions)
        assert isinstance(result, bytes)
        assert result[:4] == b'\x89PNG'

    def test_horizontal_line_path(self):
        """Test that horizontal line path renders correctly."""
        positions = [(0, 100), (100, 100), (200, 100), (300, 100)]
        result = render_path(positions)
        assert isinstance(result, bytes)
        assert result[:4] == b'\x89PNG'

    def test_dock_included_in_bounds(self):
        """Test that dock position is included in coordinate bounds."""
        positions = [(0, 0), (100, 100)]
        # Dock is far from path - should still be visible
        dock_position = (500, 500)
        result = render_path(positions, dock_position=dock_position)

        img = Image.open(io.BytesIO(result))
        pixels = list(img.getdata())
        dock_color = (0, 200, 100)
        assert dock_color in pixels

    def test_empty_rooms_list(self):
        """Test that empty rooms list doesn't cause issues."""
        positions = [(0, 0), (100, 100)]
        result = render_path(positions, rooms=[])
        assert isinstance(result, bytes)
        assert result[:4] == b'\x89PNG'

    def test_rooms_without_names(self):
        """Test that rooms without names are handled gracefully."""
        positions = [(0, 0), (100, 100)]
        rooms = [{"id": 1}, {"name": "", "id": 2}]
        result = render_path(positions, rooms=rooms)
        assert isinstance(result, bytes)
        assert result[:4] == b'\x89PNG'

    def test_zigzag_cleaning_pattern(self):
        """Test realistic zigzag cleaning pattern from DPS 179 telemetry."""
        # Simulate the horizontal zigzag pattern observed in real telemetry
        positions = [
            (-8062, 412200),
            (-8125, 412250),
            (8201, 412416),
            (-8053, 412496),
            (-8127, 412573),
        ]
        result = render_path(positions)
        assert isinstance(result, bytes)
        assert result[:4] == b'\x89PNG'

        img = Image.open(io.BytesIO(result))
        assert img.size == (512, 512)

        # Verify path and robot are visible
        pixels = list(img.getdata())
        assert (0, 180, 200) in pixels  # Cyan path
        assert (255, 220, 0) in pixels  # Yellow robot

    def test_returns_bytes_not_raises(self):
        """Test that function never raises, always returns bytes."""
        # Empty positions
        result = render_path([])
        assert isinstance(result, bytes)

        # Single point
        result = render_path([(0, 0)])
        assert isinstance(result, bytes)

        # Large coordinates
        result = render_path([(1000000, 1000000)])
        assert isinstance(result, bytes)

        # Negative large coordinates
        result = render_path([(-1000000, -1000000)])
        assert isinstance(result, bytes)