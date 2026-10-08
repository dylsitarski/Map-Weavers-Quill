# Development history and verification evidence

This is the record of how each milestone was verified and what changed along the way.
For current behavior see [README.md](../README.md). For the plan and canonical status
see [PROJECT_MANIFEST.md](../PROJECT_MANIFEST.md) §16 and §22. Design rationale lives
in the [ADRs](adr/README.md). Add new entries at the end of the relevant milestone.

## Milestone 0 — Repository and contracts (complete)

- React/TypeScript and FastAPI shells, Python models with generated JSON Schema and
  TypeScript declarations, cross-runtime fixture validation, continuous coordinate
  transforms, provider contracts and a deterministic offline mock provider.
- Provider contracts include version tags, a capability vocabulary, reference images,
  negative prompts, neutral parameters, namespaced extensions and normalized errors.
  The mock rejects unsupported options and cancellation explicitly. ADR-0001 to
  ADR-0008 are recorded.
- The schema later grew, before any release, to cover every planned entity category
  (objects, sounds, regions, generation provenance, namespaced metadata). It was
  expanded in place and the synthetic fixtures were updated with it. The
  all-entities fixture is checked in both Python and TypeScript.
- **Evidence:** clean-checkout Ubuntu CI
  [run 35686075197](https://github.com/dylsitarski/Map-Weavers-Quill/actions/runs/35686075197)
  passed on commit `2af87f4`: 20 Python tests, 10 TypeScript tests, 3 Chromium browser
  tests, schema/type drift checks, linting, typing, production build and Python/npm
  dependency audits. The browser suite also verified dev-service startup and shutdown;
  repeated termination signals are covered by a launcher regression test. Chromium was
  unavailable in the agent environment at the time, so browser evidence came from CI.

## Milestone 1 — Deterministic editor foundation (complete for the editor profile)

Built in increments (ADR-0009 to ADR-0015):

1. Konva viewport with pan, pointer-anchored zoom, resize, grid and snapping;
   rectangle rooms with server-side polygon validation and undo/redo (ADR-0009).
2. Polygon rooms; select, move, vertex editing, inspector and deletion (ADR-0011).
3. Anchor snapping and the tabbed right panel (ADR-0012). An early Layers tab with
   Raise/Lower room-shape ordering was later replaced by artwork-layer controls in
   Milestone 2.
4. Derived walls with stable IDs and wall inspection (ADR-0013).
5. Constrained doors with atomic room/wall/door undo snapshots (ADR-0014).
6. Local SQLite project snapshots and File New/Save/Open (ADR-0015).

**Evidence:** Ubuntu CI
[run 36094044452](https://github.com/dylsitarski/Map-Weavers-Quill/actions/runs/36094044452)
passed on commit `200338f`: 40 Python tests, 27 TypeScript tests, browser tests,
generated-file drift checks, typing, linting, production build and dependency audits.
Browser acceptance created two connected rooms and a door, saved, reloaded and reopened
them, and compared native geometry and canvas pixels. Tests also covered 50 scene
commands through undo/redo, concurrent saves, rollback and forced process exit before
commit.

## Milestone 2 — Layered raster pipeline and mock generation (complete for mock)

Increments: persistent mock background with content-addressed PNG assets (ADR-0016);
room crops, binary polygon masks and protected compositing (ADR-0017); artwork
ordering, visibility and opacity controls; flattened PNG/WebP export (ADR-0018);
durable generation jobs with cancellation and restart recovery (ADR-0019); browser
preview recovery (ADR-0020); room style overrides and deterministic prompt assembly
(ADR-0021); persistent map-level prompt and style defaults (ADR-0022). ADR-0023
recorded the planned exterior-background/interior-layer design.

**Evidence:** [MILESTONE_2_ACCEPTANCE.md](MILESTONE_2_ACCEPTANCE.md) maps each exit
criterion to its tests.

## Milestone 3 — First real image provider (in progress)

1. **Provider configuration (ADR-0024).** Server-only provider selection, bounded
   secret loading from environment or file, startup validation and a shared
   provider factory.
2. **Local SDXL first (ADR-0025).** The owner chose local ComfyUI/SDXL before any hosted
   provider, to avoid per-image costs during development. A standalone adapter, smoke
   command and offline protocol tests were added. Owner hardware: Linux, RTX 3060 Ti
   (8 GB VRAM), about 32 GB RAM.
3. **Resolution-aware rasters (ADR-0026).** Storage, masks, crops, composition and
   export support both the legacy 480 × 320 mock size and 960 × 640 SDXL maps.
4. **Queued SDXL in the editor (ADR-0027).** Readiness and capability display, aligned
   room crops, safe failures and persisted workflow provenance.
5. **First owner trial** found abstract room artwork and backgrounds with an oblique
   perspective; prompt changes alone did not fix it. **ADR-0028** added a
   1024 × 1024 aspect-preserving room working transform, clean generation context
   and SDXL-specific positive/negative prompts.
6. **Second owner trial** found coherent top-down imagery, but furniture at the wrong
   scale, invented interior partitions, and backgrounds that ignore the architecture.
   **ADR-0029** added physical grid/room scale to prompts and optional SDXL ControlNet
   wall/door guidance.
7. A deterministic wall/door overlay drawn by Quill (proposed ADR-0030) was prototyped
   on branch `claude/jolly-feynman-ce34pl`
   ([PR #1](https://github.com/dylsitarski/Map-Weavers-Quill/pull/1)). It is parked:
   the owner prefers to keep AI-generated walls, which can match the room's style and
   perspective, while image generation is improved.

8. **Inpainting quality (ADR-0031).** Room inpainting moved from `VAEEncodeForInpaint` to
   `InpaintModelConditioning`, and an optional dedicated SD-XL Inpainting 0.1 UNet can
   replace base SDXL for rooms.
9. **Third owner trial (2026-10-05).** Without guidance, the inpainting UNet connected
   well to neighbouring rooms, but continued the outdoor background into the room and
   invented its own layout instead of walls at the boundary. With the Control-LoRA wall
   guidance, sampling failed: Control-LoRA cannot adapt to the inpainting UNet's
   9-channel input. Readiness now refuses that pairing and the docs recommend a full
   SDXL canny ControlNet (ADR-0031).
10. **Fourth owner trial (2026-10-05).** With the inpainting UNet and the small full canny
    ControlNet, the left walls followed the partial-octagon room shape and the room joined
    its neighbours, but the right half of the enclosed room became an outdoor area (grass,
    fire pit) continuing the surrounding scene. Edge guidance works; the model does not
    treat a large enclosed area as indoors. Further SDXL guidance tuning was judged
    unlikely to fix this, and work moved to a FLUX.2 klein provider.
11. **FLUX.2 klein provider (ADR-0032).** A second local model family through ComfyUI core
    nodes. The ComfyUI transport was factored into a shared base class with SDXL unchanged.
    Rooms are edited from two reference images (context with the room blanked, and a
    floor plan); backgrounds are text-to-image.
12. **Fifth owner trial (2026-10-05, FLUX.2 klein distilled).** The large partial-octagon
    room was fully indoors, with walls following the plan nearly exactly and doors in the
    right places, a clear improvement on SDXL. The gray placeholder floor and white plan
    wall lines remained under the furniture, and doors were drawn closed regardless of
    state; about 20 seconds per room (SDXL with guidance: about 17). Response: a default
    one-image `sketch` reference with door states, and placeholder wording for the
    `plan` prompt (ADR-0032).

13. **Debugging bundle and sixth owner trial (2026-10-06, klein `sketch`).** A read-only
    `make debug-bundle` export let the owner share the test cottage map (37 generation
    records: 17 mock, 7 SDXL, 13 klein). Rooms were indoors, but: the working scale
    depended on room size (about 64 px/ft for 10-ft rooms, 26 px/ft for the 36-ft main
    room), so small rooms got miniature furniture and thick sketch walls; non-square
    crops were padded with smeared edge pixels; floors had to be described or stayed
    off-white; doors were not always honoured; rooms looked alike despite distinct
    descriptions; the map Environment ("Mystical fantasy forest") was inherited into
    every interior; 28 of 37 generations used seed 0; the background cottage was drawn in
    perspective without any scale in its prompt. The owner wants the dark wall tops kept
    if small and consistent.
14. **Fixed-scale window and room-first prompts (ADR-0033).** Rooms are edited in a fixed
    40-ft window of real map context (same working scale for every room); the klein sketch
    is drawn at that scale with floor-plan door symbols; klein prompts start with the room
    description, a default floor line and a door list from geometry; Environment is no
    longer used; backgrounds state the map's physical scale; seeds are random unless
    locked; accepting artwork prunes history records of replaced artwork. Verified with
    111 Python, 32 TypeScript and 41 browser tests; not yet trialled on a GPU.

15. **Seventh owner trial (2026-10-08, ADR-0033).** Furniture scale matched better
    across rooms, wall tops were thin and even, about 12 seconds per room. The open-door
    symbol was rendered badly and partly remained; door-like objects appeared on the
    floor, likely from the written door list; floors drifted toward the off-white
    placeholder even when described; furniture hugged the walls; room descriptions
    (cluttered, whimsical) showed weakly. Doors are now drawn closed (secret doors as
    wall) and the door list was removed. Verified with 110 Python, 32 TypeScript and 41
    browser tests.

Outstanding before Milestone 3 can close: good room floors, filled room centres and
visible room character with klein,
recorded runtime and peak VRAM, explicit building/open-air intent, and geometry-aware backgrounds
(ADR-0023). Flux Fill was considered and deferred; hosted generation moved to
Milestone 5.
