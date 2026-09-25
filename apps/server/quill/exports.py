"""Read-only, fixed-resolution artwork composition and image export."""

from io import BytesIO
from typing import Literal

from PIL import Image

from quill.models import Contract, Project
from quill.projects import ProjectStore, project_store, validate_project
from quill.raster import HEIGHT, WIDTH, image


class ExportRequest(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    project: Project
    format: Literal["png", "webp"]


def composite_artwork(project: Project, store: ProjectStore) -> Image.Image:
    """Caller validates the project/assets first. Same compositor as inpaint context."""
    source = Image.new("RGBA", (WIDTH, HEIGHT), "#e9e2ce")
    for layer in sorted(project.layers, key=lambda layer: (layer.zIndex, str(layer.id))):
        if layer.visible:
            overlay = image(store.get_asset(layer.assetHash))
            overlay.putalpha(
                overlay.getchannel("A").point(lambda alpha: round(alpha * layer.opacity))
            )
            source = Image.alpha_composite(source, overlay)
    return source


def export_image(request: ExportRequest) -> bytes:
    project = validate_project(request.project, derive_missing=True)
    store = project_store()
    db = store.connect()
    try:
        store.validate_assets(db, project)
    finally:
        db.close()
    output = BytesIO()
    composite = composite_artwork(project, store).convert("RGB")
    if request.format == "webp":
        composite.save(output, format="WEBP", lossless=True, method=4)
    else:
        composite.save(output, format="PNG")
    return output.getvalue()
