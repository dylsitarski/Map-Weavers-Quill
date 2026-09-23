# Editor interface plan

Status: Accepted layout direction, 2026-09-23. Based on the owner's interface
sketch and follow-up discussion. Applies to Milestone 1 and later features.

## Fixed layout

The canvas occupies the entire window. Panels overlay it; opening, collapsing,
or dismissing panels must never resize or shift the canvas. No document scrolling.

| Position | Purpose | Implemented now | Planned additions |
|---|---|---|---|
| Top-left | Compact identity | MQ mark and accessible project title | Project name |
| Top bar | Global actions | File/View/Settings/Help disclosures, Pan, Undo/Redo | New/Open/Save, save state, export |
| Left rail | Editing scope (what) | Map and Room | Region, Object, Light, Sound |
| Beside rail | Scope tools (how) | Map facts, rectangle tool | Polygon, selection, move, vertices, walls/doors |
| Upper-right | Collapsible persistent information | Map facts, room list, connection status | Selection inspector, layers, provider/job panels |
| Bottom-left | Temporary feedback | Validation progress, dismissible errors, fading success | Job notifications and contextual guidance |
| Bottom-right | View status | Active tool and zoom | Cursor coordinates and grid scale |

## Interaction rules

- Scope and active tool are separate state. Closing a tool panel retains the tool.
- Clicking the canvas closes transient menus and scope flyouts. Persistent info
  stays open until collapsed. Escape cancels a draft and closes transient panels.
- Pan is globally available. Space-drag temporarily pans, except when typing in
  form fields; releasing Space restores the previous tool.
- Wheel input zooms the map, including over overlays. Long information panels use
  bounded regions with draggable scrollbars and keyboard scrolling; the page
  itself never scrolls. Horizontal-only wheel input does not change zoom.
- On narrow windows, opening a flyout collapses persistent info and vice versa.
- Buttons use visible labels or accessible names and tooltips. Expanded/pressed
  states are exposed to assistive technology. Escape returns focus to the opener.
- Temporary confirmations fade. Errors requiring attention stay until dismissed
  or another attempt begins. Feedback overlays never move the map.
- Panel/view/selection changes do not enter document undo history.
- Session-only storage is stated explicitly until saving exists. Never show a
  false Saved indicator. Unavailable features are described in docs; limited
  disabled scope entries may indicate expansion without pretending to work.

## Future feature placement

Milestone 1: Room flyout adds polygon and select/edit tools. Map click selection
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

## Current limits

Only rectangular room addition and its undo/redo are implemented. No selection
inspector, file persistence, polygon tools, layer management, or generation UI is
claimed by this layout. Those remain in their scheduled milestones.
