import math
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image
from quill.backgrounds import BackgroundRequest, generate_background
from quill.exports import ExportRequest, composite_artwork, export_image
from quill.main import app
from quill.models import Door
from quill.projects import ProjectStore, validate_project
from quill.raster import image, polygon_mask
from quill.wall_art import (
    DOOR_COLOR,
    DOOR_EDGE,
    GLASS_COLOR,
    _coverage,
    render_wall_art,
    wall_art_settings,
)
from quill.walls import RoomBoundary
from shapely.geometry import Polygon
from test_projects import document

PREVIEW = (2400, 1600)  # Two pixels per native unit keeps the arithmetic exact.


def pixel(rendered: Image.Image, x: float, y: float) -> tuple[int, int, int, int]:
    """Pixel containing native point (x, y); native +y is up, image rows go down."""
    scale = rendered.width / 1200
    return rendered.getpixel((math.floor(x * scale), math.floor((800 - y) * scale)))


class WallArtTests(unittest.TestCase):
    def setUp(self):
        self.project = validate_project(document())
        self.rooms = [RoomBoundary(id=room.id, polygon=room.polygon) for room in self.project.rooms]
        self.shared = next(w for w in self.project.walls if w.start.x == w.end.x == 300)
        self.bottom = next(
            w
            for w in self.project.walls
            if w.start.y == w.end.y == 100 and min(w.start.x, w.end.x) == 100
        )

    def render(self, doors=(), *, thickness=10.0, size=PREVIEW, material="stone"):
        return render_wall_art(
            self.rooms,
            self.project.walls,
            list(doors),
            thickness=thickness,
            material=material,
            size=size,
        )

    def door(self, wall, position, **changes):
        values = {
            "id": uuid4(),
            "kind": "door",
            "revision": 0,
            "label": "Door",
            "metadata": {},
            "wallId": wall.id,
            "position": position,
            "width": 50.0,
            "state": "closed",
            "secret": False,
            "doorType": "door",
        }
        return Door(**(values | changes))

    def along(self, wall, distance, normal=0.0):
        """Native point `distance` along a wall from its start, offset along its left normal."""
        length = math.hypot(wall.end.x - wall.start.x, wall.end.y - wall.start.y)
        ux, uy = (wall.end.x - wall.start.x) / length, (wall.end.y - wall.start.y) / length
        return (
            wall.start.x + ux * distance - uy * normal,
            wall.start.y + uy * distance + ux * normal,
        )

    def test_band_thickness_orientation_and_transparent_surroundings(self):
        rendered = self.render()
        self.assertEqual(rendered.size, PREVIEW)
        # Left wall at x=100 spans x 95..105 for thickness 10.
        for x in (95.25, 100, 104.75):
            self.assertEqual(pixel(rendered, x, 200)[3], 255)
        for x in (94.25, 105.75, 200):
            self.assertEqual(pixel(rendered, x, 200), (0, 0, 0, 0))
        # Bottom wall at native y=100 appears near the bottom of the image.
        self.assertEqual(pixel(rendered, 200, 100)[3], 255)
        self.assertEqual(rendered.getpixel((400, 1400))[3], 255)
        self.assertEqual(rendered.getpixel((400, 200))[3], 0)
        # Outer corners are mitred, not rounded.
        self.assertEqual(pixel(rendered, 95.25, 95.25)[3], 255)
        # Thickness changes the band, not the wall position.
        thick = self.render(thickness=30)
        self.assertEqual(pixel(thick, 86, 200)[3], 255)
        self.assertEqual(pixel(thick, 114, 200)[3], 255)

    def test_rasterization_matches_room_mask_convention(self):
        room = self.project.rooms[0]
        for size in ((480, 320), (960, 640)):
            mask = _coverage(Polygon([(p.x, p.y) for p in room.polygon]), size, (1200.0, 800.0))
            self.assertEqual(mask.tobytes(), polygon_mask(room.polygon, size).tobytes())

    def test_deterministic_and_materials_differ(self):
        self.assertEqual(self.render().tobytes(), self.render().tobytes())
        stone, timber = self.render(), self.render(material="timber")
        self.assertNotEqual(pixel(stone, 100, 200), pixel(timber, 100, 200))
        # Same coverage: material only changes colour.
        np.testing.assert_array_equal(
            np.asarray(stone.getchannel("A")), np.asarray(timber.getchannel("A"))
        )

    def test_closed_locked_and_open_door_rendering(self):
        center = 0.375 * 200
        closed = self.render([self.door(self.shared, 0.375)])
        self.assertEqual(pixel(closed, *self.along(self.shared, center, 0.5))[:3], DOOR_COLOR)
        # The opening is cleared beside the narrower leaf.
        self.assertEqual(pixel(closed, *self.along(self.shared, center, 4.5))[3], 0)
        # Wall continues outside the opening.
        self.assertEqual(pixel(closed, *self.along(self.shared, center + 30))[3], 255)

        locked = self.render([self.door(self.shared, 0.375, state="locked")])
        self.assertEqual(pixel(locked, *self.along(self.shared, center, 0.5))[:3], DOOR_EDGE)

        opened = self.render([self.door(self.shared, 0.375, state="open")])
        self.assertEqual(pixel(opened, *self.along(self.shared, center, 0.5))[3], 0)
        # Leaf swings 90 degrees from the low-end hinge toward the left normal.
        leaf = pixel(opened, *self.along(self.shared, center - 25 + 1.5, 25))
        self.assertEqual(leaf[:3], DOOR_COLOR)
        self.assertEqual(pixel(opened, *self.along(self.shared, center - 25 + 1.5, -25))[3], 0)

    def test_secret_door_is_indistinguishable_from_wall(self):
        secret = self.render([self.door(self.shared, 0.375, secret=True, state="open")])
        self.assertEqual(secret.tobytes(), self.render().tobytes())

    def test_window_keeps_wall_and_shows_glass(self):
        rendered = self.render([self.door(self.shared, 0.375, doorType="window")])
        self.assertEqual(pixel(rendered, *self.along(self.shared, 75, 0.5))[:3], GLASS_COLOR)
        self.assertEqual(pixel(rendered, *self.along(self.shared, 75, 4.5))[3], 255)

    def test_opening_at_wall_end_does_not_notch_perpendicular_wall(self):
        length = math.hypot(
            self.bottom.end.x - self.bottom.start.x, self.bottom.end.y - self.bottom.start.y
        )
        rendered = self.render([self.door(self.bottom, 25 / length)])
        self.assertEqual(pixel(rendered, *self.along(self.bottom, 10, 4.5))[3], 0)
        # The corner shared with the perpendicular wall keeps its full band.
        corner = self.bottom.start
        self.assertEqual(pixel(rendered, corner.x + 0.25, corner.y + 0.25)[3], 255)
        self.assertEqual(pixel(rendered, corner.x - 0.25, corner.y - 0.25)[3], 255)

    def test_export_sizes_and_limits(self):
        self.assertEqual(self.render(size=(480, 320)).size, (480, 320))
        self.assertEqual(self.render(size=(960, 640)).size, (960, 640))
        for thickness in (0.5, 51):
            with self.assertRaisesRegex(ValueError, "thickness"):
                self.render(thickness=thickness)
        with self.assertRaisesRegex(ValueError, "size"):
            self.render(size=(1000, 640))
        empty = render_wall_art(
            [], [], [], thickness=10, material="stone", size=(480, 320)
        ).getextrema()
        self.assertEqual(empty[3], (0, 0))

    def test_settings_default_and_validation(self):
        self.assertEqual(
            wall_art_settings(self.project).model_dump(),
            {
                "visible": True,
                "material": "stone",
            },
        )
        for bad in (
            {"visible": "yes", "material": "stone"},
            {"visible": True, "material": "glass"},
            {"visible": True},
            "stone",
        ):
            project = self.project.model_copy(update={"settings": {"quill.wallArt": bad}})
            with self.assertRaisesRegex(ValueError, "Wall art"):
                validate_project(project)
        for thickness in (0.5, 60.0):
            project = self.project.model_copy(deep=True)
            project.map.style.wallThicknessPx = thickness
            with self.assertRaisesRegex(ValueError, "thickness"):
                validate_project(project)


class WallArtExportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = patch.dict(os.environ, {"MWQ_DATA_DIR": temp.name})
        env.start()
        self.addCleanup(env.stop)
        self.store = ProjectStore(Path(temp.name) / "projects.sqlite3")
        result = generate_background(BackgroundRequest(prompt="stone", seed=1, baseRevision=0))
        self.project = document().model_copy(update={"layers": [result.layer]})

    def test_export_draws_walls_above_artwork_but_ai_context_never_does(self):
        exported = image(export_image(ExportRequest(project=self.project, format="png")))
        context = composite_artwork(validate_project(self.project), self.store)
        self.assertEqual(exported.size, context.size)
        # Left wall at native x=100, y=200 in the 480 x 320 profile.
        on_wall = (40, 240)
        self.assertNotEqual(exported.getpixel(on_wall), context.getpixel(on_wall))
        self.assertEqual(exported.getpixel(on_wall)[3], 255)
        # Away from walls, export is the artwork composite exactly.
        self.assertEqual(exported.getpixel((300, 40)), context.getpixel((300, 40)))

    def test_hidden_wall_art_exports_artwork_only(self):
        self.project.settings["quill.wallArt"] = {"visible": False, "material": "timber"}
        exported = image(export_image(ExportRequest(project=self.project, format="png")))
        context = composite_artwork(validate_project(self.project), self.store)
        self.assertEqual(exported.tobytes(), context.tobytes())


class WallArtEndpointTests(unittest.TestCase):
    def setUp(self):
        # The app lifespan opens the job store; keep it out of the real data directory.
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = patch.dict(os.environ, {"MWQ_DATA_DIR": temp.name})
        env.start()
        self.addCleanup(env.stop)
        self.project = document()
        self.body = {
            "width": 960,
            "height": 640,
            "thickness": 10,
            "material": "stone",
            "rooms": [
                {"id": str(room.id), "polygon": [p.model_dump() for p in room.polygon]}
                for room in self.project.rooms
            ],
            "doors": [door.model_dump(mode="json") for door in self.project.doors],
        }

    def test_renders_png_matching_the_shared_renderer(self):
        with TestClient(app) as client:
            response = client.post("/api/render/walls", json=self.body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertEqual(response.headers["cache-control"], "no-store")
        rendered = Image.open(BytesIO(response.content))
        self.assertEqual(rendered.size, (960, 640))
        project = validate_project(self.project)
        expected = render_wall_art(
            [RoomBoundary(id=r.id, polygon=r.polygon) for r in project.rooms],
            project.walls,
            project.doors,
            thickness=10,
            material="stone",
            size=(960, 640),
        )
        self.assertEqual(rendered.convert("RGBA").tobytes(), expected.tobytes())

    def test_rejects_invalid_requests(self):
        with TestClient(app) as client:
            for changes in (
                {"width": 1000},
                {"thickness": 0},
                {"material": "glass"},
                {"doors": [self.body["doors"][0] | {"wallId": str(uuid4())}]},
            ):
                response = client.post("/api/render/walls", json=self.body | changes)
                self.assertEqual(response.status_code, 422, changes)
            response = client.post(
                "/api/render/walls", content="{}", headers={"Content-Type": "text/plain"}
            )
            self.assertEqual(response.status_code, 415)
