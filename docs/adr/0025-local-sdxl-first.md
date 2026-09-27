# ADR-0025: Local SDXL first, with a standalone ComfyUI adapter increment

Status: Accepted; standalone adapter and offline protocol tests implemented.
Actual GPU execution and editor integration are not yet verified/implemented.
Supersedes the hosted-first sequence in ADR-0024 and manifest section 8.4.

## Decision and hardware

The owner prioritizes avoiding recurring image-generation costs during development.
Use self-hosted ComfyUI and SDXL as the first real backend. Move the relevant local
workflow work from Milestone 5 into Milestone 3. Defer the hosted adapter; retain
Milestone 5 as proof that a second provider can use the same editor/document contract.
The deterministic mock remains the default for development and CI.

Initial user test machine: Linux, NVIDIA RTX 3060 Ti with 8192 MiB VRAM, NVIDIA driver
580.178.04 (nvidia-smi reports CUDA 13.0), approximately 32 GB system RAM. At reporting,
652 MiB VRAM was occupied and 24 GiB RAM available. This is a target configuration,
not a measured performance or compatibility guarantee. Windows 11 remains secondary.

Run ComfyUI in its own process/environment, outside Quill's repository and Python
venv. Do not add PyTorch, GPU runtimes or model weights to Quill's dependency closure.
Start with batch one and ComfyUI's automatic memory management; tune/offload only
if actual execution requires it. No refiner, ControlNet, LoRA or custom nodes initially.

## First executable increment

`quill.comfyui.ComfyProvider` implements the existing ImageProvider interface.
`scripts/comfy_smoke.py` exercises it explicitly against a local ComfyUI instance.
The `comfy-sdxl-v1` graph contains only core local nodes. It uses an SDXL base
safetensors checkpoint, 20 Euler/normal steps, CFG 7, denoise 1, explicit seed,
positive/negative prompts and batch one. Generation uses EmptyLatentImage; editing
uses LoadImage and VAEEncodeForInpaint with grow_mask_by=0. This is the standard
masked-base-model workflow, not the previously considered dedicated SDXL inpainting
fine-tune. Compare a dedicated checkpoint/workflow after establishing the baseline;
its conditioning/loader must not be assumed interchangeable with this graph.

Inputs and output are PNG at identical dimensions: multiples of 64, 64–1024 per
axis. 1024x1024 is the initial quality test, 768x768 an optional memory fallback.
The adapter never silently resizes/crops. Input images use image-row coordinates;
the future editor integration owns native bottom-left conversion exactly once.
The white-edit/black-preserve mask becomes inverse source alpha for LoadImage.
After decoding the provider result, the adapter recomposites with the original
source itself. Black-mask RGB pixels are unchanged even if ComfyUI modifies them.
Grayscale masks blend; this version returns opaque RGB images, not object cutouts.

Use /object_info for readiness, /upload/image for the unique masked input,
/prompt once, /history/{prompt_id} polling, and /view for the designated SaveImage
node's single output. Readiness checks node and checkpoint availability without
loading weights or running a GPU operation; it cannot validate model architecture.
Do not accept arbitrary workflow JSON, partner/API nodes or project-provided URLs.

Configuration uses MWQ_IMAGE_COMFY_URL, MWQ_IMAGE_COMFY_CHECKPOINT and
MWQ_IMAGE_COMFY_TIMEOUT (default 600 seconds). Restrict the endpoint to HTTP
loopback with explicit port; reject credentials, URL paths/queries and nonlocal
hosts. HTTP clients ignore proxy environment variables and refuse redirects.
Readiness has a 30-second deadline; generation has an overall configurable deadline
and per-request timeouts. Responses are capped at 16 MiB and PNG dimensions are
checked before decoding. Errors omit server payloads and private tracebacks.

Submission is not automatically retried: a lost response may already have queued
work. No provider interruption is advertised or sent; /interrupt is global and
might stop another application's generation. A timeout/abandoned CLI can leave
ComfyUI work running. ComfyUI retains uploaded files and outputs; cleanup is manual.

The smoke command saves the entire generated PNG and a JSON sidecar with provider,
workflow version/hash, checkpoint filename, prompt, seed, sampler settings, dimensions,
ComfyUI prompt ID and input/output hashes. It refuses existing output paths.
Checkpoint file hash and ComfyUI version must be recorded separately for the first
hardware trial; filename/seed alone do not ensure cross-machine reproducibility.

## Resolution and editor gate

The editor's current database, crop/mask code and exports assume 480x320. Enabling
real generation there would either fail validation or discard generated detail.
Therefore this increment is intentionally standalone: MWQ_IMAGE_PROVIDER remains
mock, /api/providers lists mock, and no project/schema migration occurs yet.
The smoke output is not a project import format.

Next implement resolution-aware persistence, masks, crop transforms, composition
and exports, preserving existing mock projects and full-resolution real assets.
Then connect the adapter to queued preview/accept/reject, capability/readiness UI,
stale-result protection and save/open. Do not silently stretch arbitrary crops or
replace old raster assets with upscaled versions. Define that contract in its own
ADR and regression fixtures. Dedicated inpainting tuning and building/open-air
layout conditioning (ADR-0023) follow; neither visual quality nor roof alignment
is established by transport tests.

## Verification

Offline httpx transports test readiness, workflow submission/poll/download, full
resolution, alpha inversion, protected pixels, malformed inputs/results, local-only
configuration, bounded timeout/response size, safe errors and no automatic resubmit
or global interruption. No weights, external service or GPU is used by make check.
See docs/COMFYUI.md for the owner-run GPU test and evidence to capture.

Primary implementation references (checked 2026-09-26):
- https://docs.comfy.org/development/comfyui-server/comms_routes
- https://docs.comfy.org/tutorials/basic/inpaint
- https://comfyanonymous.github.io/ComfyUI_examples/sdxl/
- https://github.com/Comfy-Org/ComfyUI/blob/master/nodes.py

## Follow-up status

The owner reports SDXL working locally. Flux Fill is deferred. ADR-0026 implements
the resolution gate for persistence, masks, crops, composition and export; the
historical 480x320-only limitation above no longer applies. The editor provider
remains mock until the next queued integration increment. Adapter-specific GPU
measurements and visual acceptance have not yet been recorded.
