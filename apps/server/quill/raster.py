"""Fixed-resolution native/pixel conversion and deterministic masking."""

from io import BytesIO

import numpy as np
from PIL import Image
from shapely import intersects_xy  # type: ignore[import-untyped]
from shapely.geometry import Polygon  # type: ignore[import-untyped]

from quill.models import Point

WIDTH, HEIGHT, SCALE = 480, 320, 2.5


def polygon_mask(points: list[Point]) -> Image.Image:
    """Binary pixel-center coverage; native +y is up, image rows run down."""
    polygon = Polygon([(p.x, p.y) for p in points])
    x = (np.arange(WIDTH) + 0.5) * SCALE
    y = 800 - (np.arange(HEIGHT) + 0.5) * SCALE
    covered = intersects_xy(polygon, x[None, :], y[:, None])
    return Image.fromarray(np.asarray(covered, dtype=np.uint8) * 255)


def png(image: Image.Image) -> bytes:
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def image(data: bytes) -> Image.Image:
    with Image.open(BytesIO(data)) as opened:
        return opened.convert("RGBA")


def masked_layer(generated: Image.Image, mask: Image.Image) -> Image.Image:
    return Image.composite(generated.convert("RGBA"), Image.new("RGBA", (WIDTH, HEIGHT)), mask)
