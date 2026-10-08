"""Local ComfyUI FLUX.2 [klein] adapter (ADR-0032). Core nodes only; no weights bundled.

Graphs follow ComfyUI's official klein templates: UNETLoader, CLIPLoader (type flux2),
VAELoader, ReferenceLatent edits, EmptyFlux2LatentImage, Flux2Scheduler, CFGGuider and
SamplerCustomAdvanced. Room edits use one of two reference strategies:
- sketch (default): one image, the context crop with an architectural sketch of the room
  drawn in (off-white floor, dark walls, door states);
- plan: two images, the context crop with the room blanked, and a separate floor plan.
With two room passes (the default, ADR-0034), the same graph then edits its own result
once more with a description-only prompt, so the first pass sets the layout and the
second the room's floor, furnishings and character. With latent room masking (the
default, ADR-0035), both passes sample only inside the (slightly grown) room mask: the
surroundings stay pinned to the encoded reference at every step, so the model must fit
the room inside its walls instead of composing a larger building around it.
"""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx
from PIL import Image, ImageChops

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
TWO_PASS_WORKFLOW_VERSION = "comfy-flux2-klein-edit-2pass-v1"
REPAINT_WORKFLOW_VERSION = "comfy-flux2-klein-edit-repaint-v1"
# Masked second pass (ADR-0036): the last steps of an 8-step schedule, from pass 1's
# latent re-noised, with no reference image. 0.625 runs 5 steps from sigma ~0.94.
REFINE_SCHEDULE_STEPS = 8
# Door pass (ADR-0037): one masked repaint per door, zoomed in, from a brown door
# placeholder re-noised to the last 6 of 8 steps (sigma ~0.97), with no reference.
DOOR_WORKFLOW_VERSION = "comfy-flux2-klein-door-v1"
DOOR_TEMPLATE = "flux2-klein-door-v1"
DOOR_STEPS = 6
DOOR_MASK_GROW = 8
ROOM_PASSES = (1, 2)
ROOM_MASKING = ("latent", "none")
MASK_GROW = 16  # Working pixels: the whole wall band may be redrawn to blend.
PLAN_VERSION = "room-plan-v1"
SKETCH_VERSION = "room-sketch-v3"
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
    # Room edits: 1 = layout pass only; 2 = layout pass, then a description pass (ADR-0034).
    room_passes: int = 2
    # Room sampling: "latent" pins everything outside the room mask (ADR-0035); "none"
    # regenerates the whole window from an empty latent, as before.
    room_masking: str = "latent"
    # Masked second pass: fraction of the refine schedule run (ComfyUI "denoise").
    refine_denoise: float = 0.625
    # Draw doors in a separate zoomed, masked pass after the room (ADR-0037).
    door_pass: bool = True

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
        if self.room_passes not in ROOM_PASSES:
            raise ValueError("FLUX.2 room passes must be 1 or 2.")
        if self.room_masking not in ROOM_MASKING:
            raise ValueError("FLUX.2 room masking must be latent or none.")
        if not 1 / REFINE_SCHEDULE_STEPS <= self.refine_denoise <= 1:
            raise ValueError("FLUX.2 refine denoise must be between 0.125 and 1.")

    @property
    def refine_steps(self) -> int:
        return round(REFINE_SCHEDULE_STEPS * self.refine_denoise)

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
            _passes(env.get("MWQ_IMAGE_COMFY_FLUX2_ROOM_PASSES"), defaults.room_passes),
            env.get("MWQ_IMAGE_COMFY_FLUX2_ROOM_MASKING") or defaults.room_masking,
            _denoise(env.get("MWQ_IMAGE_COMFY_FLUX2_REFINE_DENOISE"), defaults.refine_denoise),
            _flag(env.get("MWQ_IMAGE_COMFY_FLUX2_DOOR_PASS"), defaults.door_pass),
        )


def _flag(value: str | None, default: bool) -> bool:
    if not value:
        return default
    if value.strip().lower() not in {"1", "0", "true", "false"}:
        raise ValueError("FLUX.2 door pass must be 1 or 0.")
    return value.strip().lower() in {"1", "true"}


