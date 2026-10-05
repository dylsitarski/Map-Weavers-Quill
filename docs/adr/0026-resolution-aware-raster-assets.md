# ADR-0026: Resolution-aware full-map raster assets

Status: Accepted and implemented; ComfyUI editor integration is next.
Extends ADR-0016 through ADR-0018 and satisfies the resolution gate in ADR-0025.

Update 2026-10-05: ComfyUI editor integration is implemented (ADR-0027).

## Contract

Native geometry remains 1200 × 800, bottom-left origin, +y up. Full-map PNG
assets may be 480 × 320 (legacy mock) or 960 × 640 (initial SDXL profile).
Both preserve the 3:2 aspect ratio. The latter uses multiples of 64 and stays
within the standalone adapter's 1024-per-axis limit. Other shapes/sizes and
animated PNGs are rejected; encoded assets are bounded at 8 MiB.

PNG headers supply raster dimensions. Layer bounds remain native map bounds;
no structural schema change, coordinate migration or rewritten asset is needed.
Content hashes and original bytes remain stable through save/open and composition.
Mixed-resolution layers are supported. New mock backgrounds remain 480 × 320.

## Masks, crops and composition

Masks sample native polygons at pixel centers, converting image rows to native
y exactly once. Validate each room layer's alpha against a mask at that layer's
own resolution. Pixels outside the room must be transparent.

Composition uses the largest stored profile, including hidden layers so toggling
visibility cannot change export dimensions. With no assets, use the legacy profile.
Explicit compositing targets may upscale but cannot discard stored resolution.
Smaller layers are resampled in memory with Lanczos; room alpha is clipped again
against the destination-resolution polygon mask to prevent interpolation bleed.
Layer ordering, visibility and opacity retain their existing meaning. PNG and
lossless WebP exports use this composite, without changing source assets.

Room context uses the composite resolution and a 20-native-unit margin. Crops
are image-space rectangles: cut source and mask together, then paste output at
the original crop origin without stretching. The shared crop helper can expand
dimensions to multiples of 64, shifting within canvas edges while retaining the
entire mask. Queued ComfyUI integration must enable that alignment; mock retains
unaligned crops. Reject provider dimensions beyond its advertised limits before
allocating input assets, and reject returned dimensions inconsistent with the crop.

## Scope and verification

Offline tests cover corner transforms, aligned edge crops and exact paste-back,
mixed-resolution room clipping, unchanged asset bytes, high-frequency detail
through save/open and lossless export, stable hidden-layer dimensions, unsupported
profiles and invalid alpha. Existing legacy tests remain applicable.

This increment does not enable ComfyUI in provider discovery or editor generation,
add an image importer, or establish SDXL visual quality. Next wire the adapter to
queued generation, aligned room crops, provenance, readiness and preview acceptance;
then measure a real background and room edit on the owner's hardware. Small room
crops may need additional context for visual quality; evaluate rather than silently
rescaling geometry. Arbitrary resolutions and user-selectable export sizes are future work.
