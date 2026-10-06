"""Local ComfyUI FLUX.2 [klein] adapter (ADR-0032). Core nodes only; no weights bundled.

Graphs follow ComfyUI's official klein templates: UNETLoader, CLIPLoader (type flux2),
VAELoader, ReferenceLatent edits, EmptyFlux2LatentImage, Flux2Scheduler, CFGGuider and
SamplerCustomAdvanced. Room edits use one of two reference strategies:
- sketch (default): one image, the context crop with an architectural sketch of the room
  drawn in (off-white floor, dark walls, door states);
- plan: two images, the context crop with the room blanked, and a separate floor plan.
"""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx
from PIL import Image

from quill.comfyui import (
    ComfyBase,
    env_timeout,
    failure,
    validate_endpoint,
    validate_model_file,
)
from quill.providers import Capability, GenerateRequest, ProviderDescriptor

WORKFLOW_VERSION = "comfy-flux2-klein-v1"
EDIT_WORKFLOW_VERSION = "comfy-flux2-klein-edit-v1"
PLAN_VERSION = "room-plan-v1"
SKETCH_VERSION = "room-sketch-v1"
ROOM_REFERENCES = ("sketch", "plan")
SKETCH_FLOOR = (236, 232, 222)  # Off-white "paper" floor inside the room.
# Distilled klein: 4 steps, CFG 1, zeroed negative. Base klein: 20 steps, CFG 5.
VARIANTS: dict[str, tuple[int, float]] = {"distilled": (4, 1.0), "base": (20, 5.0)}
BLANK = (128, 128, 128)  # Room area in the context reference: "paint here".
PLAN_FLOOR, PLAN_WALL = 96, 255  # Plan: black outside, gray floor, white walls.


@dataclass(frozen=True)
class Flux2Config:
    url: str = "http://127.0.0.1:8188"
    timeout: float = 600.0
    model: str = "flux-2-klein-4b-fp8.safetensors"
    text_encoder: str = "qwen_3_4b.safetensors"
    vae: str = "flux2-vae.safetensors"
    variant: str = "distilled"
    # "cpu" keeps the 4B text encoder off small GPUs at the cost of prompt-encoding time.
    text_encoder_device: str = "default"
    # How the room layout reaches the model (ADR-0032): sketch or plan.
    room_reference: str = "sketch"

    def __post_init__(self) -> None:
        validate_endpoint(self.url, self.timeout)
        validate_model_file(self.model, "FLUX.2 klein model")
        validate_model_file(self.text_encoder, "FLUX.2 text encoder")
        validate_model_file(self.vae, "FLUX.2 VAE")
        if self.variant not in VARIANTS:
            raise ValueError("FLUX.2 klein variant must be distilled or base.")
        if self.text_encoder_device not in {"default", "cpu"}:
            raise ValueError("FLUX.2 text encoder device must be default or cpu.")
        if self.room_reference not in ROOM_REFERENCES:
            raise ValueError("FLUX.2 room reference must be sketch or plan.")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Flux2Config":
        env = os.environ if env is None else env
        defaults = cls()
        return cls(
            env.get("MWQ_IMAGE_COMFY_URL", defaults.url),
            env_timeout(env),
            env.get("MWQ_IMAGE_COMFY_FLUX2_MODEL") or defaults.model,
            env.get("MWQ_IMAGE_COMFY_FLUX2_TEXT_ENCODER") or defaults.text_encoder,
            env.get("MWQ_IMAGE_COMFY_FLUX2_VAE") or defaults.vae,
            env.get("MWQ_IMAGE_COMFY_FLUX2_VARIANT") or defaults.variant,
            env.get("MWQ_IMAGE_COMFY_FLUX2_TEXT_ENCODER_DEVICE") or defaults.text_encoder_device,
            env.get("MWQ_IMAGE_COMFY_FLUX2_ROOM_REFERENCE") or defaults.room_reference,
        )


