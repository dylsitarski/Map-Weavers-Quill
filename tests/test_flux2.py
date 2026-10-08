"""FLUX.2 klein adapter and editor integration with a synthetic ComfyUI; no weights or GPU."""

import json
import os
import tempfile
import time
import unittest
from email.parser import BytesParser
from email.policy import default
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from quill.backgrounds import BackgroundResult
from quill.flux2 import (
    BLANK,
    DEFAULT_FLOOR,
    PLAN_FLOOR,
    PLAN_WALL,
    SKETCH_FLOOR,
    Flux2Config,
    Flux2Provider,
    room_instruction,
    room_plan,
    room_refine_instruction,
    room_repaint_instruction,
    workflow,
)
from quill.layout_guidance import SKETCH_WALL
from quill.main import app, readiness_message
from quill.projects import ProjectStore, SaveRequest
from quill.provider_config import create_provider, load_provider_config, provider_config
from quill.providers import GenerateRequest, InpaintRequest, ProviderFailure
from quill.raster import image as raster_image
from test_projects import document


def png(image: Image.Image) -> bytes:
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def decode(data: bytes) -> Image.Image:
    with Image.open(BytesIO(data)) as opened:
        return opened.convert("RGB")


class FakeComfy:
    """Synthetic ComfyUI with the klein models installed; records graph and uploads."""

    def __init__(self):
        self.calls: list[str] = []
        self.graph = None
        self.uploads: list[tuple[str, bytes]] = []
        self.models = ["flux-2-klein-4b-fp8.safetensors"]
        self.clip_types = ["stable_diffusion", "flux2"]

    def respond(self, request):
        path = request.url.path
        self.calls.append(path)
        if path == "/object_info":
            check = GenerateRequest(requestId="c", prompt="", width=1024, height=1024)
            graph = workflow(Flux2Config(), check, "s.png", "p.png", "refine")
            info = {node["class_type"]: {} for node in graph.values()}
            info["UNETLoader"] = {"input": {"required": {"unet_name": [list(self.models)]}}}
            info["CLIPLoader"] = {
                "input": {
                    "required": {
                        "clip_name": [["qwen_3_4b.safetensors"]],
                        "type": [list(self.clip_types)],
                    }
                }
            }
            info["VAELoader"] = {"input": {"required": {"vae_name": [["flux2-vae.safetensors"]]}}}
            return httpx.Response(200, json=info)
        if path == "/upload/image":
            message = BytesParser(policy=default).parsebytes(
                f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode()
                + request.content
            )
            part = next(p for p in message.iter_parts() if p.get_filename())
            self.uploads.append((part.get_filename(), part.get_payload(decode=True)))
            return httpx.Response(
                200, json={"name": part.get_filename(), "subfolder": "", "type": "input"}
            )
        if path == "/prompt":
            self.graph = json.loads(request.content)["prompt"]
            return httpx.Response(200, json={"prompt_id": "klein-job"})
        if path == "/history/klein-job":
            return httpx.Response(
                200,
                json={
                    "klein-job": {
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": {
                            node: {
                                "images": [
                                    {"filename": name, "subfolder": "quill", "type": "output"}
                                ]
                            }
                            for node, name in (("7", "k.png"), ("47", "pass1.png"))
                            if node in self.graph
                        },
                    }
                },
            )
        if path == "/view":
            inputs = self.graph["6"]["inputs"]
            # The first pass is told apart from the final image by colour.
            color = (40, 40, 40) if request.url.params["filename"] == "pass1.png" else (9, 99, 199)
            return httpx.Response(
                200, content=png(Image.new("RGB", (inputs["width"], inputs["height"]), color))
            )
        raise AssertionError(path)


