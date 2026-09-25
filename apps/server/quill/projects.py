"""Native editor snapshots in a transactional local SQLite store."""

import os
import sqlite3
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from quill.doors import validate_doors
from quill.models import Contract, Project
from quill.walls import RoomBoundary, WallDerivationRequest, derive_walls


class SaveRequest(Contract):
    contractVersion: Literal["0.1.0"] = "0.1.0"
    expectedRevision: Annotated[int, Field(ge=1)] | None
    project: Project


class ProjectSummary(Contract):
    projectId: UUID
    name: str
    revision: Annotated[int, Field(ge=1)]


class ProjectList(Contract):
    projects: list[ProjectSummary]


class SaveConflict(ValueError):
    pass


def validate_project(project: Project, *, derive_missing: bool = False) -> Project:
    """Accept exactly the currently editable profile; never drop unsupported data."""
    if not project.name.strip():
        raise ValueError("Project name cannot be blank.")
    if project.map.width != 1200 or project.map.height != 800 or project.map.grid.sizePx != 50:
        raise ValueError("This editor supports 1200 × 800 maps with a 50-unit grid.")
    if any(
        (
            project.lights,
            project.layers,
            project.objects,
            project.regions,
            project.sounds,
            project.generations,
        )
    ):
        raise ValueError(
            "This editor cannot yet open projects containing lights, artwork, objects, regions, sounds or generation records."
        )
    entities = [*project.rooms, *project.walls, *project.doors]
    if len({entity.id for entity in entities}) != len(entities):
        raise ValueError("Entity IDs must be unique across the project.")
    if any(room.renderLayerId is not None for room in project.rooms):
        raise ValueError("A room references an unavailable render layer.")
    walls = derive_walls(
        WallDerivationRequest(
            width=project.map.width,
            height=project.map.height,
            rooms=[RoomBoundary(id=room.id, polygon=room.polygon) for room in project.rooms],
        )
    ).walls
    # Empty display caches can be filled at save, but existing walls must match
    # exactly: accepting overrides here would silently lose them in the editor.
    if not (derive_missing and not project.walls and not project.doors):
        if {w.id: w for w in project.walls} != {w.id: w for w in walls}:
            raise ValueError(
                "Stored walls do not match derived room boundaries or contain unsupported overrides."
            )
    all_ids = [entity.id for entity in [*project.rooms, *walls, *project.doors]]
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("Derived wall IDs collide with another project entity.")
    validate_doors(project.doors, walls)
    if len(project.doors) > 1024:
        raise ValueError("At most 1024 doors are supported.")
    return project.model_copy(update={"walls": walls})


class ProjectStore:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                project_id TEXT NOT NULL, revision INTEGER NOT NULL,
                name TEXT NOT NULL, document TEXT NOT NULL,
                PRIMARY KEY(project_id, revision)
            );
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                FOREIGN KEY(id, revision) REFERENCES snapshots(project_id, revision)
            );
        """)
        return db

    @staticmethod
    def publish(db: sqlite3.Connection, project_id: str, revision: int) -> None:
        db.execute(
            "INSERT INTO projects(id, revision) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision",
            (project_id, revision),
        )

    def save(self, request: SaveRequest) -> Project:
        project = validate_project(request.project, derive_missing=True)
        if project.revision != (request.expectedRevision or 0):
            raise SaveConflict("The document revision does not match the expected saved revision.")
        db = self.connect()
        try:
            with db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT revision FROM projects WHERE id=?", (str(project.projectId),)
                ).fetchone()
                actual = row[0] if row else None
                if actual != request.expectedRevision:
                    raise SaveConflict(
                        "This project changed in another session. Reopen it before saving; your current edits have not been overwritten."
                    )
                saved = project.model_copy(update={"revision": (actual or 0) + 1})
                document = saved.model_dump_json()
                # Validate the serialized snapshot before publishing its pointer.
                validate_project(Project.model_validate_json(document))
                db.execute(
                    "INSERT INTO snapshots VALUES (?, ?, ?, ?)",
                    (str(saved.projectId), saved.revision, saved.name, document),
                )
                self.publish(db, str(saved.projectId), saved.revision)
            return saved
        finally:
            db.close()

    def open(self, project_id: UUID) -> Project:
        db = self.connect()
        try:
            row = db.execute(
                "SELECT document FROM snapshots s JOIN projects p ON s.project_id=p.id AND s.revision=p.revision WHERE p.id=?",
                (str(project_id),),
            ).fetchone()
            if row is None:
                raise KeyError(project_id)
            return validate_project(Project.model_validate_json(row[0]))
        finally:
            db.close()

    def list(self) -> ProjectList:
        db = self.connect()
        try:
            rows = db.execute(
                "SELECT p.id, s.name, p.revision FROM projects p JOIN snapshots s ON s.project_id=p.id AND s.revision=p.revision ORDER BY s.name, p.id"
            ).fetchall()
            return ProjectList(
                projects=[
                    ProjectSummary(projectId=UUID(id), name=name, revision=revision)
                    for id, name, revision in rows
                ]
            )
        finally:
            db.close()


def project_store() -> ProjectStore:
    root = Path(os.environ.get("MWQ_DATA_DIR", "data"))
    return ProjectStore(root / "projects.sqlite3")
