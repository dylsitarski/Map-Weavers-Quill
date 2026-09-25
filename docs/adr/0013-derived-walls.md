# ADR-0013: Deterministic derived walls and inspection

Status: Implemented; Milestone 1 acceptance is verified in ADR-0015.

## Contract and topology

POST /api/geometry/walls accepts contractVersion 0.1.0, native map width/height,
and rooms containing UUID IDs and polygons. It returns contractVersion 0.1.0 and
existing Wall entities. GeometryContracts generates both request and response
JSON Schema/TypeScript declarations. The browser validates responses at runtime.
This is an additive stateless API; the project document schema is unchanged.

Validate each polygon with the existing geometry validator, reject duplicate room
IDs, then node all polygon edges with Shapely unary_union. Crossings and partial
shared boundaries split into atomic segments; coincident segments appear once.
Overlapping rooms retain all boundaries: this is not a union of room interiors.
Concave rooms work; holes and standalone wall input are outside this increment.
Limits are 128 rooms, 2048 total input vertices and 8192 output segments; map
sizes retain the existing one-million-unit maximum. Invalid/budget-exceeding input
returns 422 without repairing geometry or modifying room data.

## Identity and ownership

Canonicalize each segment by lexicographically sorting its two native endpoints,
normalizing signed zero, and encoding the numeric endpoint pair as compact JSON.
UUID5 under namespace 097a32d9-3f61-445e-9721-c7ac4dc5f615 produces its ID. Sort
segments and contributing room IDs for deterministic output. Endpoint coordinates
are not rounded or snapped. Unchanged endpoints retain identity despite room
ordering, winding or ownership changes. Moving/splitting a segment creates new IDs;
undo restores the old geometry and IDs. This is not a promise of identity through
arbitrary geometric edits or changes to the underlying numeric geometry engine.

Use sourceRoomId for a single owner, null for multiple owners, and always include
all contributing IDs in metadata["quill.geometry"].sourceRoomIds. A null sourceRoomId
alone does not distinguish a shared derived wall from a standalone wall. Match
source edges using a spatial index and endpoint distance tolerance 1e-8 map units;
this tolerance affects provenance only, not snapping or segment merging. Initial
walls have revision zero and block movement and sight.

## Editor and next work

Walls are a read-only asynchronous view of committed room geometry, separate from
room undo history and artwork ordering. Recompute on geometry/ID changes, not
labels, prompts or room order. Hide stale results immediately; abort replaced
requests and reject late responses. Timeout/API/validation failures preserve rooms
and expose Retry walls. Empty room sets need no server request.

Room → Inspect walls supports canvas selection at 8 screen pixels. At the owner’s
request, the segment selector and wall count were removed; Inspect walls is last
in the Room menu. Information displays endpoints, length, blocking flags and room
provenance. Selection preserves the active right-panel tab. Space-pan and existing
scope/tool toggle semantics still apply.

ADR-0014 now implements transactional door reconciliation. Scenes with doors use
the validated wall/door snapshot instead of this asynchronous display cache.
Persistence is implemented in ADR-0015; editable wall overrides remain unimplemented. Standalone wall drawing,
pillar footprints and previewed room creation from wall circuits remain future work.

Verification covers adjacent/partial shared boundaries, crossings, diagonal and
concave geometry, duplicate outlines, deterministic identity, malformed input and
budgets; browser checks cover selection, undo/redo, retry and stale responses.
