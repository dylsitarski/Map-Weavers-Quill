"""Strict structural contracts. Topology and relationship checks are separate."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

Positive = Annotated[float, Field(gt=0)]
Nonnegative = Annotated[float, Field(ge=0)]
Namespace = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$")]
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Point(Contract):
    x: float
    y: float


class Entity(Contract):
    id: UUID
    revision: Annotated[int, Field(ge=0)]
    label: str
    metadata: dict[Namespace, JsonValue] = Field(json_schema_extra={"additionalProperties": False})


class Room(Entity):
    kind: Literal["room"]
    polygon: Annotated[list[Point], Field(min_length=3)]
    prompt: str
    styleOverrides: dict[str, str]
    renderLayerId: UUID | None


class Wall(Entity):
    kind: Literal["wall"]
    start: Point
    end: Point
    movement: bool
    sight: bool
    sourceRoomId: UUID | None


class Door(Entity):
    kind: Literal["door"]
    wallId: UUID
    position: Annotated[float, Field(ge=0, le=1)]
    width: Positive
    state: Literal["open", "closed", "locked"]
    secret: bool
    doorType: Literal["door", "window"]


class Light(Entity):
    kind: Literal["light"]
    origin: Point
    brightRadius: Nonnegative
    dimRadius: Nonnegative
    units: Literal["ft", "m"]
    color: Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
    intensity: Annotated[float, Field(ge=0, le=1)]
    animation: str | None


class Bounds(Contract):
    origin: Point
    width: Positive
    height: Positive


class RasterLayer(Entity):
    kind: Literal["raster"]
    assetHash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    bounds: Bounds
    rotation: Annotated[float, Field(ge=0, lt=360)]
    zIndex: int
    opacity: Annotated[float, Field(ge=0, le=1)]
    visible: bool
    blendMode: Literal["normal", "multiply", "screen"]


class MapObject(Entity):
    kind: Literal["object"]
    anchor: Point
    footprint: Bounds
    rotation: Annotated[float, Field(ge=0, lt=360)]
    description: str
    assetHash: Hash | None
    properties: dict[Namespace, JsonValue] = Field(
        json_schema_extra={"additionalProperties": False}
    )


class Region(Entity):
    kind: Literal["region"]
    polygons: Annotated[list[Annotated[list[Point], Field(min_length=3)]], Field(min_length=1)]
    regionType: Literal["hazard", "difficult_terrain", "annotation"]
    visualStyle: dict[str, str]
    behavior: dict[Namespace, JsonValue] = Field(json_schema_extra={"additionalProperties": False})


class Sound(Entity):
    kind: Literal["sound"]
    origin: Point
    radius: Nonnegative
    units: Literal["ft", "m"]
    assetHash: Hash
    volume: Annotated[float, Field(ge=0, le=1)]


class GenerationRecord(Entity):
    kind: Literal["generation"]
    providerId: str
    capability: str
    prompt: str
    inputHashes: list[Hash]
    outputHash: Hash | None
    parameters: dict[str, JsonValue]
    status: Literal["pending", "running", "succeeded", "failed", "cancelled", "stale"]
    baseRevision: Annotated[int, Field(ge=0)]


class MapStyle(Contract):
    camera: Literal["strict orthographic top-down"]
    environment: str
    renderStyle: str
    palette: str
    wallThicknessPx: Positive
    bakedLighting: Literal["neutral"]


class Grid(Contract):
    type: Literal["square"]
    sizePx: Positive
    distance: Positive
    units: Literal["ft", "m"]
    visible: bool
    snap: bool


class Map(Contract):
    width: Positive
    height: Positive
    coordinateSystem: Literal["bottom-left-y-up-ccw"]
    grid: Grid
    style: MapStyle


class Project(Contract):
    schemaVersion: Literal["0.1.0"]
    projectId: UUID
    revision: Annotated[int, Field(ge=0)]
    name: Annotated[str, Field(min_length=1)]
    map: Map
    rooms: list[Room]
    walls: list[Wall]
    doors: list[Door]
    lights: list[Light]
    layers: list[RasterLayer]
    objects: list[MapObject]
    regions: list[Region]
    sounds: list[Sound]
    generations: list[GenerationRecord]
    settings: dict[str, JsonValue]
