"""Native editor snapshots in a transactional local SQLite store."""

import hashlib
import os
import sqlite3
from io import BytesIO
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from PIL import Image, ImageChops
from pydantic import Field

from quill.doors import validate_doors
from quill.models import Contract, Project
from quill.raster import image, polygon_mask
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
            project.objects,
            project.regions,
            project.sounds,
        )
    ):
        raise ValueError(
            "This editor cannot yet open projects containing lights, objects, regions or sounds."
        )
    entities = [
        *project.rooms,
        *project.walls,
        *project.doors,
        *project.layers,
        *project.generations,
    ]
    if len({entity.id for entity in entities}) != len(entities):
        raise ValueError("Entity IDs must be unique across the project.")
    if len(project.layers) > 129 or len(project.generations) > 128:
        raise ValueError("At most 129 raster layers and 128 generation records are supported.")
    layers = {layer.id: layer for layer in project.layers}
    rooms = {str(room.id): room for room in project.rooms}
    backgrounds = 0
    for layer in project.layers:
        role = layer.metadata.get("quill.render")
        if (
            not isinstance(role, dict)
            or layer.bounds.origin.x != 0
            or layer.bounds.origin.y != 0
            or layer.bounds.width != 1200
            or layer.bounds.height != 800
            or layer.rotation != 0
            or layer.blendMode != "normal"
        ):
            raise ValueError("Unsupported raster transform or metadata.")
        if role.get("role") == "background":
            backgrounds += 1
            if backgrounds > 1 or layer.zIndex != 0:
                raise ValueError("One base background at zIndex zero is supported.")
        elif role.get("role") == "room":
            room = rooms.get(str(role.get("roomId")))
            if room is None or room.renderLayerId != layer.id or layer.zIndex <= 0:
                raise ValueError(
                    "Room artwork must have one matching room reference and positive zIndex."
                )
        else:
            raise ValueError("Unsupported raster role.")
    for room in project.rooms:
        if room.renderLayerId is not None:
            referenced_layer = layers.get(room.renderLayerId)
            role = referenced_layer.metadata.get("quill.render") if referenced_layer else None
            if (
                not isinstance(role, dict)
                or role.get("roomId") != str(room.id)
                or role.get("role") != "room"
            ):
                raise ValueError("A room references an unavailable or mismatched render layer.")
    for record in project.generations:
        if (
            record.providerId != "mock"
            or record.capability not in {"text_to_image", "inpainting"}
            or record.status != "succeeded"
            or record.outputHash is None
            or record.baseRevision > project.revision
        ):
            raise ValueError("Unsupported mock generation provenance.")
        if (record.capability == "text_to_image" and record.inputHashes) or (
            record.capability == "inpainting" and len(record.inputHashes) != 2
        ):
            raise ValueError("Invalid mock generation input references.")
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
    all_ids = [
        entity.id
        for entity in [
            *project.rooms,
            *walls,
            *project.doors,
            *project.layers,
            *project.generations,
        ]
    ]
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
            CREATE TABLE IF NOT EXISTS assets (
                hash TEXT PRIMARY KEY, content BLOB NOT NULL
            );
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
    def validate_asset(data: bytes) -> str:
        if len(data) > 2 * 1024 * 1024:
            raise ValueError("Raster asset exceeds 2 MiB.")
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG" or image.size != (480, 320):
                raise ValueError("Expected a 480 × 320 PNG background.")
            image.verify()
        return hashlib.sha256(data).hexdigest()

    def put_asset(self, data: bytes) -> str:
        key = self.validate_asset(data)
        db = self.connect()
        try:
            with db:
                db.execute("INSERT OR IGNORE INTO assets(hash, content) VALUES (?, ?)", (key, data))
            return key
        finally:
            db.close()

    @staticmethod
    def read_asset(db: sqlite3.Connection, key: str) -> bytes:
        row = db.execute("SELECT content FROM assets WHERE hash=?", (key,)).fetchone()
        if row is None:
            raise ValueError("A referenced image asset is missing from this computer.")
        data = bytes(row[0])
        if ProjectStore.validate_asset(data) != key:
            raise ValueError("Image asset integrity check failed.")
        return data

    def get_asset(self, key: str) -> bytes:
        db = self.connect()
        try:
            return self.read_asset(db, key)
        finally:
            db.close()

    @staticmethod
    def validate_assets(db: sqlite3.Connection, project: Project) -> None:
        hashes = (
            {layer.assetHash for layer in project.layers}
            | {record.outputHash for record in project.generations if record.outputHash is not None}
            | {key for record in project.generations for key in record.inputHashes}
        )
        assets = {key: ProjectStore.read_asset(db, key) for key in hashes}
        for room in project.rooms:
            if room.renderLayerId is not None:
                layer = next(layer for layer in project.layers if layer.id == room.renderLayerId)
                alpha = image(assets[layer.assetHash]).getchannel("A")
                outside = ImageChops.multiply(alpha, ImageChops.invert(polygon_mask(room.polygon)))
                if outside.getbbox() is not None:
                    raise ValueError("Room artwork contains pixels outside its current polygon.")

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
                self.validate_assets(db, project)
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
            project = validate_project(Project.model_validate_json(row[0]))
            self.validate_assets(db, project)
            return project
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
