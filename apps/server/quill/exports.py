"""Read-only artwork composition/export at the highest stored layer resolution."""

from io import BytesIO
from typing import Literal

from PIL import Image, ImageChops

from quill.models import Contract, Project
from quill.projects import ProjectStore, project_store, validate_project
from quill.raster import DEFAULT_SIZE, image, polygon_mask, validate_size


class ExportRequest(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    project: Project
    format: Literal["png", "webp"]


def artwork_size(project: Project, store: ProjectStore) -> tuple[int, int]:
    """Include hidden layers so visibility/opacity toggles cannot change output size."""
    sizes = [image(store.get_asset(layer.assetHash)).size for layer in project.layers]
    return max(sizes, default=DEFAULT_SIZE, key=lambda size: size[0])


def composite_artwork(
    project: Project, store: ProjectStore, *, size: tuple[int, int] | None = None
) -> Image.Image:
    """Caller validates assets. Resampling affects this composite only, never originals."""
    native_size = artwork_size(project, store)
    size = native_size if size is None else size
    validate_size(size)
    if size[0] < native_size[0]:
        raise ValueError("Compositing cannot discard stored artwork resolution.")
    source = Image.new("RGBA", size, "#e9e2ce")
    rooms = {str(room.id): room for room in project.rooms}
    for layer in sorted(project.layers, key=lambda layer: (layer.zIndex, str(layer.id))):
        if layer.visible:
            overlay = image(store.get_asset(layer.assetHash))
            if overlay.size != size:
                overlay = overlay.resize(size, Image.Resampling.LANCZOS)
                # Interpolation may spread alpha over a room boundary. Re-clip at
                # destination pixel centers; do not soften deterministic geometry.
                role = layer.metadata.get("quill.render")
                if isinstance(role, dict) and role.get("role") == "room":
                    room = rooms[str(role["roomId"])]
                    overlay.putalpha(
                        ImageChops.multiply(
                            overlay.getchannel("A"), polygon_mask(room.polygon, size)
                        )
                    )
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
