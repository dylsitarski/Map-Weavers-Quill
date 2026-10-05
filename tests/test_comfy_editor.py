"""Queued editor integration through the real adapter and synthetic HTTP transport."""

import json
import os
import tempfile
import time
import unittest
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from threading import Event
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image
from quill.backgrounds import BackgroundResult
from quill.comfyui import ComfyConfig, ComfyProvider, workflow
from quill.main import app
from quill.projects import ProjectStore, SaveRequest
from quill.provider_config import create_provider, load_provider_config, provider_config
from quill.providers import GenerateRequest
from quill.raster import image, png, polygon_mask
from quill.sdxl_authoring import NEGATIVE, RoomTransform
from test_projects import document


class FakeComfy:
    def __init__(self):
        self.calls = []
        self.graph = None
        self.upload = None
        self.size = None
        self.entered = Event()
        self.release = Event()
        self.release.set()
        self.failed = False
        self.missing = False

    def respond(self, request):
        path = request.url.path
        self.calls.append(path)
        if path == "/object_info":
            graph = workflow(
                ComfyConfig(),
                GenerateRequest(requestId="test", prompt="", width=960, height=640),
                "image.png",
            )
            info = {node["class_type"]: {} for node in graph.values()}
            info["EmptyLatentImage"] = {}
            info["CheckpointLoaderSimple"] = {
                "input": {
                    "required": {
                        "ckpt_name": [[] if self.missing else ["sd_xl_base_1.0.safetensors"]]
                    }
                }
            }
            return httpx.Response(200, json=info)
        if path == "/upload/image":
            message = BytesParser(policy=default).parsebytes(
                f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode()
                + request.content
            )
            part = next(p for p in message.iter_parts() if p.get_filename())
            self.upload = image(part.get_payload(decode=True))
            self.size = self.upload.size
            return httpx.Response(
                200, json={"name": part.get_filename(), "subfolder": "", "type": "input"}
            )
        if path == "/prompt":
            self.graph = json.loads(request.content)["prompt"]
            if self.graph["4"]["class_type"] == "EmptyLatentImage":
                self.size = (
                    self.graph["4"]["inputs"]["width"],
                    self.graph["4"]["inputs"]["height"],
                )
            self.entered.set()
            if not self.release.wait(10):
                raise AssertionError("test did not release transport")
            return httpx.Response(200, json={"prompt_id": "editor-job"})
        if path == "/history/editor-job":
            return httpx.Response(
                200,
                json={
                    "editor-job": {
                        "status": {
                            "completed": True,
                            "status_str": "error" if self.failed else "success",
                            "messages": ["private traceback"],
                        },
                        "outputs": {
                            "7": {
                                "images": [
                                    {
                                        "filename": "preview.png",
                                        "subfolder": "quill",
                                        "type": "output",
                                    }
                                ]
                            }
                        },
                    }
                },
            )
        if path == "/view":
            return httpx.Response(200, content=png(Image.new("RGB", self.size, (50, 100, 150))))
        raise AssertionError(path)


class ComfyEditorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = patch.dict(
            os.environ,
            {"MWQ_DATA_DIR": temp.name, "MWQ_IMAGE_PROVIDER": "comfyui-sdxl"},
            clear=True,
        )
        env.start()
        self.addCleanup(env.stop)
        provider_config.cache_clear()
        self.addCleanup(provider_config.cache_clear)
        self.fake = FakeComfy()
        self.addCleanup(self.fake.release.set)
        transport = httpx.MockTransport(self.fake.respond)
        # Patch the client boundary, leaving factory/configuration and type checks real.
        clients = patch.object(
            ComfyProvider,
            "client",
            lambda _: httpx.AsyncClient(base_url="http://127.0.0.1:8188", transport=transport),
        )
        clients.start()
        self.addCleanup(clients.stop)
        self.store = ProjectStore(Path(temp.name) / "projects.sqlite3")

    def finish(self, client, job_id):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            result = client.get(f"/api/jobs/{job_id}").json()
            if result["status"] not in {"queued", "running"}:
                return result
            time.sleep(0.01)
        self.fail("job did not finish")

    def submit(self, client, target, payload):
        job_id = str(uuid4())
        response = client.post(f"/api/jobs/{job_id}/{target}", json=payload)
        self.assertEqual(response.status_code, 202, response.text)
        return job_id, self.finish(client, job_id)

    def test_ready_queued_background_room_accept_save_export_and_reopen(self):
        with TestClient(app) as client:
            self.assertEqual(client.get("/api/providers").json()[0]["id"], "comfyui-sdxl")
            ready = client.get("/api/providers/readiness").json()
            self.assertTrue(ready["ready"])
            self.assertEqual(self.fake.calls, ["/object_info"])
            self.assertNotIn("8188", json.dumps(ready))
            payload = {"prompt": "Forest cottage exterior", "seed": 42, "baseRevision": 0}
            job_id, job = self.submit(client, "background", payload)
            self.assertEqual(job["status"], "succeeded", job)
            self.assertEqual(client.get("/api/projects").json()["projects"], [])
            self.assertEqual(
                client.post(f"/api/jobs/{job_id}/background", json=payload).status_code, 202
            )
            self.assertEqual(self.fake.calls.count("/prompt"), 1)
            result = job["result"]
            project = document()
            background = BackgroundResult.model_validate_json(json.dumps(result))
            project.layers = [background.layer]
            project.generations = [background.generation]
            self.assertEqual(result["generation"]["providerId"], "comfyui-sdxl")
            details = result["generation"]["parameters"]["comfyui"]
            self.assertEqual(details["width"], 960)
            self.assertEqual(details["checkpoint"], "sd_xl_base_1.0.safetensors")
            self.assertNotIn("url", details)
            bg = self.store.get_asset(project.layers[0].assetHash)
            self.assertEqual(image(bg).size, (960, 640))
            for room in project.rooms:
                _, job = self.submit(
                    client,
                    "room",
                    {"project": project.model_dump(mode="json"), "roomId": str(room.id), "seed": 8},
                )
                self.assertEqual(job["status"], "succeeded", job)
                proposal = BackgroundResult.model_validate_json(json.dumps(job["result"]))
                crop = proposal.generation.parameters["crop"]
                self.assertEqual((crop[2] - crop[0]) % 64, 0)
                self.assertEqual((crop[3] - crop[1]) % 64, 0)
                self.assertEqual(self.fake.upload.size, (1024, 1024))
                self.assertEqual(self.fake.graph["3"]["inputs"]["text"], NEGATIVE)
                full_mask = polygon_mask(room.polygon, (960, 640))
                crop_mask = full_mask.crop(crop)
                _, expected_mask = RoomTransform(*crop_mask.size).prepare(
                    Image.new("RGB", crop_mask.size), crop_mask
                )
                np.testing.assert_array_equal(
                    np.asarray(self.fake.upload.getchannel("A")),
                    255 - np.asarray(expected_mask),
                )
                layer_image = image(self.store.get_asset(proposal.layer.assetHash))
                self.assertEqual(layer_image.size, (960, 640))
                self.assertTrue(np.all(np.asarray(layer_image)[np.asarray(full_mask) == 0] == 0))
                room.renderLayerId = proposal.layer.id
                project.layers.append(proposal.layer)
                project.generations.append(proposal.generation)
            saved = self.store.save(SaveRequest(project=project, expectedRevision=None))
            self.assertEqual(self.store.open(saved.projectId), saved)
            self.assertEqual(self.store.get_asset(project.layers[0].assetHash), bg)
            exported = client.post(
                "/api/export/image",
                json={"project": saved.model_dump(mode="json"), "format": "png"},
            )
            self.assertEqual(
                exported.status_code,
                200,
                exported.text[:100] if exported.status_code != 200 else "",
            )
            self.assertEqual(image(exported.content).size, (960, 640))

    def test_unavailable_safe_failure_no_retry_and_legacy_endpoint_gate(self):
        with TestClient(app) as client:
            self.fake.missing = True
            ready = client.get("/api/providers/readiness").json()
            self.assertFalse(ready["ready"])
            self.assertIn("checkpoint", ready["message"])
            payload = {"prompt": "test", "seed": 1, "baseRevision": 0}
            _, job = self.submit(client, "background", payload)
            self.assertEqual(job["status"], "failed")
            self.assertIn("checkpoint", job["error"])
            self.assertNotIn("/prompt", self.fake.calls)
            self.fake.missing = False
            self.fake.failed = True
            _, job = self.submit(client, "background", payload)
            self.assertEqual(job["status"], "failed")
            self.assertNotIn("private", job["error"])
            self.assertEqual(self.fake.calls.count("/prompt"), 1)
            self.assertEqual(
                client.post("/api/generation/background", json=payload).status_code, 409
            )
            self.assertEqual(client.post("/api/generation/room", json={}).status_code, 409)

    def test_cancelled_comfy_work_cannot_publish_or_interrupt_other_work(self):
        with TestClient(app) as client:
            self.fake.release.clear()
            job_id = str(uuid4())
            client.post(
                f"/api/jobs/{job_id}/background",
                json={"prompt": "test", "seed": 1, "baseRevision": 0},
            )
            try:
                self.assertTrue(self.fake.entered.wait(5))
                response = client.post(f"/api/jobs/{job_id}/cancel", json={})
                self.assertEqual(response.json()["status"], "cancelled")
            finally:
                self.fake.release.set()
        # TestClient shutdown joins the worker, so this assertion includes late completion.
        self.assertEqual(app.state.jobs.get(UUID(job_id)).status, "cancelled")
        self.assertIsNone(app.state.jobs.get(UUID(job_id)).result)
        self.assertNotIn("/interrupt", self.fake.calls)

    def test_server_config_snapshot_and_bad_local_configuration(self):
        first = create_provider()
        with patch.dict(os.environ, {"MWQ_IMAGE_COMFY_CHECKPOINT": "other.safetensors"}):
            self.assertEqual(create_provider().config.checkpoint, first.config.checkpoint)
        self.assertEqual(first.assets, {})
        with self.assertRaises(ValueError):
            load_provider_config(
                {
                    "MWQ_IMAGE_PROVIDER": "comfyui-sdxl",
                    "MWQ_IMAGE_COMFY_URL": "https://remote.example:8188",
                }
            )

    def test_controlled_room_upload_workflow_provenance_and_missing_model(self):
        with patch.dict(
            os.environ, {"MWQ_IMAGE_COMFY_CONTROLNET": "control-lora-canny-rank128.safetensors"}
        ):
            provider_config.cache_clear()
            original = self.fake.respond
            missing = False

            def respond(request):
                response = original(request)
                if request.url.path == "/object_info":
                    info = response.json()
                    info["ControlNetApplyAdvanced"] = {}
                    info["ControlNetLoader"] = {
                        "input": {
                            "required": {
                                "control_net_name": [
                                    [] if missing else ["control-lora-canny-rank128.safetensors"]
                                ]
                            }
                        }
                    }
                    return httpx.Response(200, json=info)
                return response

            with patch.object(
                ComfyProvider,
                "client",
                lambda _: httpx.AsyncClient(
                    base_url="http://127.0.0.1:8188", transport=httpx.MockTransport(respond)
                ),
            ):
                with TestClient(app) as client:
                    self.assertTrue(client.get("/api/providers/readiness").json()["ready"])
                    self.assertIn(
                        "control_image", client.get("/api/providers").json()[0]["capabilities"]
                    )
                    project = document()
                    room = project.rooms[0]
                    _, job = self.submit(
                        client,
                        "room",
                        {
                            "project": project.model_dump(mode="json"),
                            "roomId": str(room.id),
                            "seed": 1,
                        },
                    )
                    self.assertEqual(job["status"], "succeeded", job)
                    result = BackgroundResult.model_validate_json(json.dumps(job["result"]))
                    self.assertEqual(len(result.generation.inputHashes), 3)
                    self.assertEqual(
                        result.generation.parameters["physicalScale"]["cellDistance"], 5
                    )
                    self.assertTrue(result.generation.parameters["layoutConditioning"])
                    self.assertEqual(self.fake.calls.count("/upload/image"), 2)
                    # ControlNet conditioning feeds inpaint conditioning, which feeds sampling.
                    inpaint = self.fake.graph["4"]
                    self.assertEqual(inpaint["class_type"], "InpaintModelConditioning")
                    self.assertEqual(inpaint["inputs"]["positive"], ["11", 0])
                    self.assertEqual(inpaint["inputs"]["negative"], ["11", 1])
                    self.assertEqual(self.fake.graph["5"]["inputs"]["positive"], ["4", 0])
                    self.assertEqual(self.fake.graph["5"]["inputs"]["negative"], ["4", 1])
                    self.assertEqual(
                        result.generation.parameters["comfyui"]["workflowVersion"],
                        "comfy-sdxl-layout-v2",
                    )
                    self.assertEqual(self.fake.graph["11"]["inputs"]["strength"], 1.0)
                    self.assertEqual(
                        self.fake.graph["10"]["inputs"]["image"][:14], "quill-control-"
                    )
                    self.assertIn("each grid cell is 5 ft", self.fake.graph["2"]["inputs"]["text"])
                    self.assertEqual(self.fake.upload.size, (1024, 1024))
                    room.renderLayerId = result.layer.id
                    project.layers = [result.layer]
                    project.generations = [result.generation]
                    saved = self.store.save(SaveRequest(project=project, expectedRevision=None))
                    self.assertEqual(self.store.open(saved.projectId), saved)
                    # Persisted full-map control is distinct from the source and mask.
                    guide = image(self.store.get_asset(result.generation.inputHashes[2]))
                    self.assertEqual(guide.size, (960, 640))
                    self.assertEqual(guide.getpixel((80, 560)), (255, 255, 255, 255))
                    missing = True
                    self.assertFalse(client.get("/api/providers/readiness").json()["ready"])
                    _, failed = self.submit(
                        client,
                        "room",
                        {
                            "project": project.model_dump(mode="json"),
                            "roomId": str(room.id),
                            "seed": 2,
                        },
                    )
                    self.assertEqual(failed["status"], "failed")
                    self.assertEqual(self.fake.calls.count("/prompt"), 1)
