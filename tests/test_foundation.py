import json
import math
import unittest
from pathlib import Path

from pydantic import ValidationError
from quill.coordinates import clockwise_from_positive_x, raster_rectangle, reflect_point
from quill.models import Project

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/projects"


class ProjectTests(unittest.TestCase):
    def test_round_trip(self):
        raw = (FIXTURES / "two-rooms.json").read_text()
        project = Project.model_validate_json(raw)
        self.assertEqual(json.loads(project.model_dump_json()), json.loads(raw))

    def test_invalid_fixtures(self):
        expected = json.loads((FIXTURES / "invalid/expected-errors.json").read_text())
        for name, path in expected.items():
            with self.subTest(fixture=name):
                with self.assertRaises(ValidationError) as caught:
                    Project.model_validate_json((FIXTURES / f"invalid/{name}.json").read_text())
                self.assertIn(tuple(path), [e["loc"] for e in caught.exception.errors()])

    def test_unknown_fields_and_coercion_rejected(self):
        for key, value in [("unknown", True), ("revision", "0")]:
            raw = json.loads((FIXTURES / "two-rooms.json").read_text())
            raw[key] = value
            with self.subTest(key=key), self.assertRaises(ValidationError):
                Project.model_validate_json(json.dumps(raw))

    def test_nonfinite_rejected(self):
        raw = json.loads((FIXTURES / "two-rooms.json").read_text())
        raw["map"]["height"] = math.inf
        with self.assertRaises(ValidationError):
            Project.model_validate_json(json.dumps(raw))


class CoordinateTests(unittest.TestCase):
    def test_corners_and_inverse(self):
        for point, expected in [
            ((0, 0), (0, 600)),
            ((0, 600), (0, 0)),
            ((1000, 0), (1000, 600)),
            ((1000, 600), (1000, 0)),
            ((123.5, 222.25), (123.5, 377.75)),
        ]:
            with self.subTest(point=point):
                actual = reflect_point(*point, 600)
                self.assertEqual(actual, expected)
                self.assertEqual(reflect_point(*actual, 600), point)

    def test_rectangle(self):
        self.assertEqual(raster_rectangle(10, 20, 30, 40, 600), (10, 540, 30, 40))

    def test_angles(self):
        for angle, expected in [(0, 0), (90, 270), (180, 180), (270, 90), (360, 0), (-90, 90)]:
            self.assertEqual(clockwise_from_positive_x(angle), expected)

    def test_winding_reverses(self):
        points = [(0, 0), (5, 0), (5, 5), (0, 5)]

        def area(p):
            return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1])) / 2

        self.assertEqual(area(points), -area([reflect_point(*p, 600) for p in points]))

    def test_invalid_inputs(self):
        for args in [(0, 0, 0), (0, 0, -1), (math.nan, 0, 600), (0, math.inf, 600)]:
            with self.assertRaises(ValueError):
                reflect_point(*args)
        with self.assertRaises(ValueError):
            raster_rectangle(0, 0, -1, 20, 600)
        with self.assertRaises(ValueError):
            clockwise_from_positive_x(math.inf)


if __name__ == "__main__":
    unittest.main()
