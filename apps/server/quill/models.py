"""Strict structural contracts. Topology and relationship checks are separate."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

Positive = Annotated[float, Field(gt=0)]
Nonnegative = Annotated[float, Field(ge=0)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Point(Contract):
    x: float
    y: float


class Entity(Contract):
    id: UUID
    revision: Annotated[int, Field(ge=0)]
    label: str


class Room(Entity):
    kind: Literal["room"]
    polygon: Annotated[list[Point], Field(min_length=3)]
    prompt: str


class Wall(Entity):
    kind: Literal["wall"]
    start: Point
    end: Point
    movement: bool
    sight: bool


class Door(Entity):
    kind: Literal["door"]
    wallId: UUID
    position: Annotated[float, Field(ge=0, le=1)]
    width: Positive
    state: Literal["open", "closed", "locked"]
    secret: bool


class Light(Entity):
    kind: Literal["light"]
    origin: Point
    brightRadius: Nonnegative
    dimRadius: Nonnegative
    units: Literal["ft", "m"]
    color: Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
    intensity: Annotated[float, Field(ge=0, le=1)]


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
    settings: dict[str, JsonValue]
