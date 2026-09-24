# ADR-0014: Constrained doors and atomic geometry snapshots

Status: Implemented; Milestone 1 persistence remains unfinished.

## Contract

POST /api/geometry/doors accepts contractVersion 0.1.0, map dimensions,
beforeRooms, proposed rooms, and doors attached to the beforeRooms topology.
Return recomputed walls and reconciled doors, or 422 with an actionable reason.
Both room sets use ADR-0013 limits; at most 1024 doors are accepted. Door UUID
strings are accepted at the HTTP boundary, while other fields stay strict.
Generated GeometryContracts includes the new request/result; native project
schema remains unchanged. This stateless endpoint does not save anything.

A door position is the center fraction along canonical wall start → end; width
is in native map units. Require the whole opening to fit within one segment.
Door IDs must be unique, parents must exist and same-wall openings cannot overlap
(touching endpoints are allowed). Tolerance is 1e-7 map units. Validate both the
input attachments and reconciled output. Existing open/closed/locked, secret,
label and doorType fields are retained; the editor creates doorType=door only.

## Reconciliation and deletion

Recompute topology from both room sets; never trust client-supplied walls.
Track source-room provenance. For each surviving source, detect a rigid
translation by equal corresponding-vertex displacements. All surviving sources
of a shared door must agree on the translation; otherwise reject the edit.
Other reshaping uses the original opening location and orientation, so changes
to unrelated edges can succeed without inventing a remapping.

Find exactly one new wall with the same supporting direction, all surviving
source rooms, and room for the translated opening. Update wallId/position;
retain door ID and width. Increment door revision when attachment changes.
Splits away from an opening are supported; splits through an opening, rotation
of its supporting edge, ambiguous matches and orphaning are rejected.
Deleting a room retains a shared door if another source still supplies its wall.
Deleting the last source is cancelled with instructions to move/delete the door
first. No implicit door cascade, detachment or duplication occurs.

## Transactions and interface

The editor keeps immutable scene snapshots (rooms, walls, doors). With doors
present, every proposed room geometry change first reconciles attachments and
commits all entities together; failures preserve scene/history. Snapshot identity
rejects stale commits. Undo/redo restore exact snapshots without asynchronous
remapping. Room reorder is a synchronous artwork-order-only transaction.
Door creation/update/deletion also validates before one snapshot commit.
Pending mutations disable other geometry/history mutations; requests time out.

Without doors, the existing asynchronous derived-wall display remains sufficient.
Once doors exist, render their validated snapshot walls instead of a display cache.
This does not yet provide native project persistence or wall overrides.

Room → Place/edit door projects a canvas click onto a wall within 8 screen pixels;
an existing opening has selection precedence within 10 pixels. Snap rounds center
distance to 50-unit steps measured from canonical wall start, including diagonals;
with Snap off projection is continuous. Do not silently shrink or shift an opening
to make it fit. Information exposes Apply/Reset/Delete, label, width, exact position,
state and secret. Selecting preserves the active tab. Space temporarily pans.
Open/locked patterns differ; these are editor states, not a gameplay simulator.
Inspect walls remains last, with visual selection only and no wall count/dropdown.

## Verification and remaining work

Tests cover translated/diagonal/shared attachments, compatible/incompatible splits,
fit, overlap, deletion policy, malformed API input, 50 atomic undo/redo transactions,
UI placement/editing, failure recovery and tab preservation. Remaining Milestone 1
work: native New/Open/Save, atomic disk snapshots, and full-project relationship
validation. Standalone walls, arbitrary edge remapping and wall override editing
are not claimed by this increment.
