"""Validate openings and reconcile them before committing room geometry."""

import math
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from quill.models import Contract, Door, Wall
from quill.walls import RoomBoundary, WallDerivationRequest, derive_walls

EPS = 1e-7


class DoorInput(Door):
    id: Annotated[UUID, Field(strict=False)]
    wallId: Annotated[UUID, Field(strict=False)]


class DoorRequest(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    width: Annotated[float, Field(gt=0, le=1_000_000)]
    height: Annotated[float, Field(gt=0, le=1_000_000)]
    beforeRooms: Annotated[list[RoomBoundary], Field(max_length=128)]
    rooms: Annotated[list[RoomBoundary], Field(max_length=128)]
    doors: Annotated[list[DoorInput], Field(max_length=1024)]


class DoorResult(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    walls: Annotated[list[Wall], Field(max_length=8192)]
    doors: Annotated[list[Door], Field(max_length=1024)]


def length(wall: Wall) -> float:
    return math.hypot(wall.end.x - wall.start.x, wall.end.y - wall.start.y)


def owners(wall: Wall) -> set[str]:
    provenance = wall.metadata.get("quill.geometry")
    if not isinstance(provenance, dict):
        return set()
    values = provenance.get("sourceRoomIds")
    return {str(value) for value in values} if isinstance(values, list) else set()


def validate_doors(doors: list[Door], walls: list[Wall]) -> None:
    by_id = {wall.id: wall for wall in walls}
    seen: set[UUID] = set()
    intervals: dict[UUID, list[tuple[float, float]]] = {}
    for door in doors:
        if door.id in seen:
            raise ValueError("Door IDs must be unique.")
        seen.add(door.id)
        wall = by_id.get(door.wallId)
        if wall is None:
            raise ValueError("A door has no parent wall. Delete the door before removing its wall.")
        size = length(wall)
        low, high = door.position * size - door.width / 2, door.position * size + door.width / 2
        if low < -EPS or high > size + EPS:
            raise ValueError(
                "The full door opening must fit on one wall segment. Reduce its width."
            )
        for other_low, other_high in intervals.setdefault(wall.id, []):
            if min(high, other_high) - max(low, other_low) > EPS:
                raise ValueError("Door openings cannot overlap on the same wall.")
        intervals[wall.id].append((low, high))


def reconcile_doors(request: DoorRequest) -> DoorResult:
    def derive(rooms: list[RoomBoundary]) -> list[Wall]:
        return derive_walls(
            WallDerivationRequest(width=request.width, height=request.height, rooms=rooms)
        ).walls

    old_walls = derive(request.beforeRooms)
    walls = derive(request.rooms)
    doors: list[Door] = list(request.doors)
    validate_doors(doors, old_walls)
    old_by_id = {wall.id: wall for wall in old_walls}
    before = {str(room.id): room for room in request.beforeRooms}
    after = {str(room.id): room for room in request.rooms}
    result: list[Door] = []
    for door in doors:
        old = old_by_id[door.wallId]
        source_ids = owners(old)
        surviving = source_ids.intersection(after)
        if not surviving:
            raise ValueError("This edit removes a door's source rooms. Delete the door first.")
        # Support rigid translations only. Other reshaping may retain the original opening.
        shifts: set[tuple[float, float]] = set()
        for source in surviving:
            a, b = before[source].polygon, after[source].polygon
            if len(a) != len(b):
                shifts.add((0.0, 0.0))
                continue
            dx, dy = b[0].x - a[0].x, b[0].y - a[0].y
            if all(abs(q.x - p.x - dx) <= EPS and abs(q.y - p.y - dy) <= EPS for p, q in zip(a, b)):
                shifts.add((dx, dy))
            else:
                shifts.add((0.0, 0.0))
        if len(shifts) != 1:
            raise ValueError("This edit separates a shared door's rooms. Delete the door first.")
        dx, dy = next(iter(shifts))
        cx = old.start.x + door.position * (old.end.x - old.start.x) + dx
        cy = old.start.y + door.position * (old.end.y - old.start.y) + dy
        candidates: list[tuple[Wall, float]] = []
        for wall in walls:
            if not surviving.issubset(owners(wall)):
                continue
            wx, wy = wall.end.x - wall.start.x, wall.end.y - wall.start.y
            size = length(wall)
            # Same supporting line/direction; do not jump to a crossing wall.
            if abs(
                wx * (old.end.y - old.start.y) - wy * (old.end.x - old.start.x)
            ) > EPS * size * length(old):
                continue
            position = ((cx - wall.start.x) * wx + (cy - wall.start.y) * wy) / size**2
            distance = math.hypot(
                cx - wall.start.x - position * wx, cy - wall.start.y - position * wy
            )
            if (
                distance <= EPS
                and door.width / 2 - EPS <= position * size <= size - door.width / 2 + EPS
            ):
                candidates.append((wall, max(0.0, min(1.0, position))))
        if len(candidates) != 1:
            raise ValueError(
                "This edit would cut through or detach a door. Move or delete the door first."
            )
        wall, position = candidates[0]
        changed = wall.id != door.wallId or abs(position - door.position) > EPS
        result.append(
            door.model_copy(
                update={
                    "wallId": wall.id,
                    "position": position,
                    "revision": door.revision + int(changed),
                }
            )
        )
    validate_doors(result, walls)
    return DoorResult(walls=walls, doors=result)
