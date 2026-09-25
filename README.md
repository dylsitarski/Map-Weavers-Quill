# Map-Weaver's Quill

A local-first, AI-assisted 2D battlemap editor. Linux is the primary target;
Windows 11 follows. See [PROJECT_MANIFEST.md](PROJECT_MANIFEST.md).

## Development status

Milestone 0 is **complete**. The repository includes React and
FastAPI shells, Python models with generated JSON Schema and TypeScript types,
cross-runtime validation, coordinate transforms, and a deterministic offline
image provider. Milestone 1 is **complete for the current editor scope**: the Konva viewport supports pan,
pointer-anchored zoom, resize, grid visibility, snapping, rectangular room creation,
polygon room creation, selection/move/vertex editing, a room inspector, deletion,
undo/redo of room changes, derived wall inspection, and constrained door placement/editing. Geometry changes pass server-side polygon validation.
File → New/Save/Open now stores validated native project snapshots locally.
Milestone 2 has begun with persistent mock background generation, preview/accept,
undo and saved raster assets. There is no Foundry importer yet.

### Setup (Linux, Python 3.12 and Node 24)

```sh
nvm install
nvm use
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
npm ci
make check
```

`make dev` starts the web shell at http://127.0.0.1:5173 and API at
http://127.0.0.1:8000. Ctrl-C stops both. This launcher currently targets Linux.
The API exposes `/health`, `/api/health`, `/api/providers`, and
`POST /api/geometry/validate`, and `POST /api/geometry/walls`, and `POST /api/geometry/doors`. Project endpoints are `GET /api/projects`, `GET /api/projects/{id}`, and `POST /api/projects/save`. Visit `/docs` for API documentation; `/` returns 404.

`make schema` regenerates all schemas and TypeScript declarations. `make test`
runs Python/TypeScript tests and checks generated files for drift. `make check`
also runs Ruff lint/format checks, mypy, TypeScript checks and the Vite build.
`make audit` checks dependencies online; ordinary tests are offline.

Node 24 is declared in `.nvmrc` and enforced by npm and `make doctor`. The nvm
commands assume nvm is installed; another Node manager may also select Node 24.
For real-browser checks, run `npx playwright install --with-deps chromium`, then
`make browser`. On Linux, installing browser system dependencies may require sudo.
Browser tests cover loading, API connectivity through Vite, and failure messaging.
They start and stop the same launcher as `make dev`, with no external AI calls.

The committed Python lockfile pins the full development dependency closure.
GitHub Actions runs `make check`, `make browser`, and `make audit` on Ubuntu for pushes and PRs.
Tests use synthetic data, no credentials, paid APIs, or GPUs.

## Milestone 0 verification

