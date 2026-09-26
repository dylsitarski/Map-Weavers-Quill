"""Local ComfyUI SDXL reference adapter. No model weights or GPU dependencies."""

import asyncio
import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from PIL import Image, ImageChops

from quill.providers import (
    GenerateRequest,
    GenerationResult,
    InpaintRequest,
    ProviderDescriptor,
    ProviderError,
    ProviderFailure,
)

WORKFLOW_VERSION = "comfy-sdxl-v1"
MAX_RESPONSE = 16 * 1024 * 1024


def failure(code: str, message: str) -> ProviderFailure:
    return ProviderFailure(ProviderError.model_validate({"code": code, "message": message}))


@dataclass(frozen=True)
class ComfyConfig:
    url: str = "http://127.0.0.1:8188"
    checkpoint: str = "sd_xl_base_1.0.safetensors"
    timeout: float = 600.0

    def __post_init__(self) -> None:
        try:
            parsed = urlsplit(self.url)
            valid = (
                parsed.scheme == "http"
                and parsed.hostname in {"127.0.0.1", "::1", "localhost"}
                and parsed.username is None
                and parsed.password is None
                and parsed.path in {"", "/"}
                and not parsed.query
                and not parsed.fragment
                and parsed.port is not None
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("ComfyUI URL must be an HTTP loopback address with an explicit port.")
        if (
            not self.checkpoint.endswith(".safetensors")
            or any(c in self.checkpoint for c in "/\\\r\n")
            or len(self.checkpoint) > 200
            or self.checkpoint.startswith(".")
        ):
            raise ValueError("Use a safetensors checkpoint filename without a directory.")
        if not 1 <= self.timeout <= 1800:
            raise ValueError("ComfyUI timeout must be between 1 and 1800 seconds.")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ComfyConfig":
        env = os.environ if env is None else env
        try:
            timeout = float(env.get("MWQ_IMAGE_COMFY_TIMEOUT", "600"))
        except ValueError:
            raise ValueError("ComfyUI timeout must be a number of seconds.") from None
        return cls(
            env.get("MWQ_IMAGE_COMFY_URL", "http://127.0.0.1:8188"),
            env.get("MWQ_IMAGE_COMFY_CHECKPOINT", "sd_xl_base_1.0.safetensors"),
            timeout,
        )


def workflow(config: ComfyConfig, request: GenerateRequest, upload: str | None) -> dict[str, Any]:
    """Versioned graph containing core local nodes only; never accepts user graphs."""
    graph: dict[str, Any] = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": config.checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": request.prompt}},
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["1", 1], "text": request.negativePrompt or ""},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": request.width, "height": request.height, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": request.seed,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["6", 0], "filename_prefix": "quill/preview"},
        },
    }
    if upload is not None:
        graph["8"] = {"class_type": "LoadImage", "inputs": {"image": upload}}
        graph["4"] = {
            "class_type": "VAEEncodeForInpaint",
            "inputs": {"pixels": ["8", 0], "mask": ["8", 1], "vae": ["1", 2], "grow_mask_by": 0},
        }
    return graph


