# Map-Weaver's Quill

A local-first, AI-assisted 2D battlemap editor. You draw rooms, walls and doors as
exact geometry, describe each area in words, generate artwork for just that area, and
(planned) export the result to Foundry VTT. Linux is the primary target; Windows 11
follows later.

The structured scene is authoritative: AI-generated pixels decorate the geometry but
never define walls, doors or gameplay data. See [PROJECT_MANIFEST.md](PROJECT_MANIFEST.md)
for the full product brief and plan.

## Status

| Milestone | Status |
| --- | --- |
| 0 — Repository and contracts | Complete |
| 1 — Deterministic editor foundation | Complete for the current editor profile |
| 2 — Layered raster pipeline and mock generation | Complete for the offline mock provider |
| 3 — First real image provider (local ComfyUI/SDXL) | **In progress** |
| 4 — Foundry vertical slice | Not started |
| 5–8 — Second provider, objects/lights/regions, language commands, packaging | Not started |

Milestone 3 so far: the SDXL adapter works end to end in the editor (queued previews,
accept/undo, save/open, export) and is covered by offline tests. The owner has run SDXL
locally, but image quality is not yet acceptable and hardware measurements are not
recorded. Open problems are furniture scale, invented interior partitions, and
backgrounds that ignore the placed rooms. Rooms can optionally use a dedicated SDXL
inpainting model (ADR-0031), but SDXL still does not reliably draw a large enclosed room
as indoors. A second local model family, FLUX.2 klein (ADR-0032), draws whole rooms
indoors with walls in place in about 20 seconds. Its sketch-reference trial showed
furniture scale varying with room size, placeholder floors, and doors not always
honoured. Rooms now use a fixed-scale context window and room-first prompts, with doors
drawn closed (ADR-0033): in trial, scale and wall tops were consistent at about 12
seconds per room, but floors still drift toward the placeholder colour, furniture stays
along the walls, and room descriptions show weakly. A second klein pass now restyles each
room from its description (ADR-0034): in trial, character and furnishing improved
markedly at about 24 seconds per room, but rooms grew beyond their walls and doors were
unreliable. Klein now samples only inside the room, with the surroundings held fixed
(ADR-0035): in trial, every room stayed inside its walls, but the second pass then copied
the first, keeping placeholder floors. The second pass now repaints the first from a
partly noised image without a reference (ADR-0036). Next: a trial of that; doors remain
open.

Verification evidence and the development log are in [docs/HISTORY.md](docs/HISTORY.md).

## Setup (Linux, Python 3.12, Node 24)

```sh
nvm install          # Node version comes from .nvmrc
nvm use
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
npm ci
make check
```

Node 24 is enforced by npm and `make doctor`. Any Node manager that selects Node 24
works. For browser tests, run `npx playwright install --with-deps chromium` once
(system dependencies may need sudo), then `make browser`.

## Commands

| Command | Purpose |
| --- | --- |
| `make dev` | Start the web editor at http://127.0.0.1:5173 and API at http://127.0.0.1:8000. Ctrl-C stops both. Linux only. |
| `make test` | Python and TypeScript tests, plus checks that generated schemas and types are current |
| `make check` | `make test`, plus Ruff lint/format, mypy, TypeScript checks, Vite build and Biome lint |
| `make browser` | Playwright browser tests (starts its own `make dev`) |
| `make schema` | Regenerate JSON Schema and TypeScript declarations after changing Python models |
| `make audit` | Online dependency audit (Python and npm) |
| `make comfy-check` | Check a running local ComfyUI for the configured SDXL setup |
| `make debug-bundle PROJECT="name"` | Export one saved project for debugging (see below); without `PROJECT`, list saved projects |

All tests are offline: no credentials, paid APIs or GPUs. GitHub Actions runs
`make check`, `make browser` and `make audit` on Ubuntu for pushes and pull requests.
API documentation is served at http://127.0.0.1:8000/docs while `make dev` runs.

## Using the editor

The canvas fills the window. The top bar holds File, View, Settings, Help, Snap, Pan,
Undo and Redo. The left rail chooses a scope (Map or Room; Region, Object, Light and
Sound are shown but disabled). The upper-right panel has three tabs: **Information**
(the current selection), **Layers** (artwork order, visibility and opacity) and **AI**
(prompts and generation). Messages appear at the bottom-left. Detailed interaction
rules are in [docs/INTERFACE.md](docs/INTERFACE.md).

