# Editor interface plan

Status: Accepted layout direction, 2026-09-23. Based on the owner's interface
sketch and follow-up discussion. Applies to Milestone 1 and later features.

## Fixed layout

The canvas occupies the entire window. Panels overlay it; opening, collapsing,
or dismissing panels must never resize or shift the canvas. No document scrolling.

| Position | Purpose | Implemented now | Planned additions |
|---|---|---|---|
| Top-left | Compact identity | MQ mark and accessible project title | Project name |
| Top bar | Global actions | File/View/Settings/Help disclosures, always-visible Snap, Pan, Undo/Redo, New/Open/Save, save state | Export |
| Left rail | Editing scope (what) | Map and Room | Region, Object, Light, Sound |
| Beside rail | Scope tools (how) | Rectangle, polygon, select/edit, doors, inspect walls | Standalone walls |
| Upper-right | Collapsible tabbed panel | Information selection inspector, Layers ordering, AI room prompt | Raster/object layers, provider/job controls |
| Bottom-left | Temporary feedback | Validation progress, dismissible errors, fading success | Job notifications and contextual guidance |
| Bottom-right | View status | Active tool and zoom | Cursor coordinates and grid scale |

## Interaction rules

- Default to Pan with no scope open. At most one scope and one tool are active.
  Scope buttons toggle their panel; tool buttons toggle back to Pan when pressed
  again. Closing a scope suspends its tool and returns to Pan. Remember the last
  explicit tool choice per scope (including Pan); reopening restores it. Changing
  scopes suspends the old tool and restores the destination's choice, or Pan for
  a scope never used. This restoration takes precedence over the Pan fallback.
- Canvas clicks dismiss global dropdowns only. Scope tools remain available while
  drawing and while interacting with other controls. Escape cancels drafts and
  closes the global dropdown first, otherwise the scope (preserving its memory).
- Map selects the base background as the future generation target and has no expanded panel. It
  returns to Pan, suspends room tools, and toggles off when pressed again. The
  status overlay confirms Map background selected. Dimensions live in View and Fit
  map in View. Selecting Map does not select every room for bulk editing.
- Future Map generation replaces the base environmental image across map bounds,
  preserving rooms, objects, other layers and metadata. Selecting Map alone does
  not invoke AI. Prompt submission and generation are not implemented yet.
  Context images and the layer being regenerated are distinct; proposals still
  follow preview/accept and undo.
- Pan is globally available. Space-drag temporarily pans, except when typing in
  form fields; releasing Space restores the previous tool without changing scope
  or remembered tools. Space is reserved for pan even with a button focused; Enter
  activates focused buttons. Checkboxes retain their native Space behavior.
- Snap stays visible on the top bar. A small fixed-size point marks the snapped
  drawing position inside the map; hide it when snapping is off, the pointer leaves
  the canvas, validation is pending, or Pan/temporary pan is active. It uses the
  exact same native-to-screen conversion as the proposed room corner.
- Wheel input over a scrollable panel or textarea scrolls that surface, including
  at its limits; it must not leak into canvas zoom. Elsewhere the wheel zooms the
  map. The page never scrolls. Horizontal-only wheel input does not change zoom.
- Right tabs stay visible above the scrolling body. Information is reserved for
  selection details; Layers lists front-to-back room shapes with Raise/Lower and
  a fixed base background; AI holds the selected room prompt and future generation
  controls. Form drafts survive tab switches. Selecting rooms, walls or doors preserves the active
  tab. Information puts Apply/Reset/Delete above the fields and displays each
  vertex's x/y coordinates side by side.
- General map facts live in View, session/persistence information in File, and
  connectivity in Help with a compact top-bar indicator. The separate room list
  is replaced by selectable layer entries.
- On narrow windows, opening a scope or dropdown collapses persistent info.
  Reopening info must not close the scope or change its tool.
- Buttons use visible labels or accessible names and tooltips. Expanded/pressed
  states are exposed to assistive technology. Escape returns focus to the opener.
- Temporary confirmations fade. Errors requiring attention stay until dismissed
  or another attempt begins. Feedback overlays never move the map.
