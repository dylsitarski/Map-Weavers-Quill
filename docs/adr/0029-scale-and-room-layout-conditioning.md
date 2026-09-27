# ADR-0029: Physical scale and optional SDXL room layout conditioning

Status: Implemented with offline protocol/geometry tests; GPU quality unverified.
Extends ADR-0028. Building-aware backgrounds (ADR-0023) are still pending.

## Problem and scope

The owner reports improved room coherence and top-down views but incorrect furniture
scale, invented room partitions and backgrounds ignoring architecture. The default grid
already means 5 feet per 50 native units. That physical scale was not sent to the model.
The room mask limits editable pixels; it does not convey wall or door semantics.

This increment sends physical scale on every SDXL room request and optionally supplies
an actual wall/door control image. It does not claim that text or ControlNet enforces
exact furniture dimensions, prevents every invented wall, or guarantees door clearance.
Deterministic architectural rendering and explicit object placement remain future work.

## Geometry and scale

Convert native distance with grid.distance / grid.sizePx, respecting ft or m. Record
room bounding width/height, polygon area and working-image pixels per physical unit,
including the ADR-0028 square padding/scale. The prompt says this is a single space,
requests life-size furniture and prohibits invented subdivisions. These are soft model
instructions. Default projects retain 5-foot cells; no geometry is rescaled or mutated.

Create a full-map monochrome guide at the current raster size: white wall centerlines
on black. Use all validated wall segments, including neighbouring/hidden-room geometry.
Subtract door intervals using attachment position and width along each wall. Door gaps
are shown for open/closed/locked doors alike (architectural openings); windows do not
remove the wall. No grid, furniture, roof or speculative building envelope is drawn.
Image rows reverse native y exactly once. Crop and pad alongside the source/mask, but
pad the control image black and resize with nearest-neighbour. Do not extend wall lines
through the padding. Line-center guidance is not a final rendered wall thickness.

## ComfyUI adapter

Optional server-only MWQ_IMAGE_COMFY_CONTROLNET selects a basename .safetensors model
from ComfyUI's models/controlnet directory. Start with Stability AI's SDXL Canny
Control-LoRA rank128; no weights are bundled or downloaded by Quill. The existing
loopback/configuration snapshot rules apply. When selected, readiness checks
ControlNetLoader/ControlNetApplyAdvanced and the filename, and discovery advertises
control_image. The room UI clearly states whether guidance is configured; missing
configured nodes/files fail readiness/generation rather than silently falling back.
Readiness cannot inspect model architecture or establish GPU compatibility.

The existing namespaced request extension quill.layout accepts exactly one controlRef
for inpainting, referring to a same-sized PNG in adapter memory. Unknown fields,
unsupported operations and missing/invalid assets fail before upload/submission. No
arbitrary workflow, path, URL or strength is accepted from project data.

The fixed comfy-sdxl-layout-v1 graph uploads the guide separately, loads the configured
ControlNet, and wires both conditioning outputs from ControlNetApplyAdvanced into
KSampler (strength 1, start 0, end 1). Source alpha/mask conversion and protected-pixel
compositing remain unchanged. No custom nodes or Canny preprocessor are needed: Quill
constructs the sparse edge guide itself. The guide is experimental input for a Canny
model, not a claim of training-domain equivalence or hard architectural constraints.

## Persistence and compatibility

Unconditioned and mock inpainting retain two input hashes. Conditioned SDXL rooms have
three: full-map source, mask, guide. The store validates all three with ordinary asset
hash integrity checks. Record physicalScale, layoutConditioning, actual positive/negative
prompts, crop/working transform, and control filename/strength/range/working-image hash
in provenance. Full-map guide plus transform reconstructs the working input. Existing
schema fields suffice; older records and save/open with mock selected remain supported.
The graph version and room prompt template identify this new behavior. Existing accepted
art does not change until regeneration is accepted. Background generation remains text-only.

## Verification and next step

Tests cover default feet and metric scale, area/working pixel scale, y orientation,
wall endpoints, door gaps, absence of invented partitions in the guide, protected
padding, readiness failure, separate guide upload, positive/negative node wiring,
invalid extension rejection before network activity, and conditioned save/reopen.
All tests are offline. Hardware memory/performance and visual adherence are unverified.

Next: compare one room with guidance disabled/enabled at the same seed; inspect door
gaps, partitions, furniture scale and adjacent rooms. Then implement explicit building
membership and roof/open-air intent before geometry-aware background conditioning.
Do not silently infer roofs from every polygon or flatten interiors into the background.

Primary references checked 2026-09-27:
- https://github.com/Comfy-Org/ComfyUI/blob/master/nodes.py
- https://huggingface.co/stabilityai/control-lora/tree/main/control-LoRAs-rank128
