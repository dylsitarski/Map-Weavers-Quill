# Editor interface plan

Status: Accepted layout direction, 2026-09-23. Based on the owner's interface
sketch and follow-up discussion. Applies to Milestone 1 and later features.

## Fixed layout

The canvas occupies the entire window. Panels overlay it; opening, collapsing,
or dismissing panels must never resize or shift the canvas. No document scrolling.

| Position | Purpose | Implemented now | Planned additions |
|---|---|---|---|
| Top-left | Compact identity | MQ mark and accessible project title | Project name |
| Top bar | Global actions | File/View/Settings/Help disclosures, always-visible Snap, Pan, Undo/Redo | New/Open/Save, save state, export |
| Left rail | Editing scope (what) | Map and Room | Region, Object, Light, Sound |
| Beside rail | Scope tools (how) | Rectangle and polygon tools | Selection, move, vertices, walls/doors |
| Upper-right | Collapsible persistent information | Map facts, room list, connection status | Selection inspector, layers, provider/job panels |
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
- Map selects the entire map as editor context and has no expanded panel. It
  returns to Pan, suspends room tools, and toggles off when pressed again. The
  status overlay confirms Whole map selected. Dimensions live in Info and Fit
  map in View. Selecting Map does not select every room for bulk editing.
- Future AI prompts may use this whole-map context. Prompt submission and generation
  are not implemented yet. Context selection alone must never trigger generation
  or authorize overwriting all map content; future proposals still need explicit
  editable bounds and the normal preview/accept workflow.
- Pan is globally available. Space-drag temporarily pans, except when typing in
  form fields; releasing Space restores the previous tool without changing scope
  or remembered tools. Space is reserved for pan even with a button focused; Enter
  activates focused buttons. Checkboxes retain their native Space behavior.
- Snap stays visible on the top bar. A small fixed-size point marks the snapped
  drawing position inside the map; hide it when snapping is off, the pointer leaves
  the canvas, validation is pending, or Pan/temporary pan is active. It uses the
  exact same native-to-screen conversion as the proposed room corner.
- Wheel input zooms the map, including over overlays. Long information panels use
  bounded regions with draggable scrollbars and keyboard scrolling; the page
  itself never scrolls. Horizontal-only wheel input does not change zoom.
- On narrow windows, opening a scope or dropdown collapses persistent info.
  Reopening info must not close the scope or change its tool.
- Buttons use visible labels or accessible names and tooltips. Expanded/pressed
  states are exposed to assistive technology. Escape returns focus to the opener.
- Temporary confirmations fade. Errors requiring attention stay until dismissed
  or another attempt begins. Feedback overlays never move the map.
- Panel/view/selection changes do not enter document undo history.
- Session-only storage is stated explicitly until saving exists. Never show a
  false Saved indicator. Unavailable features are described in docs; limited
  disabled scope entries may indicate expansion without pretending to work.

## Future feature placement

Milestone 1: Room flyout adds select/edit tools. Map click selection
feeds the right inspector (name, prompt, geometry). Walls and doors initially live
under Room. File gains real New/Open/Save once atomic persistence is implemented.

Milestone 2: Right panel gains layers and generation jobs. Progress, cancel,
preview, accept/reject and stale-result feedback must be visible. Applying a result
is one undoable command. Do not auto-hide actionable job failures.

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
No selection inspector, file persistence, layer management, or generation UI is
claimed by this layout. Those remain in their scheduled milestones.
