# ADR-0009: First deterministic editor slice

Status: Accepted, Milestone 1 in progress.

Use the planned React/Konva viewport. Named TypeScript transforms convert native
bottom-left world points to viewport pixels and back. Zoom anchors to the pointer;
pan, grid visibility and snapping are transient editor settings. The initial map
is 1200 by 800 logical units with a 50-unit grid.

Rectangular room proposals go to POST /api/geometry/validate (contract 0.1.0).
Shapely checks bounded, unique vertices, simplicity and positive area without
repairing or moving geometry. The endpoint is stateless and does not save projects.
Its Pydantic contracts generate JSON Schema and TypeScript types like other APIs.
Payloads allow at most 2048 vertices and map dimensions up to one million units.

Accepted rooms enter immutable add-room transactions with undo/redo. During
validation, further drawing and history mutations are disabled; timeouts and
failures leave history unchanged. Browser refresh discards this session. Local
React reducer state is sufficient for this slice; Zustand adoption is deferred
until shared editor state is needed. Neither viewport nor screen points enter a
Room entity. Persisted project validation still needs cross-entity checks.

Derived wall inspection is implemented in ADR-0013. Doors and atomic
project persistence remain subsequent Milestone 1 work.

Polygon drawing now uses the same stateless validation endpoint and add-room
transaction as rectangles. Draft vertices remain in native coordinates while
panning/zooming. Closing with the first point does not duplicate that point in
the stored polygon. Failed submissions preserve the draft for correction.

Room selection, move, vertex editing, name/prompt inspection and deletion are now
implemented; see ADR-0011 for transaction and interaction semantics. Saving remains
unimplemented.
