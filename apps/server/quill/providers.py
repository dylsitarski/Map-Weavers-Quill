"""Capability contracts and an offline provider for deterministic contract tests."""

import hashlib
from io import BytesIO
from typing import Annotated, Literal, Protocol

from PIL import Image
from pydantic import Field, JsonValue

from quill.models import Contract, Namespace

Dimension = Annotated[int, Field(ge=1, le=16384)]
Capability = Literal[
    "text_to_image",
    "inpainting",
    "image_to_image",
    "reference_image",
    "control_image",
    "transparent_background",
    "seed",
    "negative_prompt",
    "maximum_dimensions",
    "asynchronous_jobs",
]


class ProviderDescriptor(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    id: str
    capabilities: list[Capability]
    maxWidth: Dimension
    maxHeight: Dimension
    local: bool


class GenerateRequest(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    requestId: Annotated[str, Field(min_length=1)]
    prompt: str
    width: Dimension
    height: Dimension
    seed: int = 0
    negativePrompt: str | None = None
    referenceImages: list[str] = Field(default_factory=list)
    parameters: dict[Literal["steps", "guidance"], Annotated[float, Field(gt=0)]] = Field(
        default_factory=dict
    )
    extensions: dict[Namespace, dict[str, JsonValue]] = Field(
        default_factory=dict, json_schema_extra={"additionalProperties": False}
    )


class InpaintRequest(GenerateRequest):
    sourceRef: str
    maskRef: str
    maskConvention: Literal["white-edit-black-preserve"]
    context: str = ""


class GenerationResult(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    requestId: str
    providerId: str
    assetHash: str
    width: int
    height: int
    mediaType: Literal["image/png"]


class ProviderError(Contract):
    code: Literal[
        "missing_asset",
        "invalid_image",
        "unsupported_capability",
        "invalid_request",
        "authentication",
        "rate_limited",
        "timeout",
        "unavailable",
        "cancelled",
        "invalid_output",
    ]
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
    async def cancel(self, job_id: str) -> None: ...


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

    async def cancel(self, job_id: str) -> None:
        raise ProviderFailure(
            ProviderError(code="unsupported_capability", message="Mock has no asynchronous jobs")
        )

    def _validate(self, request: GenerateRequest) -> None:
        descriptor = self.descriptor()
        if request.width > descriptor.maxWidth or request.height > descriptor.maxHeight:
            raise ProviderFailure(
                ProviderError(
                    code="invalid_request", message="Mock supports at most 512x512 pixels"
                )
            )
        if (
            request.negativePrompt is not None
            or request.referenceImages
            or request.parameters
            or request.extensions
        ):
            raise ProviderFailure(
                ProviderError(
                    code="unsupported_capability",
                    message="Mock does not support reference images, negative prompts, or parameters",
                )
            )

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
        self._validate(request)
        return self._result(self._pattern(request), request)

    async def inpaint(self, request: InpaintRequest) -> GenerationResult:
        self._validate(request)
        source = self._read(request.sourceRef, request, "RGB")
        mask = self._read(request.maskRef, request, "L")
        return self._result(Image.composite(self._pattern(request), source, mask), request)
