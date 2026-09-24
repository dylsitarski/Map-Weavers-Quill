"""Deterministic derived wall cache. Room geometry remains authoritative."""

import json
from typing import Annotated, Literal
from uuid import UUID, uuid5

from pydantic import Field
from shapely.geometry import LineString  # type: ignore[import-untyped]
from shapely.geometry import Point as GeometryPoint  # type: ignore[import-untyped]
from shapely.ops import unary_union  # type: ignore[import-untyped]
from shapely.strtree import STRtree  # type: ignore[import-untyped]

from quill.geometry import GeometryRequest, validate_geometry
from quill.models import Contract, Point, Wall

WALL_NAMESPACE = UUID("097a32d9-3f61-445e-9721-c7ac4dc5f615")
MAX_EDGES = 2048
MAX_SEGMENTS = 8192


class RoomBoundary(Contract):
    # FastAPI parses JSON before Pydantic validation; permit UUID strings here.
    id: Annotated[UUID, Field(strict=False)]
    polygon: Annotated[list[Point], Field(min_length=3, max_length=2048)]


class WallDerivationRequest(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    width: Annotated[float, Field(gt=0, le=1_000_000)]
    height: Annotated[float, Field(gt=0, le=1_000_000)]
    rooms: Annotated[list[RoomBoundary], Field(max_length=128)]


class WallDerivationResult(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    walls: Annotated[list[Wall], Field(max_length=8192)]


def derive_walls(request: WallDerivationRequest) -> WallDerivationResult:
    if sum(len(room.polygon) for room in request.rooms) > MAX_EDGES:
        raise ValueError("Wall derivation supports at most 2048 total room vertices.")
    if len({room.id for room in request.rooms}) != len(request.rooms):
        raise ValueError("Room IDs must be unique.")
    # Canonical edge orientation/order makes winding and room ordering irrelevant.
    sources: dict[tuple[tuple[float, float], tuple[float, float]], set[str]] = {}
    for room in request.rooms:
        result = validate_geometry(
            GeometryRequest(width=request.width, height=request.height, polygon=room.polygon)
        )
        if not result.valid:
            raise ValueError(f"Room {room.id}: {result.error}")
        points = [(p.x or 0.0, p.y or 0.0) for p in room.polygon]
        for i, start in enumerate(points):
            end = points[(i + 1) % len(points)]
            key = (min(start, end), max(start, end))
            sources.setdefault(key, set()).add(str(room.id))
    if not sources:
        return WallDerivationResult(walls=[])
    edges = [(LineString(key), owners) for key, owners in sorted(sources.items())]
    noded = unary_union([line for line, _ in edges])
    parts = [noded] if noded.geom_type == "LineString" else list(noded.geoms)
    segments: set[tuple[tuple[float, float], tuple[float, float]]] = set()
    for part in parts:
        coordinates = list(part.coords)
        for a, b in zip(coordinates, coordinates[1:]):
            a = (float(a[0]) or 0.0, float(a[1]) or 0.0)
            b = (float(b[0]) or 0.0, float(b[1]) or 0.0)
            if a != b:
                segments.add((min(a, b), max(a, b)))
            if len(segments) > MAX_SEGMENTS:
                raise ValueError("Too many derived wall segments; simplify overlapping rooms.")
    index = STRtree([line for line, _ in edges])
    walls = []
    for start, end in sorted(segments):
        segment = LineString([start, end])
        # Only provenance uses this tolerance; persisted endpoints are never rounded/snapped.
        owners = sorted(
            {
                owner
                for edge_index in index.query(segment.buffer(1e-8))
                for line, ids in [edges[int(edge_index)]]
                if line.distance(GeometryPoint(start)) <= 1e-8
                and line.distance(GeometryPoint(end)) <= 1e-8
                for owner in ids
            }
        )
        if not owners:
            raise ValueError("Could not resolve wall provenance; simplify the room geometry.")
        identity = json.dumps([start, end], separators=(",", ":"))
        walls.append(
            Wall(
                id=uuid5(WALL_NAMESPACE, identity),
                kind="wall",
                revision=0,
                label="Wall",
                start=Point(x=start[0], y=start[1]),
                end=Point(x=end[0], y=end[1]),
                movement=True,
                sight=True,
                sourceRoomId=UUID(owners[0]) if len(owners) == 1 else None,
                metadata={"quill.geometry": {"sourceRoomIds": [owner for owner in owners]}},
            )
        )
    return WallDerivationResult(walls=walls)
