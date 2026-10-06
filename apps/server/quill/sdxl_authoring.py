"""Versioned SDXL authoring transforms, separate from native scene geometry."""

from dataclasses import dataclass
from uuid import UUID

import numpy as np
from PIL import Image

from quill.models import Project

TEMPLATE = "sdxl-overhead-v3"
MAP_FEET = (120, 80)  # The fixed map: 1200 × 800 units on a 50-unit, 5-ft grid.
NEGATIVE = (
    "perspective view, isometric view, oblique angle, horizon, skyline, vanishing point, "
    "eye level, side view, cutaway diorama, text, letters, labels, watermark, grid, "
    "checkerboard, neon colors, abstract shapes"
)


def prompt_text(description: str, style: dict[str, str], *, room: bool, scale: str = "") -> str:
    subject = (
        "Interior floor plan, roof removed, furniture seen from directly above."
        if room
        else "Terrain and building roofs seen from directly above."
    )
    styled = ". ".join(f"{key}: {value}" for key, value in style.items() if value.strip())
    return (
        "Orthographic top-down tabletop battlemap. Camera vertically downward, "
        "parallel projection, flat overhead view. "
        + subject
        + "\n"
        + description.strip()
        + "\n"
        + (styled + ". " if styled else "")
        + (scale + " " if scale else "")
        + (
            "Even diffuse illumination, readable floor surfaces, no grid or labels."
            if room
            else "Even diffuse illumination, no grid or labels."
        )
    )


def background_scale(width: int) -> str:
    """Physical scale of the fixed 1200 × 800-unit (120 × 80 ft) map at ``width`` pixels."""
    square = width / MAP_FEET[0] * 5
    return (
        f"The image covers {MAP_FEET[0]} by {MAP_FEET[1]} feet of ground; one 5-foot square "
        f"is {square:g} pixels wide. Draw trees, paths and buildings at life size for that "
        "scale."
    )


def clean_context(project: Project, room_id: UUID) -> tuple[Project, list[str]]:
    """Hide known mock outputs and target art in a copy; unknown provenance is retained."""
    mock_hashes = {r.outputHash for r in project.generations if r.providerId == "mock"}
    result = project.model_copy(deep=True)
    excluded = []
    for layer in result.layers:
        role = layer.metadata.get("quill.render")
        target = isinstance(role, dict) and role.get("roomId") == str(room_id)
        if target or layer.assetHash in mock_hashes:
            layer.visible = False
            excluded.append(str(layer.id))
    return result, excluded


WORKING_SIDE = 1024  # Square model resolution for room edits.
WINDOW_CELLS = 8  # Default window: 8 grid cells (40 ft on a 5-ft grid) on each side.


@dataclass(frozen=True)
class RoomWindow:
    """Square map-raster window around a room, resized to a fixed working square.

    The window is a fixed physical size, so furniture and walls get the same working
    scale in every room. It holds real map context and is clamped inside the map; only a
    room too large for the map's short side gets a window that extends past the map,
    and that padding (edge colors) is outside the mask and therefore protected.
    """

    left: int
    top: int
    side: int
    raster: tuple[int, int]

    @classmethod
    def around(cls, mask: Image.Image, base: int, margin: int) -> "RoomWindow":
        box = mask.getbbox()
        if box is None:
            raise ValueError("The room is too small at the current raster resolution.")
        side = max(base, box[2] - box[0] + 2 * margin, box[3] - box[1] + 2 * margin)

        def start(low: int, high: int, limit: int) -> int:
            if side > limit:  # Centre on the map; padding falls outside it.
                return (limit - side) // 2
            return min(max(0, (low + high - side) // 2), limit - side)

        return cls(
            start(box[0], box[2], mask.width), start(box[1], box[3], mask.height), side, mask.size
        )

    @property
    def scale(self) -> float:
        """Working pixels per map-raster pixel."""
        return WORKING_SIDE / self.side

    @property
    def crop(self) -> tuple[int, int, int, int]:
        """The window's part of the map raster (the whole window unless padded)."""
        return (
            max(0, self.left),
            max(0, self.top),
            min(self.raster[0], self.left + self.side),
            min(self.raster[1], self.top + self.side),
        )

    def square(self, picture: Image.Image, *, edge: bool) -> Image.Image:
        """The window at raster resolution; out-of-map pixels repeat edges or stay black."""
        if picture.size != self.raster:
            raise ValueError("Room window input must match the map raster size.")
        crop = self.crop
        inner = picture.crop(crop)
        offset = (crop[0] - self.left, crop[1] - self.top)
        if edge and inner.size != (self.side, self.side):
            pixels = np.asarray(inner.convert("RGB"))
            pad = (
                (offset[1], self.side - inner.height - offset[1]),
                (offset[0], self.side - inner.width - offset[0]),
                (0, 0),
            )
            return Image.fromarray(np.pad(pixels, pad, mode="edge"))
        square = Image.new(picture.mode, (self.side, self.side))
        square.paste(inner, offset)
        return square

    def prepare(self, source: Image.Image, mask: Image.Image) -> tuple[Image.Image, Image.Image]:
        size = (WORKING_SIDE, WORKING_SIDE)
        return (
            self.square(source.convert("RGB"), edge=True).resize(size, Image.Resampling.LANCZOS),
            self.square(mask, edge=False).resize(size, Image.Resampling.NEAREST),
        )

    def guide(self, guide: Image.Image) -> Image.Image:
        """A full-raster guide in working space (nearest neighbour keeps exact lines)."""
        square = self.square(guide, edge=False)
        return square.resize((WORKING_SIDE, WORKING_SIDE), Image.Resampling.NEAREST).convert("RGB")

    def to_working(self, x: float, y: float) -> tuple[float, float]:
        """Map-raster pixel coordinates (rows down) to working pixels."""
        return ((x - self.left) * self.scale, (y - self.top) * self.scale)

    def restore(self, output: Image.Image) -> Image.Image:
        """The working result resized back to raster pixels for ``crop``."""
        if output.size != (WORKING_SIDE, WORKING_SIDE):
            raise ValueError("Expected a 1024 × 1024 room result.")
        crop = self.crop
        x, y = crop[0] - self.left, crop[1] - self.top
        return output.resize((self.side, self.side), Image.Resampling.LANCZOS).crop(
            (x, y, x + crop[2] - crop[0], y + crop[3] - crop[1])
        )

    def metadata(self) -> dict:
        return {
            "version": "room-window-v1",
            "window": [self.left, self.top, self.side],
            "crop": list(self.crop),
            "generationSize": [WORKING_SIDE, WORKING_SIDE],
            "workingScale": self.scale,
            "sourceFilter": "lanczos",
            "maskFilter": "nearest",
            "returnFilter": "lanczos",
        }
