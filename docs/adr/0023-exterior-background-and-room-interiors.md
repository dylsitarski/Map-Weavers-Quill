# ADR-0023: Geometry-aware exterior background with interior room layers

Status: Accepted design; geometry-aware background generation is not implemented.
Independent artwork layers and visibility toggles already exist. This ADR adds no
runtime behavior or new entity/schema fields.

## User-facing workflow

The base map depicts the exterior world: terrain, paths, vegetation and the top-down
external appearance of buildings (for example, roofs). Room artwork depicts interiors
above that background, clipped to each room's geometry. The background must retain a
complete exterior beneath room artwork; do not cut transparent room holes into it.

Example: the user draws cottage rooms and describes a forested hill with a curved path
leading to the cottage. Background generation should use those placed footprints to
locate the cottage and route the approach appropriately. Generate the rooms' interiors
separately. Hiding a room's artwork reveals the corresponding portion of the building
exterior beneath it; showing it restores the interior. Hiding all interior layers for a
building reveals its exterior, subject to any other visible layers above the background.

"Disable a room" here means hide its artwork. It does not delete or disable the room's
geometry, wall/door metadata, prompts, future generation context or gameplay semantics.
Opacity blends interior with exterior; it is not a change in architectural state.
Visibility follows existing save/undo/export rules. The current flat-image export captures
the selected visible composition, not an interactive roof-switching Foundry scene.

## Required generation context

Map generation must receive a snapshot of the current layout, not only prose/style:

- Native map dimensions and bottom-left/+y-up/CCW conventions, with explicit conversion
  to the provider's image coordinates.
- Room IDs, polygons, labels and relevant applied room descriptions; include rooms even
  when their artwork is hidden. Visibility is a compositing choice, not layout existence.
- Derived building-envelope/footprint context where justified by room geometry. Adjacent
  rooms belonging to one building should form one coherent exterior, not a roof per room.
- Door/entrance locations when available and unambiguous, to help relate paths and access
  points to the architecture. Preserve deterministic wall/door data unchanged.
- Applied background prompt, map style and explicitly selected reference context.

Room geometry alone may not identify a building: a room may represent an open courtyard,
a cave area, disconnected floors or another space with no roof. Do not automatically put
roofs on every polygon, treat every touching room as one building, or repurpose Regions
as visual/building layers. Building grouping, exterior-vs-open-air intent and ambiguous
entrance selection require an explicit design before implementation. Start with an
unambiguous single-building case; expose clarification/controls rather than silently
inventing associations. Any grouping/schema extension needs its own ADR and tests.

## Rendering and protection

Generate only the base-background layer. Treat room footprints as layout guidance for
external structures, not as holes to exclude from the background. Preserve independent
room/object art, ordering, visibility, opacity, geometry and gameplay metadata. Do not
bake room interiors into the exterior background by blindly flattening visible layers
as its source image. Context composition must distinguish exterior-compatible references
from interior art. A text-only provider cannot guarantee spatial alignment: require an
appropriate layout-conditioning/edit capability or explain the limitation before use.

Record the layout snapshot/fingerprint, prompt/style, conditioning assets and relevant
provider settings in generation provenance. Geometry/entrance/grouping changes while a
background job is outstanding must invalidate acceptance/recovery. Use existing explicit
preview/accept/reject, undo and persistent-job controls; never auto-apply new background
pixels or silently move room geometry to fit an image.

## Implementation sequence and acceptance

1. Define the minimal explicit exterior/building intent and grouping needed to distinguish
   roofs from open-air/cave footprints; document any contract changes.
2. Extend background requests/jobs/provenance with versioned layout context and add
   deterministic mock inspection tests for orientation, IDs, hidden rooms and stale state.
3. Integrate a layout-capable provider and exterior-only context construction. Validate
   a single building, then multiple adjacent rooms and exterior path/entrance continuity.
4. Verify visibility toggles reveal the existing exterior without generation or mutations;
   base regeneration leaves interior assets and deterministic geometry unchanged.
5. Verify save/open, undo/redo, stale-result/recovery refusal and flattened export, including
   the all-interiors-hidden case. Assess actual roof/footprint alignment with real output;
   mock patterns alone do not demonstrate visual alignment.

Current limitation: background requests contain prompt/style/seed only. No room layout
or building grouping reaches the background provider. Current toggles reveal whatever
background pixels already exist, not a guaranteed coherent building exterior. This work
is planned under Milestone 3 and does not retroactively claim mock rendering understands
buildings or provides Foundry roof automation.
