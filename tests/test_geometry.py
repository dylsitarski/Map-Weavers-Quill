import unittest

from fastapi.testclient import TestClient
from quill.main import app


class GeometryTests(unittest.TestCase):
    def test_polygon_validation(self):
        cases = [
            ([(0, 0), (100, 0), (100, 100), (0, 100)], True),
            ([(0, 0), (100, 0), (50, 50), (0, 100)], True),
            ([(0, 0), (100, 100), (100, 0), (0, 100)], False),
            ([(0, 0), (50, 0), (100, 0)], False),
            ([(0, 0), (100, 0), (100, 100), (0, 0)], False),
            ([(-1, 0), (100, 0), (100, 100)], False),
        ]
        with TestClient(app) as client:
            for vertices, expected in cases:
                for points in (vertices, list(reversed(vertices))):
                    with self.subTest(points=points):
                        payload = dict(
                            width=100, height=100, polygon=[dict(x=x, y=y) for x, y in points]
                        )
                        response = client.post("/api/geometry/validate", json=payload)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json()["valid"], expected)
                        self.assertEqual(response.json()["error"] is None, expected)

    def test_malformed_input_rejected(self):
        base = dict(
            width=100, height=100, polygon=[dict(x=0, y=0), dict(x=10, y=0), dict(x=0, y=10)]
        )
        with TestClient(app) as client:
            for change in (
                dict(width="100"),
                dict(width=0),
                dict(unknown=True),
                dict(polygon=[]),
                dict(polygon=[dict(x=0, y=0)] * 2049),
            ):
                self.assertEqual(
                    client.post("/api/geometry/validate", json=base | change).status_code, 422
                )
