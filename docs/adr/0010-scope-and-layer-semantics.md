# ADR-0010: Scope targets and visual layer ordering

Status: Accepted design, 2026-09-24. Generation and layer controls are planned,
not implemented by this clarification. Existing JSON structures are unchanged.

Map selects the base environmental background for generation/regeneration, not
merely AI context and not the flattened scene. Room targets bounded architecture
and its render layer. Object represents independently manipulable visual content
with optional gameplay properties. Region retains its original semantic/gameplay
role (hazards, difficult terrain, annotations); `visualStyle` describes an editor
overlay, not generated imagery. A region and a visual object may coexist without
implicit creation or synchronization. Light and Sound hold their respective scene
behaviors; visible fixtures are separate objects.

The manifest's stack is a default. Room/object/effect artwork can be reordered
across entity types. The base background stays below artwork and editor guides
stay above it. Reordering changes appearance only, never collision, geometry or
gameplay behavior. Opaque imagery naturally occludes lower layers.

Use the existing raster `zIndex` representation when implementing layer controls.
Before that implementation, specify deterministic handling of equal order values
and the binding between object assets and managed visual layers. The current object
asset reference alone does not implement this binding; avoid a second competing
source of ordering truth. No schema migration or new Region raster reference is
needed for the present clarification.

Planned Milestone 2 acceptance checks (extend to semantic objects in Milestone 6):

- Regenerating the base replaces only its asset revision, preserving independent
  artwork and all geometry/metadata, with one undoable acceptance transaction.
- Regenerating any artwork preserves its order, visibility and opacity.
- A synthetic overlapping layer fixture demonstrates different visible results
  when reordered; undo/redo restores the exact order and asset references.
- Save/open and flattened export reproduce the same composition, including
  transparency; region editor shading is excluded from ordinary image export.
- Reordering leaves collision and gameplay data unchanged. Test an object both
  below and above a room once semantic object layers are implemented.

Current changes only align scope labels and documentation. Existing regression
tests verify Map selection uses Pan, opens no panel and preserves room tool memory.
