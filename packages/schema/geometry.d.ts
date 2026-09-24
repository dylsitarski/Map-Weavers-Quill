/* Generated. Run make schema; do not edit. */

export type Id = string;
/**
 * @minItems 3
 * @maxItems 2048
 */
export type Polygon = [Point, Point, Point, ...Point[]];
export type X = number;
export type Y = number;
/**
 * @maxItems 128
 */
export type Beforerooms = RoomBoundary[];
export type Contractversion = "0.1.0";
export type Doortype = "door" | "window";
export type Id1 = string;
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
 */
export type JsonValue = unknown;
export type Position = number;
export type Revision = number;
export type Secret = boolean;
export type State = "open" | "closed" | "locked";
export type Wallid = string;
export type Width = number;
/**
 * @maxItems 1024
 */
export type Doors = DoorInput[];
export type Height = number;
/**
 * @maxItems 128
 */
export type Rooms = RoomBoundary[];
export type Width1 = number;
export type Contractversion1 = "0.1.0";
export type Doortype1 = "door" | "window";
export type Id2 = string;
export type Kind1 = "door";
export type Label1 = string;
export type Position1 = number;
export type Revision1 = number;
export type Secret1 = boolean;
export type State1 = "open" | "closed" | "locked";
export type Wallid1 = string;
export type Width2 = number;
/**
 * @maxItems 1024
 */
export type Doors1 = Door[];
export type Id3 = string;
export type Kind2 = "wall";
export type Label2 = string;
export type Movement = boolean;
export type Revision2 = number;
export type Sight = boolean;
export type Sourceroomid = string | null;
/**
 * @maxItems 8192
 */
export type Walls = Wall[];
export type Contractversion2 = "0.1.0";
export type Height1 = number;
/**
 * @minItems 3
 * @maxItems 2048
 */
export type Polygon1 = [Point, Point, Point, ...Point[]];
export type Width3 = number;
export type Error = string | null;
export type Valid = boolean;
export type Contractversion3 = "0.1.0";
export type Height2 = number;
/**
 * @maxItems 128
 */
export type Rooms1 = RoomBoundary[];
export type Width4 = number;
export type Contractversion4 = "0.1.0";
/**
 * @maxItems 8192
 */
export type Walls1 = Wall[];

export interface GeometryContracts {
  doorRequest: DoorRequest;
  doorResult: DoorResult;
  request: GeometryRequest;
  result: GeometryResult;
  wallRequest: WallDerivationRequest;
  wallResult: WallDerivationResult;
  [k: string]: unknown;
}
export interface DoorRequest {
  beforeRooms: Beforerooms;
  contractVersion?: Contractversion;
  doors: Doors;
  height: Height;
  rooms: Rooms;
  width: Width1;
}
export interface RoomBoundary {
  id: Id;
  polygon: Polygon;
}
export interface Point {
  x: X;
  y: Y;
}
export interface DoorInput {
  doorType: Doortype;
  id: Id1;
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
export interface DoorResult {
  contractVersion?: Contractversion1;
  doors: Doors1;
  walls: Walls;
}
export interface Door {
  doorType: Doortype1;
  id: Id2;
  kind: Kind1;
  label: Label1;
  metadata: Metadata1;
  position: Position1;
  revision: Revision1;
  secret: Secret1;
  state: State1;
  wallId: Wallid1;
  width: Width2;
}
export interface Metadata1 {
  [k: string]: JsonValue;
}
export interface Wall {
  end: Point;
  id: Id3;
  kind: Kind2;
  label: Label2;
  metadata: Metadata2;
  movement: Movement;
  revision: Revision2;
  sight: Sight;
  sourceRoomId: Sourceroomid;
  start: Point;
}
export interface Metadata2 {
  [k: string]: JsonValue;
}
export interface GeometryRequest {
  contractVersion?: Contractversion2;
  height: Height1;
  polygon: Polygon1;
  width: Width3;
}
export interface GeometryResult {
  error: Error;
  valid: Valid;
}
export interface WallDerivationRequest {
  contractVersion?: Contractversion3;
  height: Height2;
  rooms: Rooms1;
  width: Width4;
}
export interface WallDerivationResult {
  contractVersion?: Contractversion4;
  walls: Walls1;
}
