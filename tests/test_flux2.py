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
    PLAN_FLOOR,
    PLAN_WALL,
    SKETCH_FLOOR,
    Flux2Config,
    Flux2Provider,
    room_plan,
    workflow,
)
from quill.layout_guidance import SKETCH_WALL
from quill.main import app, readiness_message
from quill.projects import ProjectStore, SaveRequest
from quill.provider_config import create_provider, load_provider_config, provider_config
from quill.providers import GenerateRequest, InpaintRequest, ProviderFailure
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
            graph = workflow(Flux2Config(), check, "s.png", "p.png")
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
                            "7": {
                                "images": [
                                    {"filename": "k.png", "subfolder": "quill", "type": "output"}
                                ]
                            }
                        },
                    }
                },
            )
        if path == "/view":
            inputs = self.graph["6"]["inputs"]
            return httpx.Response(
                200,
                content=png(Image.new("RGB", (inputs["width"], inputs["height"]), (9, 99, 199))),
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
        self.assertEqual(self.provider.last_run["layoutReference"], "room-sketch-v1")

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
        self.assertEqual(run["workflowVersion"], "comfy-flux2-klein-edit-v1")
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
        self.assertTrue(generation.prompt.startswith("Image 1 is a top-down"))
        self.assertIn("each grid cell is 5 ft", generation.prompt)
        parameters = generation.parameters
        self.assertEqual(parameters["promptTemplate"], "flux2-klein-room-sketch-v1")
        self.assertTrue(parameters["layoutConditioning"])
        self.assertNotIn("negativePrompt", parameters)
        self.assertEqual(parameters["comfyui"]["workflowVersion"], "comfy-flux2-klein-edit-v1")
        self.assertEqual(len(generation.inputHashes), 3)
        self.assertEqual(parameters["comfyui"]["layoutReference"], "room-sketch-v1")
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