def workflow(
    config: Flux2Config,
    request: GenerateRequest,
    source: str | None = None,
    plan: str | None = None,
) -> dict[str, Any]:
    """Fixed graph; output node "7" is the single SaveImage. Never accepts user graphs."""
    steps, cfg = VARIANTS[config.variant]
    clip: dict[str, Any] = {"clip_name": config.text_encoder, "type": "flux2"}
    if config.text_encoder_device != "default":
        clip["device"] = config.text_encoder_device
    graph: dict[str, Any] = {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": config.model, "weight_dtype": "default"},
        },
        "2": {"class_type": "CLIPLoader", "inputs": clip},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": config.vae}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": request.prompt}},
        "5": (
            {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}}
            if config.variant == "distilled"
            else {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}}
        ),
        "6": {
            "class_type": "EmptyFlux2LatentImage",
            "inputs": {"width": request.width, "height": request.height, "batch_size": 1},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["10", 0], "filename_prefix": "quill/preview"},
        },
        "8": {
            "class_type": "Flux2Scheduler",
            "inputs": {"steps": steps, "width": request.width, "height": request.height},
        },
        "9": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["3", 0]}},
        "11": {"class_type": "RandomNoise", "inputs": {"noise_seed": request.seed}},
        "12": {
            "class_type": "CFGGuider",
            "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "cfg": cfg},
        },
        "13": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["11", 0],
                "guider": ["12", 0],
                "sampler": ["9", 0],
                "sigmas": ["8", 0],
                "latent_image": ["6", 0],
            },
        },
    }
    positive, negative = ["4", 0], ["5", 0]
    # Each reference image is VAE-encoded and appended to both conditionings, in order.
    for index, upload in enumerate(name for name in (source, plan) if name is not None):
        load, encode, pos, neg = (str(20 + 4 * index + k) for k in range(4))
        graph[load] = {"class_type": "LoadImage", "inputs": {"image": upload}}
        graph[encode] = {
            "class_type": "VAEEncode",
            "inputs": {"pixels": [load, 0], "vae": ["3", 0]},
        }
        graph[pos] = {
            "class_type": "ReferenceLatent",
            "inputs": {"conditioning": positive, "latent": [encode, 0]},
        }
        graph[neg] = {
            "class_type": "ReferenceLatent",
            "inputs": {"conditioning": negative, "latent": [encode, 0]},
        }
        positive, negative = [pos, 0], [neg, 0]
    graph["12"]["inputs"].update(positive=positive, negative=negative)
    return graph


def room_sketch_reference(
    source: Image.Image, mask: Image.Image, sketch: Image.Image
) -> Image.Image:
    """Context with the room filled off-white, then sketch strokes (non-black) on top."""
    reference = Image.composite(Image.new("RGB", source.size, SKETCH_FLOOR), source, mask)
    strokes = sketch.convert("L").point(lambda v: 255 if v > 0 else 0)
    reference.paste(sketch, mask=strokes)
    return reference


def room_plan(mask: Image.Image, walls: Image.Image) -> Image.Image:
    """Black outside, gray room floor, white wall lines (door gaps stay unpainted)."""
    plan = Image.new("RGB", mask.size)
    plan.paste((PLAN_FLOOR,) * 3, mask=mask.point(lambda v: 255 if v > 127 else 0))
    plan.paste((PLAN_WALL,) * 3, mask=walls.convert("L").point(lambda v: 255 if v > 127 else 0))
    return plan


