# ADR-0012: Anchor snapping and tabbed sidebar

Status: Implemented, 2026-09-24. Supersedes delta-only snapping in ADR-0011 and
wheel-over-all-overlays behavior in the original interface plan.

## Movement snapping

At drag start choose the vertex nearest the grab point (first polygon index breaks
ties). Hold that anchor throughout the gesture. Snap its proposed absolute native
position to the 50-unit grid, then apply the same translation to every vertex.
Off-grid offsets no longer persist forever; arbitrary polygons retain their shape.
The anchor is highlighted during snapped movement. Individual handle dragging and
exact coordinate entry retain their existing semantics. Clicking/selecting or
toggling Snap alone never modifies geometry. Movement commits only after the
existing drag threshold and backend validation; invalid proposals are rejected.

## Sidebar and wheel routing

Information shows selection details, Layers shows front-to-back room shapes and
AI contains the room prompt editor. Tab headers remain fixed and support arrow,
Home/End navigation. Bodies stay mounted so switching tabs retains form drafts.
New room selections open Information; updates to the same selection retain the tab.
File contains session/save limitations, View contains map facts, Help contains
connection details and the top bar has a compact live connection indicator.

Wheel events inside an actually overflowing, scrollable ancestor use native
scrolling instead of map zoom, even at its boundaries. Nested textareas participate;
overscroll containment prevents scrolling the page or zooming the canvas. Panels
without overflow retain existing wheel-to-zoom behavior.

## Ordering boundary

Raise/Lower changes room-shape drawing order using one undoable history command.
The current room array is back-to-front; the Layers UI reverses it for front-to-back
display. Hit testing follows that order. Reordering retains room references,
geometry and revisions, and is blocked during pending validation. The base
background remains fixed below room shapes. This is session-only vector ordering,
not completed raster-layer management. The compositor/persistence milestone must
map order to managed layers using the existing zIndex contract, with one ordering
authority and save/export tests as specified in ADR-0010.

AI can edit an existing room's prompt with undo; no provider is invoked. Map shows
its intended background target but has no generation control yet. No persistence
or schema/API change is introduced by this increment.
