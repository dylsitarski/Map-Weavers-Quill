/* Generated. Run make schema; do not edit. */

export type Contractversion = "0.1.0";
export type Format = "png" | "webp";
export type Doortype = "door" | "window";
export type Id = string;
export type Kind = "door";
export type Label = string;
/**
 * This interface was referenced by `Metadata`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 *
 * This interface was referenced by `Metadata1`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 *
 * This interface was referenced by `Metadata2`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 *
 * This interface was referenced by `Metadata3`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 *
 * This interface was referenced by `Metadata4`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 *
 * This interface was referenced by `Properties`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 *
 * This interface was referenced by `Behavior`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 *
 * This interface was referenced by `Metadata5`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 *
 * This interface was referenced by `Metadata6`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 *
 * This interface was referenced by `Metadata7`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 *
 * This interface was referenced by `Metadata8`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 */
export type JsonValue = unknown;
export type Position = number;
export type Revision = number;
export type Secret = boolean;
export type State = "open" | "closed" | "locked";
export type Wallid = string;
export type Width = number;
export type Doors = Door[];
export type Baserevision = number;
export type Capability = string;
export type Id1 = string;
export type Inputhashes = string[];
export type Kind1 = "generation";
export type Label1 = string;
export type Outputhash = string | null;
export type Prompt = string;
export type Providerid = string;
export type Revision1 = number;
export type Status = "pending" | "running" | "succeeded" | "failed" | "cancelled" | "stale";
export type Generations = GenerationRecord[];
export type Assethash = string;
export type Blendmode = "normal" | "multiply" | "screen";
export type Height = number;
export type X = number;
export type Y = number;
export type Width1 = number;
export type Id2 = string;
export type Kind2 = "raster";
export type Label2 = string;
export type Opacity = number;
export type Revision2 = number;
export type Rotation = number;
export type Visible = boolean;
export type Zindex = number;
export type Layers = RasterLayer[];
export type Animation = string | null;
export type Brightradius = number;
export type Color = string;
export type Dimradius = number;
export type Id3 = string;
export type Intensity = number;
export type Kind3 = "light";
export type Label3 = string;
export type Revision3 = number;
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
export type Bakedlighting = "neutral";
export type Camera = "strict orthographic top-down";
export type Environment = string;
export type Palette = string;
export type Renderstyle = string;
export type Wallthicknesspx = number;
export type Width2 = number;
export type Name = string;
export type Assethash1 = string | null;
export type Description = string;
export type Id4 = string;
export type Kind4 = "object";
export type Label4 = string;
export type Revision4 = number;
export type Rotation1 = number;
export type Objects = MapObject[];
export type Projectid = string;
export type Id5 = string;
export type Kind5 = "region";
export type Label5 = string;
/**
 * @minItems 1
 */
export type Polygons = [[Point, Point, Point, ...Point[]], ...[Point, Point, Point, ...Point[]][]];
export type Regiontype = "hazard" | "difficult_terrain" | "annotation";
export type Revision5 = number;
export type Regions = Region[];
export type Revision6 = number;
export type Id6 = string;
export type Kind6 = "room";
export type Label6 = string;
/**
 * @minItems 3
 */
export type Polygon = [Point, Point, Point, ...Point[]];
export type Prompt1 = string;
export type Renderlayerid = string | null;
export type Revision7 = number;
export type Rooms = Room[];
export type Schemaversion = "0.1.0";
export type Assethash2 = string;
export type Id7 = string;
export type Kind7 = "sound";
export type Label7 = string;
export type Radius = number;
export type Revision8 = number;
export type Units2 = "ft" | "m";
export type Volume = number;
export type Sounds = Sound[];
export type Id8 = string;
export type Kind8 = "wall";
export type Label8 = string;
export type Movement = boolean;
export type Revision9 = number;
export type Sight = boolean;
export type Sourceroomid = string | null;
export type Walls = Wall[];
export type Error = string | null;
export type Id9 = string;
export type Contractversion1 = "0.1.0";
export type Status1 = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export type Baserevision1 = number;
export type Contractversion2 = "0.1.0";
export type Prompt2 = string;
export type Seed = number;
export type Contractversion3 = "0.1.0";
export type Roomid = string;
export type Seed1 = number;

