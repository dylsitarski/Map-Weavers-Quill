"""Aspect-preserving working resolution and non-destructive context selection."""

import unittest
from uuid import uuid4

import numpy as np
from PIL import Image
from quill.models import Bounds, GenerationRecord, Point, RasterLayer
from quill.sdxl_authoring import NEGATIVE, RoomTransform, clean_context, prompt_text
from test_projects import document


class SdxlAuthoringTests(unittest.TestCase):
    def test_transform_preserves_axes_aspect_and_protected_padding(self):
        for width, height in ((64, 64), (192, 320), (960, 64), (64, 640), (319, 193)):
            with self.subTest(size=(width, height)):
                # Smooth two-axis gradient detects stretching, flipping and misplaced padding.
                pixels = np.zeros((height, width, 3), dtype=np.uint8)
                pixels[:, :, 0] = np.linspace(0, 255, width).astype(np.uint8)[None, :]
                pixels[:, :, 1] = np.linspace(0, 255, height).astype(np.uint8)[:, None]
                source = Image.fromarray(pixels)
                mask = Image.new("L", source.size)
                mask.paste(255, (0, 0, width // 2, height // 2))
                transform = RoomTransform(width, height)
                work, work_mask = transform.prepare(source, mask)
                self.assertEqual(work.size, (1024, 1024))
                self.assertEqual(set(np.unique(work_mask)), {0, 255})
                restored = transform.restore(work)
                self.assertEqual(restored.size, source.size)
                self.assertLessEqual(np.abs(np.asarray(restored).astype(int) - pixels).max(), 2)
                left, top = transform.offset
                # At a protected padding corner, the mask stays black.
                if left or top:
                    self.assertEqual(work_mask.getpixel((0, 0)), 0)
                expected = (
                    left * 1024 / transform.side,
                    top * 1024 / transform.side,
                    (left + width // 2) * 1024 / transform.side,
                    (top + height // 2) * 1024 / transform.side,
                )
                for actual, desired in zip(work_mask.getbbox(), expected, strict=True):
                    self.assertLessEqual(abs(actual - desired), 1)
        with self.assertRaises(ValueError):
            RoomTransform(64, 64).restore(Image.new("RGB", (64, 64)))

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
        style = {
            "environment": "Cottage interior",
            "renderStyle": "Ink and watercolor",
            "palette": "warm brown",
        }
        room = prompt_text("Kitchen with a hearth", style, room=True)
        exterior = prompt_text("Forest path to a cottage", style, room=False)
        self.assertTrue(room.startswith("Orthographic top-down"))
        self.assertIn("roof removed", room)
        self.assertIn("building roofs", exterior)
        self.assertIn("Kitchen with a hearth", room)
        self.assertIn("Cottage interior", room)
        self.assertNotIn("{", room)
        self.assertIn("isometric", NEGATIVE)
        self.assertIn("checkerboard", NEGATIVE)
