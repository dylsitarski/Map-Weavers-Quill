# ADR-0017: Context-cropped room artwork with enforced masks

Status: Implemented Milestone 2 increment; artwork ordering/visibility/opacity controls are implemented. Persistent
jobs and flattened export remain unfinished.

## Raster convention and protection

Canonical raster size remains 480 × 320 for a 1200 × 800 native map: 2.5 native units
per pixel. Image rows run downward; native y increases upward. Mask pixel (x,y) tests
native point ((x+0.5)*2.5, 800-(y+0.5)*2.5) for intersection with the room polygon.
Boundary centers are included. Masks are binary, not antialiased. Concave polygons
and map edges follow the same rule. A valid polygon covering no pixel centers is
rejected as too small at this resolution. Geometry itself is never quantized.

Composite current visible artwork in deterministic (zIndex, UUID) order over the
neutral base, applying normal alpha/opacity. Crop the room's covered-pixel bounding
box with eight pixels of surrounding context, clipped to image bounds. Send cropped
RGB source and grayscale white-edit/black-preserve mask to mock inpainting. The mock
ignores semantic style but proves the pipeline. Independently mask the returned image
again and embed into a transparent full-map RGBA asset; never trust provider masking.
Every outside-mask pixel in this new layer is RGBA zero. Compositing it over any
scene preserves all outside-mask pixels byte-for-byte at the canonical resolution.
Canvas additionally clips room layers to native polygons during scaled display.

## Contract, storage and provenance

POST /api/generation/room accepts contractVersion 0.1.0, current native Project,
roomId and seed; the typed result reuses the raster layer/provenance response.
Strict JSON input (4 MiB max), project topology/reference/asset validation and local
write guards run first. Use the applied room prompt (max 4000 characters). Stale UI
results cannot apply; the endpoint creates immutable assets, not a document mutation.
Store context, full mask and output PNG assets by SHA-256. Provenance records input
hashes, output hash, crop rectangle, seed, prompt and saved baseRevision. Source and
mask share the full-map asset resolution; the provider receives transient crops.

Native schema remains 0.1.0 using Room.renderLayerId, RasterLayer and GenerationRecord.
Room art uses metadata["quill.render"]={role:"room",roomId:<UUID>}, full-map bounds,
zero rotation, normal blend and positive zIndex. Require a bijective room/layer
binding; a single background, when present, remains at zIndex zero. New room layers
are inserted above existing art. Regeneration preserves identity/order/opacity/visibility.
At most 129 layers and 128 generation records. Save/Open verifies all assets and
rejects room alpha outside its current polygon. Generation records are historical
provenance, so their target metadata may refer to a subsequently deleted room.

## Transactions and UI

Room → Select/edit room → AI: Apply prompt, then Generate preview. Preview, reject,
regenerate and cancellation retain ADR-0016 semantics. Accept replaces/adds only the
selected room layer, updates its renderLayerId/revision and appends provenance in
one undo transaction. Changing geometry or document history invalidates a live
preview; changing selection invalidates it or unmounts/discards it. Selection/tab
changes do not themselves mutate document history. Saving persists accepted art.

Room addition/deletion/edit commands preserve independent artwork. Moving or reshaping
a room clears its outdated bound layer and binding in that same undoable transaction,
with a notice; name/prompt-only edits preserve art. Deletion removes its bound layer.
Undo restores geometry and artwork together. No implicit stretching, translation or
regeneration of pixels is performed. Background regeneration/reconfiguration preserves
all independent room layers. Regions retain their semantic, non-artwork definition.
Room-shape order is independent of artwork order. The Layers tab lists artwork front-to-back with raise/lower, visibility and opacity controls. Background stays at zIndex zero; room art has positive ranks. Reordering normalizes room-art ranks, resolves ties by UUID, and updates revisions only for changed ranks. Every change is one undoable document edit and invalidates pending previews. Geometry and generation provenance are unchanged.

## Verification

Tests cover concave and diagonal masks, native/image orientation and boundary pixels,
context crop bounds, exact outside-mask equality with other room art present, and a
provider deliberately painting the entire crop. Persistence tests verify binding and
reject out-of-mask alpha. Browser tests cover room preview/accept/reject/regenerate,
undo/redo, save/open, background independence, stale geometry and artwork clearing.
