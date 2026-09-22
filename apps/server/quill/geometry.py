"""Stateless world-space polygon validation. Never silently repair geometry."""

from typing import Annotated, Literal

from pydantic import Field
from shapely.geometry import Polygon  # type: ignore[import-untyped]

from quill.models import Contract, Point


class GeometryRequest(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    width: Annotated[float, Field(gt=0, le=1_000_000)]
    height: Annotated[float, Field(gt=0, le=1_000_000)]
    polygon: Annotated[list[Point], Field(min_length=3, max_length=2048)]


class GeometryResult(Contract):
    valid: bool
    error: str | None


def validate_geometry(request: GeometryRequest) -> GeometryResult:
    points = [(p.x, p.y) for p in request.polygon]
    error = None
    if any(not (0 <= x <= request.width and 0 <= y <= request.height) for x, y in points):
        error = "Keep every vertex inside the map bounds."
    elif len(set(points)) != len(points):
        error = "Remove repeated vertices; the final vertex must not repeat the first."
    else:
        polygon = Polygon(points)
        if not polygon.is_valid or polygon.area <= 0:
            error = "Draw a polygon with positive area and no crossing or overlapping edges."
    return GeometryResult(valid=error is None, error=error)
