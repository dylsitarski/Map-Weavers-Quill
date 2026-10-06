"""Provider-backed background proposals; acceptance remains an editor operation."""

import asyncio
import json
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import Field

from quill.comfyui import ComfyBase, ComfyProvider
from quill.models import Bounds, Contract, GenerationRecord, MapStyle, Point, RasterLayer
from quill.projects import project_store
from quill.provider_config import (
    check_provider,
    create_provider,
    generation_details,
    raster_profile,
)
from quill.providers import GenerateRequest
from quill.raster import image
from quill.sdxl_authoring import NEGATIVE, TEMPLATE, background_scale, prompt_text
from quill.styles import STYLE_KEYS


class BackgroundRequest(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    style: MapStyle | None = None
    prompt: Annotated[str, Field(max_length=4000)]
    seed: Annotated[int, Field(ge=0, le=2147483647)]
    baseRevision: Annotated[int, Field(ge=0)]


class BackgroundResult(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    layer: RasterLayer
    generation: GenerationRecord


def generate_background(request: BackgroundRequest) -> BackgroundResult:
    prompt = request.prompt
    if request.style is not None:
        effective = {key: getattr(request.style, key).strip() for key in STYLE_KEYS}
        if any(len(value) > 512 for value in effective.values()):
            raise ValueError("Each map style value supports at most 512 characters.")
        prompt += "\nStyle: " + json.dumps(effective, sort_keys=True, ensure_ascii=False)
        prompt += (
            f"\nCamera: {request.style.camera}. Baked lighting: {request.style.bakedLighting}."
        )
    provider = create_provider()
    comfy = isinstance(provider, ComfyBase)
    # Negative prompts are SDXL-only; FLUX.2 klein's distilled workflow ignores them.
    sdxl = isinstance(provider, ComfyProvider)
    size, _ = raster_profile(provider)
    if comfy:
        prompt = prompt_text(
            request.prompt,
            effective if request.style else {},
            room=False,
            scale=background_scale(size[0]),
        )
    asyncio.run(check_provider(provider))
    result = asyncio.run(
        provider.generate(
            GenerateRequest(
                requestId=str(uuid4()),
                prompt=prompt,
                seed=request.seed,
                negativePrompt=NEGATIVE if sdxl else None,
                width=size[0],
                height=size[1],
            )
        )
    )
    data = provider.assets[result.assetHash]
    if (result.width, result.height) != size or image(data).size != size:
        raise ValueError("Provider output dimensions do not match the requested background.")
    asset_hash = project_store().put_asset(data)
    return BackgroundResult(
        layer=RasterLayer(
            id=uuid4(),
            kind="raster",
            revision=0,
            label="Base background",
            metadata={"quill.render": {"role": "background"}},
            assetHash=asset_hash,
            bounds=Bounds(origin=Point(x=0.0, y=0.0), width=1200.0, height=800.0),
            rotation=0.0,
            zIndex=0,
            opacity=1.0,
            visible=True,
            blendMode="normal",
        ),
        generation=GenerationRecord(
            id=uuid4(),
            kind="generation",
            revision=0,
            label="Background generation",
            metadata={"quill.generation": {"target": "map"}},
            providerId=result.providerId,
            capability="text_to_image",
            prompt=prompt,
            inputHashes=[],
            outputHash=asset_hash,
            parameters={
                "seed": request.seed,
                **generation_details(provider),
                "width": size[0],
                "height": size[1],
                "backgroundPrompt": request.prompt,
                "promptTemplate": TEMPLATE
                if comfy
                else ("map-style-v1" if request.style else "background-v0"),
                **({"negativePrompt": NEGATIVE} if sdxl else {}),
                "mapStyle": request.style.model_dump(mode="json") if request.style else None,
            },
            status="succeeded",
            baseRevision=request.baseRevision,
        ),
    )
