import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image
from quill.main import app
from quill.models import Point
from quill.projects import ProjectStore, SaveRequest
from quill.providers import MockProvider
from quill.raster import image, png, polygon_mask
from quill.room_images import RoomImageRequest, generate_room
from test_projects import document


class RoomImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, {"MWQ_DATA_DIR": self.temp.name})
        env.start()
        self.addCleanup(env.stop)
        self.store = ProjectStore(Path(self.temp.name) / "projects.sqlite3")
        self.project = document()

    def test_top_left_mapping_concavity_and_boundary_pixel_centers(self):
        mask = polygon_mask(
            [
                Point(x=0.0, y=800.0),
                Point(x=10.0, y=800.0),
                Point(x=10.0, y=790.0),
                Point(x=5.0, y=790.0),
                Point(x=5.0, y=795.0),
                Point(x=0.0, y=795.0),
            ]
        )
        self.assertEqual(mask.getbbox(), (0, 0, 4, 4))
        self.assertEqual(mask.getpixel((0, 0)), 255)
        self.assertEqual(mask.getpixel((0, 3)), 0)
        self.assertEqual(mask.getpixel((3, 3)), 255)
        self.assertEqual(mask.getpixel((0, 319)), 0)
        triangle = polygon_mask([Point(x=0.0, y=0.0), Point(x=5.0, y=0.0), Point(x=0.0, y=5.0)])
        self.assertEqual(triangle.getpixel((0, 319)), 255)
        self.assertEqual(triangle.getpixel((1, 318)), 0)

    def test_untrusted_provider_output_cannot_change_outside_room_mask(self):
        async def paint_everything(provider, request):
            return provider._result(
                Image.new("RGB", (request.width, request.height), "#ff0000"), request
            )

        target = self.project.rooms[0]
        other_room = self.project.rooms[1]
        other = generate_room(RoomImageRequest(project=self.project, roomId=other_room.id, seed=3))
        self.project = self.project.model_copy(
            update={
                "rooms": [target, other_room.model_copy(update={"renderLayerId": other.layer.id})],
                "layers": [other.layer],
                "generations": [other.generation],
            }
        )
        with patch.object(MockProvider, "inpaint", paint_everything):
            result = generate_room(RoomImageRequest(project=self.project, roomId=target.id, seed=0))
        before = image(self.store.get_asset(result.generation.inputHashes[0]))
        overlay = image(self.store.get_asset(result.layer.assetHash))
        after = Image.alpha_composite(before, overlay)
        mask = np.asarray(polygon_mask(target.polygon)) != 0
        np.testing.assert_array_equal(np.asarray(after)[~mask], np.asarray(before)[~mask])
        self.assertTrue(np.any(np.asarray(after)[mask] != np.asarray(before)[mask]))
        self.assertTrue(np.all(np.asarray(overlay)[~mask] == 0))
        self.assertEqual(result.generation.parameters["crop"], [32, 192, 128, 288])

    def test_binding_provenance_and_pixels_survive_save_open(self):
        target = self.project.rooms[0]
        result = generate_room(RoomImageRequest(project=self.project, roomId=target.id, seed=0))
        project = self.project.model_copy(
            update={
                "rooms": [
                    target.model_copy(update={"renderLayerId": result.layer.id}),
                    *self.project.rooms[1:],
                ],
                "layers": [result.layer],
                "generations": [result.generation],
            }
        )
        saved = self.store.save(SaveRequest(project=project, expectedRevision=None))
        self.assertEqual(self.store.open(saved.projectId), saved)
        self.assertEqual(saved.doors, self.project.doors)
        self.assertEqual(saved.rooms[0].polygon, target.polygon)
        # A structurally valid PNG painted outside the polygon must still be rejected.
        invalid_hash = self.store.put_asset(png(Image.new("RGBA", (480, 320), "#ff0000")))
        invalid = saved.model_copy(
            update={"layers": [result.layer.model_copy(update={"assetHash": invalid_hash})]}
        )
        with self.assertRaisesRegex(ValueError, "outside"):
            self.store.save(SaveRequest(project=invalid, expectedRevision=1))
        self.assertEqual(self.store.open(saved.projectId), saved)

    def test_room_binding_and_api_reject_invalid_proposals(self):
        target = self.project.rooms[0]
        request = RoomImageRequest(project=self.project, roomId=target.id, seed=0)
        with TestClient(app) as client:
            response = client.post("/api/generation/room", json=request.model_dump(mode="json"))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(
                response.json()["layer"]["metadata"]["quill.render"]["roomId"], str(target.id)
            )
            payload = request.model_dump(mode="json")
            payload["roomId"] = str(self.project.projectId)
            self.assertEqual(client.post("/api/generation/room", json=payload).status_code, 422)
            self.assertEqual(
                client.post(
                    "/api/generation/room",
                    json=request.model_dump(mode="json"),
                    headers={"Origin": "https://evil.example"},
                ).status_code,
                403,
            )
