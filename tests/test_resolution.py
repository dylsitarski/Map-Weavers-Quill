"""Resolution compatibility, native masks, protected composition and persistence."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image
from quill.backgrounds import BackgroundRequest, generate_background
from quill.exports import ExportRequest, composite_artwork, export_image
from quill.models import Point
from quill.projects import ProjectStore, SaveRequest, validate_project
from quill.raster import SDXL_SIZE, context_crop, image, masked_layer, png, polygon_mask
from quill.room_images import RoomImageRequest, generate_room
from test_projects import document


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = patch.dict(os.environ, {"MWQ_DATA_DIR": temp.name})
        env.start()
        self.addCleanup(env.stop)
        self.store = ProjectStore(Path(temp.name) / "projects.sqlite3")
        self.project = document()
        background = generate_background(BackgroundRequest(prompt="test", seed=1, baseRevision=0))
        self.project.layers = [background.layer]

    def high_background(self):
        # One-pixel alternating columns prove export does not downsample detail.
        pixels = np.zeros((640, 960, 3), dtype=np.uint8)
        pixels[:, ::2] = 255
        data = png(Image.fromarray(pixels))
        self.project.layers[0].assetHash = self.store.put_asset(data)
        return data

    def test_native_corner_masks_and_aligned_edge_crops(self):
        for x, y in ((0, 0), (1190, 0), (0, 790), (1190, 790)):
            points = [
                Point(x=float(x), y=float(y)),
                Point(x=float(x + 10), y=float(y)),
                Point(x=float(x + 10), y=float(y + 10)),
                Point(x=float(x), y=float(y + 10)),
            ]
            mask = polygon_mask(points, SDXL_SIZE)
            box = mask.getbbox()
            self.assertEqual(
                box, (int(x * 0.8), int((790 - y) * 0.8), int((x + 10) * 0.8), int((800 - y) * 0.8))
            )
            crop = context_crop(mask, margin=16, alignment=64)
            self.assertEqual((crop[2] - crop[0]) % 64, 0)
            self.assertEqual((crop[3] - crop[1]) % 64, 0)
            self.assertTrue(crop[0] <= box[0] < box[2] <= crop[2] <= 960)
            self.assertTrue(crop[1] <= box[1] < box[3] <= crop[3] <= 640)
            # Paste the crop back at its origin: no scale, flip or translation drift.
            restored = Image.new("L", SDXL_SIZE)
            restored.paste(mask.crop(crop), crop[:2])
            self.assertEqual(restored.tobytes(), mask.tobytes())

    def test_high_resolution_detail_save_open_and_lossless_exports(self):
        data = self.high_background()
        original_hash = self.project.layers[0].assetHash
        saved = self.store.save(SaveRequest(project=self.project, expectedRevision=None))
        reopened = self.store.open(saved.projectId)
        self.assertEqual(self.store.get_asset(original_hash), data)
        for format in ("png", "webp"):
            output = image(export_image(ExportRequest(project=reopened, format=format)))
            self.assertEqual(output.size, SDXL_SIZE)
            self.assertEqual(output.tobytes(), image(data).tobytes())
        reopened.layers[0].visible = False
        self.assertEqual(composite_artwork(reopened, self.store).size, SDXL_SIZE)
        self.assertEqual(
            composite_artwork(reopened, self.store).getpixel((0, 0)), (233, 226, 206, 255)
        )
        with self.assertRaisesRegex(ValueError, "discard"):
            composite_artwork(reopened, self.store, size=(480, 320))

    def test_mixed_resolution_room_cannot_bleed_and_originals_survive(self):
        room = self.project.rooms[0]
        # Deliberately off-grid slanted polygon tests interpolation at boundaries.
        room.polygon = [Point(x=101.0, y=101.0), Point(x=299.0, y=111.0), Point(x=251.0, y=299.0)]
        self.project.walls = []
        self.project.doors = []
        self.project = validate_project(self.project, derive_missing=True)
        room = self.project.rooms[0]
        result = generate_room(RoomImageRequest(project=self.project, roomId=room.id, seed=1))
        room.renderLayerId = result.layer.id
        self.project.layers.append(result.layer)
        old_data = self.store.get_asset(result.layer.assetHash)
        self.high_background()
        before = image(self.store.get_asset(self.project.layers[0].assetHash))
        after = composite_artwork(self.project, self.store)
        outside = np.asarray(polygon_mask(room.polygon, SDXL_SIZE)) == 0
        np.testing.assert_array_equal(np.asarray(after)[outside], np.asarray(before)[outside])
        self.assertEqual(self.store.get_asset(result.layer.assetHash), old_data)
        saved = self.store.save(SaveRequest(project=self.project, expectedRevision=None))
        self.assertEqual(self.store.open(saved.projectId), saved)

    def test_high_resolution_room_crop_and_own_resolution_validation(self):
        self.high_background()
        room = self.project.rooms[0]
        result = generate_room(RoomImageRequest(project=self.project, roomId=room.id, seed=2))
        self.assertEqual(result.generation.parameters["crop"], [64, 384, 256, 576])
        self.assertEqual(result.generation.parameters["width"], 960)
        overlay = image(self.store.get_asset(result.layer.assetHash))
        self.assertEqual(overlay.size, SDXL_SIZE)
        mask = polygon_mask(room.polygon, SDXL_SIZE)
        self.assertTrue(np.all(np.asarray(overlay)[np.asarray(mask) == 0] == 0))
        room.renderLayerId = result.layer.id
        self.project.layers.append(result.layer)
        self.project.generations.append(result.generation)
        saved = self.store.save(SaveRequest(project=self.project, expectedRevision=None))
        self.assertEqual(self.store.open(saved.projectId), saved)
        invalid = saved.model_copy(deep=True)
        invalid.layers[-1].assetHash = self.store.put_asset(
            png(Image.new("RGBA", SDXL_SIZE, "red"))
        )
        with self.assertRaisesRegex(ValueError, "outside"):
            self.store.save(SaveRequest(project=invalid, expectedRevision=saved.revision))
        self.assertEqual(self.store.open(saved.projectId), saved)

    def test_unsupported_shapes_and_mask_sizes_rejected(self):
        for size in ((1024, 1024), (960, 320), (1920, 1280)):
            with self.assertRaises(ValueError):
                self.store.put_asset(png(Image.new("RGB", size)))
        with self.assertRaises(ValueError):
            masked_layer(Image.new("RGBA", (480, 320)), Image.new("L", SDXL_SIZE))
        with self.assertRaises(ValueError):
            context_crop(Image.new("L", SDXL_SIZE))
