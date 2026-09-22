/* Generated. Run make schema; do not edit. */

export type Capabilities = ("text_to_image" | "inpainting" | "seed")[];
export type Id = string;
export type Local = boolean;
export type Maxheight = number;
export type Maxwidth = number;
export type Code = "missing_asset" | "invalid_image" | "unsupported_capability";
export type Message = string;
export type Retryable = boolean;
export type Height = number;
export type Prompt = string;
export type Requestid = string;
export type Seed = number;
export type Width = number;
export type Context = string;
export type Height1 = number;
export type Maskconvention = "white-edit-black-preserve";
export type Maskref = string;
export type Prompt1 = string;
export type Requestid1 = string;
export type Seed1 = number;
export type Sourceref = string;
export type Width1 = number;
export type Assethash = string;
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
  height: Height;
  prompt: Prompt;
  requestId: Requestid;
  seed?: Seed;
  width: Width;
}
export interface InpaintRequest {
  context?: Context;
  height: Height1;
  maskConvention: Maskconvention;
  maskRef: Maskref;
  prompt: Prompt1;
  requestId: Requestid1;
  seed?: Seed1;
  sourceRef: Sourceref;
  width: Width1;
}
export interface GenerationResult {
  assetHash: Assethash;
  height: Height2;
  mediaType: Mediatype;
  providerId: Providerid;
  requestId: Requestid2;
  width: Width2;
}
