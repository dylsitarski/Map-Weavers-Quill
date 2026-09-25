"""Single-process durable generation queue with race-safe terminal transitions."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Lock
from typing import Literal
from uuid import UUID

from quill.backgrounds import BackgroundRequest, BackgroundResult, generate_background
from quill.models import Contract
from quill.projects import ProjectStore
from quill.room_images import RoomImageRequest, generate_room


class GenerationJob(Contract):
    id: UUID
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    result: BackgroundResult | None = None
    error: str | None = None


class JobConflict(ValueError):
    pass


class JobQueueFull(ValueError):
    pass


class JobService:
    def __init__(self, path: Path):
        self.store = ProjectStore(path)
        self.lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="quill-generation")
        with closing(self.connect()) as db, db:
            db.execute(
                "UPDATE generation_jobs SET status='failed', error=? WHERE status IN ('queued','running')",
                ("Generation interrupted by server restart. Generate again.",),
            )

    def connect(self) -> sqlite3.Connection:
        db = self.store.connect()
        db.execute("""CREATE TABLE IF NOT EXISTS generation_jobs (
            id TEXT PRIMARY KEY, target TEXT, request TEXT, status TEXT NOT NULL,
            result TEXT, error TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        return db

    def get(self, job_id: UUID) -> GenerationJob:
        with closing(self.connect()) as db:
            row = db.execute(
                "SELECT status,result,error FROM generation_jobs WHERE id=?", (str(job_id),)
            ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return GenerationJob(
            id=job_id,
            status=row[0],
            result=BackgroundResult.model_validate_json(row[1]) if row[1] else None,
            error=row[2],
        )

    def submit(
        self, job_id: UUID, target: str, request: BackgroundRequest | RoomImageRequest
    ) -> GenerationJob:
        payload = request.model_dump_json()
        with self.lock, closing(self.connect()) as db, db:
            previous = db.execute(
                "SELECT target,request,status FROM generation_jobs WHERE id=?", (str(job_id),)
            ).fetchone()
            if previous:
                if previous[0] is not None and previous[:2] != (target, payload):
                    raise JobConflict("Job ID already belongs to another request.")
            else:
                if (
                    db.execute(
                        "SELECT COUNT(*) FROM generation_jobs WHERE status IN ('queued','running')"
                    ).fetchone()[0]
                    >= 16
                ):
                    raise JobQueueFull("Generation queue is full. Retry shortly.")
                db.execute(
                    "INSERT INTO generation_jobs(id,target,request,status) VALUES(?,?,?,'queued')",
                    (str(job_id), target, payload),
                )
                db.commit()
                self.executor.submit(self.run, job_id, target, request)
        return self.get(job_id)

    def cancel(self, job_id: UUID) -> GenerationJob:
        # A tombstone also handles cancel arriving before submit/its response.
        with self.lock, closing(self.connect()) as db, db:
            db.execute(
                "INSERT OR IGNORE INTO generation_jobs(id,status) VALUES(?,'cancelled')",
                (str(job_id),),
            )
            db.execute(
                "UPDATE generation_jobs SET status='cancelled',result=NULL,error=NULL WHERE id=? AND status IN ('queued','running')",
                (str(job_id),),
            )
        return self.get(job_id)

    def run(self, job_id: UUID, target: str, request: BackgroundRequest | RoomImageRequest) -> None:
        with closing(self.connect()) as db, db:
            claimed = db.execute(
                "UPDATE generation_jobs SET status='running' WHERE id=? AND status='queued'",
                (str(job_id),),
            ).rowcount
        if not claimed:
            return
        try:
            if isinstance(request, BackgroundRequest):
                result = generate_background(request)
            else:
                result = generate_room(request)
            with closing(self.connect()) as db, db:
                db.execute(
                    "UPDATE generation_jobs SET status='succeeded',result=? WHERE id=? AND status='running'",
                    (result.model_dump_json(), str(job_id)),
                )
        except Exception:
            with closing(self.connect()) as db, db:
                db.execute(
                    "UPDATE generation_jobs SET status='failed',error=? WHERE id=? AND status='running'",
                    (
                        "Generation failed. Check the project and local assets, then retry.",
                        str(job_id),
                    ),
                )

    def close(self) -> None:
        with closing(self.connect()) as db, db:
            db.execute(
                "UPDATE generation_jobs SET status='failed',error=? WHERE status IN ('queued','running')",
                ("Generation interrupted by server shutdown. Generate again.",),
            )
        self.executor.shutdown(wait=True, cancel_futures=True)
