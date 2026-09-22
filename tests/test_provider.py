import unittest
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError
from quill.main import app
from quill.providers import GenerateRequest, InpaintRequest, MockProvider, ProviderFailure


def png(image):
    data = BytesIO()
    image.save(data, format="PNG")
    return data.getvalue()


class ProviderContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.provider = MockProvider()
        self.request = GenerateRequest(
            requestId="test", prompt="stone", width=16, height=16, seed=42
        )

    async def test_health_and_determinism(self):
        self.assertTrue(await self.provider.health())
        self.assertIn("inpainting", self.provider.descriptor().capabilities)
        a = await self.provider.generate(self.request)
        b = await self.provider.generate(self.request)
        self.assertEqual(a, b)
        with Image.open(BytesIO(self.provider.assets[a.assetHash])) as image:
            self.assertEqual(image.size, (16, 16))
            self.assertEqual(image.format, "PNG")

    async def test_mask_and_input_preservation(self):
        original = Image.new("RGB", (16, 16), (12, 34, 56))
        source = self.provider.put(png(original))
        for mask_value in (0, 128, 255):
            mask = self.provider.put(png(Image.new("L", (16, 16), mask_value)))
            request = InpaintRequest(
                **self.request.model_dump(),
                sourceRef=source,
                maskRef=mask,
                maskConvention="white-edit-black-preserve",
            )
            result = await self.provider.inpaint(request)
            generated = await self.provider.generate(self.request)
            with Image.open(BytesIO(self.provider.assets[generated.assetHash])) as pattern:
                expected = Image.composite(pattern, original, Image.new("L", (16, 16), mask_value))
            with Image.open(BytesIO(self.provider.assets[result.assetHash])) as actual:
                self.assertEqual(actual.tobytes(), expected.tobytes())
            self.assertEqual(self.provider.assets[source], png(original))

    async def test_invalid_assets(self):
        source = self.provider.put(b"not an image")
        for key, code in [("absent", "missing_asset"), (source, "invalid_image")]:
            request = InpaintRequest(
                **self.request.model_dump(),
                sourceRef=key,
                maskRef=key,
                maskConvention="white-edit-black-preserve",
            )
            with self.assertRaises(ProviderFailure) as error:
                await self.provider.inpaint(request)
            self.assertEqual(error.exception.error.code, code)

    def test_dimension_limits(self):
        with self.assertRaises(ValidationError):
            GenerateRequest(requestId="bad", prompt="", width=513, height=1)


class ApiTests(unittest.TestCase):
    def test_health_and_provider_discovery(self):
        with TestClient(app) as client:
            self.assertEqual(client.get("/health").json(), {"status": "ok"})
            response = client.get("/api/providers")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()[0]["local"])
            self.assertEqual(client.post("/api/projects").status_code, 404)
