import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from quill.main import app
from quill.models import Door, Project, Room
from quill.projects import ProjectStore, SaveConflict, SaveRequest
from quill.walls import RoomBoundary, WallDerivationRequest, derive_walls


def document():
    p = Project.model_validate_json(Path("fixtures/projects/two-rooms.json").read_text())
    a = RoomBoundary(
        id=uuid4(),
        polygon=[
            {"x": 100.0, "y": 100.0},
            {"x": 300.0, "y": 100.0},
            {"x": 300.0, "y": 300.0},
            {"x": 100.0, "y": 300.0},
        ],
    )
    b = RoomBoundary(
        id=uuid4(),
        polygon=[
            {"x": 300.0, "y": 100.0},
            {"x": 500.0, "y": 100.0},
            {"x": 500.0, "y": 300.0},
            {"x": 300.0, "y": 300.0},
        ],
    )
    walls = derive_walls(WallDerivationRequest(width=1200, height=800, rooms=[a, b])).walls
    shared = next(w for w in walls if w.start.x == w.end.x == 300)
    rooms = [
        Room(
            id=r.id,
            kind="room",
            revision=0,
            label=f"Room {i}",
            polygon=r.polygon,
            prompt="Stone floor",
            metadata={},
            styleOverrides={},
            renderLayerId=None,
        )
        for i, r in enumerate([a, b])
    ]
    door = Door(
        id=uuid4(),
        kind="door",
        revision=0,
        label="Door",
        metadata={},
        wallId=shared.id,
        position=0.375,
        width=50,
        state="closed",
        secret=False,
        doorType="door",
    )
    return p.model_copy(
        update={
            "projectId": uuid4(),
            "revision": 0,
            "map": p.map.model_copy(
                update={
                    "width": 1200.0,
                    "height": 800.0,
                    "grid": p.map.grid.model_copy(update={"sizePx": 50.0}),
                }
            ),
            "rooms": rooms,
            "walls": walls,
            "doors": [door],
            "lights": [],
            "layers": [],
            "objects": [],
            "regions": [],
            "sounds": [],
            "generations": [],
        }
    )


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "projects.sqlite3"
        self.store = ProjectStore(self.path)
        self.project = document()

    def save(self, project=None, revision=None):
        return self.store.save(
            SaveRequest(project=project or self.project, expectedRevision=revision)
        )

    def test_round_trip_preserves_geometry_order_metadata_and_old_snapshots(self):
        first = self.save()
        self.assertEqual(first.revision, 1)
        self.assertEqual(self.store.open(first.projectId), first)
        changed = first.model_copy(update={"name": "Changed", "rooms": list(reversed(first.rooms))})
        second = self.save(changed, 1)
        self.assertEqual(second.revision, 2)
        self.assertEqual(ProjectStore(self.path).open(first.projectId), second)
        db = self.store.connect()
        try:
            rows = db.execute("SELECT document FROM snapshots ORDER BY revision").fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual(Project.model_validate_json(rows[0][0]), first)
        finally:
            db.close()
        self.assertEqual(self.store.list().projects[0].name, "Changed")

    def test_stale_and_concurrent_saves_do_not_overwrite(self):
        first = self.save()
        with self.assertRaises(SaveConflict):
            self.save()

        def attempt(name):
            try:
                return self.save(first.model_copy(update={"name": name}), 1).name
            except SaveConflict:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            names = list(pool.map(attempt, ["A", "B"]))
        self.assertEqual(sum(name is not None for name in names), 1)
        self.assertIn(self.store.open(first.projectId).name, names)

    def test_failed_publish_rolls_back_snapshot_and_current_pointer(self):
        first = self.save()
        with patch.object(ProjectStore, "publish", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                self.save(first, 1)
        self.assertEqual(self.store.open(first.projectId), first)
        db = self.store.connect()
        try:
            self.assertEqual(db.execute("SELECT count(*) FROM snapshots").fetchone()[0], 1)
        finally:
            db.close()

    def test_process_exit_before_commit_recovers_previous_snapshot(self):
        first = self.save()
        script = """
import os, sys
from pathlib import Path
from uuid import UUID
from quill.projects import ProjectStore, SaveRequest
store = ProjectStore(Path(sys.argv[1]))
project = store.open(UUID(sys.argv[2]))
ProjectStore.publish = staticmethod(lambda *args: os._exit(17))
store.save(SaveRequest(project=project, expectedRevision=project.revision))
"""
        result = subprocess.run(
            [sys.executable, "-c", script, str(self.path), str(first.projectId)],
            env=os.environ.copy(),
            check=False,
        )
        self.assertEqual(result.returncode, 17)
        self.assertEqual(ProjectStore(self.path).open(first.projectId), first)
        self.assertEqual(self.save(first, 1).revision, 2)

    def test_invalid_references_topology_and_unsupported_content_are_rejected(self):
        bad = []
        bad.append(
            self.project.model_copy(
                update={"doors": [self.project.doors[0].model_copy(update={"wallId": uuid4()})]}
            )
        )
        bad.append(
            self.project.model_copy(
                update={"rooms": [self.project.rooms[0], self.project.rooms[0]]}
            )
        )
        room = self.project.rooms[0].model_copy(update={"renderLayerId": uuid4()})
        bad.append(self.project.model_copy(update={"rooms": [room]}))
        room = self.project.rooms[0].model_copy(
            update={"polygon": [self.project.rooms[0].polygon[i] for i in [0, 2, 1, 3]]}
        )
        bad.append(self.project.model_copy(update={"rooms": [room]}))
        bad.append(
            self.project.model_copy(
                update={
                    "walls": [
                        self.project.walls[0].model_copy(update={"movement": False}),
                        *self.project.walls[1:],
                    ]
                }
            )
        )
        bad.append(
            self.project.model_copy(
                update={"map": self.project.map.model_copy(update={"width": 1000.0})}
            )
        )
        for project in bad:
            with self.assertRaises(ValueError):
                self.save(project)
        with self.assertRaises(KeyError):
            self.store.open(self.project.projectId)

    def test_api_save_open_errors_and_write_guards(self):
        with patch.dict(os.environ, {"MWQ_DATA_DIR": self.temp.name}), TestClient(app) as client:
            payload = SaveRequest(project=self.project, expectedRevision=None).model_dump(
                mode="json"
            )
            response = client.post("/api/projects/save", json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            saved = response.json()
            self.assertEqual(client.get(f"/api/projects/{self.project.projectId}").json(), saved)
            self.assertEqual(client.get("/api/projects").json()["projects"][0]["revision"], 1)
            self.assertEqual(client.post("/api/projects/save", json=payload).status_code, 409)
            self.assertEqual(
                client.post(
                    "/api/projects/save",
                    json=payload,
                    headers={"Origin": "https://untrusted.example"},
                ).status_code,
                403,
            )
            self.assertEqual(
                client.post(
                    "/api/projects/save", content="x", headers={"Content-Type": "text/plain"}
                ).status_code,
                415,
            )
            payload["project"]["schemaVersion"] = "999.0.0"
            self.assertEqual(client.post("/api/projects/save", json=payload).status_code, 422)
            self.assertEqual(client.get(f"/api/projects/{UUID(int=999)}").status_code, 404)
            self.assertEqual(
                client.post(
                    "/api/projects/save",
                    content=json.dumps({"padding": "x" * (4 * 1024 * 1024)}),
                    headers={"Content-Type": "application/json"},
                ).status_code,
                413,
            )
