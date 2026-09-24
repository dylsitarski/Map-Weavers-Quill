import unittest
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
from quill.main import app
from quill.models import Point
from quill.walls import RoomBoundary, WallDerivationRequest, derive_walls


def room(number, coords):
    return RoomBoundary(id=UUID(int=number), polygon=[Point(x=x, y=y) for x, y in coords])


def derive(rooms):
    return derive_walls(WallDerivationRequest(width=1000, height=1000, rooms=rooms)).walls


class WallTests(unittest.TestCase):
    def test_adjacent_rooms_share_one_wall(self):
        a = room(1, [(0, 0), (100, 0), (100, 100), (0, 100)])
        b = room(2, [(100, 0), (200, 0), (200, 100), (100, 100)])
        walls = derive([a, b])
        self.assertEqual(len(walls), 7)
        shared = [w for w in walls if w.start.x == w.end.x == 100]
        self.assertEqual(len(shared), 1)
        self.assertIsNone(shared[0].sourceRoomId)
        self.assertEqual(
            shared[0].metadata["quill.geometry"], {"sourceRoomIds": [str(a.id), str(b.id)]}
        )
        self.assertTrue(all(w.movement and w.sight for w in walls))
        reversed_a = a.model_copy(update={"polygon": list(reversed(a.polygon))})
        self.assertEqual(walls, derive([b, reversed_a]))

    def test_partial_shared_edge_is_split_and_unchanged_ids_survive(self):
        a = room(1, [(0, 0), (100, 0), (100, 100), (0, 100)])
        b = room(2, [(100, 25), (150, 25), (150, 75), (100, 75)])
        original = derive([a])
        result = derive([a, b])
        self.assertEqual(len(result), 9)
        shared = [w for w in result if w.sourceRoomId is None]
        self.assertEqual(len(shared), 1)
        self.assertEqual((shared[0].start.y, shared[0].end.y), (25, 75))
        old_ids = {w.id for w in original}
        self.assertEqual(len(old_ids.intersection(w.id for w in result)), 3)
        self.assertEqual(original, derive([a]))  # Delete/undo reconstruction.

    def test_crossings_concavity_identical_rooms_and_disjoint_rooms(self):
        a = room(1, [(0, 0), (100, 0), (100, 100), (0, 100)])
        crossing = room(2, [(50, 50), (150, 50), (150, 150), (50, 150)])
        self.assertEqual(len(derive([a, crossing])), 12)
        identical = a.model_copy(update={"id": UUID(int=3)})
        shared = derive([a, identical])
        self.assertEqual(len(shared), 4)
        self.assertTrue(all(w.sourceRoomId is None for w in shared))
        concave = room(4, [(200, 200), (300, 200), (250, 250), (200, 300)])
        self.assertEqual(len(derive([a, concave])), 8)
        self.assertEqual(derive([]), [])

    def test_diagonal_crossings_preserve_provenance(self):
        a = room(1, [(0, 0), (200, 0), (100, 200)])
        b = room(2, [(0, 100), (200, 100), (100, 0)])
        walls = derive([a, b])
        self.assertGreater(len(walls), 6)
        self.assertTrue(all(w.sourceRoomId in (a.id, b.id) for w in walls))

    def test_invalid_geometry_duplicates_and_budget_rejected(self):
        a = room(1, [(0, 0), (100, 100), (0, 100), (100, 0)])
        with self.assertRaises(ValueError):
            derive([a])
        good = room(2, [(0, 0), (100, 0), (0, 100)])
        with self.assertRaises(ValueError):
            derive([good, good])
        many = [room(i + 1, [(0, 0)] * 1025) for i in range(2)]
        with patch("quill.walls.unary_union") as union:
            with self.assertRaisesRegex(ValueError, "2048"):
                derive(many)
            union.assert_not_called()

    def test_api_contract(self):
        a = room(1, [(0, 0), (100, 0), (0, 100)])
        payload = WallDerivationRequest(width=100, height=100, rooms=[a]).model_dump(mode="json")
        with TestClient(app) as client:
            response = client.post("/api/geometry/walls", json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()["walls"]), 3)
            for change in (
                {"unknown": 1},
                {"width": "100"},
                {"rooms": [payload["rooms"][0]] * 129},
            ):
                self.assertEqual(
                    client.post("/api/geometry/walls", json=payload | change).status_code, 422
                )
