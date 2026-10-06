# ADR-0028: SDXL room working resolution and authoring prompts

Status: Implemented; visual improvement requires an owner-run GPU trial.
Supersedes the unscaled SDXL crop path and prompt assembly in ADR-0027. Mock output,
native geometry, full-map storage and project schemas remain unchanged.

Update 2026-10-06: the per-room padded crop is replaced by a fixed 40-ft window of real
map context, so every room has the same working scale (ADR-0033).

## Reason

The first owner trial produced abstract room bands and backgrounds with an oblique
perspective. Prompt revisions did not resolve either issue. Small room crops were
sent directly to SDXL, sometimes only a few hundred pixels across. Readiness and
transport tests proved integration, not usable image quality.

## Working transform

Keep the existing native-to-raster mask, 20-native-unit context margin and aligned
image-space crop. Center the rectangular crop on a square whose side is the longer
crop dimension. Extend source edge pixels into padding; padding mask pixels are black
(protected). Resize the square source to 1024 × 1024 with Lanczos and its binary mask
with nearest-neighbour. Thus both axes have the same scale; no room is stretched.
This is generation at a higher working resolution, not upscaling the final map.

Check the provider result is exactly 1024 × 1024. Resize back to the padded square,
remove padding, paste at the original crop origin, and apply the original full-map
binary room mask. That final mask, not a resized approximation, defines coverage.
Final room layers stay 960 × 640. Original assets remain immutable and accepted layers
outside the target are unchanged. Very narrow rooms can still occupy a small fraction
of the working image; this transform does not guarantee good composition.

Store roomTransform version sdxl-room-fit-v1, crop size, padding offset/side, working
size and resampling filters in generation parameters. Existing crop and full-map
source/mask hashes make inputs reconstructible. ComfyUI provenance records actual
1024 × 1024 generation dimensions, while top-level dimensions mean full-map storage.

## Context and prompts

For fresh SDXL room generation, build context from a document copy with target artwork
and known mock artwork hidden. Identify mock output by matching layer asset hashes to
mock generation records, not colors or labels. Preserve unknown-provenance artwork,
real neighbouring layers, order and opacity. Record excludedContextLayers. Do not
change document visibility or delete assets. Existing mock generation behavior remains.

Both SDXL operations use sdxl-overhead-v2: lead with orthographic overhead camera
instructions, then user content and resolved plain-language style. Background guidance
calls for terrain/roofs; room guidance calls for roof-removed interiors/furniture from
above. Use even diffuse illumination for this reference workflow. Negative prompts
address oblique/isometric perspective, horizons, text, grids, checkerboards and abstract
neon patterns. Record the exact positive/negative prompts and template version.
Authored prompts and style defaults are not rewritten. Interior environment overrides
remain the user's control; an inherited forest environment may still be inappropriate.

## Verification and next trial

Offline tests verify square/portrait/landscape/very narrow transforms, axis orientation,
padding mask protection, binary masks, source round-trip placement, immutable context,
provenance-based mock exclusion, distinct prompt templates, and actual adapter upload
at 1024 × 1024. The queued integration test covers original-mask clipping, save/open
and export. Existing mock tests guard backwards compatibility.

Regenerate the same problematic room and background after restarting Quill. Capture
artwork, runtime and peak VRAM. Working resolution increases room GPU cost; no speed
or quality guarantee is made. This remains base SDXL masked editing, not a dedicated
inpainting model. If perspective/composition is still poor, evaluate a battlemap-tuned
checkpoint/LoRA or explicit geometry conditioning. Building exterior alignment remains
unimplemented under ADR-0023; stronger wording does not implement spatial constraints.
