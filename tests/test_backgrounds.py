import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from quill.backgrounds import BackgroundRequest, generate_background
from quill.projects import ProjectStore, SaveRequest
from test_projects import document


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, {"MWQ_DATA_DIR": self.temp.name})
        env.start()
        self.addCleanup(env.stop)
        self.store = ProjectStore(Path(self.temp.name) / "projects.sqlite3")

    def test_deterministic_asset_is_persistent_deduplicated_and_served_as_png(self):
        a = generate_background(BackgroundRequest(prompt="Stone", seed=4, baseRevision=0))
        b = generate_background(BackgroundRequest(prompt="Stone", seed=4, baseRevision=0))
        c = generate_background(BackgroundRequest(prompt="Stone", seed=5, baseRevision=0))
        self.assertEqual(a.layer.assetHash, b.layer.assetHash)
        self.assertNotEqual(a.layer.assetHash, c.layer.assetHash)
        data = self.store.get_asset(a.layer.assetHash)
        self.assertEqual(hashlib.sha256(data).hexdigest(), a.layer.assetHash)
        db = self.store.connect()
        try:
            self.assertEqual(db.execute("SELECT count(*) FROM assets").fetchone()[0], 2)
        finally:
            db.close()
        with TestClient(app()) as client:
            response = client.get(f"/api/assets/{a.layer.assetHash}")
            self.assertEqual(response.content, data)
            self.assertEqual(response.headers["content-type"], "image/png")
            self.assertEqual(client.get("/api/assets/" + "0" * 64).status_code, 404)
            self.assertEqual(client.get("/api/assets/bad").status_code, 404)

    def test_layer_and_provenance_survive_save_and_restart_without_geometry_changes(self):
        proposal = generate_background(BackgroundRequest(prompt="Stone", seed=0, baseRevision=0))
        before = document()
        project = before.model_copy(
            update={"layers": [proposal.layer], "generations": [proposal.generation]}
        )
        saved = self.store.save(SaveRequest(project=project, expectedRevision=None))
        loaded = ProjectStore(self.store.path).open(project.projectId)
        self.assertEqual(loaded, saved)
        self.assertEqual(loaded.rooms, before.rooms)
        self.assertEqual(loaded.doors, before.doors)
        self.assertEqual(loaded.layers[0].assetHash, proposal.layer.assetHash)
        self.assertEqual(loaded.generations[0].prompt, "Stone")
        db = self.store.connect()
        try:
            with db:
                db.execute("DELETE FROM assets")
        finally:
            db.close()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.store.open(project.projectId)

    def test_missing_assets_and_unsupported_layers_cannot_be_saved(self):
        proposal = generate_background(BackgroundRequest(prompt="Stone", seed=0, baseRevision=0))
        for layer in [
            proposal.layer.model_copy(update={"assetHash": "0" * 64}),
            proposal.layer.model_copy(update={"zIndex": 2}),
            proposal.layer.model_copy(update={"rotation": 90.0}),
        ]:
            with self.assertRaises(ValueError):
                self.store.save(
                    SaveRequest(
                        project=document().model_copy(update={"layers": [layer]}),
                        expectedRevision=None,
                    )
                )
        self.assertEqual(self.store.list().projects, [])

    def test_preview_does_not_publish_a_project_and_write_guards_apply(self):
        with TestClient(app()) as client:
            payload = {"prompt": "Stone", "seed": 4, "baseRevision": 0}
            response = client.post("/api/generation/background", json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(client.get("/api/projects").json(), {"projects": []})
            for invalid in [
                payload | {"seed": -1},
                payload | {"seed": 1.5},
                payload | {"prompt": "x" * 4001},
                payload | {"unknown": True},
            ]:
                self.assertEqual(
                    client.post("/api/generation/background", json=invalid).status_code, 422
                )
            self.assertEqual(
                client.post(
                    "/api/generation/background",
                    json=payload,
                    headers={"Origin": "https://evil.example"},
                ).status_code,
                403,
            )
            self.assertEqual(
                client.post(
                    "/api/generation/background",
                    content="x" * 32769,
                    headers={"Content-Type": "application/json"},
                ).status_code,
                413,
            )


def app():
    from quill.main import app

    return app

    def test_map_prompt_style_persistence_and_generation_provenance(self):
        project = document()
        project.settings["quill.background"] = {"prompt": "Ancient ruins"}
        project.map.style.environment = "desert"
        project.map.style.palette = "ochre"
        saved = self.store.save(SaveRequest(project=project, expectedRevision=None))
        reopened = self.store.open(saved.projectId)
        self.assertEqual(reopened.settings, project.settings)
        self.assertEqual(reopened.map.style, project.map.style)
        request = BackgroundRequest(
            prompt="Ancient ruins", style=reopened.map.style, seed=0, baseRevision=1
        )
        a = generate_background(request)
        self.assertEqual(a.generation.parameters["backgroundPrompt"], "Ancient ruins")
        self.assertEqual(a.generation.parameters["mapStyle"]["palette"], "ochre")
        self.assertIn('"environment": "desert"', a.generation.prompt)
        request.style.palette = "blue"
        b = generate_background(request)
        self.assertNotEqual(a.layer.assetHash, b.layer.assetHash)
        self.assertEqual(a.generation.parameters["mapStyle"]["palette"], "ochre")
        project.settings["quill.background"] = {"prompt": 123}
        with self.assertRaisesRegex(ValueError, "Background settings"):
            self.store.save(SaveRequest(project=project, expectedRevision=1))
