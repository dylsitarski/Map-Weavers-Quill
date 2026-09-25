"""Context-cropped mock inpainting, emitted as independently masked room art."""

import asyncio
from typing import Annotated, Literal
from uuid import UUID, uuid4

from PIL import Image
from pydantic import Field

from quill.backgrounds import BackgroundResult
from quill.models import Bounds, Contract, GenerationRecord, Point, Project, RasterLayer
from quill.projects import project_store, validate_project
from quill.providers import InpaintRequest, MockProvider
from quill.raster import HEIGHT, WIDTH, image, masked_layer, png, polygon_mask


class RoomImageRequest(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    project: Project
    roomId: UUID
    seed: Annotated[int, Field(ge=0, le=2147483647)]


def generate_room(request: RoomImageRequest) -> BackgroundResult:
    project = validate_project(request.project, derive_missing=True)
    store = project_store()
    db = store.connect()
    try:
        store.validate_assets(db, project)
    finally:
        db.close()
    room = next((room for room in project.rooms if room.id == request.roomId), None)
    if room is None:
        raise ValueError("Select a room that still exists.")
    if len(room.prompt) > 4000:
        raise ValueError("Room generation prompts support at most 4000 characters.")
    mask = polygon_mask(room.polygon)
    box = mask.getbbox()
    if box is None:
        raise ValueError("The room is too small at the current 2.5-map-unit pixel resolution.")
    # Context includes current composited art, including previous target art for regeneration.
    source = Image.new("RGBA", (WIDTH, HEIGHT), "#e9e2ce")
    for layer in sorted(project.layers, key=lambda layer: (layer.zIndex, str(layer.id))):
        if layer.visible:
            overlay = image(store.get_asset(layer.assetHash))
            overlay.putalpha(
                overlay.getchannel("A").point(lambda alpha: round(alpha * layer.opacity))
            )
            source = Image.alpha_composite(source, overlay)
    # Eight pixels of protected surrounding context; crop never changes the mask.
    crop = (max(0, box[0] - 8), max(0, box[1] - 8), min(WIDTH, box[2] + 8), min(HEIGHT, box[3] + 8))
    provider = MockProvider()
    source_hash, mask_hash = store.put_asset(png(source)), store.put_asset(png(mask))
    result = asyncio.run(
        provider.inpaint(
            InpaintRequest(
                requestId=str(uuid4()),
                prompt=room.prompt,
                seed=request.seed,
                width=crop[2] - crop[0],
                height=crop[3] - crop[1],
                sourceRef=provider.put(png(source.crop(crop).convert("RGB"))),
                maskRef=provider.put(png(mask.crop(crop))),
                maskConvention="white-edit-black-preserve",
            )
        )
    )
    generated = Image.new("RGBA", (WIDTH, HEIGHT))
    generated.paste(image(provider.assets[result.assetHash]), crop[:2])
    # Enforce outside-mask preservation ourselves, regardless of provider behavior.
    output_hash = store.put_asset(png(masked_layer(generated, mask)))
    return BackgroundResult(
        layer=RasterLayer(
            id=uuid4(),
            kind="raster",
            revision=0,
            label=f"{room.label} artwork",
            metadata={"quill.render": {"role": "room", "roomId": str(room.id)}},
            assetHash=output_hash,
            bounds=Bounds(origin=Point(x=0.0, y=0.0), width=1200.0, height=800.0),
            rotation=0.0,
            zIndex=max([layer.zIndex for layer in project.layers] + [0]) + 1,
            opacity=1.0,
            visible=True,
            blendMode="normal",
        ),
        generation=GenerationRecord(
            id=uuid4(),
            kind="generation",
            revision=0,
            label=f"Mock room: {room.label}",
            metadata={"quill.generation": {"target": "room", "roomId": str(room.id)}},
            providerId="mock",
            capability="inpainting",
            prompt=room.prompt,
            inputHashes=[source_hash, mask_hash],
            outputHash=output_hash,
            parameters={"seed": request.seed, "crop": list(crop), "width": WIDTH, "height": HEIGHT},
            status="succeeded",
            baseRevision=project.revision,
        ),
    )
