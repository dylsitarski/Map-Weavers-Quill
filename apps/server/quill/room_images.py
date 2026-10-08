"""Provider inpainting with aligned context crops and independently masked room art."""

import asyncio
from typing import Annotated, Literal
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from pydantic import Field, JsonValue

from quill.backgrounds import BackgroundResult
from quill.comfyui import ComfyBase, ComfyProvider
from quill.exports import artwork_size, composite_artwork
from quill.flux2 import (
    DOOR_TEMPLATE,
    REFINE_TEMPLATE,
    REPAINT_TEMPLATE,
    REPAINT_WALLS_TEMPLATE,
    ROOM_TEMPLATES,
    Flux2Provider,
    door_instruction,
    room_instruction,
    room_refine_instruction,
    room_repaint_instruction,
)
from quill.layout_guidance import (
    SKETCH_DOOR,
    door_strips,
    room_scale,
    room_sketch,
    scale_prompt,
    wall_guide,
)
from quill.models import (
    Bounds,
    Contract,
    GenerationRecord,
    Point,
    Project,
    RasterLayer,
    Room,
)
from quill.projects import project_store, validate_project
from quill.provider_config import (
    check_provider,
    create_provider,
    generation_details,
    raster_profile,
)
from quill.providers import InpaintRequest
from quill.raster import context_crop, image, masked_layer, png, polygon_mask
from quill.sdxl_authoring import (
    MIN_WINDOW_CELLS,
    NEGATIVE,
    WINDOW_CELLS,
    WORKING_SIDE,
    RoomWindow,
    clean_context,
    prompt_text,
)
from quill.styles import room_style_prompt


