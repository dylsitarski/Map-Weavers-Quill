"""ComfyUI protocol regressions with synthetic PNGs; no server, weights or GPU."""

import argparse
import json
import tempfile
import unittest
from email.parser import BytesParser
from email.policy import default
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import httpx
from PIL import Image
from quill.comfyui import ComfyConfig, ComfyProvider, workflow
from quill.providers import GenerateRequest, InpaintRequest, ProviderFailure


def png(color, size=(1024, 1024), mode="RGB"):
    stream = BytesIO()
    Image.new(mode, size, color).save(stream, format="PNG")
    return stream.getvalue()


class ComfyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.request = GenerateRequest(
            requestId="test", prompt="stone floor", width=1024, height=1024, seed=42
        )
        self.calls = []
        self.uploaded = None
        self.graph = None
        self.history_count = 0
        self.output = png((100, 120, 140))
        self.provider = ComfyProvider(ComfyConfig(), transport=httpx.MockTransport(self.respond))

    def respond(self, request):
        self.calls.append(request)
        path = request.url.path
        if path == "/object_info":
            graph = workflow(ComfyConfig(), self.request, "test.png")
            info = {node["class_type"]: {} for node in graph.values()}
            info["EmptyLatentImage"] = {}
            info["CheckpointLoaderSimple"] = {
                "input": {"required": {"ckpt_name": [["sd_xl_base_1.0.safetensors"]]}}
            }
            return httpx.Response(200, json=info)
        if path == "/upload/image":
            message = BytesParser(policy=default).parsebytes(
                f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode()
                + request.content
            )
            image_part = next(p for p in message.iter_parts() if p.get_filename())
            self.uploaded = image_part.get_payload(decode=True)
            return httpx.Response(
                200, json={"name": image_part.get_filename(), "subfolder": "", "type": "input"}
            )
        if path == "/prompt":
            self.graph = json.loads(request.content)["prompt"]
            return httpx.Response(200, json={"prompt_id": "test-job"})
        if path == "/history/test-job":
            self.history_count += 1
            return httpx.Response(
                200,
                json={
                    "test-job": {
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": {
                            "7": {
                                "images": [
                                    {
                                        "filename": "preview_001.png",
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
            return httpx.Response(200, content=self.output)
        raise AssertionError(path)

    async def test_smoke_command_preserves_full_resolution_and_records_metadata(self):
        from scripts.comfy_smoke import run

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "smoke.png"
            args = argparse.Namespace(
                generate=True,
                output=output,
                source=None,
                mask=None,
                prompt="synthetic room",
                negative_prompt="text",
                width=1024,
                height=1024,
                seed=42,
            )
            with (
                patch("scripts.comfy_smoke.ComfyProvider", return_value=self.provider),
                patch("builtins.print"),
            ):
                await run(args)
                with self.assertRaises(ValueError):
                    await run(args)
            with Image.open(output) as image:
                self.assertEqual(image.size, (1024, 1024))
            metadata = json.loads(output.with_suffix(".json").read_text())
            self.assertEqual(metadata["prompt"], "synthetic room")
            self.assertEqual(metadata["providerId"], "comfyui-sdxl")
            self.assertEqual(metadata["inputHashes"], [])
            self.assertEqual(len(metadata["outputHash"]), 64)
            self.assertEqual(sum(r.url.path == "/prompt" for r in self.calls), 1)

    async def test_readiness_without_generation(self):
        self.assertTrue(await self.provider.health())
        self.assertEqual([r.url.path for r in self.calls], ["/object_info"])
        self.assertEqual(self.provider.assets, {})

    async def test_full_resolution_generation_and_graph(self):
        result = await self.provider.generate(self.request)
        self.assertEqual((result.width, result.height), (1024, 1024))
        with Image.open(BytesIO(self.provider.assets[result.assetHash])) as image:
            self.assertEqual(image.size, (1024, 1024))
        self.assertEqual(self.graph["2"]["inputs"]["text"], "stone floor")
        self.assertEqual(self.graph["5"]["inputs"]["seed"], 42)
        self.assertEqual(self.graph["4"]["inputs"]["batch_size"], 1)
        self.assertEqual(self.provider.last_run["workflowVersion"], "comfy-sdxl-v1")
        self.assertEqual(sum(r.url.path == "/prompt" for r in self.calls), 1)

    async def test_mask_orientation_and_exact_outside_preservation(self):
        source = self.provider.put(png((10, 20, 30)))
        mask_image = Image.new("L", (1024, 1024), 0)
        mask_image.paste(255, (0, 0, 512, 512))
        stream = BytesIO()
        mask_image.save(stream, format="PNG")
        mask = self.provider.put(stream.getvalue())
        result = await self.provider.inpaint(
            InpaintRequest(
                **self.request.model_dump(),
                sourceRef=source,
                maskRef=mask,
                maskConvention="white-edit-black-preserve",
            )
        )
        with Image.open(BytesIO(self.uploaded)) as uploaded:
            self.assertEqual(uploaded.getpixel((0, 0))[3], 0)
            self.assertEqual(uploaded.getpixel((1023, 1023))[3], 255)
        with Image.open(BytesIO(self.provider.assets[result.assetHash])) as image:
            expected = Image.composite(
                Image.new("RGB", image.size, (100, 120, 140)),
                Image.new("RGB", image.size, (10, 20, 30)),
                mask_image,
            )
            self.assertEqual(image.tobytes(), expected.tobytes())
        self.assertEqual(self.graph["4"]["inputs"]["grow_mask_by"], 0)
        self.assertEqual(self.provider.assets[source], png((10, 20, 30)))

    async def test_invalid_request_and_assets_never_contact_server(self):
        for update in (
            {"width": 480},
            {"height": 2048},
            {"seed": -1},
            {"referenceImages": ["x"]},
            {"parameters": {"steps": 10.0}},
        ):
            with self.assertRaises(ProviderFailure):
                await self.provider.generate(self.request.model_copy(update=update))
        for data in (b"broken", png((0, 0, 0), (64, 64))):
            key = self.provider.put(data)
            with self.assertRaises(ProviderFailure):
                await self.provider.inpaint(
                    InpaintRequest(
                        **self.request.model_dump(),
                        sourceRef=key,
                        maskRef=key,
                        maskConvention="white-edit-black-preserve",
                    )
                )
        self.assertEqual(self.calls, [])

    async def test_wrong_dimensions_or_invalid_png_cannot_publish(self):
        for data in (b"invalid", png((0, 0, 0), (64, 64))):
            self.output = data
            with self.assertRaises(ProviderFailure) as error:
                await self.provider.generate(self.request)
            self.assertEqual(error.exception.error.code, "invalid_output")
            self.assertEqual(self.provider.assets, {})
            self.assertEqual(self.provider.last_run, {})

    async def test_error_mapping_no_leak_or_automatic_resubmission(self):
        for fault, code in (
            ("timeout", "timeout"),
            ("connection", "unavailable"),
            ("status", "invalid_request"),
            ("json", "invalid_output"),
        ):
            attempts = []

            def respond(request):
                attempts.append(request)
                if fault == "timeout":
                    raise httpx.ReadTimeout("private detail")
                if fault == "connection":
                    raise httpx.ConnectError("private detail")
                if fault == "status":
                    return httpx.Response(400, text="private detail")
                return httpx.Response(200, text="private detail")

            provider = ComfyProvider(ComfyConfig(), transport=httpx.MockTransport(respond))
            with self.assertRaises(ProviderFailure) as error:
                await provider.generate(self.request)
            self.assertEqual(error.exception.error.code, code)
            self.assertNotIn("private", str(error.exception))
            self.assertEqual(len(attempts), 1)

    async def test_execution_failure_and_untrusted_output_reference(self):
        original = self.respond
        for record in (
            {"status": {"status_str": "error", "messages": ["private traceback"]}},
            {
                "status": {"completed": True},
                "outputs": {
                    "7": {
                        "images": [
                            {"filename": "../private.png", "subfolder": "quill", "type": "output"}
                        ]
                    }
                },
            },
        ):

            def respond(request):
                if request.url.path.startswith("/history/"):
                    return httpx.Response(200, json={"test-job": record})
                return original(request)

            provider = ComfyProvider(ComfyConfig(), transport=httpx.MockTransport(respond))
            with self.assertRaises(ProviderFailure) as error:
                await provider.generate(self.request)
            self.assertNotIn("private", str(error.exception))
            self.assertEqual(provider.assets, {})
        self.assertFalse(any(r.url.path == "/view" for r in self.calls))

    async def test_pending_poll_and_response_limit(self):
        original = self.respond
        polled = 0

        def pending(request):
            nonlocal polled
            if request.url.path.startswith("/history/"):
                polled += 1
                if polled == 1:
                    return httpx.Response(200, json={})
            return original(request)

        provider = ComfyProvider(ComfyConfig(), transport=httpx.MockTransport(pending))
        with patch("quill.comfyui.asyncio.sleep"):
            await provider.generate(self.request)
        self.assertEqual(polled, 2)
        self.assertEqual(sum(r.url.path == "/prompt" for r in self.calls), 1)
        self.output = b"x" * 2048
        with patch("quill.comfyui.MAX_RESPONSE", 1024), self.assertRaises(ProviderFailure) as error:
            await self.provider.generate(self.request)
        self.assertEqual(error.exception.error.code, "invalid_output")

    async def test_overall_deadline_bounds_pending_job(self):
        original = self.respond

        def pending(request):
            if request.url.path.startswith("/history/"):
                return httpx.Response(200, json={})
            return original(request)

        provider = ComfyProvider(ComfyConfig(timeout=1), transport=httpx.MockTransport(pending))
        with self.assertRaises(ProviderFailure) as error:
            await provider.generate(self.request)
        self.assertEqual(error.exception.error.code, "timeout")
        self.assertEqual(sum(r.url.path == "/prompt" for r in self.calls), 1)
        self.assertEqual(provider.assets, {})

    async def test_missing_checkpoint_and_no_global_interrupt(self):
        provider = ComfyProvider(
            ComfyConfig(checkpoint="missing.safetensors"),
            transport=httpx.MockTransport(self.respond),
        )
        self.assertFalse(await provider.health())
        with self.assertRaises(ProviderFailure):
            await provider.cancel("some-job")
        self.assertFalse(any(r.url.path == "/interrupt" for r in self.calls))

    def test_loopback_configuration_and_fixed_workflow(self):
        for url in (
            "https://remote.example:8188",
            "http://127.0.0.1:8188/private",
            "http://user:secret@127.0.0.1:8188",
            "http://127.0.0.1:8188?key=secret",
            "http://127.0.0.1:bad",
            "http://127.0.0.1",
        ):
            with self.assertRaises(ValueError):
                ComfyConfig(url=url)
        for checkpoint in ("../model.safetensors", "model.ckpt", "/model.safetensors"):
            with self.assertRaises(ValueError):
                ComfyConfig(checkpoint=checkpoint)
        for timeout in (0, float("nan"), float("inf"), 1801):
            with self.assertRaises(ValueError):
                ComfyConfig(timeout=timeout)

    async def test_layout_extension_rejects_unknown_fields_and_missing_assets_before_upload(self):
        provider = ComfyProvider(
            ComfyConfig(controlnet="control.safetensors"),
            transport=httpx.MockTransport(self.respond),
        )
        source = provider.put(png((10, 20, 30)))
        mask = provider.put(png(255, mode="L"))
        for extension in (
            {"quill.layout": {"controlRef": "missing"}},
            {"quill.layout": {"controlRef": source, "workflow": "untrusted"}},
            {"other.layout": {"controlRef": source}},
        ):
            with self.assertRaises(ProviderFailure):
                await provider.inpaint(
                    InpaintRequest(
                        **self.request.model_dump(exclude={"extensions"}),
                        sourceRef=source,
                        maskRef=mask,
                        maskConvention="white-edit-black-preserve",
                        extensions=extension,
                    )
                )
        self.assertEqual(self.calls, [])
        for name in ("../control.safetensors", "control.ckpt", "/control.safetensors"):
            with self.assertRaises(ValueError):
                ComfyConfig(controlnet=name)
