/* Generated. Run make schema; do not edit. */

export type Id = string;
export type Kind = "door";
export type Label = string;
export type Position = number;
export type Revision = number;
export type Secret = boolean;
export type State = "open" | "closed" | "locked";
export type Wallid = string;
export type Width = number;
export type Doors = Door[];
export type Assethash = string;
export type Height = number;
export type X = number;
export type Y = number;
export type Width1 = number;
export type Id1 = string;
export type Kind1 = "raster";
export type Label1 = string;
export type Opacity = number;
export type Revision1 = number;
export type Rotation = number;
export type Visible = boolean;
export type Zindex = number;
export type Layers = RasterLayer[];
export type Brightradius = number;
export type Color = string;
export type Dimradius = number;
export type Id2 = string;
export type Intensity = number;
export type Kind2 = "light";
export type Label2 = string;
export type Revision2 = number;
export type Units = "ft" | "m";
export type Lights = Light[];
export type Coordinatesystem = "bottom-left-y-up-ccw";
export type Distance = number;
export type Sizepx = number;
export type Snap = boolean;
export type Type = "square";
export type Units1 = "ft" | "m";
export type Visible1 = boolean;
export type Height1 = number;
export type Width2 = number;
export type Name = string;
export type Projectid = string;
export type Revision3 = number;
export type Id3 = string;
export type Kind3 = "room";
export type Label3 = string;
/**
 * @minItems 3
 */
export type Polygon = [Point, Point, Point, ...Point[]];
export type Prompt = string;
export type Revision4 = number;
export type Rooms = Room[];
export type Schemaversion = "0.1.0";
export type JsonValue = unknown;
export type Id4 = string;
export type Kind4 = "wall";
export type Label4 = string;
export type Movement = boolean;
export type Revision5 = number;
export type Sight = boolean;
export type Walls = Wall[];

export interface Project {
  doors: Doors;
  layers: Layers;
  lights: Lights;
  map: Map;
  name: Name;
  projectId: Projectid;
  revision: Revision3;
  rooms: Rooms;
  schemaVersion: Schemaversion;
  settings: Settings;
  walls: Walls;
}
export interface Door {
  id: Id;
  kind: Kind;
  label: Label;
  position: Position;
  revision: Revision;
  secret: Secret;
  state: State;
  wallId: Wallid;
  width: Width;
}
export interface RasterLayer {
  assetHash: Assethash;
  bounds: Bounds;
  id: Id1;
  kind: Kind1;
  label: Label1;
  opacity: Opacity;
  revision: Revision1;
  rotation: Rotation;
  visible: Visible;
  zIndex: Zindex;
}
export interface Bounds {
  height: Height;
  origin: Point;
  width: Width1;
}
export interface Point {
  x: X;
  y: Y;
}
export interface Light {
  brightRadius: Brightradius;
  color: Color;
  dimRadius: Dimradius;
  id: Id2;
  intensity: Intensity;
  kind: Kind2;
  label: Label2;
  origin: Point;
  revision: Revision2;
  units: Units;
}
export interface Map {
  coordinateSystem: Coordinatesystem;
  grid: Grid;
  height: Height1;
  width: Width2;
}
export interface Grid {
  distance: Distance;
  sizePx: Sizepx;
  snap: Snap;
  type: Type;
  units: Units1;
  visible: Visible1;
}
export interface Room {
  id: Id3;
  kind: Kind3;
  label: Label3;
  polygon: Polygon;
  prompt: Prompt;
  revision: Revision4;
}
export interface Settings {
  [k: string]: JsonValue;
}
export interface Wall {
  end: Point;
  id: Id4;
  kind: Kind4;
  label: Label4;
  movement: Movement;
  revision: Revision5;
  sight: Sight;
  start: Point;
}