def _denoise(value: str | None, default: float) -> float:
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        raise ValueError("FLUX.2 refine denoise must be a number.") from None


def _passes(value: str | None, default: int) -> int:
    if not value:
        return default
    if value.strip() not in {"1", "2"}:
        raise ValueError("FLUX.2 room passes must be 1 or 2.")
    return int(value)


def workflow(
    config: Flux2Config,
    request: GenerateRequest,
    source: str | None = None,
    plan: str | None = None,
    refine: str | None = None,
) -> dict[str, Any]:
    """Fixed graph; output node "7" is the final SaveImage. Never accepts user graphs.

    With ``refine`` (a second prompt), the first pass's latent becomes the only reference of
    a second edit with that prompt and the same noise, sampler and steps (ADR-0034). Node
    "7" then saves the second pass; the first pass is also saved, as ``quill/pass1`` (node
    "47"), and fetched for diagnostics.
    """
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
    masked = source is not None and config.room_masking == "latent"
    if masked:
        # The first reference's mask output is the room (the upload's alpha is inverted).
        graph["50"] = {
            "class_type": "GrowMask",
            "inputs": {"mask": ["20", 1], "expand": MASK_GROW, "tapered_corners": True},
        }
        graph["51"] = {
            "class_type": "SetLatentNoiseMask",
            "inputs": {"samples": ["21", 0], "mask": ["50", 0]},
        }
        graph["13"]["inputs"]["latent_image"] = ["51", 0]
    if refine is not None:
        graph["40"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": refine}}
        graph["41"] = (
            {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["40", 0]}}
            if config.variant == "distilled"
            else {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}}
        )
        positive, negative = ["40", 0], ["41", 0]
        if not masked:  # Reference edit of pass 1's result (ADR-0034).
            for node, conditioning in (("42", "40"), ("43", "41")):
                graph[node] = {
                    "class_type": "ReferenceLatent",
                    "inputs": {"conditioning": [conditioning, 0], "latent": ["13", 0]},
                }
            positive, negative = ["42", 0], ["43", 0]
        graph["44"] = {
            "class_type": "CFGGuider",
            "inputs": {"model": ["1", 0], "positive": positive, "negative": negative, "cfg": cfg},
        }
        graph["45"] = {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["11", 0],
                "guider": ["44", 0],
                "sampler": ["9", 0],
                "sigmas": ["8", 0],
                "latent_image": ["6", 0],
            },
        }
        if masked:
            # Repaint (ADR-0036): no reference to copy; pass 1's latent, re-noised to the
            # tail of a longer schedule, keeps the layout while the prompt changes the
            # floor, contents and character. The surroundings stay pinned by the mask.
            graph["52"] = {
                "class_type": "SetLatentNoiseMask",
                "inputs": {"samples": ["13", 0], "mask": ["50", 0]},
            }
            graph["53"] = {
                "class_type": "Flux2Scheduler",
                "inputs": {
                    "steps": REFINE_SCHEDULE_STEPS,
                    "width": request.width,
                    "height": request.height,
                },
            }
            graph["54"] = {
                "class_type": "SplitSigmas",
                "inputs": {
                    "sigmas": ["53", 0],
                    "step": REFINE_SCHEDULE_STEPS - config.refine_steps,
                },
            }
            graph["45"]["inputs"].update(latent_image=["52", 0], sigmas=["54", 1])
        graph["10"]["inputs"]["samples"] = ["45", 0]
        graph["46"] = {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["3", 0]}}
        graph["47"] = {
            "class_type": "SaveImage",
            "inputs": {"images": ["46", 0], "filename_prefix": "quill/pass1"},
        }
    return graph


