"""Aspect-preserving working resolution and non-destructive context selection."""

import unittest
from uuid import uuid4

import numpy as np
from PIL import Image
from quill.models import Bounds, GenerationRecord, Point, RasterLayer
from quill.sdxl_authoring import (
    NEGATIVE,
    RoomWindow,
    background_scale,
    clean_context,
    prompt_text,
)
from test_projects import document


class SdxlAuthoringTests(unittest.TestCase):
    def test_window_has_fixed_physical_size_real_context_and_exact_return(self):
        # Smooth two-axis gradient detects stretching, flipping and misplaced crops.
        pixels = np.zeros((640, 960, 3), dtype=np.uint8)
        pixels[:, :, 0] = np.linspace(0, 255, 960).astype(np.uint8)[None, :]
        pixels[:, :, 1] = np.linspace(0, 255, 640).astype(np.uint8)[:, None]
        source = Image.fromarray(pixels)
        for box in ((400, 300, 480, 380), (0, 0, 64, 64), (900, 600, 960, 640), (100, 50, 300, 90)):
            with self.subTest(room=box):
                mask = Image.new("L", source.size)
                mask.paste(255, box)
                window = RoomWindow.around(mask, 320, 16)
                # Same window, so the same working scale, for rooms of different sizes.
                self.assertEqual((window.side, window.scale), (320, 3.2))
                left, top, right, bottom = window.crop
                self.assertEqual((right - left, bottom - top), (320, 320))  # No padding.
                self.assertTrue(left <= box[0] and top <= box[1])
                self.assertTrue(right >= box[2] and bottom >= box[3])
                work, work_mask = window.prepare(source, mask)
                self.assertEqual((work.size, work_mask.size), ((1024, 1024), (1024, 1024)))
                self.assertEqual(set(np.unique(work_mask)), {0, 255})
                expected = [
                    round(v) for v in (*window.to_working(*box[:2]), *window.to_working(*box[2:]))
                ]
                for actual, desired in zip(work_mask.getbbox(), expected, strict=True):
                    self.assertLessEqual(abs(actual - desired), 1)
                restored = window.restore(work)
                self.assertEqual(restored.size, (320, 320))
                original = np.asarray(source.crop(window.crop)).astype(int)
                self.assertLessEqual(np.abs(np.asarray(restored).astype(int) - original).max(), 2)
        with self.assertRaises(ValueError):
            window.restore(Image.new("RGB", (64, 64)))
        with self.assertRaises(ValueError):
            RoomWindow.around(Image.new("L", (960, 640)), 320, 16)

    def test_window_shrinks_for_tiny_rooms_down_to_the_minimum(self):
        mask = Image.new("L", (960, 640))
        mask.paste(255, (400, 300, 440, 340))  # A 5-ft room: 40 raster px.
        window = RoomWindow.around(mask, 320, 16, 160)
        self.assertEqual(window.side, 160)  # 20 ft, so the room spans a quarter.
        mask = Image.new("L", (960, 640))
        mask.paste(255, (400, 300, 410, 310))  # Smaller still: the 20-ft minimum holds.
        self.assertEqual(RoomWindow.around(mask, 320, 16, 160).side, 160)
        mask = Image.new("L", (960, 640))
        mask.paste(255, (400, 300, 460, 340))  # 7.5 ft: 4 × 60 px.
        self.assertEqual(RoomWindow.around(mask, 320, 16, 160).side, 240)
        mask = Image.new("L", (960, 640))
        mask.paste(255, (400, 300, 480, 380))  # 10 ft and larger: the full window.
        self.assertEqual(RoomWindow.around(mask, 320, 16, 160).side, 320)
        self.assertEqual(RoomWindow.around(mask, 320, 16).side, 320)

    def test_window_grows_for_large_rooms_and_pads_only_past_the_map(self):
        source = Image.new("RGB", (960, 640), (10, 200, 30))
        mask = Image.new("L", source.size)
        mask.paste(255, (100, 100, 600, 300))
        window = RoomWindow.around(mask, 320, 16)
        self.assertEqual(window.side, 532)  # Room width plus margins.
        self.assertEqual(window.crop[2] - window.crop[0], 532)
        mask = Image.new("L", source.size)
        mask.paste(255, (10, 4, 950, 636))  # Wider than the map is tall.
        window = RoomWindow.around(mask, 320, 16)
        self.assertEqual(window.side, 972)
        self.assertEqual(window.crop, (0, 0, 960, 640))
        work, work_mask = window.prepare(source, mask)
        # Padding repeats edge colors and stays protected by the mask.
        self.assertEqual(work.getpixel((0, 0)), (10, 200, 30))
        self.assertEqual(work_mask.getpixel((0, 0)), 0)
        self.assertEqual(window.restore(work).size, (960, 640))

    def test_context_excludes_target_and_known_mock_without_mutating_document(self):
        project = document()

        def layer(label, metadata, asset):
            return RasterLayer(
                id=uuid4(),
                kind="raster",
                revision=0,
                label=label,
                metadata={"quill.render": metadata},
                assetHash=asset,
                bounds=Bounds(origin=Point(x=0.0, y=0.0), width=1200.0, height=800.0),
                rotation=0.0,
                zIndex=1,
                opacity=1.0,
                visible=True,
                blendMode="normal",
            )

        target, neighbour = project.rooms
        layers = [
            layer("target", {"role": "room", "roomId": str(target.id)}, "a" * 64),
            layer("old mock", {"role": "background"}, "b" * 64),
            layer("another mock output", {"role": "room", "providerId": "mock"}, "b" * 64),
            layer(
                "neighbour",
                {"role": "room", "roomId": str(neighbour.id), "providerId": "comfyui-sdxl"},
                "d" * 64,
            ),
            layer("unknown", {"role": "background"}, "e" * 64),
        ]
        project.layers = layers
        project.generations = [
            GenerationRecord(
                id=uuid4(),
                kind="generation",
                revision=0,
                label="legacy",
                metadata={},
                providerId="mock",
                capability="text_to_image",
                prompt="",
                inputHashes=[],
                outputHash="b" * 64,
                parameters={},
                status="succeeded",
                baseRevision=0,
            )
        ]
        original = project.model_dump_json()
        context, excluded = clean_context(project, target.id)
        self.assertEqual(
            [item.visible for item in context.layers], [False, False, False, True, True]
        )
        self.assertEqual(excluded, [str(item.id) for item in layers[:3]])
        self.assertEqual(project.model_dump_json(), original)

    def test_templates_distinguish_exterior_and_interior_and_keep_authored_content(self):
        style = {"renderStyle": "Ink and watercolor", "palette": "warm brown"}
        room = prompt_text("Kitchen with a hearth", style, room=True)
        exterior = prompt_text(
            "Forest path to a cottage", style, room=False, scale=background_scale(960)
        )
        self.assertTrue(room.startswith("Orthographic top-down"))
        self.assertIn("roof removed", room)
        self.assertIn("building roofs", exterior)
        self.assertIn("Kitchen with a hearth", room)
        self.assertIn("renderStyle: Ink and watercolor", room)
        self.assertIn("readable floor surfaces", room)
        self.assertNotIn("floor surfaces", exterior)
        self.assertIn("120 by 80 feet", exterior)
        self.assertIn("one 5-foot square is 40 pixels wide", exterior)
        self.assertNotIn("{", room)
        self.assertIn("isometric", NEGATIVE)
        self.assertIn("checkerboard", NEGATIVE)
