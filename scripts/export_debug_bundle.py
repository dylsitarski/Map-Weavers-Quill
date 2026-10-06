"""Export one saved project as a readable debugging bundle (folder plus zip).

Read-only: the local database is opened with SQLite's read-only mode, so this never
changes projects, even while Quill is running. The bundle contains the project's
prompts, images and generation records; treat it as private project content.

Usage (from the repository root):
    PYTHONPATH=apps/server .venv/bin/python scripts/export_debug_bundle.py --list
    PYTHONPATH=apps/server .venv/bin/python scripts/export_debug_bundle.py "Cottage test"
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image
from quill.backgrounds import BackgroundResult
from quill.models import GenerationRecord, Project
from quill.projects import ProjectStore

# Input hash order written by background/room generation (ADR-0017, ADR-0029).
INPUT_ROLES = ("source", "mask", "guide")
# Masks and guides/sketches need exact pixels and compress well; artwork does not.
EXACT_ROLES = {"mask", "guide"}
WARN_BYTES = 25 * 1024 * 1024


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "untitled"


def connect(data_dir: Path) -> sqlite3.Connection:
    path = data_dir / "projects.sqlite3"
    if not path.exists():
        raise SystemExit(f"No Quill database at {path}. Use --data-dir or set MWQ_DATA_DIR.")
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def projects(db: sqlite3.Connection) -> list[tuple[str, str, int]]:
    return db.execute(
        "SELECT p.id, s.name, p.revision FROM projects p "
        "JOIN snapshots s ON s.project_id=p.id AND s.revision=p.revision ORDER BY s.name, p.id"
    ).fetchall()


def resolve(db: sqlite3.Connection, query: str) -> str:
    rows = projects(db)
    try:
        wanted = str(UUID(query))
        matches = [row for row in rows if row[0] == wanted]
    except ValueError:
        matches = [row for row in rows if row[1].casefold() == query.casefold()]
    if len(matches) == 1:
        return matches[0][0]
    if not matches:
        raise SystemExit(f"No saved project named or with ID {query!r}. Use --list.")
    listing = "\n".join(f"  {row[0]}  revision {row[2]}" for row in matches)
    raise SystemExit(f"Several projects are named {query!r}; pass an ID:\n{listing}")


def load(db: sqlite3.Connection, project_id: str, revision: int | None) -> Project:
    if revision is None:
        row = db.execute(
            "SELECT s.document FROM snapshots s JOIN projects p "
            "ON s.project_id=p.id AND s.revision=p.revision WHERE p.id=?",
            (project_id,),
        ).fetchone()
    else:
        row = db.execute(
            "SELECT document FROM snapshots WHERE project_id=? AND revision=?",
            (project_id, revision),
        ).fetchone()
    if row is None:
        raise SystemExit("That project revision is not in the database.")
    return Project.model_validate_json(row[0])


class Writer:
    """Writes assets by hash, remembering any that are missing or corrupt."""

    def __init__(self, db: sqlite3.Connection, *, lossless: bool = False):
        self.db = db
        self.lossless = lossless
        self.missing: list[str] = []

    def image(self, key: str) -> Image.Image | None:
        try:
            data = ProjectStore.read_asset(self.db, key)
        except ValueError:
            self.missing.append(key)
            return None
        with Image.open(BytesIO(data)) as opened:
            return opened.copy()

    def save(
        self, key: str, path: Path, crop: list[int] | None = None, *, exact: bool = False
    ) -> None:
        """Save as PNG when exact (or --lossless), otherwise as compact WebP."""
        picture = self.image(key)
        if picture is None:
            return
        png = exact or self.lossless
        suffix = ".png" if png else ".webp"
        options = {} if png else {"quality": 85, "method": 4}
        picture.save(path.with_suffix(suffix), **options)
        if crop is not None and len(crop) == 4:
            picture.crop(tuple(crop)).save(path.with_name(path.name + "-crop" + suffix), **options)


def write_generation(
    writer: Writer, record: GenerationRecord, folder: Path, extra: dict | None = None
) -> None:
    folder.mkdir(parents=True)
    (folder / "prompt.txt").write_text(record.prompt + "\n")
    (folder / "record.json").write_text(
        json.dumps(record.model_dump(mode="json") | (extra or {}), indent=2) + "\n"
    )
    crop = record.parameters.get("crop")
    crop = crop if isinstance(crop, list) else None
    for index, key in enumerate(record.inputHashes):
        role = INPUT_ROLES[index] if index < len(INPUT_ROLES) else f"input-{index + 1}"
        writer.save(key, folder / f"input-{index + 1}-{role}", crop, exact=role in EXACT_ROLES)
    if record.outputHash:
        writer.save(record.outputHash, folder / "output", crop)


def summary(project: Project) -> str:
    style = project.map.style
    background = project.settings.get("quill.background")
    lines = [
        f"Project: {project.name}",
        f"ID: {project.projectId}  revision: {project.revision}",
        f"Map: {project.map.width:g} x {project.map.height:g} units, grid "
        f"{project.map.grid.sizePx:g} units = {project.map.grid.distance:g} {project.map.grid.units}",
        "",
        "Map style:",
        f"  environment (unused since ADR-0033): {style.environment}",
        f"  render style: {style.renderStyle}",
        f"  palette: {style.palette}",
        f"  wall thickness: {style.wallThicknessPx:g}",
        f"Background prompt: {background.get('prompt') if isinstance(background, dict) else ''}",
        "",
        "Rooms:",
    ]
    for room in project.rooms:
        points = ", ".join(f"({p.x:g},{p.y:g})" for p in room.polygon)
        lines += [
            f"- {room.label} [{room.id}]",
            f"  prompt: {room.prompt}",
            f"  style overrides: {json.dumps(room.styleOverrides)}",
            f"  artwork layer: {room.renderLayerId}",
            f"  polygon: {points}",
        ]
    lines += ["", "Doors:"]
    for door in project.doors:
        lines.append(
            f"- {door.label}: {door.doorType}, {door.state}"
            f"{', secret' if door.secret else ''}, width {door.width:g}, "
            f"position {door.position:.3f} on wall {door.wallId}"
        )
    return "\n".join(lines) + "\n"


def export(
    data_dir: Path,
    query: str,
    output: Path,
    *,
    revision: int | None = None,
    background_jobs: bool = False,
    last: int = 3,
    lossless: bool = False,
) -> Path:
    """Export a bundle. `last` keeps only the most recent N accepted generations and N
    previews (0 keeps all); artwork is WebP unless `lossless`."""
    if output.exists():
        raise SystemExit(f"{output} already exists; choose another --output.")
    db = connect(data_dir)
    try:
        project_id = resolve(db, query)
        project = load(db, project_id, revision)
        writer = Writer(db, lossless=lossless)
        output.mkdir(parents=True)
        (output / "project.json").write_text(project.model_dump_json(indent=2) + "\n")
        (output / "summary.txt").write_text(summary(project))

        layers = output / "layers"
        layers.mkdir()
        rooms = {str(room.id): room.label for room in project.rooms}
        layer_info = []
        for layer in sorted(project.layers, key=lambda layer: layer.zIndex):
            role = layer.metadata.get("quill.render")
            role = role if isinstance(role, dict) else {}
            name = (
                "background"
                if role.get("role") == "background"
                else f"room-{slug(rooms.get(str(role.get('roomId')), 'room'))}"
            )
            filename = f"{layer.zIndex:02d}-{name}" + (".png" if lossless else ".webp")
            writer.save(layer.assetHash, layers / filename)
            layer_info.append(
                {
                    "file": filename,
                    "zIndex": layer.zIndex,
                    "visible": layer.visible,
                    "opacity": layer.opacity,
                    "assetHash": layer.assetHash,
                }
            )
        (layers / "layers.json").write_text(json.dumps(layer_info, indent=2) + "\n")

        accepted = {record.outputHash for record in project.generations}
        numbered = list(enumerate(project.generations, 1))
        kept_generations = numbered[-last:] if last else numbered
        for number, record in kept_generations:
            target = record.metadata.get("quill.generation")
            target = target.get("target", "unknown") if isinstance(target, dict) else "unknown"
            write_generation(
                writer,
                record,
                output / "generations" / f"{number:02d}-{target}-{slug(record.label)}",
            )

        has_jobs = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='generation_jobs'"
        ).fetchone()
        rows = (
            db.execute(
                "SELECT id, target, request, status, result, error, created_at "
                "FROM generation_jobs WHERE request IS NOT NULL ORDER BY created_at, rowid"
            ).fetchall()
            if has_jobs
            else []
        )
        matching = []
        for job_id, target, request, status, result, error, created in rows:
            payload = json.loads(request)
            if target == "room":
                if payload.get("project", {}).get("projectId") != project_id:
                    continue
                room_id = payload.get("roomId")
                about = {
                    "roomId": room_id,
                    "room": rooms.get(str(room_id), "(room no longer in project)"),
                    "seed": payload.get("seed"),
                    "projectRevision": payload.get("project", {}).get("revision"),
                }
            elif background_jobs:
                about = {key: payload.get(key) for key in ("prompt", "seed", "style")}
            else:
                continue
            matching.append((job_id, target, status, result, error, created, about))
        numbered_jobs = list(enumerate(matching, 1))
        kept_jobs = numbered_jobs[-last:] if last else numbered_jobs
        for number, (job_id, target, status, result, error, created, about) in kept_jobs:
            folder = output / "jobs" / f"{number:02d}-{status}-{target}-{job_id[:8]}"
            extra = {"job": {"id": job_id, "status": status, "created": created, **about}}
            if result:
                generation = BackgroundResult.model_validate_json(result).generation
                extra["job"]["accepted"] = generation.outputHash in accepted
                write_generation(writer, generation, folder, extra)
            else:
                folder.mkdir(parents=True)
                (folder / "job.json").write_text(json.dumps(extra | {"error": error}, indent=2))

        (output / "README.txt").write_text(
            "Map-Weaver's Quill debugging bundle (private project content).\n"
            f"Exported {datetime.now(UTC).isoformat(timespec='seconds')} from {data_dir}.\n\n"
            "summary.txt     map style, background prompt, rooms with prompts, doors\n"
            "project.json    the saved project document\n"
            "layers/         current artwork layers by zIndex, plus layers.json\n"
            "generations/    accepted generations: prompt.txt (exact model prompt),\n"
            "                record.json (all parameters), input and output images;\n"
            "                *-crop files show the room's working window\n"
            "jobs/           queued previews for this project, including unaccepted ones\n"
            + (
                "                (background jobs from every project are included)\n"
                if background_jobs
                else ""
            )
            + f"\nIncluded {len(kept_generations)} of {len(numbered)} accepted generations and "
            f"{len(kept_jobs)} of {len(numbered_jobs)} previews"
            + (" (the most recent; use --last 0 for all).\n" if last else ".\n")
            + (
                "Images are PNG.\n"
                if lossless
                else "Artwork is WebP (quality 85); masks, guides and sketches are exact PNG.\n"
            )
            + (
                f"\nMissing or corrupt assets: {', '.join(writer.missing)}\n"
                if writer.missing
                else ""
            )
        )
    finally:
        db.close()
    archive = shutil.make_archive(str(output), "zip", root_dir=output.parent, base_dir=output.name)
    return Path(archive)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("project", nargs="?", help="Saved project name or ID")
    parser.add_argument("--list", action="store_true", help="List saved projects and exit")
    parser.add_argument("--revision", type=int, help="Export this saved revision instead")
    parser.add_argument("--output", type=Path, help="New folder to create (default: under data/)")
    parser.add_argument(
        "--background-jobs",
        action="store_true",
        help="Also include background previews; these are not linked to a project",
    )
    parser.add_argument(
        "--last",
        type=int,
        default=3,
        help="Keep the most recent N accepted generations and N previews (0: all; default 3)",
    )
    parser.add_argument(
        "--lossless", action="store_true", help="Save artwork as PNG instead of WebP (larger)"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("MWQ_DATA_DIR", "data")),
        help="Quill data directory (default: MWQ_DATA_DIR or ./data)",
    )
    args = parser.parse_args()
    if args.list or not args.project:
        db = connect(args.data_dir)
        try:
            rows = projects(db)
        finally:
            db.close()
        for project_id, name, revision in rows:
            print(f"{project_id}  revision {revision}  {name}")
        if not rows:
            print("No saved projects.")
        return
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    output = args.output or args.data_dir / f"debug-{slug(args.project)}-{stamp}"
    archive = export(
        args.data_dir,
        args.project,
        output,
        revision=args.revision,
        background_jobs=args.background_jobs,
        last=max(0, args.last),
        lossless=args.lossless,
    )
    size = archive.stat().st_size
    print(f"Wrote {output}/ and {archive} ({size / 1024 / 1024:.1f} MB)")
    if size > WARN_BYTES:
        print("That is over 25 MB; try a smaller --last (for example --last 1).")
    print("It contains your prompts and images for this project; share it privately.")


if __name__ == "__main__":
    main()
