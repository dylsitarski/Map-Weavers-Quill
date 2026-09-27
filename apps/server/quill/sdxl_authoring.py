"""Versioned SDXL authoring transforms, separate from native scene geometry."""

from dataclasses import dataclass
from uuid import UUID

import numpy as np
from PIL import Image

from quill.models import Project

TEMPLATE = "sdxl-overhead-v2"
NEGATIVE = (
    "perspective view, isometric view, oblique angle, horizon, skyline, vanishing point, "
    "eye level, side view, cutaway diorama, text, letters, labels, watermark, grid, "
    "checkerboard, neon colors, abstract shapes"
)


def prompt_text(description: str, style: dict[str, str], *, room: bool) -> str:
    subject = (
        "Interior floor plan, roof removed, furniture seen from directly above."
        if room
        else "Terrain and building roofs seen from directly above."
    )
    return (
        "Orthographic top-down tabletop battlemap. Camera vertically downward, "
        "parallel projection, flat overhead view. "
        + subject
        + "\n"
        + description.strip()
        + "\n"
        + ". ".join(f"{key}: {value}" for key, value in style.items() if value.strip())
        + ". Even diffuse illumination, readable floor surfaces, no grid or labels."
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


@dataclass(frozen=True)
class RoomTransform:
    width: int
    height: int

    @property
    def side(self) -> int:
        return max(self.width, self.height)

    @property
    def offset(self) -> tuple[int, int]:
        return ((self.side - self.width) // 2, (self.side - self.height) // 2)

    def prepare(self, source: Image.Image, mask: Image.Image) -> tuple[Image.Image, Image.Image]:
        if source.size != (self.width, self.height) or mask.size != source.size:
            raise ValueError("Room transform input sizes must match the crop.")
        left, top = self.offset
        # Extend edge colors, never invent a black frame. Padding is protected.
        pixels = np.pad(
            np.asarray(source.convert("RGB")),
            ((top, self.side - self.height - top), (left, self.side - self.width - left), (0, 0)),
            mode="edge",
        )
        square_mask = Image.new("L", (self.side, self.side))
        square_mask.paste(mask, self.offset)
        return (
            Image.fromarray(pixels).resize((1024, 1024), Image.Resampling.LANCZOS),
            square_mask.resize((1024, 1024), Image.Resampling.NEAREST),
        )

    def restore(self, output: Image.Image) -> Image.Image:
        if output.size != (1024, 1024):
            raise ValueError("Expected a 1024 × 1024 SDXL room result.")
        left, top = self.offset
        return output.resize((self.side, self.side), Image.Resampling.LANCZOS).crop(
            (left, top, left + self.width, top + self.height)
        )

    def metadata(self) -> dict:
        return {
            "version": "sdxl-room-fit-v1",
            "cropSize": [self.width, self.height],
            "paddingOffset": list(self.offset),
            "paddedSide": self.side,
            "generationSize": [1024, 1024],
            "sourceFilter": "lanczos",
            "maskFilter": "nearest",
            "returnFilter": "lanczos",
        }
