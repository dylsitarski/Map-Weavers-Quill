"""Physical units and deterministic wall/door image orientation."""

import unittest

from quill.layout_guidance import (
    SKETCH_DOOR,
    SKETCH_WALL,
    room_scale,
    room_sketch,
    scale_prompt,
    wall_guide,
    working_guide,
)
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

    def test_room_sketch_draws_wall_thickness_and_door_states(self):
        project = document()
        door = project.doors[0]
        wall = next(w for w in project.walls if w.id == door.wallId)

        def pixel(t, offset=0.0):
            # Native point along the door's (vertical) wall, offset across it.
            return (
                round((wall.start.x + offset + (wall.end.x - wall.start.x) * t) * 0.8),
                round(640 - (wall.start.y + (wall.end.y - wall.start.y) * t) * 0.8),
            )

        project.map.style.wallThicknessPx = 10  # 8 px at 960 x 640.
        closed = room_sketch(project, (960, 640), project.rooms[0])
        self.assertEqual(closed.getpixel(pixel(0.05)), SKETCH_WALL)
        self.assertEqual(closed.getpixel(pixel(0.05, offset=3)), SKETCH_WALL)  # Thick wall.
        self.assertEqual(closed.getpixel(pixel(door.position)), SKETCH_DOOR)  # Closed bar.
        self.assertEqual(closed.getpixel((160, 480)), (0, 0, 0))  # Room interior empty.
        self.assertEqual(closed.getpixel((80, 80)), (0, 0, 0))  # No y-axis mirroring.
        door.state = "open"
        self.assertEqual(
            room_sketch(project, (960, 640), project.rooms[0]).getpixel(pixel(door.position)),
            (0, 0, 0),
        )
        door.secret = True
        self.assertEqual(
            room_sketch(project, (960, 640), project.rooms[0]).getpixel(pixel(door.position)),
            SKETCH_WALL,
        )
        door.secret, door.doorType = False, "window"
        self.assertEqual(
            room_sketch(project, (960, 640), project.rooms[0]).getpixel(pixel(door.position)),
            SKETCH_WALL,
        )
        # Only the target room's walls: room 1's far wall (native x=500) is not drawn.
        self.assertEqual(closed.getpixel((400, 480)), (0, 0, 0))
        other = room_sketch(project, (960, 640), project.rooms[1])
        self.assertEqual(other.getpixel((400, 480)), SKETCH_WALL)
        self.assertEqual(other.getpixel((80, 480)), (0, 0, 0))  # Room 0's far wall omitted.
        # RGB sketches keep their colors through the working transform.
        work = working_guide(closed, (64, 384, 256, 640), RoomTransform(192, 256))
        self.assertIn(SKETCH_WALL, {c for _, c in work.getcolors(1024 * 1024)})
