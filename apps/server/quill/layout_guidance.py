"""Deterministic room wall guidance and physical scale; image rows point down."""

import math

from PIL import Image, ImageDraw
from shapely.geometry import Polygon  # type: ignore[import-untyped]

from quill.models import Project, Room
from quill.sdxl_authoring import RoomTransform


def wall_guide(project: Project, size: tuple[int, int]) -> Image.Image:
    guide = Image.new("L", size)
    draw = ImageDraw.Draw(guide)
    sx, sy = size[0] / project.map.width, size[1] / project.map.height
    for wall in project.walls:
        dx, dy = wall.end.x - wall.start.x, wall.end.y - wall.start.y
        length = math.hypot(dx, dy)
        gaps = sorted(
            (
                max(0.0, d.position - d.width / (2 * length)),
                min(1.0, d.position + d.width / (2 * length)),
            )
            for d in project.doors
            if d.wallId == wall.id and d.doorType == "door"
        )
        segments = []
        start = 0.0
        for low, high in gaps:
            if low > start:
                segments.append((start, low))
            start = max(start, high)
        if start < 1:
            segments.append((start, 1.0))
        for low, high in segments:
            draw.line(
                [
                    ((wall.start.x + dx * t) * sx, size[1] - (wall.start.y + dy * t) * sy)
                    for t in (low, high)
                ],
                fill=255,
                width=1,
            )
    return guide


def working_guide(
    guide: Image.Image, crop: tuple[int, int, int, int], transform: RoomTransform
) -> Image.Image:
    square = Image.new("L", (transform.side, transform.side))
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
