# ADR-0027: Queued SDXL editor generation

Status: Implemented with offline adapter/editor regression tests. Hardware visual
acceptance remains outstanding; Milestone 3 is not complete.

## Selection and API

MWQ_IMAGE_PROVIDER accepts mock (default) or comfyui-sdxl. The API process snapshots
ComfyConfig at startup alongside provider selection; restart to change settings.
Invalid settings fail startup. An unreachable ComfyUI server does not prevent editing
or opening projects. No model weights or GPU dependencies are bundled.

GET /api/providers retains its descriptor contract. GET /api/providers/readiness
adds ProviderReadiness: descriptor, ready and a safe message. It checks core nodes
and checkpoint filename without queuing GPU work. The AI panel validates the response,
displays provider/capabilities, gates generation and offers an explicit retry. Preview
recovery and acceptance do not require the provider to be online. A readiness result
cannot guarantee GPU capacity or validate the checkpoint architecture.

Real generation uses only the existing durable single-worker queue. Legacy synchronous
background/room endpoints return 409 under SDXL, avoiding a parallel unqueued GPU path.
Each operation creates an isolated adapter and checks readiness before submission.
Provider failures retain their fixed safe messages in job records; unexpected exceptions
retain a generic error. No remote response bodies, endpoint URLs or credentials enter
project/job output. Requests are not automatically resubmitted to ComfyUI.

## Raster and provenance

SDXL backgrounds use 960 × 640. Room operations compose at that profile (or the largest
stored profile), resampling legacy context only in memory. Mask bounds plus a 20-native-
unit margin are expanded to multiples of 64 and shifted within the canvas at edges.
Source/mask crops stay paired; output returns to its original pixel location without
stretching. The server enforces full-map transparent pixels outside the room polygon.
Native geometry and full-map layer bounds do not change.

Generation parameters retain existing prompts, resolved style, seed, native revision,
full-map input hashes and image-space crop placement. A nested comfyui object records
the adapter's explicit last_run fields: workflow version/hash, checkpoint filename,
prompt ID, seed, steps, CFG, sampler/scheduler and actual provider crop dimensions.
Top-level width/height mean full-map layer dimensions. Filename alone is not model
identity; checkpoint SHA-256 and ComfyUI version remain hardware-trial evidence.
Persistence accepts mock and comfyui-sdxl records regardless of the currently selected
provider. Existing schema fields suffice; only the provider readiness API adds a schema.

Preview/accept/reject, stale-state checks, undo/redo, save/open and export reuse the
existing document workflow. Generation alone never changes a saved project. Cancelled
jobs cannot publish late output. Cancellation does not interrupt ComfyUI or release an
active worker immediately; subsequent work waits until completion/timeout, and graceful
shutdown can wait too. This avoids globally interrupting another application's work.
An abandoned provider job may continue in ComfyUI. Upload/output cleanup remains manual.

## Verification and next step

Tests use the real adapter/factory/queue/API with a synthetic HTTP transport. They
cover readiness without GPU submission, idempotent submission, 960 × 640 background,
two room edits, crop alignment and inverse-alpha masks, protected pixels, provenance,
save/reopen/export, safe failure, unavailable checkpoint, configuration snapshots,
legacy endpoint rejection and cancellation with late completion and no global interrupt.
A browser test covers unavailable/ready transitions and generation gating; existing
browser workflows cover acceptance, undo, stale previews and recovery.

Next perform the owner-run background plus adjacent-room trial in docs/COMFYUI.md.
Assess small crops, room borders, continuity, top-down perspective, speed and peak VRAM.
Larger context windows, checkpoint/workflow tuning, and geometry-aware exterior guidance
(ADR-0023) remain future increments; transport success is not a visual-quality claim.
