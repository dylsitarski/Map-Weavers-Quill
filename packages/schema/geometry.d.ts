/* Generated. Run make schema; do not edit. */

export type Contractversion = "0.1.0";
export type Height = number;
/**
 * @minItems 3
 * @maxItems 2048
 */
export type Polygon = [Point, Point, Point, ...Point[]];
export type X = number;
export type Y = number;
export type Width = number;
export type Error = string | null;
export type Valid = boolean;
export type Contractversion1 = "0.1.0";
export type Height1 = number;
export type Id = string;
/**
 * @minItems 3
 * @maxItems 2048
 */
export type Polygon1 = [Point, Point, Point, ...Point[]];
/**
 * @maxItems 128
 */
export type Rooms = RoomBoundary[];
export type Width1 = number;
export type Contractversion2 = "0.1.0";
export type Id1 = string;
export type Kind = "wall";
export type Label = string;
/**
 * This interface was referenced by `Metadata`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 */
export type JsonValue = unknown;
export type Movement = boolean;
export type Revision = number;
export type Sight = boolean;
export type Sourceroomid = string | null;
/**
 * @maxItems 8192
 */
export type Walls = Wall[];

export interface GeometryContracts {
  request: GeometryRequest;
  result: GeometryResult;
  wallRequest: WallDerivationRequest;
  wallResult: WallDerivationResult;
  [k: string]: unknown;
}
export interface GeometryRequest {
  contractVersion?: Contractversion;
  height: Height;
  polygon: Polygon;
  width: Width;
}
export interface Point {
  x: X;
  y: Y;
}
export interface GeometryResult {
  error: Error;
  valid: Valid;
}
export interface WallDerivationRequest {
  contractVersion?: Contractversion1;
  height: Height1;
  rooms: Rooms;
  width: Width1;
}
export interface RoomBoundary {
  id: Id;
  polygon: Polygon1;
}
export interface WallDerivationResult {
  contractVersion?: Contractversion2;
  walls: Walls;
}
export interface Wall {
  end: Point;
  id: Id1;
  kind: Kind;
  label: Label;
  metadata: Metadata;
  movement: Movement;
  revision: Revision;
  sight: Sight;
  sourceRoomId: Sourceroomid;
  start: Point;
}
export interface Metadata {
  [k: string]: JsonValue;
}
