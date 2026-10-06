"""Read-only debugging bundle export with mock generations and queued jobs."""

import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from quill.backgrounds import BackgroundRequest, generate_background
from quill.jobs import JobService
from quill.projects import ProjectStore, SaveRequest
from quill.room_images import RoomImageRequest, generate_room
from test_projects import document

from scripts.export_debug_bundle import export


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DebugBundleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.data = Path(temp.name)
        env = patch.dict(os.environ, {"MWQ_DATA_DIR": temp.name})
        env.start()
        self.addCleanup(env.stop)
        self.store = ProjectStore(self.data / "projects.sqlite3")
        project = document().model_copy(update={"name": "Cottage Test"})
        project.rooms[0].prompt = "Cozy kitchen with a hearth"
        background = generate_background(BackgroundRequest(prompt="meadow", seed=1, baseRevision=0))
        room = generate_room(RoomImageRequest(project=project, roomId=project.rooms[0].id, seed=2))
        project.rooms[0].renderLayerId = room.layer.id
        project.layers = [background.layer, room.layer]
        project.generations = [background.generation, room.generation]
        first = self.store.save(SaveRequest(project=project, expectedRevision=None))
        self.project = self.store.save(
            SaveRequest(
                project=first.model_copy(update={"name": "Cottage Test"}), expectedRevision=1
            )
        )
        # Queued previews: one for this project (unaccepted), one for another project,
        # one background (not linked to any project), and one failed room job.
        preview = generate_room(
            RoomImageRequest(project=self.project, roomId=project.rooms[1].id, seed=3)
        )
        jobs = JobService(self.store.path)
        self.addCleanup(jobs.executor.shutdown)
        other = self.project.model_copy(update={"projectId": uuid4()})
        rows = [
            (
                "room",
                RoomImageRequest(project=self.project, roomId=project.rooms[1].id, seed=3),
                "succeeded",
                preview.model_dump_json(),
                None,
            ),
            (
                "room",
                RoomImageRequest(project=other, roomId=project.rooms[1].id, seed=4),
                "succeeded",
                preview.model_dump_json(),
                None,
            ),
            (
                "background",
                BackgroundRequest(prompt="other map", seed=5, baseRevision=0),
                "succeeded",
                background.model_dump_json(),
                None,
            ),
            (
                "room",
                RoomImageRequest(project=self.project, roomId=project.rooms[0].id, seed=6),
                "failed",
                None,
                "ComfyUI execution failed.",
            ),
        ]
        db = jobs.connect()
        with db:
            for target, request, status, result, error in rows:
                db.execute(
                    "INSERT INTO generation_jobs(id,target,request,status,result,error) "
                    "VALUES(?,?,?,?,?,?)",
                    (str(uuid4()), target, request.model_dump_json(), status, result, error),
                )
        db.close()
        self.room_output = room.generation.outputHash

    def test_bundle_contents_and_database_unchanged(self):
        before = digest(self.store.path)
        out = self.data / "bundle"
        archive = export(self.data, "cottage test", out)
        self.assertEqual(digest(self.store.path), before)
        summary = (out / "summary.txt").read_text()
        self.assertIn("Cozy kitchen with a hearth", summary)
        self.assertIn("closed", summary)  # Door state.
        self.assertEqual(
            json.loads((out / "project.json").read_text())["projectId"], str(self.project.projectId)
        )
        layers = json.loads((out / "layers" / "layers.json").read_text())
        self.assertEqual([layer["file"] for layer in layers][0], "00-background.png")
        for layer in layers:
            self.assertTrue((out / "layers" / layer["file"]).exists())
        generations = sorted(p.name for p in (out / "generations").iterdir())
        self.assertEqual(len(generations), 2)
        self.assertTrue(generations[0].startswith("01-map-"))
        room = out / "generations" / generations[1]
        self.assertTrue(generations[1].startswith("02-room-"))
        record = json.loads((room / "record.json").read_text())
        self.assertEqual(record["outputHash"], self.room_output)
        self.assertEqual((room / "prompt.txt").read_text().strip(), record["prompt"])
        for name in ("input-1-source", "input-2-mask", "output"):
            self.assertTrue((room / f"{name}.png").exists(), name)
            self.assertTrue((room / f"{name}-crop.png").exists(), name)
        jobs = sorted(p.name for p in (out / "jobs").iterdir())
        self.assertEqual(len(jobs), 2)  # This project's room jobs only.
        succeeded = next(p for p in jobs if "-succeeded-room-" in p)
        job = json.loads((out / "jobs" / succeeded / "record.json").read_text())["job"]
        self.assertFalse(job["accepted"])
        self.assertEqual(job["seed"], 3)
        failed = next(p for p in jobs if "-failed-room-" in p)
        self.assertIn("execution failed", (out / "jobs" / failed / "job.json").read_text())
        self.assertNotIn("Missing", (out / "README.txt").read_text())
        with zipfile.ZipFile(archive) as bundle:
            self.assertIn("bundle/summary.txt", bundle.namelist())

    def test_background_jobs_are_opt_in(self):
        out = self.data / "with-backgrounds"
        export(self.data, str(self.project.projectId), out, background_jobs=True)
        self.assertEqual(sum("-background-" in p.name for p in (out / "jobs").iterdir()), 1)

    def test_selection_errors_and_existing_output(self):
        with self.assertRaisesRegex(SystemExit, "No saved project"):
            export(self.data, "missing", self.data / "x")
        twin = self.project.model_copy(update={"projectId": uuid4(), "revision": 0})
        self.store.save(SaveRequest(project=twin, expectedRevision=None))
        with self.assertRaisesRegex(SystemExit, "Several projects"):
            export(self.data, "Cottage Test", self.data / "y")
        (self.data / "taken").mkdir()
        with self.assertRaisesRegex(SystemExit, "already exists"):
            export(self.data, str(self.project.projectId), self.data / "taken")
        with self.assertRaisesRegex(SystemExit, "No Quill database"):
            export(self.data / "nowhere", "x", self.data / "z")

    def test_older_revision(self):
        out = self.data / "first"
        export(self.data, str(self.project.projectId), out, revision=1)
        self.assertEqual(json.loads((out / "project.json").read_text())["revision"], 1)
