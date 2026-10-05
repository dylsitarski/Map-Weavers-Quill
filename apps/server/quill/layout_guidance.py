"""Deterministic room wall guidance and physical scale; image rows point down."""

import math

from PIL import Image, ImageDraw
from shapely.geometry import Polygon  # type: ignore[import-untyped]

from quill.doors import owners
from quill.models import Project, Room, Wall
from quill.sdxl_authoring import RoomTransform

# Sketch colors for reference-image room edits (ADR-0032). Pure black means "no sketch".
SKETCH_WALL = (30, 30, 30)
SKETCH_DOOR = (140, 90, 45)


def _openings(project: Project, wall: Wall, length: float, *, secret: bool) -> list:
    """Door intervals along a wall as (low, high, door) fractions, sorted."""
    return sorted(
        (
            max(0.0, d.position - d.width / (2 * length)),
            min(1.0, d.position + d.width / (2 * length)),
            d,
        )
        for d in project.doors
        if d.wallId == wall.id and d.doorType == "door" and (secret or not d.secret)
    )


def _solid(openings: list) -> list[tuple[float, float]]:
    segments = []
    start = 0.0
    for low, high, _ in openings:
        if low > start:
            segments.append((start, low))
        start = max(start, high)
    if start < 1:
        segments.append((start, 1.0))
    return segments


def wall_guide(project: Project, size: tuple[int, int]) -> Image.Image:
    guide = Image.new("L", size)
    draw = ImageDraw.Draw(guide)
    sx, sy = size[0] / project.map.width, size[1] / project.map.height
    for wall in project.walls:
        dx, dy = wall.end.x - wall.start.x, wall.end.y - wall.start.y
        length = math.hypot(dx, dy)
        for low, high in _solid(_openings(project, wall, length, secret=True)):
            draw.line(
                [
                    ((wall.start.x + dx * t) * sx, size[1] - (wall.start.y + dy * t) * sy)
                    for t in (low, high)
                ],
                fill=255,
                width=1,
            )
    return guide


def room_sketch(project: Project, size: tuple[int, int], room: Room) -> Image.Image:
    """Architectural sketch of one room's walls on black: thick dark walls at the project's
    wall thickness, open doors as gaps, closed/locked doors as brown bars, secret doors as
    plain wall, windows as wall. Other rooms' walls are omitted so only the target room
    reads as a sketch. Black pixels are transparent when composited."""
    sketch = Image.new("RGB", size)
    draw = ImageDraw.Draw(sketch)
    sx, sy = size[0] / project.map.width, size[1] / project.map.height
    width = max(3, round(project.map.style.wallThicknessPx * sx))
    bar = max(2, width // 2)

    def point(wall: Wall, t: float) -> tuple[float, float]:
        return (
            (wall.start.x + (wall.end.x - wall.start.x) * t) * sx,
            size[1] - (wall.start.y + (wall.end.y - wall.start.y) * t) * sy,
        )

    for wall in project.walls:
        if str(room.id) not in owners(wall):
            continue
        length = math.hypot(wall.end.x - wall.start.x, wall.end.y - wall.start.y)
        openings = _openings(project, wall, length, secret=False)
        for low, high in _solid(openings):
            ends = [point(wall, low), point(wall, high)]
            draw.line(ends, fill=SKETCH_WALL, width=width)
            for x, y in ends:  # Round joints so corners have no notches.
                r = width / 2
                draw.ellipse((x - r, y - r, x + r, y + r), fill=SKETCH_WALL)
        for low, high, door in openings:
            if door.state != "open":
                draw.line([point(wall, low), point(wall, high)], fill=SKETCH_DOOR, width=bar)
    return sketch


def working_guide(
    guide: Image.Image, crop: tuple[int, int, int, int], transform: RoomTransform
) -> Image.Image:
    square = Image.new(guide.mode, (transform.side, transform.side))
    square.paste(guide.crop(crop), transform.offset)
    return square.resize((1024, 1024), Image.Resampling.NEAREST).convert("RGB")


def room_scale(
    project: Project, room: Room, size: tuple[int, int], transform: RoomTransform
) -> dict:
    grid = project.map.grid
    factor = grid.distance / grid.sizePx
    xs, ys = [p.x for p in room.polygon], [p.y for p in room.polygon]
    return {
        "version": "room-layout-v1",
        "units": grid.units,
        "cellDistance": grid.distance,
        "nativeCellSize": grid.sizePx,
        "boundsWidth": (max(xs) - min(xs)) * factor,
        "boundsHeight": (max(ys) - min(ys)) * factor,
        "area": Polygon([(p.x, p.y) for p in room.polygon]).area * factor * factor,
        "workingPixelsPerUnit": size[0] / project.map.width / factor * 1024 / transform.side,
    }


def scale_prompt(scale: dict, *, controlled: bool) -> str:
    text = (
        f"Physical scale: each grid cell is {scale['cellDistance']:g} {scale['units']}. "
        f"This single space has bounding dimensions {scale['boundsWidth']:g} by "
        f"{scale['boundsHeight']:g} {scale['units']}, area {scale['area']:g} square {scale['units']}. "
        "Use life-size furniture that fits this space, not a miniature house. "
        "Do not subdivide the space or add interior partitions. "
    )
    if controlled:
        text += "Follow the supplied wall lines; gaps are door openings. Keep openings clear. "
    return text
