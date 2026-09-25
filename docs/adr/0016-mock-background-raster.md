# ADR-0016: Persistent mock background raster workflow

Status: Implemented first Milestone 2 increment; remaining exit criteria are pending.

## Data and assets

Reuse native RasterLayer and GenerationRecord without changing Project schema 0.1.0.
The current persistence profile now permits one full-map background layer at zIndex
zero, rotation zero, normal blend, with metadata["quill.render"].role="background".
Opacity and visibility use existing fields. Only succeeded mock text_to_image
records with existing output assets are enabled, at most 128 records per project.
Other artwork/layer profiles remain explicitly rejected rather than silently lost.

Add an assets(hash PRIMARY KEY, content BLOB) table to the existing SQLite store
with CREATE TABLE IF NOT EXISTS. Old projects need no rewrite. PNG bytes are validated
at 480 × 320 (2 MiB maximum) and stored immutably by SHA-256; repeated output deduplicates.
This size respects the mock's 512-axis limit and exactly matches the map aspect ratio.
Every asset read and save/open reference verifies content hash and PNG integrity.
Missing/corrupt images prevent opening or saving the project. Snapshot history retains
its referenced assets; rejected/orphan proposals also remain until future garbage
collection. Asset creation is atomic and precedes a future project save; a rejected
proposal publishes no project snapshot.

## API and preview lifecycle

POST /api/generation/background takes version 0.1.0, prompt (max 4000 characters),
nonnegative 32-bit seed and saved baseRevision. The local mock runs in a worker and
returns a typed candidate layer plus provenance record. GET /api/assets/{sha256}
serves validated PNG with immutable caching. Request bodies are limited to 32 KiB;
JSON and local Origin checks match persistence. No credentials/network models.
RasterContracts generates request/result schemas and TypeScript declarations; the
client validates responses at runtime. Provider in-memory assets are request-local;
the durable bytes live in SQLite, not the provider dictionary.

Preview is transient UI state, separate from document layers. Accept requires a
successfully loaded preview and unchanged project identity, content fingerprint and
history object. Any history transition, including undo back to the original scene,
invalidates the proposal. Save alone does not invalidate unchanged content. Generation
records capture saved baseRevision; the stricter session guard handles unsaved edits.
Changing project also invalidates the preview. Nothing auto-applies. Rejection and
regeneration discard the candidate. Cancel aborts the client request and ignores late
responses using a sequence token; it does not claim to stop server-side computation.
Persistent jobs, progress recovery and provider cancellation remain later work.

Acceptance adds/replaces only the base layer and appends provenance in one scene
transaction. Regeneration keeps existing layer ID, visibility, opacity and order,
increments layer revision, and leaves rooms/walls/doors unchanged. Scene mutations
preserve layers and provenance; undo/redo restore them together. Save/open includes
both and validates all UUIDs and asset references. Background renders top-down into
the full native map bounds, below the grid and geometry guides. It is never treated
as room/object art or a region visual. Layers supports undoable visibility/opacity.

## Verification and next slice

Tests cover deterministic deduplication, persisted asset reads, project round trips,
missing assets, invalid layer profiles and write guards. Browser coverage exercises
preview/reject, accept/undo/redo, geometry preservation, regeneration retaining opacity,
canvas pixel equality after save/open, stale geometry and cancel/late-response handling.
Milestone 2 is not complete: next add room context crops and polygon masks with exact
outside-mask preservation, then room layers/order, job orchestration and flattened
PNG/WebP export. Mock output is visibly a test pattern, not generated fantasy art.
