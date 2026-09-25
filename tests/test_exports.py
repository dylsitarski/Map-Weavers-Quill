import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image
from quill.backgrounds import BackgroundRequest, generate_background
from quill.exports import ExportRequest, composite_artwork, export_image
from quill.main import app
from quill.projects import ProjectStore, SaveRequest
from quill.raster import image, png
from quill.room_images import RoomImageRequest, generate_room
from test_projects import document


class ExportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = patch.dict(os.environ, {"MWQ_DATA_DIR": temp.name})
        env.start()
        self.addCleanup(env.stop)
        self.store = ProjectStore(Path(temp.name) / "projects.sqlite3")
        self.project = document()
        result = generate_background(BackgroundRequest(prompt="stone", seed=1, baseRevision=0))
        self.project = self.project.model_copy(update={"layers": [result.layer]})

    def test_composition_order_opacity_visibility_and_ties(self):
        base = self.project.layers[0]
        red = self.store.put_asset(png(Image.new("RGBA", (480, 320), "red")))
        blue = self.store.put_asset(png(Image.new("RGBA", (480, 320), "blue")))
        a = base.model_copy(update={"assetHash": red, "zIndex": 1})
        b = base.model_copy(update={"assetHash": blue, "zIndex": 2, "opacity": 0.5})
        project = self.project.model_copy(update={"layers": [b, a]})
        self.assertEqual(
            composite_artwork(project, self.store).getpixel((0, 0)), (127, 0, 128, 255)
        )
        b.zIndex = 0
        self.assertEqual(composite_artwork(project, self.store).getpixel((0, 0)), (255, 0, 0, 255))
        a.visible = False
        b.opacity = 0.0
        self.assertEqual(
            composite_artwork(project, self.store).getpixel((0, 0)), (233, 226, 206, 255)
        )

    def test_png_webp_round_trip_save_open_and_no_mutation(self):
        target = self.project.rooms[0]
        result = generate_room(RoomImageRequest(project=self.project, roomId=target.id, seed=2))
        target.renderLayerId = result.layer.id
        self.project.layers.append(result.layer)
        before = self.project.model_dump_json()
        png_bytes = export_image(ExportRequest(project=self.project, format="png"))
        webp_bytes = export_image(ExportRequest(project=self.project, format="webp"))
        self.assertTrue(png_bytes.startswith(b"\x89PNG"))
        self.assertEqual(webp_bytes[8:12], b"WEBP")
        self.assertEqual(image(png_bytes).size, (480, 320))
        np.testing.assert_array_equal(np.asarray(image(png_bytes)), np.asarray(image(webp_bytes)))
        self.assertEqual(self.project.model_dump_json(), before)
        self.assertEqual(self.store.list().projects, [])
        saved = self.store.save(SaveRequest(project=self.project, expectedRevision=None))
        reopened = self.store.open(saved.projectId)
        self.assertEqual(export_image(ExportRequest(project=reopened, format="png")), png_bytes)

    def test_api_guards_missing_assets_and_empty_map(self):
        with TestClient(app) as client:
            payload = ExportRequest(project=self.project, format="png").model_dump(mode="json")
            response = client.post("/api/export/image", json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.headers["content-type"], "image/png")
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertIn("attachment", response.headers["content-disposition"])
            self.assertEqual(
                client.post(
                    "/api/export/image", json=payload, headers={"Origin": "https://evil.example"}
                ).status_code,
                403,
            )
            self.assertEqual(client.post("/api/export/image", content="x").status_code, 415)
            self.assertEqual(
                client.post(
                    "/api/export/image",
                    content=b" " * (4 * 1024 * 1024 + 1),
                    headers={"Content-Type": "application/json"},
                ).status_code,
                413,
            )
            payload["format"] = "jpeg"
            self.assertEqual(client.post("/api/export/image", json=payload).status_code, 422)
            payload["format"] = "png"
            payload["project"]["layers"][0]["assetHash"] = "f" * 64
            self.assertEqual(client.post("/api/export/image", json=payload).status_code, 422)
        empty = self.project.model_copy(update={"layers": []})
        self.assertEqual(
            image(export_image(ExportRequest(project=empty, format="png"))).getpixel((0, 0)),
            (233, 226, 206, 255),
        )
