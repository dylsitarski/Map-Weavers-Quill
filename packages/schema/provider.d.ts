/* Generated. Run make schema; do not edit. */

export type Capabilities = (
  | "text_to_image"
  | "inpainting"
  | "image_to_image"
  | "reference_image"
  | "control_image"
  | "transparent_background"
  | "seed"
  | "negative_prompt"
  | "maximum_dimensions"
  | "asynchronous_jobs"
)[];
export type Contractversion = "0.1.0";
export type Id = string;
export type Local = boolean;
export type Maxheight = number;
export type Maxwidth = number;
export type Code =
  | "missing_asset"
  | "invalid_image"
  | "unsupported_capability"
  | "invalid_request"
  | "authentication"
  | "rate_limited"
  | "timeout"
  | "unavailable"
  | "cancelled"
  | "invalid_output";
export type Message = string;
export type Retryable = boolean;
export type Contractversion1 = "0.1.0";
export type JsonValue = unknown;
export type Height = number;
export type Negativeprompt = string | null;
export type Prompt = string;
export type Referenceimages = string[];
export type Requestid = string;
export type Seed = number;
export type Width = number;
export type Context = string;
export type Contractversion2 = "0.1.0";
export type Height1 = number;
export type Maskconvention = "white-edit-black-preserve";
export type Maskref = string;
export type Negativeprompt1 = string | null;
export type Prompt1 = string;
export type Referenceimages1 = string[];
export type Requestid1 = string;
export type Seed1 = number;
export type Sourceref = string;
export type Width1 = number;
export type Assethash = string;
export type Contractversion3 = "0.1.0";
export type Height2 = number;
export type Mediatype = "image/png";
export type Providerid = string;
export type Requestid2 = string;
export type Width2 = number;

export interface ProviderContracts {
  descriptor: ProviderDescriptor;
  error: ProviderError;
  generate: GenerateRequest;
  inpaint: InpaintRequest;
  result: GenerationResult;
  [k: string]: unknown;
}
export interface ProviderDescriptor {
  capabilities: Capabilities;
  contractVersion?: Contractversion;
  id: Id;
  local: Local;
  maxHeight: Maxheight;
  maxWidth: Maxwidth;
}
export interface ProviderError {
  code: Code;
  message: Message;
  retryable?: Retryable;
}
export interface GenerateRequest {
  contractVersion?: Contractversion1;
  extensions?: Extensions;
  height: Height;
  negativePrompt?: Negativeprompt;
  parameters?: Parameters;
  prompt: Prompt;
  referenceImages?: Referenceimages;
  requestId: Requestid;
  seed?: Seed;
  width: Width;
}
export interface Extensions {
  /**
   * This interface was referenced by `Extensions`'s JSON-Schema definition
   * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
   */
  [k: string]: {
    [k: string]: JsonValue;
  };
}
export interface Parameters {
  [k: string]: number;
}
export interface InpaintRequest {
  context?: Context;
  contractVersion?: Contractversion2;
  extensions?: Extensions1;
  height: Height1;
  maskConvention: Maskconvention;
  maskRef: Maskref;
  negativePrompt?: Negativeprompt1;
  parameters?: Parameters1;
  prompt: Prompt1;
  referenceImages?: Referenceimages1;
  requestId: Requestid1;
  seed?: Seed1;
  sourceRef: Sourceref;
  width: Width1;
}
export interface Extensions1 {
  /**
   * This interface was referenced by `Extensions1`'s JSON-Schema definition
   * via the `patternProperty` "^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$".
   */
  [k: string]: {
    [k: string]: JsonValue;
  };
}
export interface Parameters1 {
  [k: string]: number;
}
export interface GenerationResult {
  assetHash: Assethash;
  contractVersion?: Contractversion3;
  height: Height2;
  mediaType: Mediatype;
  providerId: Providerid;
  requestId: Requestid2;
  width: Width2;
}
