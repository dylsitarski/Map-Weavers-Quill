# ADR-0018: Flattened PNG and lossless WebP export

Status: Implemented Milestone 2 increment. Persistent generation jobs remain unfinished.

POST /api/export/image accepts contractVersion 0.1.0, the current native Project and
format (png or webp). JSON-only loopback-origin guards and a streamed 4 MiB body limit
match native persistence. Strict contract, geometry, layer bindings and asset/mask
validation run before composition. Invalid or missing artwork produces an error;
export never silently skips a missing asset or publishes a project revision.

Export uses the accepted document snapshot captured when the button is clicked,
including unsaved applied edits. It omits proposals, field drafts, grid, room/wall/door
editing guides, selection highlights and pan/zoom. It is an image only; Foundry
metadata/bundles and portable project archives remain separate future work.

Current output is 480 × 320 pixels (the existing mock raster profile, 2.5 native
units per pixel), with top-down image rows and the native bottom-left geometry
convention unchanged. Composite visible layers in ascending (zIndex, UUID) order,
apply round(alpha * opacity), and alpha-compose over opaque neutral #e9e2ce. An empty
or fully hidden scene exports that neutral image. This compositor is shared with
room-generation context so masks, visibility, opacity and ordering remain consistent.
PNG and lossless WebP encode identical decoded RGB pixels. No upscaling or resolution
selector is exposed while source artwork remains fixed-resolution.

File has Export PNG and Export WebP actions, download-in-progress state and inline
retryable failures. Downloads use a sanitized project name and correct extension;
responses include attachment, no-store and nosniff headers. Export does not change
history, saved state, geometry or generation records. Tests cover pixel composition,
format equivalence, save/reopen, request guards, missing assets, browser downloads,
exclusion of an on-map preview, unsaved state and failure recovery.