export interface RasterContracts {
  exportRequest: ExportRequest;
  job: GenerationJob;
  request: BackgroundRequest;
  result: BackgroundResult;
  roomRequest: RoomImageRequest;
  [k: string]: unknown;
}
export interface ExportRequest {
  contractVersion?: Contractversion;
  format: Format;
  project: Project;
}
export interface Project {
  doors: Doors;
  generations: Generations;
  layers: Layers;
  lights: Lights;
  map: Map;
  name: Name;
  objects: Objects;
  projectId: Projectid;
  regions: Regions;
  revision: Revision6;
  rooms: Rooms;
  schemaVersion: Schemaversion;
  settings: Settings;
  sounds: Sounds;
  walls: Walls;
}
export interface Door {
  doorType: Doortype;
  id: Id;
  kind: Kind;
  label: Label;
  metadata: Metadata;
  position: Position;
  revision: Revision;
  secret: Secret;
  state: State;
  wallId: Wallid;
  width: Width;
}
export interface Metadata {
  [k: string]: JsonValue;
}
export interface GenerationRecord {
  baseRevision: Baserevision;
  capability: Capability;
  id: Id1;
  inputHashes: Inputhashes;
  kind: Kind1;
  label: Label1;
  metadata: Metadata1;
  outputHash: Outputhash;
  parameters: Parameters;
  prompt: Prompt;
  providerId: Providerid;
  revision: Revision1;
  status: Status;
}
export interface Metadata1 {
  [k: string]: JsonValue;
}
export interface Parameters {
  [k: string]: JsonValue;
}
export interface RasterLayer {
  assetHash: Assethash;
  blendMode: Blendmode;
  bounds: Bounds;
  id: Id2;
  kind: Kind2;
  label: Label2;
  metadata: Metadata2;
  opacity: Opacity;
  revision: Revision2;
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
export interface Metadata2 {
  [k: string]: JsonValue;
}
export interface Light {
  animation: Animation;
  brightRadius: Brightradius;
  color: Color;
  dimRadius: Dimradius;
  id: Id3;
  intensity: Intensity;
  kind: Kind3;
  label: Label3;
  metadata: Metadata3;
  origin: Point;
  revision: Revision3;
  units: Units;
}
export interface Metadata3 {
  [k: string]: JsonValue;
}
export interface Map {
  coordinateSystem: Coordinatesystem;
  grid: Grid;
  height: Height1;
  style: MapStyle;
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
export interface MapStyle {
  bakedLighting: Bakedlighting;
  camera: Camera;
  environment: Environment;
  palette: Palette;
  renderStyle: Renderstyle;
  wallThicknessPx: Wallthicknesspx;
}
export interface MapObject {
  anchor: Point;
  assetHash: Assethash1;
  description: Description;
  footprint: Bounds;
  id: Id4;
  kind: Kind4;
  label: Label4;
  metadata: Metadata4;
  properties: Properties;
  revision: Revision4;
  rotation: Rotation1;
}
export interface Metadata4 {
  [k: string]: JsonValue;
}
export interface Properties {
  [k: string]: JsonValue;
}
export interface Region {
  behavior: Behavior;
  id: Id5;
  kind: Kind5;
  label: Label5;
  metadata: Metadata5;
  polygons: Polygons;
  regionType: Regiontype;
  revision: Revision5;
  visualStyle: Visualstyle;
}
export interface Behavior {
  [k: string]: JsonValue;
}
export interface Metadata5 {
  [k: string]: JsonValue;
}
export interface Visualstyle {
  [k: string]: string;
}
export interface Room {
  id: Id6;
  kind: Kind6;
  label: Label6;
  metadata: Metadata6;
  polygon: Polygon;
  prompt: Prompt1;
  renderLayerId: Renderlayerid;
  revision: Revision7;
  styleOverrides: Styleoverrides;
}
export interface Metadata6 {
  [k: string]: JsonValue;
}
export interface Styleoverrides {
  [k: string]: string;
}
export interface Settings {
  [k: string]: JsonValue;
}
export interface Sound {
  assetHash: Assethash2;
  id: Id7;
  kind: Kind7;
  label: Label7;
  metadata: Metadata7;
  origin: Point;
  radius: Radius;
  revision: Revision8;
  units: Units2;
  volume: Volume;
}
export interface Metadata7 {
  [k: string]: JsonValue;
}
export interface Wall {
  end: Point;
  id: Id8;
  kind: Kind8;
  label: Label8;
  metadata: Metadata8;
  movement: Movement;
  revision: Revision9;
  sight: Sight;
  sourceRoomId: Sourceroomid;
  start: Point;
}
export interface Metadata8 {
  [k: string]: JsonValue;
}
export interface GenerationJob {
  error?: Error;
  id: Id9;
  result?: BackgroundResult | null;
  status: Status1;
}
export interface BackgroundResult {
  contractVersion?: Contractversion1;
  generation: GenerationRecord;
  layer: RasterLayer;
}
export interface BackgroundRequest {
  baseRevision: Baserevision1;
  contractVersion?: Contractversion2;
  prompt: Prompt2;
  seed: Seed;
  style?: MapStyle | null;
}
export interface RoomImageRequest {
  contractVersion?: Contractversion3;
  project: Project;
  roomId: Roomid;
  seed: Seed1;
}
