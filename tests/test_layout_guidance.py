"""Physical units and deterministic wall/door image orientation."""

import unittest

from quill.layout_guidance import room_scale, scale_prompt, wall_guide, working_guide
from quill.sdxl_authoring import RoomTransform
from test_projects import document


class LayoutGuidanceTests(unittest.TestCase):
    def test_scale_uses_document_units_and_crop_transform(self):
        project = document()
        transform = RoomTransform(192, 256)
        scale = room_scale(project, project.rooms[0], (960, 640), transform)
        self.assertEqual(scale["cellDistance"], 5)
        self.assertEqual(scale["units"], "ft")
        self.assertEqual(
            (scale["boundsWidth"], scale["boundsHeight"], scale["area"]), (20, 20, 400)
        )
        self.assertEqual(scale["workingPixelsPerUnit"], 32)
        self.assertIn("each grid cell is 5 ft", scale_prompt(scale, controlled=True))
        project.map.grid.distance = 1.5
        project.map.grid.units = "m"
        scale = room_scale(project, project.rooms[0], (960, 640), transform)
        self.assertEqual((scale["boundsWidth"], scale["area"]), (6, 36))
        self.assertIn("1.5 m", scale_prompt(scale, controlled=False))

    def test_walls_doors_orientation_visibility_and_padded_control(self):
        project = document()
        door = project.doors[0]
        wall = next(w for w in project.walls if w.id == door.wallId)

        def pixel(t):
            return (
                round((wall.start.x + (wall.end.x - wall.start.x) * t) * 0.8),
                round(640 - (wall.start.y + (wall.end.y - wall.start.y) * t) * 0.8),
            )

        guide = wall_guide(project, (960, 640))
        self.assertEqual(guide.getpixel(pixel(door.position)), 0)
        self.assertEqual(guide.getpixel(pixel(0)), 255)
        self.assertEqual(guide.getpixel(pixel(1)), 255)
        self.assertEqual(guide.getpixel((80, 560)), 255)  # Native (100,100).
        self.assertEqual(guide.getpixel((80, 80)), 0)  # No y-axis mirroring.
        # No invented interior partition through the room center.
        self.assertEqual(guide.getpixel((160, 480)), 0)
        crop = (64, 384, 256, 640)
        work = working_guide(guide, crop, RoomTransform(192, 256))
        self.assertEqual(work.size, (1024, 1024))
        self.assertEqual(work.getpixel((0, 0)), (0, 0, 0))
        project.doors = []
        self.assertEqual(wall_guide(project, (960, 640)).getpixel(pixel(door.position)), 255)
