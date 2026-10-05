# Editor interface

Status: Accepted layout direction, 2026-09-23, based on the owner's interface sketch
and follow-up discussion. Rewritten 2026-10-05 to describe current behavior; the
interaction rules themselves are unchanged. Applies to Milestone 1 and later.

## Fixed layout

The canvas occupies the entire window. Panels overlay it; opening, collapsing,
or dismissing panels must never resize or shift the canvas. No document scrolling.

| Position | Purpose | Implemented | Planned |
|---|---|---|---|
| Top-left | Compact identity | MQ mark and accessible project title | Visible project name |
| Top bar | Global actions | File (New/Open/Save, save state, Export PNG/WebP), View (map size, Fit map, Grid), Settings, Help (connection, shortcuts), Snap, Pan, Undo/Redo; connection indicator | Provider settings; Foundry export with a compatibility summary |
| Left rail | Editing scope (what) | Map and Room; Region, Object, Light and Sound shown disabled | Enable remaining scopes as their tools land |
| Beside rail | Scope tools (how) | Room: Rectangle room, Polygon room, Select/edit room, Place/edit door, Inspect walls | Standalone walls |
| Upper-right | Collapsible tabbed panel | Information (selection), Layers (artwork), AI (prompts, generation, provider readiness) | Object layers, job history |
| Bottom-left | Temporary feedback | Validation progress, dismissible errors, fading confirmations | Contextual guidance |
| Bottom-right | View status | Active tool, zoom, "Map background selected" | Cursor coordinates and grid scale |

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
- Map selects the base background as the generation target and has no tool panel.
  It returns to Pan, suspends room tools, and toggles off when pressed again. The
  status overlay confirms "Map background selected". Selecting Map does not select
  every room and does not invoke AI; generation happens in the AI tab.
- Map generation replaces only the base environmental image across the map bounds,
  preserving rooms, objects, other layers and metadata. Context images and the layer
  being regenerated are distinct. Proposals follow preview/accept and undo.
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
  selection details. Layers lists artwork front-to-back above a pinned background.
  AI holds prompts and generation. Form drafts survive tab switches. Selecting rooms,
  walls or doors preserves the active tab. Information puts Apply/Reset/Delete above
  the fields and displays each vertex's x/y coordinates side by side.
- General map facts live in View, session/persistence information in File, and
  connectivity in Help with a compact top-bar indicator.
- On narrow windows, opening a scope or dropdown collapses persistent info.
  Reopening info must not close the scope or change its tool.
- Buttons use visible labels or accessible names and tooltips. Expanded/pressed
  states are exposed to assistive technology. Escape returns focus to the opener.
- Temporary confirmations fade. Errors requiring attention stay until dismissed
  or another attempt begins. Feedback overlays never move the map.
- Panel, view and selection changes do not enter document undo history.
- File shows Not saved, Unsaved changes or Saved with its revision. Only a validated
  successful save can show Saved; failures and stale-revision conflicts retain work.
  Unavailable features may appear as disabled entries but must not pretend to work.

## Current behavior by area

### Drawing rooms

- Rectangle room: drag opposite corners. Leaving the drawing surface cancels the draft.
- Polygon room: click to place corners. Close by clicking the first point again (within
  8 screen pixels, or at the same snapped coordinate) or choose Finish polygon. At
  least three distinct vertices are required; drafts allow at most 2048 vertices.
  Remove last point, Cancel polygon and Escape correct or discard a draft. Pan and zoom
  preserve placed points; changing tools or scope discards the draft. Remembered tools
  never restore drafts.
- The backend rejects crossings, zero area and out-of-bounds geometry without changing
  history. Rejected polygon drafts remain editable.

### Editing rooms

- Select/edit room, then drag inside a room to move it or drag a corner handle to
  reshape it. With Snap, a move snaps the vertex nearest the grab point to the grid
  (that anchor is highlighted) and translates every vertex equally, realigning
  off-grid rooms without deforming irregular polygons. Corner edits snap that corner.
- Information edits the name and exact native coordinates (not snapped), inserts or
  removes points, and deletes the room. Apply validates and commits one history entry;
  Reset discards the draft. Drafts reset on selection change or after a committed
  edit, undo or redo.
- Escape, leaving the canvas or changing tools cancels an uncommitted drag. Failed
  validation leaves the room intact. Selection itself creates no undo entry.
- One room is selected at a time. Overlapping rooms select the topmost; clicking
  empty canvas deselects. A room with artwork can also be selected from its Layers row.

### Walls and doors

