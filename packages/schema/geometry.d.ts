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

export interface GeometryContracts {
  request: GeometryRequest;
  result: GeometryResult;
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