class RoomImageRequest(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    project: Project
    roomId: UUID
    seed: Annotated[int, Field(ge=0, le=2147483647)]


DOOR_PAD = 4  # Working pixels beyond the wall band on each side of a door strip.
DOOR_MODEL_SIZE = 512


def draw_doors(
    provider: Flux2Provider,
    project: Project,
    size: tuple[int, int],
    room: Room,
    window: RoomWindow,
    output: Image.Image,
    style: dict[str, str],
    seed: int,
) -> tuple[Image.Image, dict[str, JsonValue]]:
    """Door pass (ADR-0037): for each visible door of the room, crop the finished working
    image around the doorway, paint a brown placeholder on the exact door strip, and let
    the model repaint only that strip at 512 × 512. Position and size come from geometry;
    the model only decides how the door looks."""
    output = output.copy()
    prompt = door_instruction(style)
    records: list[JsonValue] = []
    run: dict[str, JsonValue] = {}
    for index, (door, quad) in enumerate(door_strips(project, size, room, window, DOOR_PAD)):
        xs, ys = [x for x, _ in quad], [y for _, y in quad]
        extent = max(max(xs) - min(xs), max(ys) - min(ys))
        side = 256 if extent <= 192 else DOOR_MODEL_SIZE
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        left = min(max(0, round(cx - side / 2)), WORKING_SIDE - side)
        top = min(max(0, round(cy - side / 2)), WORKING_SIDE - side)
        zoom = DOOR_MODEL_SIZE / side
        strip = Image.new("L", (DOOR_MODEL_SIZE, DOOR_MODEL_SIZE))
        ImageDraw.Draw(strip).polygon(
            [((x - left) * zoom, (y - top) * zoom) for x, y in quad], fill=255
        )
        crop = output.crop((left, top, left + side, top + side)).resize(
            (DOOR_MODEL_SIZE, DOOR_MODEL_SIZE), Image.Resampling.LANCZOS
        )
        crop.paste(SKETCH_DOOR, mask=strip)  # Placeholder: re-noised, not copied.
        door_seed = (seed + index + 1) % 2147483648
        result = asyncio.run(
            provider.inpaint(
                InpaintRequest(
                    requestId=str(uuid4()),
                    prompt=prompt,
                    seed=door_seed,
                    width=DOOR_MODEL_SIZE,
                    height=DOOR_MODEL_SIZE,
                    sourceRef=provider.put(png(crop)),
                    maskRef=provider.put(png(strip)),
                    maskConvention="white-edit-black-preserve",
                    extensions={"quill.door": {}},
                )
            )
        )
        painted = image(provider.assets[result.assetHash]).convert("RGB")
        if painted.size != (DOOR_MODEL_SIZE, DOOR_MODEL_SIZE):
            raise ValueError("Provider output dimensions do not match the door crop.")
        resample = Image.Resampling.LANCZOS
        output.paste(
            painted.resize((side, side), resample),
            (left, top),
            strip.resize((side, side), Image.Resampling.NEAREST),
        )
        run = dict(provider.last_run)
        records.append({"doorId": str(door.id), "crop": [left, top, side], "seed": door_seed})
    if not records:
        return output, {}
    return output, {
        "template": DOOR_TEMPLATE,
        "prompt": prompt,
        "pad": DOOR_PAD,
        "modelSize": DOOR_MODEL_SIZE,
        "comfyui": {
            key: run[key] for key in ("workflowVersion", "steps", "scheduleSteps", "maskGrow")
        },
        "doors": records,
    }


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
    prompt, effective_style = room_style_prompt(room, project.map.style)
    provider = create_provider()
    # Local ComfyUI families share the working transform, clean context and scale data.
    comfy = isinstance(provider, ComfyBase)
    sdxl = isinstance(provider, ComfyProvider)
    # FLUX.2 klein room-reference strategy (ADR-0032), or None for other providers.
    reference = provider.config.room_reference if isinstance(provider, Flux2Provider) else None
    klein = reference is not None
    # Second, description-only klein pass (ADR-0034), or None.
    refine: str | None = None
    repaint = False
    # Doors drawn in their own zoomed, masked passes after the room (ADR-0037).
    door_pass = (
        isinstance(provider, Flux2Provider) and reference == "sketch" and provider.config.door_pass
    )
    if sdxl:
        prompt = prompt_text(room.prompt, effective_style, room=True)
    elif reference is not None:
        prompt = room_instruction(room.prompt, effective_style, reference, doors=not door_pass)
    profile, alignment = raster_profile(provider)
    size = max(artwork_size(project, store), profile, key=lambda size: size[0])
    mask = polygon_mask(room.polygon, size)
    # Keep the same native 20-unit context margin at either pixel density.
    margin = round(20 * size[0] / 1200)
    descriptor = provider.descriptor()
    window = None
    if comfy:
        # A fixed physical window (ADR-0033) gives every room the same working scale.
        cell = project.map.grid.sizePx * size[0] / project.map.width
        window = RoomWindow.around(
            mask, round(WINDOW_CELLS * cell), margin, round(MIN_WINDOW_CELLS * cell)
        )
        crop = window.crop
    else:
        crop = context_crop(mask, margin=margin, alignment=alignment)
        if crop[2] - crop[0] > descriptor.maxWidth or crop[3] - crop[1] > descriptor.maxHeight:
            raise ValueError("This room crop exceeds the configured provider's dimension limits.")
    asyncio.run(check_provider(provider))
    context, excluded = clean_context(project, room.id) if comfy else (project, [])
    source = composite_artwork(context, store, size=size)
    source_hash, mask_hash = store.put_asset(png(source)), store.put_asset(png(mask))
    if window:
        source_crop, mask_crop = window.prepare(source, mask)
    else:
        source_crop, mask_crop = source.crop(crop).convert("RGB"), mask.crop(crop)
    if source_crop.width > descriptor.maxWidth or source_crop.height > descriptor.maxHeight:
        raise ValueError("Generation resolution exceeds provider limits.")
    input_hashes = [source_hash, mask_hash]
    layout_details: dict[str, JsonValue] = {}
    extensions: dict[str, dict[str, JsonValue]] = {}
    if window:
        controlled = "control_image" in descriptor.capabilities
        scale = room_scale(project, room, size, window)
        if klein:
            # Room facts and the edit instruction first, then scale. The sketch itself
            # explains walls and doors, so the SDXL wall-line sentence is not used.
            prompt = prompt + "\n" + scale_prompt(scale, controlled=False)
        else:
            prompt = scale_prompt(scale, controlled=controlled) + "\n" + prompt
        layout_details = {"physicalScale": scale, "layoutConditioning": controlled}
        if controlled:
            if reference == "sketch":
                # The stored copy is at map size; the model's copy is drawn directly in
                # working space so wall width is physically constant and lines are crisp.
                doors = not door_pass
                input_hashes.append(
                    store.put_asset(png(room_sketch(project, size, room, doors=doors)))
                )
                guide = room_sketch(project, size, room, window, doors=doors)
            else:
                full = wall_guide(project, size)
                input_hashes.append(store.put_asset(png(full)))
                guide = window.guide(full)
            extensions = {"quill.layout": {"controlRef": provider.put(png(guide))}}
            if (
                isinstance(provider, Flux2Provider)
                and reference is not None
                and provider.config.room_passes == 2
            ):
                repaint = provider.config.room_masking == "latent"
                refine = (
                    (
                        room_repaint_instruction(room.prompt, effective_style, doors=not door_pass)
                        if repaint
                        else room_refine_instruction(room.prompt, effective_style)
                    )
                    + "\n"
                    + scale_prompt(scale, controlled=False)
                )
                extensions["quill.refine"] = {"prompt": refine}
    result = asyncio.run(
        provider.inpaint(
            InpaintRequest(
                requestId=str(uuid4()),
                prompt=prompt,
                seed=request.seed,
                negativePrompt=NEGATIVE if sdxl else None,
                width=source_crop.width,
                height=source_crop.height,
                sourceRef=provider.put(png(source_crop)),
                maskRef=provider.put(png(mask_crop)),
                maskConvention="white-edit-black-preserve",
                extensions=extensions,
            )
        )
    )
    output = image(provider.assets[result.assetHash])
    expected = source_crop.size
    if output.size != expected or (result.width, result.height) != expected:
        raise ValueError("Provider output dimensions do not match the requested room crop.")
    # Room provenance and unclipped pass images, before any door edit replaces them.
    details = generation_details(provider)
    pass_images = dict(provider.diagnostics) if isinstance(provider, ComfyBase) else {}
    door_details: dict[str, JsonValue] = {}
    if door_pass and window and isinstance(provider, Flux2Provider):
        output, door_details = draw_doors(
            provider, project, size, room, window, output, effective_style, request.seed
        )
    if window:
        output = window.restore(output)
    generated = Image.new("RGBA", size)
    generated.paste(output, crop[:2])
    # Enforce outside-mask preservation ourselves, regardless of provider behavior.
    output_hash = store.put_asset(png(masked_layer(generated, mask)))
    # Unclipped window images (each klein pass, ADR-0034) for debugging bundles only.
    diagnostics: dict[str, JsonValue] = {}
    if window and isinstance(provider, ComfyBase):
        for name, key in pass_images.items():
            unclipped = Image.new("RGBA", size)
            unclipped.paste(window.restore(image(provider.assets[key])), crop[:2])
            diagnostics[name] = store.put_asset(png(unclipped))
    return BackgroundResult(
        layer=RasterLayer(
            id=uuid4(),
            kind="raster",
            revision=0,
            label=f"{room.label} artwork",
            metadata={
                "quill.render": {
                    "role": "room",
                    "roomId": str(room.id),
                }
            },
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
            label=f"Room generation: {room.label}",
            metadata={"quill.generation": {"target": "room", "roomId": str(room.id)}},
            providerId=result.providerId,
            capability="inpainting",
            prompt=prompt,
            inputHashes=input_hashes,
            outputHash=output_hash,
            parameters={
                "seed": request.seed,
                **details,
                **({"doorPass": door_details} if door_details else {}),
                **layout_details,
                "crop": list(crop),
                "width": size[0],
                "height": size[1],
                "promptTemplate": "sdxl-room-layout-v2"
                if sdxl
                else ROOM_TEMPLATES["sketch-walls" if door_pass else reference]
                if reference
                else "room-style-v1",
                **(
                    {
                        **({"negativePrompt": NEGATIVE} if sdxl else {}),
                        "roomTransform": window.metadata(),
                        "excludedContextLayers": [str(item) for item in excluded],
                    }
                    if window
                    else {}
                ),
                **(
                    {
                        "refinePrompt": refine,
                        "refineTemplate": (
                            (REPAINT_WALLS_TEMPLATE if door_pass else REPAINT_TEMPLATE)
                            if repaint
                            else REFINE_TEMPLATE
                        ),
                    }
                    if refine
                    else {}
                ),
                **({"diagnosticImages": diagnostics} if diagnostics else {}),
                "roomPrompt": room.prompt,
                "styleOverrides": dict(room.styleOverrides),
                "effectiveStyle": {key: value for key, value in effective_style.items()},
                "mapStyle": project.map.style.model_dump(mode="json"),
            },
            status="succeeded",
            baseRevision=project.revision,
        ),
    )