Ubuntu clean-checkout CI passed on commit `2af87f4`: 20 Python tests, 10 TypeScript
tests, 3 Chromium browser tests, schema/type drift checks, linting, typing,
production build, and Python/npm dependency audits.
See [the successful run](https://github.com/dylsitarski/Map-Weavers-Quill/actions/runs/35686075197).
The browser suite also verifies development service startup and shutdown; repeated
termination signals are covered by a launcher regression test. Local Chromium
installation was unavailable in the agent environment, so browser evidence comes
from hosted Ubuntu CI. Windows 11 and Foundry compatibility are not yet tested.

Provider contracts now include version tags, capability vocabulary, reference
images, negative prompts, neutral parameters, namespaced extensions and normalized
errors. The mock rejects unsupported options and cancellation explicitly. All
seven initial architecture decisions are recorded. Geometry topology and cross-entity validation for the supported editor profile
are implemented and run before persistence (ADR-0015).

## Milestone 1 first increment

The accepted UI scheme and future feature placement are in [docs/INTERFACE.md](docs/INTERFACE.md).
The left rail selects the Map background or toggles persistent Room tools. Map
targets the base environmental image without opening a left panel; AI contains mock preview controls.
Global menus live along the top, and the
right panel at upper-right collapses and has Information, Layers and AI tabs.
Information contains selection details only. Layers replaces the room list and
offers Raise/Lower controls for undoable room drawing order (front to back).
AI edits the selected room's prompt for future generation. File explains session
storage; Help and the top-bar indicator show connectivity. View contains map size, Fit map and Grid;
Snap is always visible on the top bar. Pan is the default. Closing a scope returns
to Pan; reopening restores its last tool. Tool buttons toggle off to Pan.
Space-drag temporarily pans, including with a tool button focused (Enter activates
focused buttons). A small point previews the snapped drawing position. Escape closes menus or
cancels a draft. Errors remain at bottom-left until dismissed; confirmations fade.
Panels overlay the canvas without changing its size. Future scopes are disabled.

Regions are semantic/gameplay areas, not generated visual assets. Visual features
belong to objects. Planned layer controls will allow room, object and effect artwork
to be reordered above the base background, with undo and consistent save/export.
Regeneration will preserve other layers and the target's stacking position.
Room-shape ordering and independent generated-artwork ordering work now; object composition remains unimplemented; flattened PNG/WebP export is available. See docs/adr/0012-snapping-and-sidebar.md.

Run `make dev`, open the web interface, choose Room → Rectangle room, and drag inside the map.
Choose Pan to drag the view, scroll over the canvas to zoom, or use Fit map to
recenter. Scroll over a panel with a scrollbar to scroll its contents, including
at the scroll limits; this never zooms the map. Grid visibility and snapping are independent.
Undo/Redo applies to room additions, edits and deletion. Invalid geometry and API failures do not
add a room or change history. Dragging out of the drawing surface cancels a draft.

This is a mouse-based, in-memory session on a fixed 1200 by 800 map with a 50-unit
grid. **Unsaved changes are lost on refresh.** Saved projects remain available in File → Open saved project.
Persistence validates the currently editable profile before saving or opening. The Milestone 1 acceptance suite passes on Ubuntu.

Choose Room → Inspect walls to select a derived segment on the canvas. Information shows its endpoints, length, blocking flags and
contributing rooms; selection preserves your current right-panel tab. Shared
boundaries produce one segment, and intersections split segments. Unchanged
endpoints preserve IDs across room reordering and undo/redo. Wall derivation is
asynchronous; outdated results are hidden and failures offer Retry walls without
changing rooms. Limits: 128 rooms, 2048 total input vertices, 8192 output segments.
Walls remain read-only; door-bearing scenes keep reconciled walls and doors in
one undoable snapshot. Standalone wall drawing is not implemented. See ADR-0013/0014.

Choose Room → Place/edit door, set a width, and click a wall. Snap projects the
center to grid-cell midpoints (25, 75, 125, …); with Snap off, placement is continuous.
For diagonal walls the dominant coordinate snaps, while the center stays on the wall.
The full opening must fit on one segment and cannot overlap another opening.
Drag an existing door to slide it along its attached wall, or click to edit its
name, width, position, open/closed/locked state
and secret flag in Information. The default width remains 50 units: openings may
meet wall endpoints exactly. Dragging clamps the full opening to the wall; each
release is one validated, undoable edit. Leaving the canvas, Escape, blur or a tool
change cancels the preview. Apply, Reset and Delete are at the top. Door
selection preserves the current tab. Open doors use dashes; locked doors use a
long/short dash pattern. These are editor geometry/state, not Foundry gameplay yet.
Whole-room translations carry doors. Wall splits away from openings remap their
attachments; cuts through openings, ambiguous shared-wall movement, or deleting
the last source room are rejected. Move/delete the door first, then retry the room
edit. Room geometry, walls and doors undo together. Save through File to keep the committed scene across restarts.

Choose Room → Polygon room to place corners with clicks. Click the first point
again (within 8 screen pixels, or at the same snapped coordinate) or choose Finish
polygon after at least three points. Remove last point corrects a draft; Cancel
polygon or Escape discards it. Rejected polygons remain available for correction.
Space-pan and zoom preserve placed points; changing tools or closing the scope
discards unfinished geometry. Polygon drafts support at most 2048 unique vertices.

Choose Room → Select/edit room and click a room, or choose its name in Layers.
Drag inside to move; drag a corner handle to reshape. With Snap enabled, movement
snaps the vertex nearest the initial grab point to the actual grid and translates
every vertex equally. The anchor stays fixed and is highlighted during the drag.
This realigns off-grid rooms without deforming irregular polygons; other vertices
may remain off-grid. Corner edits snap the individual corner to the grid.
The Information inspector provides name and native-coordinate fields, plus point
insertion/removal. Apply commits the whole inspector edit once; Reset discards form
changes. Exact coordinate fields are not snapped. Delete room is undoable.
The AI tab's Apply prompt stores the prompt in session history; it does not call an AI provider.

Overlapping rooms select the topmost room in drawing order; Layers can select covered rooms.
Escape, leaving the canvas or changing tools cancels an unsubmitted drag. Validation
failure leaves the original room intact; rejected inspector values remain editable.
Selection itself creates no undo entry. Inspector drafts reset after switching
selection or after a committed edit/undo/redo. Only one room is selected at a time.

The schema now covers every planned entity category, including namespaced
metadata, object transforms, sounds, regions, and generation provenance. The
all-entities fixture is checked across Python and TypeScript. This unreleased
schema was expanded in place; old synthetic fixtures were updated together.
The current schema validates structural data, not polygon simplicity or door
attachment geometry. These limitations are explicit; do not use it as a complete
editor validation boundary yet.


## Milestone 1 verification

[Ubuntu CI passed](https://github.com/dylsitarski/Map-Weavers-Quill/actions/runs/36094044452) on code commit `200338f`: 40 Python tests,
27 TypeScript tests, browser tests, generated-file drift checks, typing, linting,
production build and dependency audits. Browser acceptance creates two connected
rooms and a door, saves/reloads/reopens, and compares native geometry and canvas
pixels. Tests also cover 50 scene commands through undo/redo, concurrent saves,
rollback and forced process exit before commit. The current map/profile limits
are listed below; Windows 11 and Foundry remain unverified.

## Local project files

Open File, enter a project name, and choose **Save project**. **New project** starts
a blank map; **Open saved project** lists saved maps. New/Open asks before discarding
unsaved committed edits. Save records applied scene edits, room order, prompts,
door states and grid preferences; Apply inspector drafts before saving. Opening
resets selection, view and undo history; undo history is session-local. A save does
not clear undo history. Dirty status compares content, so undoing to the saved
scene returns to Saved. Browser refresh starts a new blank editor: reopen your
saved map explicitly from File.

Snapshots are stored in `data/projects.sqlite3` relative to the server working
directory (normally the repository root). Export `MWQ_DATA_DIR` before `make dev`
to choose another directory. This data is ignored by git. Stop the server before
copying the whole data directory for a manual backup. SQLite uses WAL and FULL
synchronous transactions; previous snapshots are retained. Concurrent/stale saves
return a conflict instead of overwriting another session. A failed or interrupted
save leaves the previous committed version available.

This first persistence profile supports 1200 × 800 maps, a 50-unit grid, rooms,
derived walls, doors, one base background, independently masked room artwork and mock generation records.
Unsupported dimensions, wall overrides, non-room artwork layers, lights, objects,
regions and sounds are rejected rather than stripped.
All supported IDs, references, polygons and door openings are checked. Save requests
are limited to 4 MiB, with existing geometry limits (128 rooms, 2048 total vertices,
8192 walls, 1024 doors). Unknown schema versions are rejected without migration.
Portable JSON/archive import/export, autosave and a revision-recovery UI are not
implemented. Saved revision numbers are monotonic; unsaved scene snapshots remain
local to this editor. See ADR-0015.

## Milestone 2: First raster increment

Select **Map → AI → Generate preview**. The offline mock produces a deterministic
480 × 320 checker pattern from the prompt and seed, scaled across the 1200 × 800 map.
This is a pipeline test, not AI artwork. Accept background creates/replaces only
the base layer; Reject preview changes no document data. Regenerate preview replaces
the proposal. Accepted artwork and provenance support undo/redo and File Save/Open.
Layers offers background visibility and opacity; regeneration preserves both and
the layer's ID. Room and door geometry remain independent.

Any document/history change makes a preview stale, including an edit followed by
Undo. Regenerate before accepting. Cancel preview abandons the response; the fast
mock computation may still finish on the server. This increment is not a persistent
job queue and does not claim provider-side cancellation.

PNG bytes are SHA-256 addressed in the same local SQLite database. Save/open verify
that referenced assets exist and match their hashes; missing/corrupt assets reject
opening rather than silently dropping artwork. Previous and rejected assets are
retained (garbage collection is not implemented). This profile permits one base background, one art layer per room (129 total
layers maximum), and at most 128 generation records. Existing projects remain compatible.
No credentials or external model calls are used.

Select a room with Select/edit room, open AI, enter its prompt and choose Apply
prompt, then Generate preview. Accept room artwork creates an independent transparent
layer bound to that room. Regeneration keeps its layer identity, opacity and order;
background regeneration preserves room artwork. Rejection changes nothing.
Room previews use an eight-pixel context margin and a binary polygon mask at the
canonical 480 × 320 resolution (2.5 map units per pixel). Coverage is evaluated at
pixel centers; outside-mask RGBA pixels are transparent, and compositing preserves
all outside-mask pixels exactly, even if the provider paints outside the mask.
This is still the deterministic offline mock, not AI imagery.

Moving/reshaping a room clears its outdated art in the same undoable transaction;
undo restores both. Changing its name or prompt preserves art. Deleting a room also
removes its bound layer. Save/Open validates bindings and rejects art that has alpha
outside its current room mask. Apply inspector drafts before generation. Geometry
changes make open previews stale; changing scope may discard room previews.

Artwork ordering, visibility and opacity controls are available in Layers and persist
through undo/redo and save/open. Durable generation jobs are implemented in ADR-0019. Room masks/crops and protected compositing are now implemented.
See ADR-0016. APIs: POST /api/generation/background, POST /api/generation/room and GET /api/assets/{sha256}. See ADR-0017 for room generation.

## Distribution

Public, free distribution is intended. A software license has not been selected;
this repository does not yet grant a general redistribution license. The owner's
noncommercial release intent does not itself select a legal license. Do not bundle
third-party model weights or private assets.

### Export artwork

File → Export PNG or Export WebP downloads the current accepted artwork at 480 × 320
pixels. Export respects layer order, visibility and opacity, including unsaved applied
edits. It excludes previews, grid and editing guides. Both formats are lossless; empty
areas use the neutral map background. Export does not save the project or change undo
history. Higher-resolution output and Foundry metadata bundles are not implemented.
See docs/adr/0018-flattened-artwork-export.md.

### Generation jobs

Generation runs through a durable local queue with queued/running status and cancellation.
Job requests/results survive server restart; interrupted work is marked failed and can
be regenerated. Cancelling prevents a queued job from starting and discards late output
from running work. The synchronous mock may finish internally after cancellation. After reload, reopen the saved project and select the same Map/room target in AI, then
choose Recover preview. Recovery requires the matching document and same browser origin.
Changed/lost unsaved work blocks recovery. Accept/Reject or Discard clears the recovery
record. Real-provider interruption and a general job-history browser remain future work.
Use one API worker per data directory. See docs/adr/0019-durable-generation-jobs.md.

The Milestone 2 acceptance review is in docs/MILESTONE_2_ACCEPTANCE.md. Milestone 2 is complete for the local mock profile, including room style controls.

Room AI style fields (Environment, Render style, Palette) override map defaults when
nonblank. Apply prompt and style is undoable, preserves existing art, and invalidates
pending previews. Generate again to use the new style. The assembled provider prompt
and resolved style are saved in generation provenance. Output remains a mock pattern.
