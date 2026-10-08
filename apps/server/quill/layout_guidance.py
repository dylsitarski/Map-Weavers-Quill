"""Deterministic room wall guidance and physical scale; image rows point down."""

import math
from collections.abc import Callable

from PIL import Image, ImageDraw
from shapely.geometry import Polygon  # type: ignore[import-untyped]

from quill.doors import owners
from quill.models import Door, Project, Room, Wall
from quill.sdxl_authoring import WORKING_SIDE, RoomWindow

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


def _room_doors(project: Project, room: Room) -> list[tuple[Wall, float, list]]:
    walls = []
    for wall in project.walls:
        if str(room.id) in owners(wall):
            length = math.hypot(wall.end.x - wall.start.x, wall.end.y - wall.start.y)
            walls.append((wall, length, _openings(project, wall, length, secret=False)))
    return walls


def _sketch_space(
    project: Project, size: tuple[int, int], window: RoomWindow | None
) -> tuple[int, Callable[[Wall, float], tuple[float, float]]]:
    """Wall width and a wall-point mapper in working space (or map raster space)."""
    sx, sy = size[0] / project.map.width, size[1] / project.map.height
    zoom = window.scale if window else 1.0
    width = max(3, round(project.map.style.wallThicknessPx * sx * zoom))

    def point(wall: Wall, t: float) -> tuple[float, float]:
        x = (wall.start.x + (wall.end.x - wall.start.x) * t) * sx
        y = size[1] - (wall.start.y + (wall.end.y - wall.start.y) * t) * sy
        return window.to_working(x, y) if window else (x, y)

    return width, point


def room_sketch(
    project: Project,
    size: tuple[int, int],
    room: Room,
    window: RoomWindow | None = None,
    *,
    doors: bool = True,
) -> Image.Image:
    """Floor-plan sketch of one room's walls on black, in working space for ``window``
    or at map raster ``size`` without one (the stored provenance copy).

    Walls are dark bands at the project's wall thickness, so they have the same physical
    width in every room. With ``doors``, every door is drawn closed, whatever its state: a
    brown band of wall thickness filling its opening (open-door symbols were rendered
    badly and left in the image). Without, doorways are drawn as wall, for a separate door
    pass (ADR-0037). Secret doors and windows are always wall. Other rooms' walls are
    omitted. Black pixels are transparent when composited.
    """
    sketch = Image.new("RGB", (WORKING_SIDE,) * 2 if window else size)
    draw = ImageDraw.Draw(sketch)
    width, point = _sketch_space(project, size, window)
    for wall, _, openings in _room_doors(project, room):
        for low, high in _solid(openings if doors else []):
            ends = [point(wall, low), point(wall, high)]
            draw.line(ends, fill=SKETCH_WALL, width=width)
            for x, y in ends:  # Round joints so corners have no notches.
                r = width / 2
                draw.ellipse((x - r, y - r, x + r, y + r), fill=SKETCH_WALL)
        if doors:
            for low, high, _ in openings:
                draw.line([point(wall, low), point(wall, high)], fill=SKETCH_DOOR, width=width)
    return sketch


def door_strips(
    project: Project, size: tuple[int, int], room: Room, window: RoomWindow, pad: float
) -> list[tuple[Door, list[tuple[float, float]]]]:
    """Each visible door of a room as a quadrilateral in working pixels: the opening
    along its wall, wall thickness plus ``pad`` on each side across it (ADR-0037)."""
    width, point = _sketch_space(project, size, window)
    strips = []
    for wall, _, openings in _room_doors(project, room):
        for low, high, door in openings:
            (x0, y0), (x1, y1) = point(wall, low), point(wall, high)
            length = math.hypot(x1 - x0, y1 - y0)
            if not length:
                continue
            half = width / 2 + pad
            nx, ny = -(y1 - y0) / length * half, (x1 - x0) / length * half
            strips.append(
                (
                    door,
                    [
                        (x0 + nx, y0 + ny),
                        (x1 + nx, y1 + ny),
                        (x1 - nx, y1 - ny),
                        (x0 - nx, y0 - ny),
                    ],
                )
            )
    return strips


def room_scale(project: Project, room: Room, size: tuple[int, int], window: RoomWindow) -> dict:
    grid = project.map.grid
    factor = grid.distance / grid.sizePx
    xs, ys = [p.x for p in room.polygon], [p.y for p in room.polygon]
    raster = size[0] / project.map.width
    return {
        "version": "room-layout-v2",
        "units": grid.units,
        "cellDistance": grid.distance,
        "nativeCellSize": grid.sizePx,
        "boundsWidth": (max(xs) - min(xs)) * factor,
        "boundsHeight": (max(ys) - min(ys)) * factor,
        "area": Polygon([(p.x, p.y) for p in room.polygon]).area * factor * factor,
        "windowSize": round(window.side / raster * factor, 4),
        "workingPixelsPerUnit": round(raster * window.scale / factor, 4),
    }


def scale_prompt(scale: dict, *, controlled: bool) -> str:
    units = scale["units"]
    cell = scale["cellDistance"] * scale["workingPixelsPerUnit"]
    text = (
        f"Scale: the image shows {scale['windowSize']:g} by {scale['windowSize']:g} {units}; "
        f"one {scale['cellDistance']:g}-{units} grid square is {cell:.0f} pixels wide. "
        f"This room measures {scale['boundsWidth']:g} by {scale['boundsHeight']:g} {units}. "
        "Use life-size furniture for that scale, not a miniature house. "
        "Do not subdivide the space or add interior partitions."
    )
    if controlled:
        text += " Follow the supplied wall lines; gaps are door openings. Keep openings clear."
    return text
