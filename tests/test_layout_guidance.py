"""Physical units and deterministic wall/door image orientation."""

import unittest

from PIL import Image
from quill.layout_guidance import (
    SKETCH_DOOR,
    SKETCH_WALL,
    door_list,
    room_scale,
    room_sketch,
    scale_prompt,
    wall_guide,
)
from quill.raster import polygon_mask
from quill.sdxl_authoring import RoomWindow
from test_projects import document


def window_for(project, index=0):
    return RoomWindow.around(polygon_mask(project.rooms[index].polygon, (960, 640)), 320, 16)


class LayoutGuidanceTests(unittest.TestCase):
    def test_scale_uses_document_units_and_fixed_window(self):
        project = document()
        window = window_for(project)
        scale = room_scale(project, project.rooms[0], (960, 640), window)
        self.assertEqual(scale["cellDistance"], 5)
        self.assertEqual(scale["units"], "ft")
        self.assertEqual(
            (scale["boundsWidth"], scale["boundsHeight"], scale["area"]), (20, 20, 400)
        )
        self.assertEqual((scale["windowSize"], scale["workingPixelsPerUnit"]), (40, 25.6))
        text = scale_prompt(scale, controlled=True)
        self.assertIn("the image shows 40 by 40 ft", text)
        self.assertIn("one 5-ft grid square is 128 pixels wide", text)
        self.assertIn("This room measures 20 by 20 ft", text)
        self.assertIn("Follow the supplied wall lines", text)
        self.assertNotIn("wall lines", scale_prompt(scale, controlled=False))
        # The other room gets the identical working scale.
        other = room_scale(project, project.rooms[1], (960, 640), window_for(project, 1))
        self.assertEqual(other["workingPixelsPerUnit"], scale["workingPixelsPerUnit"])
        project.map.grid.distance = 1.5
        project.map.grid.units = "m"
        scale = room_scale(project, project.rooms[0], (960, 640), window)
        self.assertEqual((scale["boundsWidth"], scale["area"]), (6, 36))
        self.assertIn("1.5-m", scale_prompt(scale, controlled=False))

    def test_walls_doors_orientation_visibility_and_working_guide(self):
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
        window = window_for(project)
        work = window.guide(guide)
        self.assertEqual(work.size, (1024, 1024))
        x, y = window.to_working(80, 560)
        self.assertEqual(work.getpixel((round(x) + 1, round(y) - 5)), (255, 255, 255))
        project.doors = []
        self.assertEqual(wall_guide(project, (960, 640)).getpixel(pixel(door.position)), 255)

    def test_room_sketch_draws_wall_thickness_and_door_symbols(self):
        project = document()
        door = project.doors[0]
        wall = next(w for w in project.walls if w.id == door.wallId)
        room = project.rooms[0]
        window = window_for(project)

        def pixel(t, inward=0.0):
            # Working pixel along the door's wall (native x=300), moved into room 0.
            x = (wall.start.x - inward) * 0.8
            y = 640 - (wall.start.y + (wall.end.y - wall.start.y) * t) * 0.8
            px, py = window.to_working(x, y)
            return round(px), round(py)

        project.map.style.wallThicknessPx = 5  # 4 raster px, 12.8 working px.
        closed = room_sketch(project, (960, 640), room, window)
        self.assertEqual(closed.size, (1024, 1024))
        self.assertEqual(closed.getpixel(pixel(0.1)), SKETCH_WALL)
        self.assertEqual(closed.getpixel(pixel(0.1, inward=2)), SKETCH_WALL)  # 6 px in.
        self.assertEqual(closed.getpixel(pixel(0.1, inward=4)), (0, 0, 0))  # Thin wall.
        self.assertEqual(closed.getpixel(pixel(door.position)), SKETCH_DOOR)  # Closed leaf.
        self.assertEqual(closed.getpixel(pixel(door.position, inward=10)), (0, 0, 0))
        # Wall width is the same physical size whatever the room's size.
        project.map.style.wallThicknessPx = 10
        self.assertEqual(
            room_sketch(project, (960, 640), room, window).getpixel(pixel(0.1, inward=4)),
            SKETCH_WALL,
        )
        project.map.style.wallThicknessPx = 5
        door.state = "open"
        opened = room_sketch(project, (960, 640), room, window)
        self.assertEqual(opened.getpixel(pixel(door.position)), (0, 0, 0))  # Clear opening.
        # The leaf stands into the room from the hinge (the door's low end).
        low = door.position - door.width / 2 / 200
        self.assertEqual(opened.getpixel(pixel(low, inward=door.width / 2)), SKETCH_DOOR)
        # Raster-size copy for provenance.
        self.assertEqual(room_sketch(project, (960, 640), room).size, (960, 640))
        door.secret = True
        self.assertEqual(
            room_sketch(project, (960, 640), room, window).getpixel(pixel(door.position)),
            SKETCH_WALL,
        )
        door.secret, door.doorType = False, "window"
        self.assertEqual(
            room_sketch(project, (960, 640), room, window).getpixel(pixel(door.position)),
            SKETCH_WALL,
        )
        # Only the target room's walls: room 1's far wall (native x=500) is not drawn.
        flat = room_sketch(project, (960, 640), room)
        self.assertEqual(flat.getpixel((400, 480)), (0, 0, 0))
        self.assertEqual(flat.getpixel((80, 80)), (0, 0, 0))  # No y-axis mirroring.
        other = room_sketch(project, (960, 640), project.rooms[1])
        self.assertEqual(other.getpixel((400, 480)), SKETCH_WALL)
        self.assertEqual(other.getpixel((80, 480)), (0, 0, 0))  # Room 0's far wall omitted.
        self.assertIsInstance(other, Image.Image)

    def test_door_list_names_image_side_and_state(self):
        project = document()
        door = project.doors[0]
        self.assertEqual(door_list(project, project.rooms[0]), ["a closed door in the right wall"])
        # The same shared-wall door is on room 1's left wall.
        door.state = "open"
        self.assertEqual(
            door_list(project, project.rooms[1]),
            ["an open door swung into the room in the left wall"],
        )
        door.secret = True
        self.assertEqual(door_list(project, project.rooms[0]), [])
