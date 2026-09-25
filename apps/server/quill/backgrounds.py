"""First raster workflow: deterministic mock background proposals."""

import asyncio
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import Field

from quill.models import Bounds, Contract, GenerationRecord, Point, RasterLayer
from quill.projects import project_store
from quill.providers import GenerateRequest, MockProvider


class BackgroundRequest(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    prompt: Annotated[str, Field(max_length=4000)]
    seed: Annotated[int, Field(ge=0, le=2147483647)]
    baseRevision: Annotated[int, Field(ge=0)]


class BackgroundResult(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    layer: RasterLayer
    generation: GenerationRecord


def generate_background(request: BackgroundRequest) -> BackgroundResult:
    provider = MockProvider()
    result = asyncio.run(
        provider.generate(
            GenerateRequest(
                requestId=str(uuid4()),
                prompt=request.prompt,
                seed=request.seed,
                width=480,
                height=320,
            )
        )
    )
    asset_hash = project_store().put_asset(provider.assets[result.assetHash])
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
            label="Mock background",
            metadata={"quill.generation": {"target": "map"}},
            providerId="mock",
            capability="text_to_image",
            prompt=request.prompt,
            inputHashes=[],
            outputHash=asset_hash,
            parameters={"seed": request.seed, "width": 480, "height": 320},
            status="succeeded",
            baseRevision=request.baseRevision,
        ),
    )
