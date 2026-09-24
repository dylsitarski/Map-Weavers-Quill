import unittest
from uuid import UUID

from fastapi.testclient import TestClient
from quill.doors import DoorInput, DoorRequest, reconcile_doors
from quill.main import app
from test_walls import derive, room


class DoorTests(unittest.TestCase):
    def setUp(self):
        self.a = room(1, [(100, 100), (300, 100), (300, 300), (100, 300)])
        self.wall = next(w for w in derive([self.a]) if w.start.x == w.end.x == 300)
        self.door = DoorInput(
            id=UUID(int=10),
            kind="door",
            revision=0,
            label="Door",
            metadata={},
            wallId=self.wall.id,
            position=0.5,
            width=50,
            state="closed",
            secret=False,
            doorType="door",
        )

    def request(self, rooms=None, doors=None, before=None):
        return DoorRequest(
            width=1000,
            height=1000,
            beforeRooms=before if before is not None else [self.a],
            rooms=rooms if rooms is not None else [self.a],
            doors=doors if doors is not None else [self.door],
        )

    def test_translation_and_round_trip_preserve_attachment(self):
        moved = room(1, [(200, 150), (400, 150), (400, 350), (200, 350)])
        result = reconcile_doors(self.request([moved]))
        door = result.doors[0]
        self.assertEqual(door.id, self.door.id)
        self.assertNotEqual(door.wallId, self.door.wallId)
        self.assertEqual(door.position, 0.5)
        self.assertEqual(door.revision, 1)
        wall = next(w for w in result.walls if w.id == door.wallId)
        self.assertEqual((wall.start.x, wall.start.y), (400, 150))
        restored = reconcile_doors(
            self.request([self.a], [DoorInput.model_validate(door.model_dump())], [moved])
        )
        self.assertEqual(restored.doors[0].wallId, self.door.wallId)

    def test_split_away_from_opening_remaps_but_split_through_it_rejects(self):
        b = room(2, [(300, 250), (400, 250), (400, 300), (300, 300)])
        result = reconcile_doors(self.request([self.a, b]))
        self.assertNotEqual(result.doors[0].wallId, self.door.wallId)
        self.assertAlmostEqual(result.doors[0].position, 2 / 3)
        crossing = room(2, [(300, 200), (400, 200), (400, 300), (300, 300)])
        with self.assertRaisesRegex(ValueError, "cut through"):
            reconcile_doors(self.request([self.a, crossing]))

    def test_shared_door_rejects_separation_but_allows_removing_one_owner(self):
        b = room(2, [(300, 100), (500, 100), (500, 300), (300, 300)])
        original = [self.a, b]
        moved = room(1, [(50, 100), (250, 100), (250, 300), (50, 300)])
        with self.assertRaisesRegex(ValueError, "separates"):
            reconcile_doors(self.request([moved, b], before=original))
        self.assertEqual(
            reconcile_doors(self.request([b], before=original)).doors[0].wallId, self.wall.id
        )
        with self.assertRaisesRegex(ValueError, "source rooms"):
            reconcile_doors(self.request([]))
        self.assertEqual(reconcile_doors(self.request([], [])).doors, [])

    def test_fit_overlap_duplicate_and_missing_parent(self):
        for changes, message in [
            ({"width": 201}, "full door"),
            ({"position": 0}, "full door"),
            ({"wallId": UUID(int=999)}, "parent wall"),
        ]:
            with self.assertRaisesRegex(ValueError, message):
                reconcile_doors(self.request(doors=[self.door.model_copy(update=changes)]))
        with self.assertRaisesRegex(ValueError, "unique"):
            reconcile_doors(self.request(doors=[self.door, self.door]))
        with self.assertRaisesRegex(ValueError, "overlap"):
            reconcile_doors(
                self.request(doors=[self.door, self.door.model_copy(update={"id": UUID(int=11)})])
            )
        touching = self.door.model_copy(update={"id": UUID(int=11), "position": 0.75})
        self.assertEqual(len(reconcile_doors(self.request(doors=[self.door, touching])).doors), 2)

    def test_api_strict_contract_and_door_states(self):
        with TestClient(app) as client:
            payload = self.request().model_dump(mode="json")
            for state in ("open", "closed", "locked"):
                payload["doors"][0]["state"] = state
                response = client.post("/api/geometry/doors", json=payload)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["doors"][0]["state"], state)
            for field, value in [
                ("width", "50"),
                ("width", 0),
                ("state", "broken"),
                ("position", 2),
                ("wallId", "bad"),
            ]:
                invalid = self.request().model_dump(mode="json")
                invalid["doors"][0][field] = value
                self.assertEqual(client.post("/api/geometry/doors", json=invalid).status_code, 422)

    def test_diagonal_translation_and_nontranslation_rejection(self):
        a = room(1, [(100, 100), (300, 100), (300, 300)])
        wall = next(w for w in derive([a]) if w.start.x != w.end.x and w.start.y != w.end.y)
        door = self.door.model_copy(update={"wallId": wall.id})
        b = room(1, [(150, 150), (350, 150), (350, 350)])
        self.assertEqual(reconcile_doors(self.request([b], [door], [a])).doors[0].position, 0.5)
        reshape = room(1, [(100, 100), (300, 100), (350, 300)])
        with self.assertRaisesRegex(ValueError, "detach"):
            reconcile_doors(self.request([reshape], [door], [a]))