def door_workflow(config: Flux2Config, request: GenerateRequest, source: str) -> dict[str, Any]:
    """Masked repaint of one door (ADR-0037): the uploaded crop, with a brown door
    placeholder and the door strip as inverted alpha, is VAE-encoded and re-noised to the
    last DOOR_STEPS of an 8-step schedule under the (slightly grown) strip mask. No
    reference image, so the model cannot copy the plain wall; node "7" saves the result."""
    graph = workflow(config, request)
    graph["20"] = {"class_type": "LoadImage", "inputs": {"image": source}}
    graph["21"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["20", 0], "vae": ["3", 0]}}
    graph["50"] = {
        "class_type": "GrowMask",
        "inputs": {"mask": ["20", 1], "expand": DOOR_MASK_GROW, "tapered_corners": True},
    }
    graph["51"] = {
        "class_type": "SetLatentNoiseMask",
        "inputs": {"samples": ["21", 0], "mask": ["50", 0]},
    }
    graph["53"] = {
        "class_type": "Flux2Scheduler",
        "inputs": {
            "steps": REFINE_SCHEDULE_STEPS,
            "width": request.width,
            "height": request.height,
        },
    }
    graph["54"] = {
        "class_type": "SplitSigmas",
        "inputs": {"sigmas": ["53", 0], "step": REFINE_SCHEDULE_STEPS - DOOR_STEPS},
    }
    graph["13"]["inputs"].update(latent_image=["51", 0], sigmas=["54", 1])
    graph["7"]["inputs"]["filename_prefix"] = "quill/door"
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

    def _accepts_refine(self) -> bool:
        return self.config.room_passes == 2

    def _accepts_door(self) -> bool:
        return True

    def _diagnostic_nodes(self, request: GenerateRequest) -> dict[str, str]:
        return {"47": "firstPass"} if "quill.refine" in request.extensions else {}

    def _validate(self, request: GenerateRequest) -> None:
        super()._validate(request)
        if request.negativePrompt:
            raise failure(
                "unsupported_capability", "The FLUX.2 klein workflow does not use negative prompts."
            )

    def _check_info(self, info: dict[str, Any]) -> None:
        check = GenerateRequest(requestId="check", prompt="", width=1024, height=1024)
        self._require_nodes(info, workflow(self.config, check, "source.png", "plan.png", "x"))
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
        self,
        request: GenerateRequest,
        source: Image.Image | None,
        mask: Image.Image | None,
        control: Image.Image | None,
    ) -> list[tuple[str, str, Image.Image]]:
        uploads = []
        if source is not None and mask is not None and "quill.door" in request.extensions:
            # The crop as given (Quill painted the placeholder), mask as inverted alpha.
            door = source.convert("RGBA")
            door.putalpha(ImageChops.invert(mask.convert("L")))
            uploads.append(("source", f"quill-door-{uuid4().hex}.png", door))
        elif source is not None and mask is not None and self.config.room_reference == "sketch":
            # One reference: the surroundings with the room drawn as a sketch to render.
            reference = (
                room_sketch_reference(source, mask, control)
                if control is not None
                else Image.composite(Image.new("RGB", source.size, SKETCH_FLOOR), source, mask)
            )
            uploads.append(("source", f"quill-{uuid4().hex}.png", self._masked(reference, mask)))
        elif source is not None and mask is not None:
            # The model sees the surroundings, with the room itself blanked out.
            blanked = Image.composite(Image.new("RGB", source.size, BLANK), source, mask)
            uploads.append(("source", f"quill-{uuid4().hex}.png", self._masked(blanked, mask)))
            if control is not None:
                uploads.append(("plan", f"quill-plan-{uuid4().hex}.png", room_plan(mask, control)))
        return uploads

    def _masked(self, reference: Image.Image, mask: Image.Image) -> Image.Image:
        """With latent masking, carry the room mask as inverted alpha: ComfyUI's LoadImage
        returns 1 - alpha as its mask, so the mask output is the room."""
        if self.config.room_masking != "latent":
            return reference
        rgba = reference.convert("RGBA")
        rgba.putalpha(ImageChops.invert(mask.convert("L")))
        return rgba

    def _graph(self, request: GenerateRequest, names: dict[str, str]) -> dict[str, Any]:
        if "quill.door" in request.extensions:
            return door_workflow(self.config, request, names["source"])
        refine = request.extensions.get("quill.refine")
        return workflow(
            self.config,
            request,
            names.get("source"),
            names.get("plan"),
            str(refine["prompt"]) if refine else None,
        )

    def _provenance(self, request: GenerateRequest, names: dict[str, str]) -> dict[str, Any]:
        steps, cfg = VARIANTS[self.config.variant]
        if "quill.door" in request.extensions:
            return {
                "workflowVersion": DOOR_WORKFLOW_VERSION,
                "model": self.config.model,
                "variant": self.config.variant,
                "steps": DOOR_STEPS,
                "scheduleSteps": REFINE_SCHEDULE_STEPS,
                "cfg": cfg,
                "maskGrow": DOOR_MASK_GROW,
            }
        return {
            "workflowVersion": (
                REPAINT_WORKFLOW_VERSION
                if "quill.refine" in request.extensions and self.config.room_masking == "latent"
                else (
                    TWO_PASS_WORKFLOW_VERSION
                    if "quill.refine" in request.extensions
                    else EDIT_WORKFLOW_VERSION
                )
                + ("-masked" if self.config.room_masking == "latent" else "")
            )
            if "source" in names
            else WORKFLOW_VERSION,
            "roomPasses": 2 if "quill.refine" in request.extensions else 1,
            **(
                {"roomMasking": self.config.room_masking, "maskGrow": MASK_GROW}
                if "source" in names
                else {}
            ),
            **(
                {
                    "refineDenoise": self.config.refine_denoise,
                    "refineSteps": self.config.refine_steps,
                    "refineScheduleSteps": REFINE_SCHEDULE_STEPS,
                }
                if "quill.refine" in request.extensions and self.config.room_masking == "latent"
                else {}
            ),
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
                if "quill.layout" in request.extensions
                else {}
            ),
        }