Navigation: Pan is the default tool. Drag with Pan, or hold Space, to move the view.
Scroll over the canvas to zoom; scrolling over a panel scrolls the panel instead.
View → Fit map recenters. Grid visibility (View) and Snap (top bar) are independent.
Escape cancels a draft or closes a menu.

### Rooms

Choose **Room**, then a tool:

- **Rectangle room**: drag opposite corners.
- **Polygon room**: click to place corners; click the first point again or choose
  Finish polygon (at least three points). Remove last point and Cancel polygon correct
  a draft.
- **Select/edit room**: drag inside a room to move it, or drag a corner to reshape it.
  With Snap on, a move snaps the vertex nearest your grab point to the grid and shifts
  the whole room by the same amount; corner drags snap that corner. The Information tab
  edits the name and exact coordinates, adds or removes points, and deletes the room.
  Apply commits the whole edit once; Reset discards it.

The server validates every geometry change. Self-crossing, zero-area or out-of-bounds
shapes are rejected without changing the room or undo history. Room edits support
Undo/Redo. Where rooms overlap, clicking selects the one drawn last.

### Walls and doors

Walls are derived automatically from room boundaries. Shared boundaries become one wall
and intersections split walls. **Inspect walls** shows a wall's endpoints, length,
blocking flags and source rooms. Standalone walls (not attached to a room) are not
implemented.

**Place/edit door**: set a width (default 50 units) and click a wall. The whole opening
must fit on one wall without overlapping another opening. Drag a door to slide it
along its wall. Click a door to edit its name, width, position, state (open, closed,
locked) and secret flag in Information. Moving a whole room carries its doors. Edits
that would cut through a door or leave it without a wall are rejected: move or delete
the door first. Room, wall and door changes undo together.

### Projects

File → **Save project** stores a validated snapshot; **Open saved project** lists saved
maps; **New project** starts a blank map. New and Open ask before discarding unsaved
edits. Opening resets selection, view and undo history (undo history is per session).
Refreshing the browser starts a blank editor, so reopen your map from File.

To share a project for debugging, run `make debug-bundle PROJECT="Your project name"`. It
writes a folder and a `.zip` under the data directory containing a readable summary of
prompts, rooms and doors, the project JSON, current artwork layers, and every accepted
generation and queued preview for that project with its exact model prompt, parameters
and input/output images. To keep it small enough to attach, it includes only the 3 most
recent accepted generations and previews, and saves artwork as WebP; it prints the zip
size. Run the script directly for more control, for example
`PYTHONPATH=apps/server .venv/bin/python scripts/export_debug_bundle.py "Name" --last 1`
(`--last 0` for everything, `--lossless` for PNG). It only reads the database, so it is
safe while Quill runs. The bundle is private project content; never commit it.

Projects are stored in `data/projects.sqlite3` under the server's working directory.
Set `MWQ_DATA_DIR` before `make dev` to use another directory. Stop the server before
copying that directory as a backup. Saves are atomic, earlier snapshots are kept, and
a stale or conflicting save is refused rather than overwriting newer work.

### Artwork and AI generation

The default provider is an offline **mock** that paints deterministic test patterns,
useful for exercising the workflow without a GPU. To generate real images, set up
local SDXL (below).

- **Map background**: choose Map, open the AI tab, enter a background prompt and map
  style (Render style, Palette), Apply, then **Generate preview**. Describe the setting
  (forest, desert) in the background prompt and in each room's prompt.
- **Room artwork**: select a room, open AI, enter its prompt and optional style
  overrides (blank fields inherit the map style), Apply, then **Generate preview**.
  Describe the room's contents and floor. Doors come from the map and are currently
  always drawn closed; secret doors look like wall.

Each generation uses a new random seed; check **Lock seed** (or type a seed) to reuse
one. Accepting artwork drops the history records of artwork it replaces, so
regenerating never reaches the 128-record limit.

Previews appear on the map but change nothing until you **Accept**; Reject or
Regenerate instead. Accepting is one undoable step. Any edit made while a preview is
pending makes it stale, and stale previews cannot be accepted. Room artwork is clipped
exactly to the room: pixels outside it never change. Moving or reshaping a room
clears its artwork (Undo restores it).

Generation runs in a durable local queue. Cancel discards the result, though the
provider may keep computing. After a browser reload, reopen the saved project,
select the same target and use **Recover preview** in AI.