class ComfyProvider:
    def __init__(
        self, config: ComfyConfig, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.config = config
        self.transport = transport
        self.assets: dict[str, bytes] = {}
        self.last_run: dict[str, Any] = {}

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            id="comfyui-sdxl",
            capabilities=["text_to_image", "inpainting", "seed", "negative_prompt"],
            maxWidth=1024,
            maxHeight=1024,
            local=True,
        )

    def put(self, data: bytes) -> str:
        key = hashlib.sha256(data).hexdigest()
        self.assets[key] = data
        return key

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.config.url.rstrip("/"),
            transport=self.transport,
            timeout=30,
            trust_env=False,
            follow_redirects=False,
        )

    async def _request(
        self, client: httpx.AsyncClient, method: str, path: str, **kwargs: Any
    ) -> bytes:
        async with client.stream(method, path, **kwargs) as response:
            if response.status_code != 200:
                code = "invalid_request" if response.status_code == 400 else "unavailable"
                raise failure(code, "ComfyUI rejected the request. Check its local setup.")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > MAX_RESPONSE:
                    raise failure("invalid_output", "ComfyUI response exceeds the size limit.")
            return bytes(body)

    async def _json(
        self, client: httpx.AsyncClient, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        value = json.loads(await self._request(client, method, path, **kwargs))
        if not isinstance(value, dict):
            raise ValueError
        return value

    async def check(self) -> None:
        """Check connectivity, required core nodes, and checkpoint; never queues GPU work."""
        try:
            async with asyncio.timeout(30), self.client() as client:
                info = await self._json(client, "GET", "/object_info")
                graph = workflow(
                    self.config,
                    GenerateRequest(requestId="check", prompt="", width=1024, height=1024),
                    "check.png",
                )
                required = {node["class_type"] for node in graph.values()} | {"EmptyLatentImage"}
                if not required.issubset(info):
                    raise failure(
                        "unsupported_capability", "ComfyUI is missing required core workflow nodes."
                    )
                names = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
                if not isinstance(names, list) or self.config.checkpoint not in names:
                    raise failure(
                        "unavailable", "The configured SDXL checkpoint is not installed in ComfyUI."
                    )
        except (TimeoutError, httpx.TimeoutException):
            raise failure("timeout", "ComfyUI readiness check timed out.") from None
        except httpx.HTTPError:
            raise failure("unavailable", "Cannot connect to the local ComfyUI server.") from None
        except (ValueError, KeyError, TypeError, IndexError):
            raise failure(
                "invalid_output", "ComfyUI returned invalid readiness information."
            ) from None

    async def health(self) -> bool:
        try:
            await self.check()
            return True
        except ProviderFailure:
            return False

    async def cancel(self, job_id: str) -> None:
        # /interrupt is global; never risk cancelling another application's work.
        raise failure(
            "unsupported_capability",
            "Provider interruption is not implemented; local work may finish.",
        )

    def _validate(self, request: GenerateRequest) -> None:
        if any(n < 64 or n > 1024 or n % 64 for n in (request.width, request.height)):
            raise failure(
                "invalid_request",
                "ComfyUI reference dimensions must be multiples of 64 from 64 to 1024.",
            )
        if not 0 <= request.seed <= 2147483647:
            raise failure("invalid_request", "Seed must be between 0 and 2147483647.")
        if request.parameters or request.extensions or request.referenceImages:
            raise failure(
                "unsupported_capability",
                "The reference workflow does not support extra parameters or reference images.",
            )
        if isinstance(request, InpaintRequest) and request.context:
            raise failure(
                "unsupported_capability",
                "Put contextual instructions in the prompt for this workflow.",
            )

    def _image(self, key: str, size: tuple[int, int], mode: str) -> Image.Image:
        if key not in self.assets:
            raise failure("missing_asset", "Input image asset is missing.")
        try:
            return self._decode(self.assets[key], size, mode)
        except (ValueError, OSError, Image.DecompressionBombError):
            raise failure(
                "invalid_image", "Inputs must be PNG images with the requested dimensions."
            ) from None

    @staticmethod
    def _decode(data: bytes, size: tuple[int, int], mode: str) -> Image.Image:
        if len(data) > MAX_RESPONSE:
            raise ValueError
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG" or image.size != size:
                raise ValueError
            return image.convert(mode)

    @staticmethod
    def _png(image: Image.Image) -> bytes:
        stream = BytesIO()
        image.save(stream, format="PNG")
        return stream.getvalue()

    async def generate(self, request: GenerateRequest) -> GenerationResult:
        return await self._run(request)

    async def inpaint(self, request: InpaintRequest) -> GenerationResult:
        return await self._run(request)

    async def _run(self, request: GenerateRequest) -> GenerationResult:
        self._validate(request)
        self.last_run = {}
        size = (request.width, request.height)
        source = mask = None
        upload = None
        if isinstance(request, InpaintRequest):
            source = self._image(request.sourceRef, size, "RGB")
            mask = self._image(request.maskRef, size, "L")
            upload = f"quill-{uuid4().hex}.png"
        graph = workflow(self.config, request, upload)
        try:
            async with asyncio.timeout(self.config.timeout), self.client() as client:
                if source is not None and mask is not None:
                    rgba = source.convert("RGBA")
                    # LoadImage returns 1-alpha as its mask: white means edit.
                    rgba.putalpha(ImageChops.invert(mask))
                    uploaded = await self._json(
                        client,
                        "POST",
                        "/upload/image",
                        files={"image": (upload, self._png(rgba), "image/png")},
                        data={"type": "input", "overwrite": "false"},
                    )
                    if (
                        uploaded.get("name") != upload
                        or uploaded.get("subfolder", "") != ""
                        or uploaded.get("type") != "input"
                    ):
                        raise ValueError
                queued = await self._json(
                    client, "POST", "/prompt", json={"prompt": graph, "client_id": str(uuid4())}
                )
                prompt_id = queued.get("prompt_id")
                if (
                    not isinstance(prompt_id, str)
                    or not prompt_id
                    or len(prompt_id) > 128
                    or any(
                        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
                        for c in prompt_id
                    )
                ):
                    raise ValueError
                while True:
                    history = await self._json(client, "GET", f"/history/{prompt_id}")
                    record = history.get(prompt_id)
                    if record is not None:
                        if not isinstance(record, dict) or not isinstance(
                            record.get("status"), dict
                        ):
                            raise ValueError
                        status = record["status"]
                        if status.get("status_str") == "error":
                            raise failure(
                                "unavailable",
                                "ComfyUI execution failed. Check its local console; the project is unchanged.",
                            )
                        if status.get("completed") is True:
                            break
                    await asyncio.sleep(0.5)
                outputs = record["outputs"]["7"]["images"]
                if len(outputs) != 1:
                    raise ValueError
                output = outputs[0]
                if not isinstance(output, dict):
                    raise ValueError
                filename, subfolder = output["filename"], output.get("subfolder", "")
                if (
                    not isinstance(filename, str)
                    or not filename
                    or any(c in filename for c in "/\\")
                    or not filename.endswith(".png")
                    or not isinstance(subfolder, str)
                    or subfolder != "quill"
                    or output.get("type") != "output"
                ):
                    raise ValueError
                data = await self._request(
                    client,
                    "GET",
                    "/view",
                    params={"filename": filename, "subfolder": subfolder, "type": "output"},
                )
                result_image = self._decode(data, size, "RGB")
                if source is not None and mask is not None:
                    result_image = Image.composite(result_image, source, mask)
                output_hash = self.put(self._png(result_image))
                self.last_run = {
                    "workflowVersion": WORKFLOW_VERSION,
                    "workflowSha256": hashlib.sha256(
                        json.dumps(graph, sort_keys=True).encode()
                    ).hexdigest(),
                    "checkpoint": self.config.checkpoint,
                    "promptId": prompt_id,
                    "seed": request.seed,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler": "euler",
                    "scheduler": "normal",
                    "width": request.width,
                    "height": request.height,
                }
                return GenerationResult(
                    requestId=request.requestId,
                    providerId="comfyui-sdxl",
                    assetHash=output_hash,
                    width=request.width,
                    height=request.height,
                    mediaType="image/png",
                )
        except (TimeoutError, httpx.TimeoutException):
            raise failure(
                "timeout",
                "ComfyUI timed out; its queued work may still finish. No automatic retry was sent.",
            ) from None
        except httpx.HTTPError:
            raise failure(
                "unavailable", "Cannot communicate with local ComfyUI. No automatic retry was sent."
            ) from None
        except (ValueError, KeyError, TypeError, IndexError, OSError, Image.DecompressionBombError):
            raise failure(
                "invalid_output", "ComfyUI returned an invalid workflow result."
            ) from None
