/* Generated. Run make schema; do not edit. */

export type Baserevision = number;
export type Contractversion = "0.1.0";
export type Prompt = string;
export type Seed = number;
export type Contractversion1 = "0.1.0";
export type Baserevision1 = number;
export type Capability = string;
export type Id = string;
export type Inputhashes = string[];
export type Kind = "generation";
export type Label = string;
/**
 * This interface was referenced by `Metadata`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 *
 * This interface was referenced by `Metadata1`'s JSON-Schema definition
 * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
 */
export type JsonValue = unknown;
export type Outputhash = string | null;
export type Prompt1 = string;
export type Providerid = string;
export type Revision = number;
export type Status = "pending" | "running" | "succeeded" | "failed" | "cancelled" | "stale";
export type Assethash = string;
export type Blendmode = "normal" | "multiply" | "screen";
export type Height = number;
export type X = number;
export type Y = number;
export type Width = number;
export type Id1 = string;
export type Kind1 = "raster";
export type Label1 = string;
export type Opacity = number;
export type Revision1 = number;
export type Rotation = number;
export type Visible = boolean;
export type Zindex = number;

export interface RasterContracts {
  request: BackgroundRequest;
  result: BackgroundResult;
  [k: string]: unknown;
}
export interface BackgroundRequest {
  baseRevision: Baserevision;
  contractVersion?: Contractversion;
  prompt: Prompt;
  seed: Seed;
}
export interface BackgroundResult {
  contractVersion?: Contractversion1;
  generation: GenerationRecord;
  layer: RasterLayer;
}
export interface GenerationRecord {
  baseRevision: Baserevision1;
  capability: Capability;
  id: Id;
  inputHashes: Inputhashes;
  kind: Kind;
  label: Label;
  metadata: Metadata;
  outputHash: Outputhash;
  parameters: Parameters;
  prompt: Prompt1;
  providerId: Providerid;
  revision: Revision;
  status: Status;
}
export interface Metadata {
  [k: string]: JsonValue;
}
export interface Parameters {
  [k: string]: JsonValue;
}
export interface RasterLayer {
  assetHash: Assethash;
  blendMode: Blendmode;
  bounds: Bounds;
  id: Id1;
  kind: Kind1;
  label: Label1;
  metadata: Metadata1;
  opacity: Opacity;
  revision: Revision1;
  rotation: Rotation;
  visible: Visible;
  zIndex: Zindex;
}
export interface Bounds {
  height: Height;
  origin: Point;
  width: Width;
}
export interface Point {
  x: X;
  y: Y;
}
export interface Metadata1 {
  [k: string]: JsonValue;
}
