"""Loopback editor API and local project snapshots."""

import re
import sqlite3
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from quill.backgrounds import BackgroundRequest, BackgroundResult, generate_background
from quill.doors import DoorRequest, DoorResult, reconcile_doors
from quill.geometry import GeometryRequest, GeometryResult, validate_geometry
from quill.models import Project
from quill.projects import ProjectList, SaveConflict, SaveRequest, project_store
from quill.providers import MockProvider, ProviderDescriptor
from quill.room_images import RoomImageRequest, generate_room
from quill.walls import WallDerivationRequest, WallDerivationResult, derive_walls

app = FastAPI(title="Map-Weaver's Quill", version="0.0.0")
provider = MockProvider()


@app.get("/health")
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/providers", response_model=list[ProviderDescriptor])
def providers() -> list[ProviderDescriptor]:
    return [provider.descriptor()]


@app.post("/api/geometry/validate", response_model=GeometryResult)
def geometry(request: GeometryRequest) -> GeometryResult:
    return validate_geometry(request)


@app.post("/api/geometry/walls", response_model=WallDerivationResult)
def walls(request: WallDerivationRequest) -> WallDerivationResult:
    try:
        return derive_walls(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/geometry/doors", response_model=DoorResult)
def doors(request: DoorRequest) -> DoorResult:
    try:
        return reconcile_doors(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/projects", response_model=ProjectList)
def list_projects() -> ProjectList:
    try:
        return project_store().list()
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(503, "Could not read the local project store.") from error


@app.get("/api/projects/{project_id}", response_model=Project)
def open_project(project_id: UUID) -> Project:
    try:
        return project_store().open(project_id)
    except KeyError as error:
        raise HTTPException(404, "Saved project not found.") from error
    except ValueError as error:
        raise HTTPException(
            422, "Saved project is invalid or unsupported. It was not opened."
        ) from error
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(503, "Could not read the local project store.") from error


@app.post("/api/projects/save", response_model=Project)
async def save_project(request: Request) -> Project:
    # JSON-only local writes block simple cross-site form submissions. No CORS.
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise HTTPException(415, "Use application/json.")
    origin = request.headers.get("origin")
    if origin and origin not in {
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    }:
        raise HTTPException(403, "Only the local editor may save projects.")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 4 * 1024 * 1024:
            raise HTTPException(413, "Project exceeds the 4 MiB save limit.")
    try:
        data = SaveRequest.model_validate_json(bytes(body))
        return await run_in_threadpool(project_store().save, data)
    except SaveConflict as error:
        raise HTTPException(409, str(error)) from error
    except ValidationError as error:
        raise HTTPException(422, "Invalid project format or unsupported schema version.") from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(
            503, "Save failed. The previous saved snapshot remains available; retry saving."
        ) from error


@app.post("/api/generation/background", response_model=BackgroundResult)
async def background(request: Request) -> BackgroundResult:
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise HTTPException(415, "Use application/json.")
    origin = request.headers.get("origin")
    if origin and origin not in {
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    }:
        raise HTTPException(403, "Only the local editor may generate images.")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 32768:
            raise HTTPException(413, "Background request is too large.")
    try:
        data = BackgroundRequest.model_validate_json(bytes(body))
        return await run_in_threadpool(generate_background, data)
    except ValueError as error:
        raise HTTPException(422, "Invalid background request or image output.") from error
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(
            503, "Could not store the generated background. Retry generation."
        ) from error


@app.get("/api/assets/{asset_hash}")
def asset(asset_hash: str) -> Response:
    if not re.fullmatch(r"[0-9a-f]{64}", asset_hash):
        raise HTTPException(404, "Image asset not found.")
    try:
        data = project_store().get_asset(asset_hash)
        return Response(
            data,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except ValueError as error:
        raise HTTPException(404, "Image asset is missing or invalid.") from error
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(503, "Could not read the image asset.") from error


@app.post("/api/generation/room", response_model=BackgroundResult)
async def room_image(request: Request) -> BackgroundResult:
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise HTTPException(415, "Use application/json.")
    origin = request.headers.get("origin")
    if origin and origin not in {
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    }:
        raise HTTPException(403, "Only the local editor may generate images.")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 4 * 1024 * 1024:
            raise HTTPException(413, "Room generation request exceeds 4 MiB.")
    try:
        data = RoomImageRequest.model_validate_json(bytes(body))
        return await run_in_threadpool(generate_room, data)
    except ValidationError as error:
        raise HTTPException(422, "Invalid room generation request.") from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(503, "Could not generate or store room artwork. Retry.") from error
