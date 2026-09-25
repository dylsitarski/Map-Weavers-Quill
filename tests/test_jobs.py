import os
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from quill.backgrounds import BackgroundRequest, generate_background
from quill.jobs import JobConflict, JobService
from quill.main import app


class JobTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = patch.dict(os.environ, {"MWQ_DATA_DIR": temp.name})
        env.start()
        self.addCleanup(env.stop)
        self.path = Path(temp.name) / "projects.sqlite3"
        self.service = JobService(self.path)
        self.addCleanup(self.service.close)
        self.request = BackgroundRequest(prompt="stone", seed=0, baseRevision=0)

    def wait_terminal(self, job_id):
        for _ in range(200):
            job = self.service.get(job_id)
            if job.status not in {"queued", "running"}:
                return job
            time.sleep(0.01)
        self.fail("Job did not terminate")

    def test_success_idempotence_conflict_and_durability(self):
        job_id = uuid4()
        self.service.submit(job_id, "background", self.request)
        result = self.wait_terminal(job_id)
        self.assertEqual(result.status, "succeeded")
        self.assertIsNotNone(result.result)
        self.assertEqual(self.service.submit(job_id, "background", self.request), result)
        with self.assertRaises(JobConflict):
            self.service.submit(job_id, "background", self.request.model_copy(update={"seed": 1}))
        other = JobService(self.path)
        try:
            self.assertEqual(other.get(job_id), result)
        finally:
            other.close()

    def test_cancel_queued_running_and_before_submission(self):
        entered, release = Event(), Event()
        self.addCleanup(release.set)
        calls = []

        def slow(request):
            calls.append(request)
            entered.set()
            release.wait(3)
            return generate_background(request)

        with patch("quill.jobs.generate_background", slow):
            running, queued, early = uuid4(), uuid4(), uuid4()
            self.service.submit(running, "background", self.request)
            self.assertTrue(entered.wait(2))
            self.service.submit(queued, "background", self.request)
            self.service.cancel(running)
            self.service.cancel(queued)
            self.service.cancel(early)
            self.assertEqual(
                self.service.submit(early, "background", self.request).status, "cancelled"
            )
            release.set()
            self.service.executor.shutdown(wait=True)
        self.assertEqual(len(calls), 1)
        for job_id in (running, queued, early):
            job = self.service.get(job_id)
            self.assertEqual(job.status, "cancelled")
            self.assertIsNone(job.result)

    def test_failed_job_and_restart_recovery(self):
        job_id = uuid4()
        with patch("quill.jobs.generate_background", side_effect=ValueError("secret details")):
            self.service.submit(job_id, "background", self.request)
            failed = self.wait_terminal(job_id)
        self.assertEqual(failed.status, "failed")
        self.assertNotIn("secret", failed.error)
        abandoned = uuid4()
        db = self.service.connect()
        with db:
            db.execute(
                "INSERT INTO generation_jobs(id,status) VALUES(?,'running')", (str(abandoned),)
            )
        db.close()
        recovered = JobService(self.path)
        try:
            self.assertEqual(recovered.get(abandoned).status, "failed")
            self.assertIn("restart", recovered.get(abandoned).error)
        finally:
            recovered.close()

    def test_api_validates_and_cancellation_is_idempotent(self):
        with TestClient(app) as client:
            job_id = uuid4()
            url = f"/api/jobs/{job_id}"
            self.assertEqual(client.get(url).status_code, 404)
            self.assertEqual(
                client.post(
                    url + "/cancel", json={}, headers={"Origin": "https://evil.example"}
                ).status_code,
                403,
            )
            self.assertEqual(
                client.post(url + "/background", json={"seed": "bad"}).status_code, 422
            )
            self.assertEqual(client.post(url + "/cancel", json={}).json()["status"], "cancelled")
            self.assertEqual(
                client.post(url + "/background", json=self.request.model_dump(mode="json")).json()[
                    "status"
                ],
                "cancelled",
            )
            self.assertEqual(client.get(url).json()["status"], "cancelled")