- Panel/view/selection changes do not enter document undo history.
- File shows Not saved, Unsaved changes or Saved with its revision. Only a validated
  successful save can show Saved; failures and stale-revision conflicts retain work. Unavailable features are described in docs; limited
  disabled scope entries may indicate expansion without pretending to work.

## Future feature placement

Milestone 1: Select/edit and Layers feed the right inspector (name,
geometry). Dragging a room moves it; corner handles reshape it. Numeric edits,
inserting/removing vertices and Delete room are available in the inspector.
Apply validates before committing one history entry. Selection preserves the active tab;
clicking empty canvas deselects. Only one room is selected. Covered rooms remain
selectable in Layers. Room prompts live in AI. Walls and doors initially live
under Room. File provides New/Open/Save with local atomic snapshots (ADR-0015).

Milestone 2: Right panel gains layers and generation jobs. Progress, cancel,
preview, accept/reject and stale-result feedback must be visible. Applying a result
is one undoable command. Do not auto-hide actionable job failures.

Layer controls must allow room/object/effect artwork to be reordered, including
objects below rooms, with the base background anchored underneath. Preserve order,
visibility and opacity when regenerating a layer. Reorder actions enter document
history and survive save/open and export. Editor overlays remain above artwork.
Regions remain semantic/gameplay areas; their shading is an editing aid, not a
generated layer. Visual features belong to objects, optionally accompanied by a
separate gameplay region. See ADR-0010 and manifest section 10.2.1 for all scopes.

Milestones 3–5: Settings gains providers and capability status. File gains Foundry
export with a compatibility summary. Provider secrets stay on the server.

Milestones 6–7: Enable Region/Object/Light/Sound scopes as tools land. Brush masks
and language proposals use the same preview/approval area; they must not obscure
the selected map area unnecessarily.

## Standalone walls: proposed direction, not yet implemented

Independent wall segments can use the existing nullable `sourceRoomId`; room
boundaries are not a prerequisite for a floating wall. A pillar is a closed
obstacle footprint, not automatically a room. The current room schema has one
outer polygon and no holes; pillar exclusions from room floors/generation need
an explicit geometry decision and contract tests before implementation.

Recommend detecting bounded wall circuits and offering a previewed **Create room
from enclosure** command, rather than silently creating rooms for every loop.
Optional automatic proposals may come later. Endpoint snapping, intersection
splitting, shared boundaries, nested loops and stable wall/door references need
deterministic topology rules first. Open doors still belong to a structural
boundary. Creating a room from walls must not duplicate the existing segments;
the result should be one validated, undoable transaction. This is a design proposal
for the Milestone 1 wall work, not an accepted schema change or implemented tool.

## Current limits

Rectangle and polygon room addition with undo/redo are implemented. Polygon drafts
use click-to-place corners, first-point closure (8 screen pixel tolerance), Finish,
Remove last point and Cancel. At least three distinct vertices are required;
backend validation rejects crossings, zero area and out-of-bounds geometry without
changing history. Rejected drafts remain editable. Pan/zoom preserve draft points;
tool/scope changes or Escape cancel the draft. Remembered tools never restore drafts.
Selection, moving, vertex editing, name/prompt inspection and deletion are implemented
with undo/redo. Rejected geometry leaves the existing room unchanged. Leaving a drag,
Escape or tool changes cancel its preview. Inspector drafts reset on selection or
committed room changes; exact coordinate entry bypasses grid snapping.
Room-shape ordering and the AI prompt editor are implemented. Raster/object layer
management and generation execution are not claimed by this layout. Those remain in their scheduled milestones. File persistence now covers the current
rooms/walls/doors profile. Apply inspector drafts before saving. New/Open confirms
discarding unsaved committed edits and resets undo history; saving preserves it.

Derived wall inspection is implemented under Room → Inspect walls. Canvas hits use
an 8-screen-pixel tolerance. Inspect walls is the last scope-menu button; no wall
dropdown or segment-count text appears in the menu. Information
shows endpoints, length, blocking flags and contributing rooms. Walls are geometry
overlays, not reorderable artwork layers. Loading hides stale segments; derivation
failures retain rooms and provide Retry walls. Door placement/editing is available immediately above Inspect walls. Information
contains door Apply/Reset/Delete, name, width, position, state and secret flag.
Door selection preserves the active tab. Wall overrides remain unavailable.
See ADR-0013/0014 for shared-boundary and attachment rules.

