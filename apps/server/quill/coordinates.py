"""Continuous world/raster transforms only; not a Foundry adapter."""

from math import isfinite


def _finite(*values: float) -> None:
    if any(not isfinite(v) for v in values):
        raise ValueError("Coordinates must be finite")


def reflect_point(x: float, y: float, map_height: float) -> tuple[float, float]:
    """Bidirectional top-left/bottom-left continuous edge transform."""
    _finite(x, y, map_height)
    if map_height <= 0:
        raise ValueError("Map height must be positive")
    return x, map_height - y


def raster_rectangle(
    x: float, y: float, width: float, height: float, map_height: float
) -> tuple[float, float, float, float]:
    """Bottom-left world bounds to top-left raster bounds at scale one."""
    _finite(width, height)
    if width <= 0 or height <= 0:
        raise ValueError("Rectangle dimensions must be positive")
    rx, ry = reflect_point(x, y + height, map_height)
    return rx, ry, width, height


def clockwise_from_positive_x(angle: float) -> float:
    """CCW world angle to CW target angle sharing +x as zero."""
    _finite(angle)
    return (-angle) % 360
