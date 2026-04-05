"""PIL-based path-tracker map renderer for vacuum cleaning path visualization."""

from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageDraw


def render_path(
    positions: list[tuple[int, int]],
    dock_position: tuple[int, int] | None = None,
    rooms: list[dict[str, Any]] | None = None,
    image_size: int = 512,
) -> bytes:
    """Render cleaning path as PNG.

    Args:
        positions: List of (x, y) raw coordinate pairs from DPS 179 telemetry.
        dock_position: Optional dock (x, y) coordinate.
        rooms: Optional list of {"name": str, "id": int} for labels (not positioned).
        image_size: Output image dimension (square).

    Returns:
        PNG bytes. Never raises — returns a placeholder if positions is empty.

    Coordinates are raw int values from DPS 179 (can be any range).
    Auto-scales to fit the image with 5% margin on each side.
    """
    # Colors
    BG_COLOR = (20, 20, 30)  # Dark blue-gray (HA dark mode friendly)
    PATH_COLOR = (0, 180, 200)  # Cyan
    ROBOT_COLOR = (255, 220, 0)  # Bright yellow
    DOCK_COLOR = (0, 200, 100)  # Bright green
    LABEL_COLOR = (180, 180, 180)  # Light gray

    # Create image with dark background
    img = Image.new("RGB", (image_size, image_size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # If no positions, return empty dark background
    if not positions:
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    # Calculate bounds with 5% margin
    margin_ratio = 0.05
    margin_pixels = int(image_size * margin_ratio)
    usable_size = image_size - 2 * margin_pixels

    # Find coordinate bounds
    x_coords = [p[0] for p in positions]
    y_coords = [p[1] for p in positions]

    min_x = min(x_coords)
    max_x = max(x_coords)
    min_y = min(y_coords)
    max_y = max(y_coords)

    # Include dock position in bounds if provided
    if dock_position:
        min_x = min(min_x, dock_position[0])
        max_x = max(max_x, dock_position[0])
        min_y = min(min_y, dock_position[1])
        max_y = max(max_y, dock_position[1])

    # Calculate scale factors
    x_range = max_x - min_x
    y_range = max_y - min_y

    # Handle degenerate cases (single point or line)
    if x_range == 0 and y_range == 0:
        # Single point - center it
        scale = 1.0
    elif x_range == 0:
        # Vertical line
        scale = usable_size / y_range if y_range > 0 else 1.0
    elif y_range == 0:
        # Horizontal line
        scale = usable_size / x_range if x_range > 0 else 1.0
    else:
        # Normal case - scale to fit
        scale = min(usable_size / x_range, usable_size / y_range)

    def transform_x(x: int) -> int:
        """Transform raw X coordinate to image coordinate."""
        if x_range == 0:
            return image_size // 2
        return margin_pixels + int((x - min_x) * scale)

    def transform_y(y: int) -> int:
        """Transform raw Y coordinate to image coordinate (flipped for image coords)."""
        if y_range == 0:
            return image_size // 2
        # Flip Y axis (image Y increases downward, map Y increases upward)
        return margin_pixels + int((max_y - y) * scale)

    # Draw path as connected polyline
    if len(positions) >= 2:
        path_points = [(transform_x(x), transform_y(y)) for x, y in positions]
        draw.line(path_points, fill=PATH_COLOR, width=2)

    # Draw dock marker if provided
    if dock_position:
        dock_x = transform_x(dock_position[0])
        dock_y = transform_y(dock_position[1])
        # Draw 10x10 filled square centered at dock position
        draw.rectangle(
            [dock_x - 5, dock_y - 5, dock_x + 5, dock_y + 5],
            fill=DOCK_COLOR,
        )

    # Draw current robot position (last point) as bright yellow dot
    if positions:
        last_x, last_y = positions[-1]
        robot_x = transform_x(last_x)
        robot_y = transform_y(last_y)
        # Draw circle with radius 8
        draw.ellipse(
            [robot_x - 8, robot_y - 8, robot_x + 8, robot_y + 8],
            fill=ROBOT_COLOR,
        )

    # Draw room labels (positioned at top-left, no positioning data available)
    if rooms:
        y_offset = 10
        for room in rooms:
            name = room.get("name", "")
            if name:
                draw.text((10, y_offset), name, fill=LABEL_COLOR)
                y_offset += 15

    # Convert to PNG bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()