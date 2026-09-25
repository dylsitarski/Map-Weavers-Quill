# ADR-0015: Local project snapshots and File workflow

Status: Implemented; hosted acceptance verification follows the code commit.

## Storage and API

Use the native Project 0.1.0 JSON document without a schema migration. Add generated
PersistenceContracts for SaveRequest, Project result and ProjectList. GET /api/projects
lists current saved projects; GET /api/projects/{UUID} returns a validated current
snapshot; POST /api/projects/save accepts {contractVersion: "0.1.0", expectedRevision,
project}. expectedRevision is null for a new project (document revision zero), or
the current saved revision. New is a local draft until its first successful save.
The save endpoint parses strict JSON models, including UUID strings, with a 4 MiB
streamed input limit. Responses are runtime-validated in the browser. Writes require
JSON and reject non-local Origin values; services remain loopback-only with no CORS.
This is not an authenticated multi-user hosting service.

Store complete immutable native JSON snapshots and a current-revision pointer in
SQLite. Default path is data/projects.sqlite3 under the server working directory;
MWQ_DATA_DIR selects the directory. A BEGIN IMMEDIATE transaction checks the expected
revision, inserts a validated snapshot, then publishes the pointer. WAL + synchronous
FULL provide SQLite crash recovery. A failed transaction publishes neither row;
retained earlier snapshots are never overwritten. A concurrent stale writer gets
409; it cannot replace the current revision. Native saved revision increases per
successful save independently of session undo. Metadata lives in the same transaction
as JSON: no separately written JSON file can disagree with the index.

No automatic cleanup, autosave, history-recovery UI or portable archive/import is
claimed. Stop the server before copying the data directory for a manual backup.
The implementation uses Python's standard sqlite3 and adds no dependencies.

## Validation profile

Accept the current editor's 1200 × 800 map and 50-unit square grid. Reject unsupported
entity collections and room render-layer references, never silently discard them.
Validate global entity UUID uniqueness, room topology/bounds and ADR-0013 budgets.
Derive authoritative walls from rooms; save may fill an empty wall display cache
when there are no doors. Otherwise stored walls must equal the complete derived
set, including blocking flags/provenance. Reject unsupported wall overrides. Validate
every door parent, full-width fit and same-wall non-overlap. Keep all supported
entity IDs, metadata, room ordering/prompts and door fields. Read validates again;
a corrupt/unsupported snapshot does not replace the editor. Version mismatches
are rejected with no implicit migration; historical snapshots remain intact.

Full validation for future artwork/light/object/region/sound/generation references
must be added before enabling those project profiles. Structural fixture tests can
still use richer synthetic projects; those are not current editor import fixtures.

## UI and history

File contains name, save status, Save project, New project, saved-project list and
Refresh project list. Controls stay within the existing fixed scrolling overlay.
Save persists committed edits only; inspector drafts must be applied separately.
Save failure/conflict leaves local work and history untouched. New/Open confirms
before discarding dirty committed work; errors and invalid responses leave it intact.
Dirty comparison ignores JSON object-key order, saved revision and derived wall cache,
but includes native geometry/order, metadata, name and grid preferences. Undoing to
saved content clears dirty state. Save preserves undo history. New/Open reset history,
selection, drafts and viewport so undo cannot resurrect a different project's scene.
Refresh starts blank; saved maps must be explicitly reopened. Warn before navigation
with unsaved committed changes. Unsaved inspector drafts are not a stored revision.

## Acceptance evidence

Tests cover native round trips, retained snapshots, concurrent revision conflicts,
rollback after insert, forced process exit before commit, strict API validation,
unsupported topology/references and write guards. Browser tests create connected
rooms and a door, save/reload/open and compare native geometry and canvas pixels;
also test failure recovery, conflicts and cancelling New. Existing tests cover
50 sequential scene changes through undo/redo. Linux is the tested platform;
Windows 11 remains unverified. No Foundry importer or AI generation is implied.