class Flux2ProtocolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fake = FakeComfy()
        self.provider = self.make(Flux2Config())
        self.request = GenerateRequest(
            requestId="t", prompt="mossy ruins", width=960, height=640, seed=7
        )

    def make(self, config):
        return Flux2Provider(config, transport=httpx.MockTransport(self.fake.respond))

    async def test_readiness_checks_nodes_files_and_flux2_support_without_gpu_work(self):
        self.assertTrue(await self.provider.health())
        self.assertEqual(self.fake.calls, ["/object_info"])
        self.fake.models = []
        with self.assertRaises(ProviderFailure) as error:
            await self.provider.check()
        self.assertIn("FLUX.2 klein model", error.exception.error.message)
        self.fake.models = ["flux-2-klein-4b-fp8.safetensors"]
        self.fake.clip_types = ["stable_diffusion"]
        with self.assertRaises(ProviderFailure) as error:
            await self.provider.check()
        self.assertIn("Update ComfyUI", error.exception.error.message)
        self.assertNotIn("/prompt", self.fake.calls)

    async def test_text_to_image_follows_the_distilled_template(self):
        result = await self.provider.generate(self.request)
        self.assertEqual(result.providerId, "comfyui-flux2-klein")
        self.assertEqual((result.width, result.height), (960, 640))
        g = self.fake.graph
        self.assertEqual(g["1"]["inputs"]["unet_name"], "flux-2-klein-4b-fp8.safetensors")
        self.assertEqual(g["2"]["inputs"], {"clip_name": "qwen_3_4b.safetensors", "type": "flux2"})
        self.assertEqual(
            g["5"], {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}}
        )
        self.assertEqual(g["6"]["inputs"], {"width": 960, "height": 640, "batch_size": 1})
        self.assertEqual(g["8"]["inputs"], {"steps": 4, "width": 960, "height": 640})
        self.assertEqual(
            g["12"]["inputs"],
            {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "cfg": 1.0},
        )
        self.assertEqual(g["11"]["inputs"]["noise_seed"], 7)
        self.assertEqual(g["13"]["inputs"]["latent_image"], ["6", 0])
        self.assertEqual(g["7"]["inputs"]["images"], ["10", 0])
        self.assertFalse(any(n["class_type"] == "LoadImage" for n in g.values()))
        self.assertEqual(self.fake.uploads, [])
        run = self.provider.last_run
        self.assertEqual(run["workflowVersion"], "comfy-flux2-klein-v1")
        self.assertEqual((run["variant"], run["steps"], run["cfg"]), ("distilled", 4, 1.0))
        self.assertNotIn("layoutReference", run)

    async def test_sketch_reference_is_one_image_and_protects_outside_pixels(self):
        size = (1024, 1024)
        source = Image.new("RGB", size, (200, 10, 10))
        mask = Image.new("L", size)
        mask.paste(255, (256, 256, 768, 768))
        sketch = Image.new("RGB", size)
        ImageDraw.Draw(sketch).rectangle((250, 250, 773, 773), outline=SKETCH_WALL, width=12)
        refs = [self.provider.put(png(i)) for i in (source, mask, sketch)]
        await self.provider.inpaint(
            InpaintRequest(
                requestId="r",
                prompt="Image 1",
                width=1024,
                height=1024,
                seed=3,
                sourceRef=refs[0],
                maskRef=refs[1],
                maskConvention="white-edit-black-preserve",
                extensions={"quill.layout": {"controlRef": refs[2]}},
            )
        )
        ((name, reference),) = self.fake.uploads
        reference = decode(reference)
        self.assertEqual(reference.getpixel((10, 10)), (200, 10, 10))  # Surroundings kept.
        self.assertEqual(reference.getpixel((512, 512)), SKETCH_FLOOR)  # Room is "paper".
        self.assertEqual(reference.getpixel((252, 512)), SKETCH_WALL)  # Wall drawn over context.
        g = self.fake.graph
        self.assertEqual(g["20"]["inputs"]["image"], name)
        self.assertNotIn("24", g)  # Single reference image.
        self.assertEqual(g["12"]["inputs"]["positive"], ["22", 0])
        self.assertEqual(g["12"]["inputs"]["negative"], ["23", 0])
        result = decode(self.provider.assets[next(reversed(self.provider.assets))])
        self.assertEqual(result.getpixel((10, 10)), (200, 10, 10))
        self.assertEqual(result.getpixel((512, 512)), (9, 99, 199))
        self.assertEqual(self.provider.last_run["layoutReference"], "room-sketch-v3")

    async def test_latent_masking_pins_the_surroundings_in_both_passes(self):
        size = (1024, 1024)
        source = Image.new("RGB", size, (200, 10, 10))
        mask = Image.new("L", size)
        mask.paste(255, (256, 256, 768, 768))
        images = (source, mask, Image.new("RGB", size))
        refs = [self.provider.put(png(i)) for i in images]
        request = InpaintRequest(
            requestId="r",
            prompt="Image 1",
            width=1024,
            height=1024,
            seed=3,
            sourceRef=refs[0],
            maskRef=refs[1],
            maskConvention="white-edit-black-preserve",
            extensions={
                "quill.layout": {"controlRef": refs[2]},
                "quill.refine": {"prompt": "Restyle the room"},
            },
        )
        await self.provider.inpaint(request)
        # The upload carries the room as inverted alpha, so LoadImage's mask is the room.
        ((_, data),) = self.fake.uploads
        with Image.open(BytesIO(data)) as upload:
            self.assertEqual(upload.mode, "RGBA")
            self.assertEqual(upload.getpixel((10, 10))[3], 255)
            self.assertEqual(upload.getpixel((512, 512))[3], 0)
        g = self.fake.graph
        self.assertEqual(g["50"]["class_type"], "GrowMask")
        self.assertEqual(g["50"]["inputs"]["mask"], ["20", 1])
        # Pass 1 samples from the encoded reference under the mask, not an empty latent.
        self.assertEqual(g["51"]["inputs"], {"samples": ["21", 0], "mask": ["50", 0]})
        self.assertEqual(g["13"]["inputs"]["latent_image"], ["51", 0])
        # Pass 2 samples from pass 1 under the same mask.
        self.assertEqual(g["52"]["inputs"], {"samples": ["13", 0], "mask": ["50", 0]})
        self.assertEqual(g["45"]["inputs"]["latent_image"], ["52", 0])
        self.assertEqual(self.provider.last_run["roomMasking"], "latent")
        # Unmasked: whole-window generation from an empty latent and an RGB upload.
        self.fake.uploads.clear()
        unmasked = self.make(Flux2Config(room_masking="none"))
        self.assertEqual([unmasked.put(png(i)) for i in images], refs)
        await unmasked.inpaint(request)
        g = self.fake.graph
        self.assertNotIn("50", g)
        self.assertEqual(g["13"]["inputs"]["latent_image"], ["6", 0])
        self.assertEqual(g["45"]["inputs"]["latent_image"], ["6", 0])
        # Unmasked, pass 2 is still the reference edit of pass 1 on the full schedule.
        self.assertEqual(g["42"]["inputs"], {"conditioning": ["40", 0], "latent": ["13", 0]})
        self.assertEqual(g["44"]["inputs"]["positive"], ["42", 0])
        self.assertEqual(g["45"]["inputs"]["sigmas"], ["8", 0])
        self.assertNotIn("54", g)
        with Image.open(BytesIO(self.fake.uploads[0][1])) as upload:
            self.assertEqual(upload.mode, "RGB")
        self.assertEqual(unmasked.last_run["workflowVersion"], "comfy-flux2-klein-edit-2pass-v1")

    async def test_masked_second_pass_repaints_pass_one_without_a_reference(self):
        size = (1024, 1024)
        source = Image.new("RGB", size, (200, 10, 10))
        mask = Image.new("L", size)
        mask.paste(255, (256, 256, 768, 768))
        images = (source, mask, Image.new("RGB", size))
        refs = [self.provider.put(png(i)) for i in images]
        request = InpaintRequest(
            requestId="r",
            prompt="Image 1",
            width=1024,
            height=1024,
            seed=3,
            sourceRef=refs[0],
            maskRef=refs[1],
            maskConvention="white-edit-black-preserve",
            extensions={
                "quill.layout": {"controlRef": refs[2]},
                "quill.refine": {"prompt": "Restyle the room"},
            },
        )
        await self.provider.inpaint(request)
        self.assertEqual(len(self.fake.uploads), 1)  # Still one upload and one submission.
        self.assertEqual(self.fake.calls.count("/prompt"), 1)
        g = self.fake.graph
        self.assertEqual(g["40"]["inputs"]["text"], "Restyle the room")
        self.assertEqual(g["41"]["inputs"], {"conditioning": ["40", 0]})  # Zeroed negative.
        # No reference image to copy: the prompt alone conditions the repaint.
        self.assertNotIn("42", g)
        self.assertEqual(g["44"]["inputs"]["positive"], ["40", 0])
        self.assertEqual(g["44"]["inputs"]["negative"], ["41", 0])
        self.assertEqual(g["45"]["inputs"]["guider"], ["44", 0])
        self.assertEqual(g["45"]["inputs"]["noise"], ["11", 0])
        # Pass 1's latent, re-noised to the last 5 of 8 scheduler steps, under the mask.
        self.assertEqual(g["45"]["inputs"]["latent_image"], ["52", 0])
        self.assertEqual(g["52"]["inputs"]["samples"], ["13", 0])
        self.assertEqual(g["53"]["class_type"], "Flux2Scheduler")
        self.assertEqual(g["53"]["inputs"]["steps"], 8)
        self.assertEqual(g["54"]["inputs"], {"sigmas": ["53", 0], "step": 3})
        self.assertEqual(g["45"]["inputs"]["sigmas"], ["54", 1])
        # The final image is the second pass; the first is saved only for inspection.
        self.assertEqual(g["10"]["inputs"]["samples"], ["45", 0])
        self.assertEqual(g["7"]["inputs"]["images"], ["10", 0])
        self.assertEqual(g["47"]["inputs"]["filename_prefix"], "quill/pass1")
        result = decode(self.provider.assets[next(reversed(self.provider.assets))])
        self.assertEqual(result.getpixel((10, 10)), (200, 10, 10))  # Outside still exact.
        # Unclipped diagnostics: the first pass and the final image before clipping.
        diagnostics = self.provider.diagnostics
        self.assertEqual(set(diagnostics), {"raw", "firstPass"})
        first = decode(self.provider.assets[diagnostics["firstPass"]])
        self.assertEqual(first.getpixel((10, 10)), (40, 40, 40))
        raw = decode(self.provider.assets[diagnostics["raw"]])
        self.assertEqual(raw.getpixel((10, 10)), (9, 99, 199))  # Not clipped.
        run = self.provider.last_run
        self.assertNotIn("raw", run)
        self.assertEqual(run["workflowVersion"], "comfy-flux2-klein-edit-repaint-v1")
        self.assertEqual(run["roomPasses"], 2)
        self.assertEqual((run["refineDenoise"], run["refineSteps"]), (0.625, 5))
        # A stronger repaint runs more of the schedule.
        strong = self.make(Flux2Config(refine_denoise=1.0))
        self.assertEqual([strong.put(png(i)) for i in images], refs)
        await strong.inpaint(request)
        self.assertEqual(self.fake.graph["54"]["inputs"]["step"], 0)
        # Base variant: an empty-text negative, as in the first pass.
        base = self.make(Flux2Config(variant="base"))
        self.assertEqual([base.put(png(i)) for i in images], refs)
        await base.inpaint(request)
        self.assertEqual(self.fake.graph["41"]["inputs"]["text"], "")
        # One-pass configuration, a missing layout or an empty prompt: refused offline.
        calls = len(self.fake.calls)
        one_pass = self.make(Flux2Config(room_passes=1))
        for i in images:
            one_pass.put(png(i))
        bad = [
            (one_pass, request),
            (
                self.provider,
                request.model_copy(update={"extensions": {"quill.refine": {"prompt": "x"}}}),
            ),
            (
                self.provider,
                request.model_copy(
                    update={
                        "extensions": {
                            "quill.layout": {"controlRef": refs[2]},
                            "quill.refine": {"prompt": " "},
                        }
                    }
                ),
            ),
        ]
        for provider, bad_request in bad:
            with self.assertRaises(ProviderFailure):
                await provider.inpaint(bad_request)
        self.assertEqual(len(self.fake.calls), calls)

    async def test_plan_reference_sends_blanked_context_and_plan(self):
        self.provider = self.make(Flux2Config(room_reference="plan"))
        size = (1024, 1024)
        source = Image.new("RGB", size, (200, 10, 10))
        mask = Image.new("L", size)
        mask.paste(255, (256, 256, 768, 768))
        walls = Image.new("RGB", size)
        ImageDraw.Draw(walls).rectangle((256, 256, 767, 767), outline="white", width=3)
        refs = [self.provider.put(png(i)) for i in (source, mask, walls)]
        await self.provider.inpaint(
            InpaintRequest(
                requestId="r",
                prompt="Edit image 1",
                width=1024,
                height=1024,
                seed=3,
                sourceRef=refs[0],
                maskRef=refs[1],
                maskConvention="white-edit-black-preserve",
                extensions={"quill.layout": {"controlRef": refs[2]}},
            )
        )
        # Image 1: surroundings unchanged, the room blanked to neutral gray.
        (source_name, blanked), (plan_name, plan) = self.fake.uploads
        blanked, plan = decode(blanked), decode(plan)
        self.assertEqual(blanked.getpixel((10, 10)), (200, 10, 10))
        self.assertEqual(blanked.getpixel((512, 512)), BLANK)
        # Image 2: black outside, gray floor, white walls.
        self.assertEqual(plan.getpixel((10, 10)), (0, 0, 0))
        self.assertEqual(plan.getpixel((512, 512)), (PLAN_FLOOR,) * 3)
        self.assertEqual(plan.getpixel((257, 512)), (PLAN_WALL,) * 3)
        g = self.fake.graph
        self.assertEqual(g["20"]["inputs"]["image"], source_name)
        self.assertEqual(g["24"]["inputs"]["image"], plan_name)
        # Reference latents chain: prompt -> image 1 -> image 2, on both conditionings.
        self.assertEqual(g["22"]["inputs"], {"conditioning": ["4", 0], "latent": ["21", 0]})
        self.assertEqual(g["23"]["inputs"], {"conditioning": ["5", 0], "latent": ["21", 0]})
        self.assertEqual(g["26"]["inputs"], {"conditioning": ["22", 0], "latent": ["25", 0]})
        self.assertEqual(g["27"]["inputs"], {"conditioning": ["23", 0], "latent": ["25", 0]})
        self.assertEqual(g["12"]["inputs"]["positive"], ["26", 0])
        self.assertEqual(g["12"]["inputs"]["negative"], ["27", 0])
        # Outside the mask the result is the original source, whatever the model painted.
        result = decode(self.provider.assets[next(reversed(self.provider.assets))])
        self.assertEqual(result.getpixel((10, 10)), (200, 10, 10))
        self.assertEqual(result.getpixel((512, 512)), (9, 99, 199))
        run = self.provider.last_run
        self.assertEqual(run["workflowVersion"], "comfy-flux2-klein-edit-v1-masked")
        self.assertEqual(run["layoutReference"], "room-plan-v1")
        self.assertEqual(run["controlHash"], refs[2])

    async def test_base_variant_and_cpu_text_encoder(self):
        provider = self.make(Flux2Config(variant="base", text_encoder_device="cpu"))
        await provider.generate(self.request)
        g = self.fake.graph
        self.assertEqual(g["2"]["inputs"]["device"], "cpu")
        self.assertEqual(
            g["5"], {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}}
        )
        self.assertEqual(g["8"]["inputs"]["steps"], 20)
        self.assertEqual(g["12"]["inputs"]["cfg"], 5.0)
        self.assertEqual((provider.last_run["steps"], provider.last_run["cfg"]), (20, 5.0))

    async def test_unsupported_requests_never_contact_the_server(self):
        for request in (
            self.request.model_copy(update={"negativePrompt": "text"}),
            self.request.model_copy(update={"extensions": {"quill.layout": {"controlRef": "x"}}}),
            self.request.model_copy(update={"width": 1000}),
        ):
            with self.assertRaises(ProviderFailure):
                await self.provider.generate(request)
        self.assertEqual(self.fake.calls, [])

    def test_configuration_validation_and_environment(self):
        for bad in (
            {"variant": "turbo"},
            {"text_encoder_device": "gpu"},
            {"model": "../klein.safetensors"},
            {"room_reference": "mask"},
            {"room_passes": 3},
            {"room_masking": "pixel"},
            {"refine_denoise": 0.1},
            {"refine_denoise": 1.5},
            {"vae": "vae.ckpt"},
            {"url": "http://example.com:8188"},
        ):
            with self.assertRaises(ValueError, msg=bad):
                Flux2Config(**bad)
        config = Flux2Config.from_env(
            {
                "MWQ_IMAGE_COMFY_FLUX2_MODEL": "flux-2-klein-base-4b-fp8.safetensors",
                "MWQ_IMAGE_COMFY_FLUX2_VARIANT": "base",
                "MWQ_IMAGE_COMFY_FLUX2_TEXT_ENCODER_DEVICE": "cpu",
                "MWQ_IMAGE_COMFY_FLUX2_ROOM_REFERENCE": "plan",
            }
        )
        self.assertEqual(config.room_reference, "plan")
        self.assertEqual(Flux2Config.from_env({}).room_reference, "sketch")
        self.assertEqual(Flux2Config.from_env({}).room_passes, 2)
        self.assertEqual(Flux2Config.from_env({}).room_masking, "latent")
        masking = {"MWQ_IMAGE_COMFY_FLUX2_ROOM_MASKING": "none"}
        self.assertEqual(Flux2Config.from_env(masking).room_masking, "none")
        denoise = {"MWQ_IMAGE_COMFY_FLUX2_REFINE_DENOISE": "0.75"}
        self.assertEqual(Flux2Config.from_env(denoise).refine_steps, 6)
        with self.assertRaises(ValueError):
            Flux2Config.from_env({"MWQ_IMAGE_COMFY_FLUX2_REFINE_DENOISE": "high"})
        passes = {"MWQ_IMAGE_COMFY_FLUX2_ROOM_PASSES": "1"}
        self.assertEqual(Flux2Config.from_env(passes).room_passes, 1)
        with self.assertRaises(ValueError):
            Flux2Config.from_env({"MWQ_IMAGE_COMFY_FLUX2_ROOM_PASSES": "two"})
        self.assertEqual(
            (config.model, config.variant, config.text_encoder_device, config.vae),
            ("flux-2-klein-base-4b-fp8.safetensors", "base", "cpu", "flux2-vae.safetensors"),
        )
        loaded = load_provider_config({"MWQ_IMAGE_PROVIDER": "comfyui-flux2-klein"})
        self.assertEqual(loaded.flux2, Flux2Config())
        self.assertIsNone(loaded.comfy)
        with self.assertRaises(ValueError):
            load_provider_config(
                {"MWQ_IMAGE_PROVIDER": "comfyui-flux2-klein", "MWQ_IMAGE_COMFY_FLUX2_VARIANT": "x"}
            )
        self.assertEqual(readiness_message(self.provider), "Ready · distilled model")

    def test_plan_marks_floor_and_walls_only(self):
        mask = Image.new("L", (64, 64))
        mask.paste(255, (16, 16, 48, 48))
        walls = Image.new("RGB", (64, 64))
        walls.paste((255, 255, 255), (0, 0, 64, 1))
        plan = room_plan(mask, walls)
        self.assertEqual(plan.getpixel((32, 32)), (PLAN_FLOOR,) * 3)
        self.assertEqual(plan.getpixel((5, 0)), (PLAN_WALL,) * 3)
        self.assertEqual(plan.getpixel((5, 5)), (0, 0, 0))

    def test_room_instruction_puts_room_facts_first(self):
        style = {"renderStyle": "inked", "palette": " "}
        text = room_instruction("Cluttered storeroom with crates", style, "sketch")
        lines = text.splitlines()
        self.assertEqual(
            lines[:3],
            ["Cluttered storeroom with crates", DEFAULT_FLOOR, "Rendering style: inked."],
        )
        self.assertTrue(lines[3].startswith("Edit image 1"))
        # Doors are shown only in the sketch; a written list put doors on the floor.
        self.assertNotIn("Doors:", text)
        self.assertIn("closed wooden door set in the wall", text)
        self.assertNotIn("Palette", text)
        self.assertNotIn("same art style", text)
        self.assertIn("its own furnishings, materials and colors", text)
        refine = room_refine_instruction("Cluttered storeroom with crates", style)
        self.assertIn("description:\nCluttered storeroom with crates\n", refine)
        self.assertIn("must not be plain, flat or pale", refine)
        self.assertIn("not only along the walls", refine)
        self.assertIn("Rendering style: inked.", refine)
        self.assertIn("keep everything outside the room unchanged", refine)
        self.assertIn("draw it as a wooden door in that wall. Add no other doors.", refine)
        self.assertIn(
            "Make the floor exactly as described", room_refine_instruction("Oak floor", {})
        )
        self.assertIn("with no other doors", text)
        repaint = room_repaint_instruction("Cluttered storeroom with crates", style)
        self.assertIn("seen from directly above:\nCluttered storeroom with crates\n", repaint)
        self.assertIn("never plain, flat or pale", repaint)
        self.assertIn("there are no other doors", repaint)
        self.assertNotIn("image 1", repaint.lower())  # No reference image in this pass.
        self.assertIn(
            "The floor is exactly as described", room_repaint_instruction("Dark wood floor", {})
        )
        described = room_instruction("Bedroom, mossy flagstone FLOORS", {}, "plan")
        self.assertNotIn(DEFAULT_FLOOR, described)
        self.assertIn("Image 2 is its floor plan", described)