- Walls are read-only and derived from room boundaries. Inspect walls (the last Room
  tool) selects a segment within 8 screen pixels and shows endpoints, length, blocking
  flags and contributing rooms. Shared boundaries produce one segment; intersections
  split segments; unchanged endpoints keep their IDs through reordering and undo/redo.
  Derivation is asynchronous: outdated results are hidden, and failures offer Retry
  walls without changing rooms. Limits: 128 rooms, 2048 total vertices, 8192 segments.
- Place/edit door (just above Inspect walls): set a width (default 50 units), click a
  wall. The full opening must fit on one segment without overlapping another opening;
  openings may meet wall endpoints exactly. With Snap, door centers snap to globally
  anchored grid-cell midpoints (25, 75, 125, …); on diagonal walls the dominant
  coordinate snaps and the center stays on the wall. Inspector positions are exact.
- Drag a door to slide it along its wall, with a live preview clamped to the wall and
  one validated undo entry on release. Leaving the canvas, blur, Escape or a tool
  change cancels. Information has Apply/Reset/Delete plus name, width, position,
  state and secret flag. Open doors draw dashed; locked doors use a long/short dash.
- Whole-room translations carry doors, and wall splits away from openings remap them.
  Cuts through openings, ambiguous shared-wall movement, or deleting a door's last
  source room are rejected. Room geometry, walls and doors undo together.

### Layers

- Artwork rows are listed front-to-back above the pinned background. Each row has a
  drag handle, a truncated name, a visibility checkbox and a 0–100% opacity slider.
- Drag a row onto another to move it there; an insertion line appears above targets
  before the source row and below targets after it, and clears on invalid targets,
  leaving the list, drop or cancel. Focus the handle and press Up/Down to reorder
  from the keyboard.
- Opacity commits once on release, key completion or blur, so a gesture is one undo
  entry. Clicking a room's artwork name selects that room without switching tabs.
- Order, visibility and opacity are undoable, saved, used by export, and preserved
  when a layer is regenerated. Reordering never changes geometry or gameplay data.
  Editor overlays (grid, outlines, selection) always stay above artwork.

### AI generation

- Map → AI: background prompt and map-wide Environment, Render style and Palette.
  Apply is one undoable change; pending (unapplied) drafts disable generation.
- Room → AI (with a room selected): room prompt and style overrides. Blank fields
  inherit the map value, shown as a placeholder. Apply is one undoable change that
  keeps existing artwork until a replacement is accepted.
- The AI tab shows provider identity, readiness and capabilities. Check provider
  re-runs readiness; generation stays disabled until it passes.
- Generate preview queues a job and shows queued/running state. The preview renders on
  the map in the target layer's stack position, at full opacity, without entering
  history or save data. Accept applies it as one undoable step; Reject, Regenerate and
  Cancel preview are available. Cancel sends server-side cancellation. Results never
  auto-apply, and job failures stay visible until dismissed.
- Any document change makes an open preview stale; stale previews explain why they
  cannot be accepted. Leaving the target scope removes the preview overlay.
- After a reload, reopen the saved map, choose the same Map or room target, and use
  AI → Recover preview. A document mismatch blocks recovery and offers Discard. A
  browser-storage failure is reported without blocking generation.
- Moving or reshaping a room clears its artwork with a notice; Undo restores it.
  Room interiors have no editor tint; wall outlines and selection guides remain.

### File and export

- New/Open confirm before discarding unsaved committed edits and reset undo history;
  Save keeps it. Apply inspector drafts before saving.
- Export PNG and Export WebP flatten accepted artwork at the highest stored resolution,
  with current layer settings and unsaved applied edits, excluding on-map previews and
  all editing guides. Export does not save or change history.

## Planned placement

- Milestones 3–5: provider settings and capability status move into Settings as
  providers multiply. File gains Foundry export with a compatibility summary. Provider
  secrets stay on the server.
- Milestones 6–7: enable Region, Object, Light and Sound scopes as tools land. Brush
  masks and language proposals use the same preview/approval area and must not obscure
  the selected map area unnecessarily.
- Object artwork joins the Layers list and can be placed below rooms. Regions remain
  semantic/gameplay areas: their shading is an editing aid, not generated artwork.
  Visual features belong to objects, optionally paired with a separate region. See
  ADR-0010 and manifest §10.2.1.

### Exterior and interior composition (planned, ADR-0023)

Map AI will use placed room footprints and relevant descriptions to generate exterior
terrain and building exteriors. Interior room artwork covers that background, and the
layer visibility checkbox reveals the exterior underneath without deleting room
geometry or wall/door data. The exterior must remain complete under hidden interiors.
This requires layout-aware generation and explicit building/open-air intent, neither of
which exists yet. Do not add implicit roofs to every room polygon or relabel Regions
as building artwork. Flat-image export reflects visible artwork only.

### Standalone walls (proposed direction, not accepted)

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
the result should be one validated, undoable transaction.
