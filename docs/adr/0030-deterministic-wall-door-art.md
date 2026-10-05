# ADR-0030: Deterministic wall and door artwork

Status: Accepted; first implementation complete with offline and browser tests.
Visual quality with real SDXL interiors still needs an owner trial.
Implements the "deterministic wall/door visual treatment" layer of manifest §10.2.
Narrows the role of ADR-0029's wall guidance; does not supersede it.

## Context

Walls and doors are authoritative geometry (ADR-0001, ADR-0013, ADR-0014), but
until now their only *visual* appearance in artwork came from the image model.
SDXL painted floors, furniture and walls together, steered by a mask, prompt text
and optional ControlNet guidance. Owner trials found invented partitions, walls in
the wrong place and unclear doorways; ADR-0029 itself calls this soft conditioning.
The flattened export contained no walls unless a model happened to paint them,
so visible walls could disagree with the collision walls a Foundry export would
carry. `map.style.wallThicknessPx` existed in the schema but nothing used it.

## Decision

Quill renders walls and doors itself, from geometry, as a transparent overlay
composited above all raster artwork. AI providers paint only floors, furnishings
and terrain.

Geometry:

- The wall body is the union of each room boundary, buffered by half the wall
  thickness with mitred joins (mitre limit 2), clipped to map bounds. Derived walls
  come from those same boundaries, so this matches them; buffering whole rings
  gives clean corners that buffering separate segments cannot.
- Visible doors (`doorType: door`, not secret) cut an opening of the door's width
  across the full band. The opening never removes other walls' bands, so a door
  meeting a wall end does not notch the perpendicular wall.
- Closed door: a leaf across the opening. Locked: the same leaf with a dark bar.
  Open: the leaf swung 90° on the opening's low-end hinge toward the wall's left
  normal. Secret doors are drawn as plain wall, so they are invisible in artwork.
  Windows keep the wall and add a glass pane.
- Pixel coverage uses the pixel-center rule of `raster.polygon_mask`; continuous
  native-to-image conversion is `raster.native_to_pixel` (+y up becomes rows down
  exactly once). Pillow only proposes candidate pixels; Shapely decides them.
  Outputs at 1200 px wide or smaller are 2× supersampled and box-filtered for
  antialiasing.

Appearance: three materials (stone, timber, plaster) built from seeded value
noise on a lattice in native units, so texture placement is deterministic and
independent of output resolution, plus a darkened rim so walls read clearly over
any floor art. No bundled image textures and no AI. Renderer id: `quill-wall-art-v1`.

Settings and contracts:

- Thickness reuses `map.style.wallThicknessPx` (native map units, despite the
  name), now validated to 1–50. New editor projects default to 10 units, one
  foot with the default grid. Existing projects keep their stored value.
- Visibility and material live in `project.settings["quill.wallArt"]` as
  `{visible: bool, material: "stone" | "timber" | "plaster"}`, the same
  namespaced-settings pattern ADR-0022 uses for the background prompt. Absent
  means visible stone. Malformed values are rejected on save/open, never stripped.
- No project schema change and no migration. New API contract `WallArtRequest`
  (geometry schema) for `POST /api/render/walls`: raster size, thickness,
  material, rooms and doors. The server re-derives walls and validates doors.
  Sizes are limited to the export profiles and a 2400 × 1600 preview.

Composition and use:

- Flattened PNG/WebP export draws wall art above every artwork layer when
  visible. Hidden wall art leaves export identical to the artwork composite.
- The editor shows the same server-rendered PNG (2400 × 1600) above artwork and
  below grid and editing overlays, so preview and export share one renderer.
  Changes are debounced. A pending render keeps the previous image; a failed
  render shows a message and leaves geometry unchanged. Wall and unselected door
  guides dim to 35% while wall art is shown.
- Layers → Walls & doors toggles visibility and sets material and thickness.
  Each change is one undoable map-authoring edit and persists through Save/Open.
- Wall art is never part of AI generation context. `composite_artwork`, used to
  build provider inputs, stays artwork-only.
- When wall art is visible, SDXL room prompts start with an instruction to paint
  only the floor, right up to the boundary, and no walls or doorways. Provenance
  records `wallArt` (renderer, visibility, material, thickness) and
  `promptTemplate` `sdxl-room-layout-v2`. ADR-0029's ControlNet guide is
  unchanged and still shows where walls are, but it is no longer what makes walls
  correct. Mock generation and background prompts are unchanged.

## Consequences

- Visible walls always match collision geometry, at any resolution, with no GPU
  or model involved. Seams between adjacent room generations are covered by a
  shared wall band, and model-painted walls near a boundary are mostly covered.
- Existing projects gain visible stone walls in previews and exports by default.
  Accepted artwork assets do not change; hide wall art to restore the previous
  export.
- Doors are drawn in their current editor state. Foundry doors change state
  during play, so the Foundry slice (Milestone 4) must decide whether to bake
  doors closed or export them as separate door tiles. Recorded as an open item.
- Interior partitions cannot be prompted: they need standalone wall geometry,
  which is still planned (docs/INTERFACE.md).
- Limitations of v1: one material and thickness per map, no per-wall overrides;
  timber grain runs along x regardless of wall direction; no wall shadows or
  height cues; the 2400 × 1600 preview softens at high zoom. Exports are still
  limited to 480 × 320 and 960 × 640 (a separate resolution item).
- Renderer output changes must bump the renderer id and update golden tests.

## Verification

`tests/test_wall_art.py` covers band thickness and position, image orientation,
mitred corners, transparent surroundings, each door state, secret doors matching
plain wall exactly, windows, openings at wall ends, rasterization identical to
`polygon_mask`, determinism, materials, size/thickness limits, settings
validation, export composition (visible and hidden), exclusion from AI context,
and the render endpoint (byte-identical to the shared renderer; invalid sizes,
thickness, material, door references and content type). The SDXL editor test
checks the prompt prefix and `wallArt` provenance. `tests/wall-art.test.ts`
covers settings defaults, undoable map-authoring changes and request/schema
agreement. `tests/browser/wall-art.spec.ts` covers on-canvas rendering,
visibility with undo/redo, material, thickness validation and Save. Existing
save/reopen pixel tests now wait for wall art to settle.

Next: owner trial with SDXL interiors (wall art on and off, same seed). Then
consider per-wall material/visibility, standalone walls for partitions, and the
Foundry door-state decision above.