class Flux2EditorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = patch.dict(
            os.environ,
            {"MWQ_DATA_DIR": temp.name, "MWQ_IMAGE_PROVIDER": "comfyui-flux2-klein"},
            clear=True,
        )
        env.start()
        self.addCleanup(env.stop)
        provider_config.cache_clear()
        self.addCleanup(provider_config.cache_clear)
        self.fake = FakeComfy()
        transport = httpx.MockTransport(self.fake.respond)
        clients = patch.object(
            Flux2Provider,
            "client",
            lambda _: httpx.AsyncClient(base_url="http://127.0.0.1:8188", transport=transport),
        )
        clients.start()
        self.addCleanup(clients.stop)
        self.store = ProjectStore(Path(temp.name) / "projects.sqlite3")

    def run_job(self, client, target, payload):
        job_id = str(uuid4())
        self.assertEqual(client.post(f"/api/jobs/{job_id}/{target}", json=payload).status_code, 202)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["status"] not in {"queued", "running"}:
                return job
            time.sleep(0.01)
        self.fail("job did not finish")

    def test_room_job_uses_klein_prompt_plan_and_saves(self):
        self.assertIsInstance(create_provider(), Flux2Provider)
        with TestClient(app) as client:
            ready = client.get("/api/providers/readiness").json()
            self.assertTrue(ready["ready"], ready)
            self.assertEqual(ready["descriptor"]["id"], "comfyui-flux2-klein")
            self.assertIn("control_image", ready["descriptor"]["capabilities"])
            background = self.run_job(
                client, "background", {"prompt": "Forest clearing", "seed": 1, "baseRevision": 0}
            )
            self.assertEqual(background["status"], "succeeded", background)
            bg = BackgroundResult.model_validate_json(json.dumps(background["result"]))
            self.assertNotIn("negativePrompt", bg.generation.parameters)
            project = document()
            room = project.rooms[0]
            job = self.run_job(
                client,
                "room",
                {"project": project.model_dump(mode="json"), "roomId": str(room.id), "seed": 2},
            )
            self.assertEqual(job["status"], "succeeded", job)
        result = BackgroundResult.model_validate_json(json.dumps(job["result"]))
        generation = result.generation
        self.assertEqual(generation.providerId, "comfyui-flux2-klein")
        # Room facts first: the description, then the edit instruction.
        lines = generation.prompt.splitlines()
        self.assertEqual(lines[0], room.prompt)
        self.assertNotIn("Doors:", generation.prompt)
        self.assertIn("one 5-ft grid square is 128 pixels wide", generation.prompt)
        self.assertNotIn("Follow the supplied wall lines", generation.prompt)
        parameters = generation.parameters
        self.assertEqual(parameters["promptTemplate"], "flux2-klein-room-sketch-v4")
        self.assertTrue(parameters["layoutConditioning"])
        self.assertNotIn("negativePrompt", parameters)
        # Two passes by default: layout, then a description-only edit of that result.
        self.assertEqual(
            parameters["comfyui"]["workflowVersion"], "comfy-flux2-klein-edit-repaint-v1"
        )
        self.assertEqual(parameters["refineTemplate"], "flux2-klein-room-repaint-v1")
        # Both passes are kept unclipped, at map size, for debugging bundles.
        unclipped = parameters["diagnosticImages"]
        self.assertEqual(set(unclipped), {"raw", "firstPass"})
        first = raster_image(self.store.get_asset(unclipped["firstPass"]))
        self.assertEqual(first.size, (960, 640))
        crop = parameters["crop"]
        self.assertEqual(first.getpixel((crop[0] + 2, crop[1] + 2)), (40, 40, 40, 255))
        self.assertEqual(first.getpixel((crop[2] + 2, crop[1] + 2))[3], 0)
        self.assertTrue(
            parameters["refinePrompt"].startswith("Orthographic overhead view of one room")
        )
        self.assertIn(room.prompt, parameters["refinePrompt"])
        self.assertIn("128 pixels wide", parameters["refinePrompt"])
        self.assertEqual(self.fake.graph["40"]["inputs"]["text"], parameters["refinePrompt"])
        self.assertEqual(len(generation.inputHashes), 3)
        self.assertEqual(parameters["comfyui"]["layoutReference"], "room-sketch-v3")
        # One sketch reference at the working size, with off-white floor and dark walls.
        ((_, data),) = self.fake.uploads
        reference = decode(data)
        self.assertEqual(reference.size, (1024, 1024))
        colors = {color for _, color in reference.getcolors(1024 * 1024)}
        self.assertIn(SKETCH_FLOOR, colors)
        self.assertIn(SKETCH_WALL, colors)
        room.renderLayerId = result.layer.id
        project.layers = [bg.layer, result.layer]
        project.generations = [bg.generation, generation]
        saved = self.store.save(SaveRequest(project=project, expectedRevision=None))
        self.assertEqual(self.store.open(saved.projectId), saved)
