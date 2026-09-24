# ADR-0011: Validated room editing

Status: Implemented, Milestone 1 in progress. Existing JSON/API contracts unchanged.

Select/edit is an exclusive Room tool. Native polygon hit tests include boundaries;
the last drawn room wins overlap hits. The room list provides access to covered
rooms. Selected rooms have dashed outlines and corner handles plus a named inspector.
Selection is transient and never enters document history.

Dragging the interior proposes a translation. Snap quantizes displacement, not each
vertex, preserving off-grid geometry. Handles snap the edited point to grid positions.
Both use the existing native/view conversions and fixed screen-pixel hit tolerances.
Leaving the canvas, blur, Escape or tool/scope changes cancel unsubmitted drags.
Space begins a pan gesture instead of editing. Zoom is paused during an edit drag.

The inspector supports label, future-generation prompt, exact vertex coordinates,
midpoint insertion and vertex removal (minimum three, maximum 2048). Inputs are a
local draft until Apply. All proposed geometry passes the existing stateless backend
validator. Errors retain original room/history; inspector drafts remain available
for correction. Inspector drafts reset when selection or committed room data changes.

Accepted edits replace a room in one immutable transaction, retaining its ID and
other properties while incrementing revision. The reducer requires the captured
room snapshot still to be current; stale replacements and no-ops create no history.
Pending validation disables history mutations, deletion and new edits. Deletion is
one undoable command. Undo/redo restores complete snapshots, including revisions;
future generation must also use the planned project-level revision/stale checks.

No wall/door dependents exist in this editor yet. Their update/delete policies must
be implemented before those entities are editable; this room-only delete path is
not a general project dependency resolver. Persistence and cross-entity validation
remain future Milestone 1 work.

Verification covers concave hit tests, shape-preserving snapped movement, independent
vertex edits, 50 edit transactions plus deletion through undo/redo, stale rejection,
and browser workflows for selection, movement, handles, inspector edits, invalid
geometry and Escape cancellation.