In **Layers**, drag artwork rows (or focus the handle and press Up/Down) to reorder
them, and set each layer's visibility and opacity. The background stays at the bottom.
Clicking a room's artwork name selects that room. All of this is undoable and saved.

### Export

File → **Export PNG** or **Export WebP** downloads the accepted artwork, flattened, at
the highest stored resolution (480 × 320 for mock art, 960 × 640 for SDXL art). Both
formats are lossless. Export respects layer order, visibility and opacity, includes
unsaved applied edits, and excludes previews, the grid and editing guides. It does not
save the project. Foundry export is not implemented yet.

## Local image generation via ComfyUI

Real generation uses [ComfyUI](https://docs.comfy.org), installed and run separately
from Quill, with one of two model families: SDXL or FLUX.2 klein. Quill bundles no model weights. Full setup, configuration and
current limitations are in [docs/COMFYUI.md](docs/COMFYUI.md). In short, with ComfyUI
running on 127.0.0.1:8188:

```sh
export MWQ_IMAGE_PROVIDER=comfyui-sdxl
export MWQ_IMAGE_COMFY_CHECKPOINT=sd_xl_base_1.0.safetensors
make dev
```

Map → AI then reports provider readiness. Generation stays disabled until the check
passes. For better SDXL room artwork, also install the optional SD-XL Inpainting 0.1 UNet
and set `MWQ_IMAGE_COMFY_INPAINT_UNET`.

For FLUX.2 klein, install its three model files (docs/COMFYUI.md section 5), then use
`export MWQ_IMAGE_PROVIDER=comfyui-flux2-klein`. Klein receives each room's walls and
doors as a sketch in a reference image, so no ControlNet is needed.

## Provider configuration and secrets

The image provider is selected on the server with `MWQ_IMAGE_PROVIDER` (`mock`,
`comfyui-sdxl` or `comfyui-flux2-klein`); unknown values stop the API at startup. A hosted provider is planned
for Milestone 5. Its credential can already be supplied through exactly one of
`MWQ_IMAGE_API_KEY` or `MWQ_IMAGE_API_KEY_FILE`. Prefer a key file outside the
repository and data directory, with `chmod 600`. Keys never reach the browser,
provider discovery, projects or job data. `.env` is not loaded automatically: export
variables before `make dev`, and never use `VITE_` variables for secrets. See
[.env.example](.env.example) and ADR-0024.

## Current limits

- Fixed 1200 × 800 map with a 50-unit (5 ft) grid. Stored raster sizes are 480 × 320
  (mock) and 960 × 640 (SDXL).
- Up to 128 rooms, 2048 room vertices in total, 8192 walls, 1024 doors, 129 artwork
  layers and 128 generation records (only records for current artwork are kept). Save
  requests are limited to 4 MiB.
- Lights, objects, regions and sounds exist in the schema but are rejected by the
  editor's save/open validation rather than silently dropped.
- No standalone walls, wall overrides or room-shape reordering.
- No Foundry export, portable project archives, autosave, revision browser or asset
  garbage collection. Unknown schema versions are rejected (no migrations yet).
- Run one API process per data directory.
- The JSON Schema checks structure only; polygon and door topology are validated by
  the server.
- Windows 11 and Foundry compatibility are untested.

## Documentation

| Document | Contents |
| --- | --- |
| [PROJECT_MANIFEST.md](PROJECT_MANIFEST.md) | Product definition, architecture, contracts, milestones and current state (canonical) |
| [AGENTS.md](AGENTS.md) | Rules for AI coding agents working in this repository |
| [docs/INTERFACE.md](docs/INTERFACE.md) | Editor layout and interaction rules |
| [docs/COMFYUI.md](docs/COMFYUI.md) | Local ComfyUI/SDXL setup and behavior |
| [docs/adr/README.md](docs/adr/README.md) | Index of architecture decision records with current status |
| [docs/HISTORY.md](docs/HISTORY.md) | Milestone verification evidence and development log |
| [docs/MILESTONE_2_ACCEPTANCE.md](docs/MILESTONE_2_ACCEPTANCE.md) | Milestone 2 exit-criteria review |

## Distribution

Public, free, noncommercial distribution is intended, but no software license has been
selected yet, so this repository does not grant a redistribution license. Do not bundle
third-party model weights or private assets.
