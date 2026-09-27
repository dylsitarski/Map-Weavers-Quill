"""Resolution-aware native/pixel conversion and deterministic masking."""

from io import BytesIO

import numpy as np
from PIL import Image
from shapely import intersects_xy  # type: ignore[import-untyped]
from shapely.geometry import Polygon  # type: ignore[import-untyped]

from quill.models import Point

# The old profile remains the default for existing mock projects.
WIDTH, HEIGHT, SCALE = 480, 320, 2.5
DEFAULT_SIZE = (WIDTH, HEIGHT)
SDXL_SIZE = (960, 640)
SUPPORTED_SIZES = {DEFAULT_SIZE, SDXL_SIZE}


def validate_size(size: tuple[int, int]) -> None:
    if size not in SUPPORTED_SIZES:
        raise ValueError("Supported map raster sizes are 480 × 320 and 960 × 640.")


def polygon_mask(points: list[Point], size: tuple[int, int] = DEFAULT_SIZE) -> Image.Image:
    """Binary pixel-center coverage on the fixed 1200x800 native map; +y is up."""
    validate_size(size)
    width, height = size
    polygon = Polygon([(p.x, p.y) for p in points])
    x = (np.arange(width) + 0.5) * 1200 / width
    y = 800 - (np.arange(height) + 0.5) * 800 / height
    covered = intersects_xy(polygon, x[None, :], y[:, None])
    return Image.fromarray(np.asarray(covered, dtype=np.uint8) * 255)


def context_crop(
    mask: Image.Image, *, margin: int = 8, alignment: int = 1
) -> tuple[int, int, int, int]:
    """Pad a mask bbox without stretching; optional provider-aligned dimensions.

    A crop's (left, top) is its image-space translation. Alignment adds context,
    never scales pixels. Edge clamping still includes every editable pixel.
    """
    validate_size(mask.size)
    if margin < 0 or alignment < 1 or any(n % alignment for n in mask.size):
        raise ValueError("Invalid crop margin or alignment for this raster size.")
    box = mask.getbbox()
    if box is None:
        raise ValueError("The room is too small at the current raster resolution.")

    def axis(start: int, end: int, limit: int) -> tuple[int, int]:
        low, high = max(0, start - margin), min(limit, end + margin)
        length = min(limit, ((high - low + alignment - 1) // alignment) * alignment)
        low = max(0, min(low - (length - (high - low)) // 2, limit - length))
        return low, low + length

    left, right = axis(box[0], box[2], mask.width)
    top, bottom = axis(box[1], box[3], mask.height)
    return left, top, right, bottom


def png(image: Image.Image) -> bytes:
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def image(data: bytes) -> Image.Image:
    with Image.open(BytesIO(data)) as opened:
        return opened.convert("RGBA")


def masked_layer(generated: Image.Image, mask: Image.Image) -> Image.Image:
    validate_size(mask.size)
    if generated.size != mask.size:
        raise ValueError("Generated artwork and its mask must have identical dimensions.")
    return Image.composite(generated.convert("RGBA"), Image.new("RGBA", mask.size), mask)