Doors snap to globally anchored grid-cell midpoints. On diagonals the dominant
coordinate snaps and the center remains on the wall. A 50-unit opening can meet a
wall endpoint exactly. Click-drag slides only along its attached wall, with a live
preview and one validated undo entry on release; leaving the canvas, blur, Escape
or tool changes cancel. Inspector positions remain exact, independent of Snap.

Milestone 2 first increment: Map → AI now provides mock background prompt/seed,
Generate preview, Accept background, Reject preview, Regenerate preview and Cancel
preview. The image preview stays in the right panel until accepted; it does not
replace canvas pixels automatically. Stale previews explain why acceptance is
blocked. Layers exposes background visibility and opacity; the base stays at the
bottom. Room imagery and independent artwork ordering remain planned (ADR-0016).

Room generation now follows the applied room prompt in AI. Generate preview,
Accept room artwork, Reject preview and regeneration use the same preview lifecycle
as Map. Room layers are bound through renderLayerId. Geometry changes clear outdated
artwork with a notice; Undo restores it. Layers still orders room geometry only;
independent artwork ordering remains the next layer-management increment (ADR-0017).

Artwork controls in Layers are listed front-to-back separately from room outlines. Raise/lower changes raster composition only; background stays pinned at the bottom. Visibility and opacity apply per artwork layer. All changes support undo/redo and native save/open; regeneration retains these settings.

Generation previews render temporarily on the map in the target layer's stack position
(or its proposed position for new art), at full opacity and visible. They do not enter
history or save data until accepted. Reject, stale context and leaving the target scope
remove the overlay. Accepted artwork settings remain unchanged. The AI panel contains
preview actions, with no thumbnail. Room-outline lists are removed; geometry selection
is performed on the canvas.

Artwork rows use a drag handle, truncated room name, visibility checkbox and compact
0–100% opacity slider. Drag onto another artwork row to move to its position. Focus the
handle and use Up/Down for keyboard reordering. The background is pinned. Opacity edits
commit once on release/keyboard completion/blur, so a gesture is one undo transaction.

The drag insertion line appears above targets preceding the source row and below
targets following it. Line and highlight clear on the source row, invalid targets,
leaving a row/list, drop or cancellation. Clicking a room artwork name selects that
room without switching the right-panel tab. Object artwork selection will use the
same interaction when object editing is implemented.

File offers Export PNG and Export WebP (480 × 320). Export uses accepted artwork with
current layer settings, excluding on-map previews and all editing guides. It includes
unsaved applied edits without saving or changing history.

AI generation displays queued/running job state and Cancel preview sends server-side
cancellation. Job completion still requires explicit acceptance. Room interiors have no
green fill; wall outlines and selection/editing guides remain.

After reload, reopen the saved map, choose its Map or room target, and use AI → Recover
preview. A document mismatch blocks recovery with an explanation and Discard action.
Nothing is auto-accepted. Browser storage failure is reported without blocking generation.

Room AI includes Environment, Render style and Palette. Blank values inherit the map
default shown as a placeholder. Apply prompt and style commits one undoable edit;
existing artwork stays until the user generates and accepts a replacement.

Map AI exposes Background prompt and map-wide Environment, Render style and Palette.
Apply map prompt and style is one undoable change; Save persists applied values. Pending
map drafts disable generation. Blank room fields inherit these defaults. Editing map
settings invalidates previews but preserves accepted artwork.

### Planned exterior/interior composition

Map AI will use placed room footprints and relevant descriptions to generate exterior
terrain/buildings. Interior room artwork covers that background. The existing layer
visibility checkbox reveals the exterior underneath; it never deletes room geometry or
wall/door metadata. The exterior must remain complete under hidden interiors. This
requires layout-aware generation and explicit building/open-air intent (ADR-0023), neither
of which is implemented yet. Do not add implicit roof behavior to every room polygon or
relabel Regions as building artwork. Flat-image export reflects visible artwork only.