ROOM_TEMPLATES = {
    "sketch": "flux2-klein-room-sketch-v4",
    "sketch-walls": "flux2-klein-room-sketch-walls-v1",
    "plan": "flux2-klein-room-plan-v4",
}
MATCH_MAP = (
    "Match the surrounding map's rendering technique, lighting and level of detail, but "
    "give this room its own furnishings, materials and colors as described."
)
_ROOM_INSTRUCTIONS = {
    "sketch": (
        "Edit image 1, a top-down tabletop battlemap. It contains a floor-plan sketch of the "
        "room described above: the flat off-white area is the room's floor, dark bands are "
        "its walls, and brown bands set into the walls are closed doors. Render the room as "
        "a finished roof-removed interior seen from directly above: keep the walls exactly "
        "along the dark bands as narrow dark wall tops of the same width, turn the "
        "off-white area into the described floor and furnishings, and draw each brown band "
        "as a closed wooden door set in the wall, with no other doors. No off-white fill or "
        "flat brown may remain. "
        + MATCH_MAP
        + " Keep everything outside the room unchanged. Orthographic overhead view, no "
        "perspective, no text, labels or grid."
    ),
    # With the door pass (ADR-0037) the sketch has no door bands and walls stay solid.
    "sketch-walls": (
        "Edit image 1, a top-down tabletop battlemap. It contains a floor-plan sketch of the "
        "room described above: the flat off-white area is the room's floor and dark bands "
        "are its walls. Render the room as a finished roof-removed interior seen from "
        "directly above: keep the walls exactly along the dark bands as narrow, solid dark "
        "wall tops of the same width, with no doors or openings in them, and turn the "
        "off-white area into the described floor and furnishings. No off-white fill may "
        "remain. "
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
    description: str, style: dict[str, str], reference: str, *, doors: bool = True
) -> str:
    """Room facts first (the user's description unchanged, floor, style), then the edit
    instruction for the configured reference strategy. Doors are shown only in the
    reference: a written door list made the model draw extra doors on the floor."""
    lines = [description.strip() or "An interior room."]
    if not re.search(r"\bfloor", description, re.IGNORECASE):
        lines.append(DEFAULT_FLOOR)
    lines += [
        f"{STYLE_LABELS[key]}: {value.strip()}."
        for key, value in style.items()
        if key in STYLE_LABELS and value.strip()
    ]
    key = reference if doors or reference != "sketch" else "sketch-walls"
    return "\n".join(lines) + "\n" + _ROOM_INSTRUCTIONS[key]


REFINE_TEMPLATE = "flux2-klein-room-refine-v2"
REPAINT_TEMPLATE = "flux2-klein-room-repaint-v1"
REPAINT_WALLS_TEMPLATE = "flux2-klein-room-repaint-walls-v1"
REFINE_FLOOR = (
    "Give the floor a clearly textured material that suits this room, such as wood planks, "
    "flagstones or packed earth; it must not be plain, flat or pale."
)


def room_repaint_instruction(description: str, style: dict[str, str], *, doors: bool = True) -> str:
    """Masked second-pass prompt (ADR-0036). There is no reference image to refer to: the
    prompt describes the finished room, and pass 1's layout comes from the re-noised
    latent."""
    described = description.strip() or "An interior room."
    floor = (
        "The floor is exactly as described, with visible material and texture."
        if re.search(r"\bfloor", description, re.IGNORECASE)
        else "The floor is a clearly textured material that suits this room, such as wood "
        "planks, flagstones or packed earth, never plain, flat or pale."
    )
    styled = " ".join(
        f"{STYLE_LABELS[key]}: {value.strip()}."
        for key, value in style.items()
        if key in STYLE_LABELS and value.strip()
    )
    return (
        "Orthographic overhead view of one room on a tabletop battlemap, roof removed, seen "
        f"from directly above:\n{described}\n"
        f"{floor} Furnishings and objects that fit the description fill the whole room, "
        "spread across the floor and not only along the walls, with floor visible between "
        "them, and the room has the character the description asks for. "
        + (styled + " " if styled else "")
        + (
            "Narrow dark wall tops run along the room's edges; doors are closed wooden doors "
            "set in the walls, and there are no other doors. "
            if doors
            else "Narrow, solid dark wall tops run along the room's edges, with no doors or "
            "openings in them. "
        )
        + "No perspective, no text, labels or grid."
    )


def room_refine_instruction(description: str, style: dict[str, str]) -> str:
    """Second-pass prompt: the room already has walls and doors; make it match the
    description, with a real floor and furnishings across the whole room."""
    described = description.strip() or "An interior room."
    floor = (
        "Make the floor exactly as described, with visible material and texture."
        if re.search(r"\bfloor", description, re.IGNORECASE)
        else REFINE_FLOOR
    )
    styled = " ".join(
        f"{STYLE_LABELS[key]}: {value.strip()}."
        for key, value in style.items()
        if key in STYLE_LABELS and value.strip()
    )
    return (
        "Restyle the interior of the room near the centre of image 1 to match this "
        f"description:\n{described}\n"
        f"{floor} Fill the whole room with furnishings and objects that fit the description, "
        "spread across the floor and not only along the walls, with floor visible between "
        "them. Give the room the character the description asks for. "
        + (styled + " " if styled else "")
        + "Keep the room's walls and dark wall tops exactly where they are and keep "
        "everything outside the room unchanged. Any flat brown strip set into a wall is a "
        "closed door: draw it as a wooden door in that wall. Add no other doors. "
        "Orthographic overhead view of a tabletop battlemap, no perspective, no text, labels "
        "or grid."
    )


def door_instruction(style: dict[str, str]) -> str:
    """Door-pass prompt (ADR-0037); position and size come from the mask, not the text."""
    styled = " ".join(
        f"{STYLE_LABELS[key]}: {value.strip()}."
        for key, value in style.items()
        if key in STYLE_LABELS and value.strip()
    )
    return (
        "Orthographic overhead view of a tabletop battlemap, seen from directly above, no "
        "perspective. A closed wooden door is set into a wall: a narrow strip of wooden "
        "planks with a simple frame, lying exactly in line with the wall and filling the "
        "gap in it, the same width as the wall's dark top. It matches the wall and floor "
        "around it in material, lighting and level of detail. "
        + (styled + " " if styled else "")
        + "No text, labels or grid."
    )