class Flux2Provider(ComfyBase):
    """FLUX.2 [klein] family. Room layout is always supplied as a reference image."""

    config: Flux2Config

    def __init__(
        self, config: Flux2Config, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        super().__init__(config, transport=transport)

    def descriptor(self) -> ProviderDescriptor:
        capabilities: list[Capability] = ["text_to_image", "inpainting", "seed", "control_image"]
        return ProviderDescriptor(
            id="comfyui-flux2-klein",
            capabilities=capabilities,
            maxWidth=1024,
            maxHeight=1024,
            local=True,
        )

    def _accepts_layout(self) -> bool:
        return True

    def _validate(self, request: GenerateRequest) -> None:
        super()._validate(request)
        if request.negativePrompt:
            raise failure(
                "unsupported_capability", "The FLUX.2 klein workflow does not use negative prompts."
            )

    def _check_info(self, info: dict[str, Any]) -> None:
        check = GenerateRequest(requestId="check", prompt="", width=1024, height=1024)
        self._require_nodes(info, workflow(self.config, check, "source.png", "plan.png"))
        types = info["CLIPLoader"]["input"]["required"]["type"][0]
        if not isinstance(types, list) or "flux2" not in types:
            raise failure(
                "unsupported_capability",
                "This ComfyUI version cannot load FLUX.2 text encoders. Update ComfyUI.",
            )
        self._require_file(info, "UNETLoader", "unet_name", self.config.model, "FLUX.2 klein model")
        self._require_file(
            info, "CLIPLoader", "clip_name", self.config.text_encoder, "FLUX.2 text encoder"
        )
        self._require_file(info, "VAELoader", "vae_name", self.config.vae, "FLUX.2 VAE")

    def _uploads(
        self, source: Image.Image | None, mask: Image.Image | None, control: Image.Image | None
    ) -> list[tuple[str, str, Image.Image]]:
        uploads = []
        if source is not None and mask is not None and self.config.room_reference == "sketch":
            # One reference: the surroundings with the room drawn as a sketch to render.
            reference = (
                room_sketch_reference(source, mask, control)
                if control is not None
                else Image.composite(Image.new("RGB", source.size, SKETCH_FLOOR), source, mask)
            )
            uploads.append(("source", f"quill-{uuid4().hex}.png", reference))
        elif source is not None and mask is not None:
            # The model sees the surroundings, with the room itself blanked out.
            blanked = Image.composite(Image.new("RGB", source.size, BLANK), source, mask)
            uploads.append(("source", f"quill-{uuid4().hex}.png", blanked))
            if control is not None:
                uploads.append(("plan", f"quill-plan-{uuid4().hex}.png", room_plan(mask, control)))
        return uploads

    def _graph(self, request: GenerateRequest, names: dict[str, str]) -> dict[str, Any]:
        return workflow(self.config, request, names.get("source"), names.get("plan"))

    def _provenance(self, request: GenerateRequest, names: dict[str, str]) -> dict[str, Any]:
        steps, cfg = VARIANTS[self.config.variant]
        return {
            "workflowVersion": EDIT_WORKFLOW_VERSION if "source" in names else WORKFLOW_VERSION,
            "model": self.config.model,
            "textEncoder": self.config.text_encoder,
            "textEncoderDevice": self.config.text_encoder_device,
            "vae": self.config.vae,
            "variant": self.config.variant,
            "steps": steps,
            "cfg": cfg,
            "sampler": "euler",
            "scheduler": "Flux2Scheduler",
            **(
                {
                    "layoutReference": SKETCH_VERSION
                    if self.config.room_reference == "sketch"
                    else PLAN_VERSION,
                    "controlHash": request.extensions["quill.layout"]["controlRef"],
                }
                if request.extensions
                else {}
            ),
        }


ROOM_TEMPLATES = {"sketch": "flux2-klein-room-sketch-v2", "plan": "flux2-klein-room-plan-v3"}
MATCH_MAP = (
    "Match the surrounding map's rendering technique, lighting and level of detail, but "
    "give this room its own furnishings, materials and colors as described."
)
_ROOM_INSTRUCTIONS = {
    "sketch": (
        "Edit image 1, a top-down tabletop battlemap. It contains a floor-plan sketch of the "
        "room described above: the flat off-white area is the room's floor, dark bands are "
        "its walls, and brown floor-plan symbols mark its doors. A brown bar across the wall "
        "is a closed door. A brown bar standing out from the wall with a thin quarter-circle "
        "arc is an open door, swung into the room. Render the room as a finished "
        "roof-removed interior seen from directly above: keep the walls exactly along the "
        "dark bands as narrow dark wall tops of the same width, turn the off-white area into "
        "the described floor and furnishings, and draw each door as a real door in its shown "
        "state. No off-white fill or brown symbols may remain. "
        + MATCH_MAP
        + " Keep everything outside the room unchanged. Orthographic overhead view, no "
        "perspective, no text, labels or grid."
    ),
    "plan": (
        "Edit image 1, a top-down tabletop battlemap. The flat gray area in image 1 is a "
        "placeholder for the room described above. Image 2 is its floor plan: the gray area "
        "is the room's floor, white lines are its walls, and gaps in the white lines are "
        "door openings. Draw the room as a finished roof-removed interior seen from directly "
        "above: walls along the white lines, the described floor and furnishings across the "
        "entire gray area, and no outdoor ground, grass or sky inside the walls. No flat gray "
        "or white plan lines may remain. "
        + MATCH_MAP
        + " Keep everything outside the room unchanged and make the walls meet it naturally. "
        "Orthographic overhead view, no perspective, no text, labels or grid."
    ),
}
STYLE_LABELS = {"renderStyle": "Rendering style", "palette": "Palette"}
DEFAULT_FLOOR = (
    "Floor: a textured floor material that suits this room, such as wood planks, flagstones "
    "or packed earth, never a plain off-white surface."
)


def room_instruction(
    description: str, style: dict[str, str], reference: str, doors: list[str]
) -> str:
    """Room facts first (the user's description unchanged, floor, doors, style), then
    the edit instruction for the configured reference strategy."""
    lines = [description.strip() or "An interior room."]
    if not re.search(r"\bfloor", description, re.IGNORECASE):
        lines.append(DEFAULT_FLOOR)
    lines.append("Doors: " + "; ".join(doors) + "." if doors else "Doors: this room has no doors.")
    lines += [
        f"{STYLE_LABELS[key]}: {value.strip()}."
        for key, value in style.items()
        if key in STYLE_LABELS and value.strip()
    ]
    return "\n".join(lines) + "\n" + _ROOM_INSTRUCTIONS[reference]
