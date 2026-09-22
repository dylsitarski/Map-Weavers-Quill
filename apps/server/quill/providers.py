"""Capability contracts and an offline provider for deterministic contract tests."""

import hashlib
from io import BytesIO
from typing import Annotated, Literal, Protocol

from PIL import Image
from pydantic import Field

from quill.models import Contract

Dimension = Annotated[int, Field(ge=1, le=512)]
Capability = Literal["text_to_image", "inpainting", "seed"]


class ProviderDescriptor(Contract):
    id: str
    capabilities: list[Capability]
    maxWidth: int
    maxHeight: int
    local: bool


class GenerateRequest(Contract):
    requestId: str
    prompt: str
    width: Dimension
    height: Dimension
    seed: int = 0


class InpaintRequest(GenerateRequest):
    sourceRef: str
    maskRef: str
    maskConvention: Literal["white-edit-black-preserve"]
    context: str = ""


class GenerationResult(Contract):
    requestId: str
    providerId: str
    assetHash: str
    width: int
    height: int
    mediaType: Literal["image/png"]


class ProviderError(Contract):
    code: Literal["missing_asset", "invalid_image", "unsupported_capability"]
    message: str
    retryable: bool = False


class ProviderFailure(Exception):
    def __init__(self, error: ProviderError):
        self.error = error
        super().__init__(error.message)


class ImageProvider(Protocol):
    def descriptor(self) -> ProviderDescriptor: ...
    async def health(self) -> bool: ...
    async def generate(self, request: GenerateRequest) -> GenerationResult: ...
    async def inpaint(self, request: InpaintRequest) -> GenerationResult: ...


class MockProvider:
    """In-memory assets; synchronous work wrapped in the asynchronous contract.

    Not a persistent asset service or a job queue. Cancellation is deliberately
    unadvertised. Assets are immutable PNG bytes addressed by SHA-256.
    """

    def __init__(self) -> None:
        self.assets: dict[str, bytes] = {}

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            id="mock",
            capabilities=["text_to_image", "inpainting", "seed"],
            maxWidth=512,
            maxHeight=512,
            local=True,
        )

    async def health(self) -> bool:
        return True

    def put(self, data: bytes) -> str:
        key = hashlib.sha256(data).hexdigest()
        self.assets[key] = data
        return key

    def _pattern(self, request: GenerateRequest) -> Image.Image:
        color = hashlib.sha256(f"{request.seed}:{request.prompt}".encode()).digest()
        image = Image.new("RGB", (request.width, request.height))
        image.putdata(
            [
                tuple(color[i] if (x // 8 + y // 8) % 2 else 255 - color[i] for i in range(3))
                for y in range(request.height)
                for x in range(request.width)
            ]
        )
        return image

    def _result(self, image: Image.Image, request: GenerateRequest) -> GenerationResult:
        output = BytesIO()
        image.save(output, format="PNG")
        return GenerationResult(
            requestId=request.requestId,
            providerId="mock",
            assetHash=self.put(output.getvalue()),
            width=request.width,
            height=request.height,
            mediaType="image/png",
        )

    def _read(self, key: str, request: GenerateRequest, mode: str) -> Image.Image:
        if key not in self.assets:
            raise ProviderFailure(ProviderError(code="missing_asset", message="Asset not found"))
        try:
            with Image.open(BytesIO(self.assets[key])) as image:
                if image.size != (request.width, request.height) or image.format != "PNG":
                    raise ValueError("Expected PNG with requested dimensions")
                return image.convert(mode)
        except (OSError, ValueError) as error:
            raise ProviderFailure(
                ProviderError(code="invalid_image", message="Invalid image")
            ) from error

    async def generate(self, request: GenerateRequest) -> GenerationResult:
        return self._result(self._pattern(request), request)

    async def inpaint(self, request: InpaintRequest) -> GenerationResult:
        source = self._read(request.sourceRef, request, "RGB")
        mask = self._read(request.maskRef, request, "L")
        return self._result(Image.composite(self._pattern(request), source, mask), request)
