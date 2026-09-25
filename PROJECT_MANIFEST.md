# Map-Weaver's Quill: Project Manifest and Implementation Plan

**Document status:** Canonical implementation brief  
**Version:** 0.3.0
**Last updated:** 2026-09-22
**Audience:** Human maintainers and AI software-engineering agents  
**Project name:** Map-Weaver's Quill  

## 1. Purpose of this document

This document is the source of truth for building a local-first, AI-assisted, top-down battlemap editor with Foundry Virtual Tabletop export. It records the product intent, architectural constraints, data contracts, staged implementation plan, acceptance criteria, and agent handoff rules.

Statements using **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative requirements:

- **MUST / MUST NOT:** required for the applicable release.
- **SHOULD:** expected unless a documented technical reason prevents it.
- **MAY:** optional.

When this document conflicts with an implementation detail in the repository, an accepted Architecture Decision Record (ADR) takes precedence. Otherwise, this manifest takes precedence.

## 2. Product definition

Map-Weaver's Quill is a two-dimensional, top-down map editor in which the user draws deterministic geometry, attaches semantic meaning, invokes interchangeable AI providers to render selected areas or objects, and exports the result to Foundry VTT.

The central design rule is:

> The structured scene graph is authoritative. AI-generated pixels are editable render assets, not the source of architectural or gameplay truth.

The primary interaction loop is:

1. **Draw** rooms, walls, doors, and regions.
2. **Describe** a room, object, terrain feature, or edit in natural language.
3. **Generate** imagery only for the selected scope.
4. **Manipulate** the resulting geometry and raster layers without destroying unrelated work.
5. **Export** a background image and deterministic gameplay metadata to Foundry VTT.

### 2.1 Primary user

A tabletop role-playing game GM who:

- wants visually rich maps without manually illustrating them;
- wants to improvise or revise rooms quickly;
- needs walls, doors, lights, and hazard regions to work reliably in Foundry;
- may prefer hosted AI, local open-weight models, or a mixture of both;
- is willing to perform modest initial setup for a fast recurring workflow.

### 2.2 Core value proposition

The application combines the direct manipulation of a map editor with natural-language authoring and localized image generation. It avoids the failure mode of generating an attractive flat image and later attempting to reconstruct gameplay geometry from pixels.

### 2.3 MVP success scenario

A user can create two connected rooms, describe and generate each interior independently while preserving room boundaries, add one functioning door and two lights, save and reopen the project, and import the flattened visual map plus working walls, door, and lights into a supported Foundry version.

## 3. Scope

### 3.1 MVP scope

The first usable release MUST provide:

- a browser-based 2D editor with pan, zoom, selection, and an optional square grid;
- rectangular and polygonal room creation;
- deterministic room boundaries and derived wall segments;
- door placement on wall segments;
- room names, prompts, and semantic metadata;
- localized room rendering through at least one image-provider adapter;
- provider discovery and capability reporting;
- a layered raster/vector canvas;
- undo and redo for document mutations;
- project save/load using a versioned native format;
- flattened WebP or PNG export;
- a Foundry importer path that creates a Scene, walls, doors, and lights;
- automated tests for geometry, serialization, provider contracts, and export conversion.

### 3.2 First post-MVP scope

After the success scenario is stable, the product SHOULD add:

- arbitrary AI brush masks;
- movable AI-generated object layers with transparent backgrounds;
- semantic light, sound, hazard, and difficult-terrain tools;
- an independent language-model provider interface for converting commands into validated operations;
- more than one image-provider adapter, including a local workflow backend;
- autosave and crash recovery;
- project migration between schema versions;
- packaging for non-developer installation.

### 3.3 Explicit non-goals for MVP

The MVP MUST NOT attempt to provide:

- multiplayer or simultaneous editing;
- cloud accounts, billing, or a hosted project service;
- procedural 3D geometry;
- full parity with Photoshop, Dungeon Alchemist, or a general-purpose VTT;
- arbitrary Foundry system automation or game-rule scripting;
- automatic perfect recovery of walls and doors from a flat image;
- mobile-first editing;
- a plugin marketplace;
- model training or fine-tuning;
- Kubernetes, distributed queues, or other production-scale infrastructure.

### 3.4 Distribution intent

The project is intended for a **public, freely distributed, noncommercial release**. Engineering and packaging decisions MUST therefore assume that people other than the original developer will install and run the application.

- Installation, upgrades, migrations, privacy behavior, bundled third-party assets, and license notices MUST be suitable for public distribution.
- Model weights and workflows MUST NOT be redistributed unless their licenses explicitly permit it. User-installed model paths are preferred when redistribution rights are unclear.
- The project license MUST be selected before the first public release. If commercial use is prohibited, documentation MUST describe the project as source-available or noncommercial rather than claiming an Open Source Initiative-approved open-source license.
- Public distribution does not imply a hosted service, paid support, warranty, or commercial product commitment.

## 4. Product principles

1. **Deterministic architecture, generative appearance.** Room boundaries, walls, doors, light origins, and gameplay regions are stored as geometry. AI may decorate them but MUST NOT silently move them.
2. **Localized generation.** A normal edit regenerates only the selected mask or asset. Map-scope regeneration explicitly targets the base background, preserving independent visual layers and scene geometry.
3. **Provider independence.** Product logic depends on declared capabilities, not model or vendor names.
4. **Local-first ownership.** Projects and generated assets are stored locally by default. Remote calls occur only through a configured provider.
5. **Non-destructive editing.** Generated rooms, objects, effects, metadata, and overlays remain separable where practical.
6. **Foundry is an export target.** The native project format MUST NOT be Foundry Scene JSON.
7. **Validated AI actions.** Language-model output is an untrusted proposal. It MUST pass schema and domain validation before changing a project.
8. **Visible uncertainty.** The UI SHOULD expose unsupported capabilities and failed generations rather than silently degrading.
9. **Reproducibility where available.** Provider, model identifier, workflow revision, prompt, seed, parameters, input asset hashes, and output asset hash SHOULD be recorded for each generation.
10. **Graceful evolution.** Native documents, provider interfaces, and export adapters MUST be versioned.

## 5. System architecture

### 5.1 Recommended stack

| Area | Initial choice | Rationale |
|---|---|---|
| Front end | React + TypeScript | Mature component ecosystem and strong typing |
| Canvas | Konva through react-konva | Scene graph, transforms, layers, pointer interaction |
| Client state | Zustand with command-based history | Small API and explicit undo/redo boundaries |
| Backend | Python + FastAPI | Strong image, geometry, validation, and AI tooling |
| Validation | Pydantic on server; generated TypeScript types or Zod on client | Shared, enforceable contracts |
| Geometry | Shapely | Polygon validation, clipping, buffering, and intersections |
| Raster processing | Pillow; OpenCV only where needed | Masks, crops, compositing, image conversion |
| Metadata database | SQLite | Local, transactional, easy backup |
| Asset storage | Content-addressed local files | Deduplication and stable references |
| Image AI | Provider adapters | Hosted and local backends remain interchangeable |
| Language AI | Separate provider adapters | Semantic commands are independent from rendering |
| Foundry integration | Small JavaScript/TypeScript module | Stable import boundary against Foundry API changes |
| Development packaging | Docker Compose plus native dev commands | Reproducible services without forcing final packaging |
| Desktop packaging | Deferred evaluation: Tauri preferred over Electron | Smaller distribution if native installer becomes necessary |

No dependency choice is irrevocable. Replacing a row marked as an initial choice requires an ADR if it affects public contracts or project persistence.

### 5.2 Logical components

```text
Web Editor
  - canvas and tools
  - inspectors and prompts
  - history and selection
       |
       | versioned HTTP/WebSocket API
       v
Application Server
  - project service
  - geometry service
  - generation orchestrator
  - provider registry
  - asset service
  - export service
       |                 |
       v                 v
Local persistence     External/local AI providers
  - SQLite              - hosted image API
  - asset files          - ComfyUI-compatible API
  - project snapshots    - local language server
       |
       v
Foundry export bundle -> Foundry importer module -> Foundry Scene documents
```

### 5.3 Deployment modes

The architecture MUST support these configurations without changing project data:

| Mode | Editor/backend | Image provider | Language provider |
|---|---|---|---|
| Simple hosted | Local | Hosted API | Hosted API or disabled |
| Local visual | Local | Local workflow server | Hosted API or disabled |
| Fully local | Local | Local workflow server | Local model server or disabled |
| Developer | Local hot reload | Mock or selected provider | Mock or selected provider |

Language AI is optional for the MVP. Direct room prompts and image generation MUST work without it.

## 6. Repository layout

Use a monorepo with explicit package boundaries:

```text
map-weavers-quill/
  README.md
  PROJECT_MANIFEST.md
  AGENTS.md
  LICENSE
  .env.example
  docker-compose.yml
  docs/
    adr/
    api/
    foundry/
  apps/
    web/                    # React/TypeScript editor
    server/                 # FastAPI application
  packages/
    schema/                 # JSON Schema and generated types
    provider-contracts/     # capability and request/response contracts
    geometry/               # shared geometry algorithms/tests as appropriate
    foundry-export/         # native-to-Foundry conversion logic
  integrations/
    foundry-module/         # companion importer module
    comfyui-workflows/      # versioned reference workflows
  fixtures/
    projects/
    provider-responses/
    export-golden/
  scripts/
  tests/
```

The exact workspace tooling MAY vary. Front-end and back-end lockfiles MUST be committed. Generated build output and model weights MUST NOT be committed.

## 7. Native project model

### 7.1 Coordinate conventions

- Project geometry MUST use logical map units independent of display zoom. The initial implementation MAY define one logical map unit as one output pixel at scale 1, but persisted geometry MUST NOT depend on viewport zoom or device pixel ratio.
- The authoritative project/world-space origin MUST be the bottom-left corner of the map.
- Positive x MUST point right; positive y MUST point up.
- Unless a field explicitly declares otherwise, angles MUST be stored in degrees, measured counter-clockwise from the positive x-axis, and normalized to the half-open interval `[0, 360)`.
- Distances used by gameplay metadata MUST include units.
- Grid visibility and snapping are editor settings; geometry MUST remain valid when the grid is hidden.
- Browser canvas, raster image, and Foundry Scene coordinates are boundary representations, not native project coordinates. They MUST NOT leak into the persisted scene graph.
- Conversion to browser/raster space and conversion to Foundry space MUST occur through named, centralized coordinate-transform modules with tests.

The required coordinate spaces are:

| Space | Origin and axes | Purpose |
|---|---|---|
| Project/world | Bottom-left; +x right; +y up | Authoritative persisted geometry and general angle convention |
| Raster/canvas | Top-left; +x right; +y down | Browser rendering, masks, crops, generated images, and flattened exports |
| Foundry | Version-specific Scene/canvas convention, expected to be pixel-oriented | Import adapter output only |

For a map of logical height `H`, the continuous point conversion between project/world space and a top-left, +y-down target is:

```text
x_target = x_world
y_target = H - y_world
```

For an axis-aligned rectangle stored by its bottom-left corner `(x, y)` and size `(width, height)`, its top-left target placement is:

```text
x_target = x
y_target = H - (y + height)
```

Raster pixel-index conversion has discrete edge semantics and MUST be implemented in the rasterization module rather than by scattering `H - y` or `H - y - 1` expressions through application code. The conversion tests MUST cover all four map corners, boundary edges, rectangle bounds, polygon winding, masks, wall endpoints, anchors, and round trips.

Angles in the native project remain counter-clockwise. Each target adapter MUST explicitly convert angular fields according to that target API's documented convention; it MUST NOT pass rotation values through merely because a simple y-axis inversion appears correct. Reflections reverse polygon winding and angular orientation, so those effects MUST be tested.

### 7.2 Project envelope

The canonical project document SHOULD resemble the following. The actual JSON Schema is authoritative once implemented.

```json
{
  "schemaVersion": "0.1.0",
  "projectId": "uuid",
  "revision": 17,
  "name": "Ruined Abbey",
  "createdAt": "2026-09-21T12:00:00Z",
  "updatedAt": "2026-09-21T12:30:00Z",
  "map": {
    "width": 3000,
    "height": 2000,
    "grid": {
      "type": "square",
      "sizePx": 100,
      "distance": 5,
      "units": "ft",
      "visible": true,
      "snap": true
    },
    "style": {
      "camera": "strict orthographic top-down",
      "environment": "ancient gothic stone monastery",
      "renderStyle": "detailed painterly fantasy battlemap",
      "palette": "cool moonlight with warm practical lights",
      "wallThicknessPx": 18,
      "bakedLighting": "neutral"
    }
  },
  "rooms": [],
  "walls": [],
  "doors": [],
  "objects": [],
  "lights": [],
  "regions": [],
  "sounds": [],
  "layers": [],
  "generations": [],
  "settings": {}
}
```

### 7.3 Entity requirements

Every persistent entity MUST have:

- a stable UUID;
- a `kind` discriminator;
- geometry or an asset transform as applicable;
- a human-readable label where useful;
- `createdAt` and `updatedAt` timestamps, or equivalent revision provenance;
- extensible metadata namespaced to avoid vendor collisions.

Minimum entity definitions:

| Entity | Required information |
|---|---|
| Room | polygon, name, prompt, style overrides, render-layer reference |
| Wall | start/end points, movement restriction, sight restriction, source provenance |
| Door | parent wall reference, position or segment, width, door type, state, secret flag |
| Object | anchor, footprint, rotation, description, optional raster asset, gameplay properties |
| Light | origin, bright/dim radii, color, intensity, optional animation identifier |
| Region | polygon(s), semantic type, editor overlay style, optional Foundry behavior mapping; no generated imagery |
| Sound | origin or region, radius, asset reference, volume |
| Raster layer | asset hash, bounds, z-index, opacity, blend mode, visibility |
| Generation record | provider, capability, inputs, prompt, parameters, status, hashes, timestamps |

### 7.4 Geometry rules

- Room polygons MUST be simple, non-self-intersecting polygons with at least three unique vertices.
- Invalid proposed geometry MUST be rejected with an actionable error.
- Walls derived from rooms MUST preserve stable identity when unchanged.
- A door MUST remain constrained to its parent wall until explicitly detached or the wall is deleted.
- Deleting a parent MUST require deterministic handling of dependents: cascade, detach, or cancel. The choice MUST be presented or encoded by the tool command.
- Polygon clipping, mask rasterization, and Foundry export MUST have golden fixtures covering concave polygons and map-edge intersections.

### 7.5 Persistence and migrations

- The native project format MUST be versioned with semantic versions.
- A project save MUST be atomic: write a new snapshot, validate it, then update the current pointer.
- The server MUST retain enough history for crash recovery.
- Migration code MUST be one-way and covered by fixtures. Older source data MUST remain backed up.
- Asset paths stored in documents MUST be logical references, not machine-specific absolute paths.

## 8. Provider architecture

### 8.1 Capability model

Code MUST ask for capabilities rather than branching on model names. Initial image capabilities:

- `text_to_image`
- `inpainting`
- `image_to_image`
- `reference_image`
- `control_image`
- `transparent_background`
- `seed`
- `negative_prompt`
- `maximum_dimensions`
- `asynchronous_jobs`

Initial language capabilities:

- `structured_output`
- `tool_calling`
- `vision_input`
- `local_execution`

### 8.2 Image-provider contract

Conceptual interface:

```python
class ImageProvider(Protocol):
    def descriptor(self) -> ProviderDescriptor: ...
    async def health(self) -> HealthStatus: ...
    async def generate(self, request: GenerateRequest) -> GenerationResult: ...
    async def inpaint(self, request: InpaintRequest) -> GenerationResult: ...
    async def cancel(self, job_id: str) -> None: ...
```

`InpaintRequest` MUST include:

- source image reference;
- binary or grayscale mask reference and documented mask convention;
- prompt;
- output dimensions;
- optional style/reference images;
- optional seed and provider-neutral parameters;
- generation context containing map style and adjacent-area instructions;
- request ID for idempotency and diagnostics.

Provider-specific options MUST be stored under a namespaced extension field and MUST NOT leak into core editor logic.

### 8.3 Language-provider contract

The language provider MUST return operations conforming to a closed, versioned schema. It MUST NOT directly mutate the project.

Example operation envelope:

```json
{
  "operationSchemaVersion": "0.1.0",
  "baseRevision": 17,
  "summary": "Add two torches and rubble terrain",
  "operations": [
    {"op": "add_object", "objectType": "torch", "anchor": {"relativeTo": "altar", "side": "left"}},
    {"op": "add_object", "objectType": "torch", "anchor": {"relativeTo": "altar", "side": "right"}},
    {"op": "add_region", "regionType": "difficult_terrain", "scope": {"roomId": "uuid", "portion": "west_half"}}
  ],
  "warnings": []
}
```

The application MUST:

1. validate syntax and schema;
2. resolve semantic references;
3. validate geometry and permissions;
4. show a preview or operation summary;
5. apply operations as one undoable transaction only after approval, unless the user has explicitly enabled a safe auto-apply category.

### 8.4 Required initial adapters

Development MUST begin with a deterministic mock image provider. It enables tests without network access, credentials, GPUs, or variable model behavior.

The first real adapter SHOULD target one hosted image-editing API. The second real adapter SHOULD target a local workflow API such as ComfyUI. Direct in-process Diffusers support MAY follow later because it complicates GPU packaging and dependency isolation.

### 8.5 Provider configuration and secrets

- Secrets MUST NOT be written into project files, logs, URLs, exports, or browser local storage.
- Server-side environment variables or OS-backed credential storage SHOULD be used initially.
- Provider configuration MUST distinguish harmless settings from secrets.
- The settings screen MUST show which data a remote provider receives.
- A provider health test MUST avoid sending private project imagery unless explicitly required and disclosed.

### 8.6 License metadata

The registry SHOULD record, when known:

- model/workflow identifier and revision;
- license name and URL;
- commercial-use status;
- redistribution constraints;
- user acknowledgement timestamp if required.

The program MUST NOT claim that a publicly downloadable model is necessarily free of use restrictions.

## 9. Rendering and editing pipeline

### 9.1 Room generation

For a room-generation request, the server MUST:

1. validate the selected room polygon;
2. compute a padded context bounding box clipped to map bounds;
3. render the current composite for that bounding box;
4. rasterize the editable polygon mask at the provider's required resolution;
5. assemble the room prompt plus persistent map-style constraints;
6. invoke a provider that supports inpainting or an explicitly documented fallback;
7. validate output dimensions and media type;
8. composite only masked pixels into a new raster layer or immutable asset revision;
9. store a generation record;
10. return a preview that the user may accept, reject, or regenerate.

The default prompt wrapper SHOULD require strict orthographic top-down view, stable scale, preserved boundaries, continuity with visible context, no grid, no labels, and no UI artifacts.

### 9.2 Context margins

The AI input SHOULD include pixels outside the editable mask so the model can preserve floor, wall, palette, and lighting continuity. Only the authorized mask is composited into the project. Context pixels returned by the model MUST NOT overwrite protected areas.

### 9.3 AI objects

Post-MVP AI objects SHOULD be separate transparent raster layers bound to semantic object entities. Moving, rotating, scaling, hiding, or deleting an object MUST NOT require regeneration of the underlying floor.

### 9.4 AI brush

The brush tool SHOULD create an explicit mask entity or temporary mask transaction. A brush generation MUST record the mask and input asset revisions so the action can be reproduced or audited.

### 9.5 Concurrency and stale results

Every generation request MUST capture the project revision and affected entity revisions. If relevant geometry changes while generation is running, the result MUST be marked stale and MUST NOT overwrite current content automatically. The user MAY apply it as a new layer after previewing.

### 9.6 Failures and cancellation

- Provider timeouts and errors MUST leave the project unchanged.
- Long-running jobs SHOULD support cancellation.
- Partial provider output MUST be quarantined until validated.
- Retrying MUST create a new generation attempt linked to the previous record.

## 10. Editor behavior

### 10.1 Initial tools

- Select/move
- Pan/zoom
- Rectangle room
- Polygon room
- Wall inspection
- Door placement
- Light placement
- Generate selected room
- Delete
- Undo/redo

### 10.2 Layer order

The visual stack SHOULD start with this default order (not permanent ordering by entity type):

1. base environmental raster;
2. room render layers;
3. object raster layers;
4. effect raster layers;
5. deterministic wall/door visual treatment;
6. gameplay regions and metadata overlays;
7. editor selection and control overlays;
8. optional grid.

Export profiles decide which layers are flattened and which remain metadata.

The base environmental raster MUST remain beneath the artwork. Room, object and
effect raster layers MUST be user-reorderable relative to one another, including
objects below rooms. Editor guides, region outlines and selection controls remain
separate overlays above artwork; they MUST NOT become generated image content.
Wall/door collision and visibility behavior are geometry, independent of visual order.

Layer reordering MUST be an undoable document operation, persist across save/open,
and be respected by preview and flattened export. Regeneration MUST preserve the
target layer's order, visibility and opacity while replacing its image revision.
Reordering MUST NOT alter geometry, collision, region membership or gameplay rules.
Opaque pixels hide lower layers; revealing them requires transparency or a mask.
The existing raster `zIndex` field represents raster order. Interactive room-shape
ordering is implemented in the Layers tab; managed raster/object compositing remains planned. Room-shape order now persists
through File Save/Open (ADR-0015). See ADR-0010 and ADR-0012 for boundaries and planned checks.

### 10.2.1 Scope semantics

- **Map:** selects the base background as the target for future generation or
  regeneration across map bounds. It does not target the flattened scene or all
  entities. Other layers may supply context but MUST NOT be replaced by this action.
- **Room:** bounded architectural geometry and an associated masked render layer;
  imagery may be regenerated without silently changing boundaries or separate assets.
- **Object:** independent visual asset and optional gameplay properties. Use objects
  for visual features such as rugs, vegetation and hazard imagery; place their
  layers as needed relative to rooms and other objects.
- **Region:** semantic/gameplay area such as a hazard, difficult terrain or annotation.
  Its visual style controls editor visualization, not AI-generated artwork. A visual
  object and a region may describe the same place, but neither automatically creates
  the other and their geometry is not automatically linked.
- **Light:** source parameters and exportable lighting behavior; a visible fixture
  is a separate object. Background regeneration preserves light entities.
- **Sound:** audio source/area, asset and playback properties; no raster layer required.

Scopes identify editing targets; layers determine visual composition. Selecting a
scope does not invoke AI. Future generation still follows preview, accept/reject,
revision checks and undo. The current Map button selects the future background
target only; there is no background-generation operation yet.

### 10.3 Undo and redo

- All document mutations MUST use a command or transaction abstraction.
- An accepted generation is one undoable command.
- Provider invocation itself is not undone; applying its result is.
- Selection, viewport movement, and panel state SHOULD NOT pollute document history.
- A compound natural-language command MUST apply atomically.

### 10.4 Accessibility and usability

The accepted editor layout and future control placement are recorded in
[`docs/INTERFACE.md`](docs/INTERFACE.md). The owner's scheme uses a full-window
canvas, global top bar, left scope rail with adjacent tools, collapsible persistent
information at upper-right, and temporary feedback at bottom-left. Panels MUST
overlay the canvas without moving it. Page scrolling is disabled; wheel input zooms
except over scrollable panels/textareas, where it scrolls without changing map zoom.
The right panel has Information (selection), Layers (ordering), and AI (prompts) tabs.

- Core tools MUST have keyboard-accessible actions.
- Color alone MUST NOT communicate selection, validation errors, or door state.
- Destructive actions MUST be reversible through undo or confirmation.
- Long operations MUST expose progress or an indeterminate busy state.
- The editor SHOULD remain responsive while generation occurs.

## 11. Foundry integration

### 11.1 Export boundary

The editor MUST export a portable bundle rather than treating Foundry JSON as native state:

```text
ruined-abbey.map-weavers-quill-export.zip
  manifest.json
  scene.webp
  scene-data.json
  assets/
```

The bundle manifest MUST declare:

- export schema version;
- project and revision identifiers;
- target Foundry compatibility range;
- map dimensions and grid settings;
- asset paths and hashes;
- coordinate convention;
- the project map height required for coordinate conversion;
- the target coordinate convention and transform revision used by the exporter;
- contained feature types.

### 11.2 Importer responsibilities

The Foundry companion module MUST:

- validate bundle version and checksums;
- copy or register assets through supported Foundry APIs;
- create a Scene with the correct background, dimensions, grid, distance, and units;
- create walls and encode doors through the target Foundry document API;
- create ambient lights;
- consume only coordinates already converted by the version-specific Foundry export adapter; it MUST NOT reinterpret native project coordinates independently;
- report unsupported region behaviors without discarding the rest of the import;
- avoid duplicate import when the same project revision is reprocessed, or clearly offer update/copy behavior.

### 11.3 Compatibility strategy

- Support one explicitly selected Foundry major version first.
- Isolate version-specific conversion in adapter modules.
- Keep golden export fixtures and an importer smoke-test checklist for each supported version.
- Do not promise compatibility with an untested Foundry version.
- Add regions, sounds, notes, and advanced behaviors only after walls, doors, and lights are dependable.

## 12. API outline

The precise OpenAPI document will be generated from FastAPI. Initial endpoints SHOULD include:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/projects` | Create project |
| `GET` | `/api/projects/{id}` | Read current project |
| `PATCH` | `/api/projects/{id}` | Apply validated command with base revision |
| `POST` | `/api/projects/{id}/validate` | Validate document and geometry |
| `POST` | `/api/projects/{id}/save` | Force snapshot |
| `GET` | `/api/providers` | List provider descriptors and capabilities |
| `POST` | `/api/providers/{id}/health` | Test provider configuration |
| `POST` | `/api/projects/{id}/generations` | Start generation job |
| `GET` | `/api/generations/{jobId}` | Read job status/result |
| `DELETE` | `/api/generations/{jobId}` | Cancel job |
| `POST` | `/api/projects/{id}/exports/foundry` | Build export bundle |
| `GET` | `/api/assets/{hash}` | Retrieve immutable asset |

Mutating calls MUST include `baseRevision`. Revision conflicts MUST return a typed conflict response rather than silently overwriting changes.

## 13. Security and privacy requirements

- Treat uploaded images, prompts, projects, provider outputs, and Foundry exports as private user data.
- Default server binding SHOULD be localhost.
- Remote access MUST require explicit configuration and authentication.
- File endpoints MUST prevent path traversal and restrict access to managed asset roots.
- Uploaded files MUST be size-limited and decoded safely; file extensions alone are not trusted.
- ZIP imports MUST prevent zip-slip and decompression bombs.
- AI output and model-supplied text MUST be treated as untrusted input.
- Logs MUST redact credentials and SHOULD avoid full prompts or images by default.
- Exported HTML, Markdown, or Foundry labels MUST be escaped or sanitized as appropriate.
- The Foundry module MUST use supported APIs and MUST NOT evaluate arbitrary code contained in an export bundle.
- Dependencies MUST be pinned and automatically scanned in continuous integration.
- Network calls MUST have timeouts and bounded retries.

## 14. Testing strategy

### 14.1 Test layers

| Layer | Required coverage |
|---|---|
| Unit | Geometry validation, mask convention, transforms, commands, migrations, capability selection |
| Contract | Every provider adapter against shared request/result tests |
| Property-based | Polygon and coordinate transformations, serialization round trips |
| Golden-file | Masks, flattened composites, project migrations, Foundry export data |
| Integration | Project CRUD, generation orchestration with mock provider, asset storage |
| Front-end | Tool state, selection, undo/redo, inspectors, generation acceptance |
| End-to-end | Create rooms through export bundle using mock generation |
| Manual compatibility | Import bundle into supported Foundry release and verify documents |

### 14.2 Deterministic fixtures

Tests MUST NOT require a paid or nondeterministic AI provider. The mock provider SHOULD produce predictable patterns that make masking and compositing errors obvious.

### 14.3 Critical invariants

The test suite MUST prove:

- pixels outside the authorized mask do not change;
- save/load preserves entity IDs and logical geometry;
- undo restores both document references and prior visible composition;
- stale generation results do not auto-apply;
- door placement remains attached under supported wall edits;
- coordinate conversion produces expected Foundry coordinates;
- project/world coordinates round-trip through raster/canvas conversion within the declared numerical tolerance;
- project bottom-left, top-left, bottom-right, and top-right map corners map to the correct target corners;
- counter-clockwise project rotations and polygon winding convert correctly for every supported target field;
- no provider secret appears in native project or export fixtures;
- native projects can be migrated from every released schema version.

## 15. Observability

The application SHOULD produce structured local logs with:

- request/job ID;
- project ID and revision, but not project content;
- provider adapter and non-secret model/workflow identifier;
- stage timings;
- input/output dimensions;
- normalized error code;
- opt-in diagnostic detail.

User-facing errors MUST state what failed, whether project state changed, and a useful recovery action.

## 16. Implementation plan

Milestones are dependency-ordered. Do not begin later visual features to bypass an incomplete persistence or geometry foundation.

### Milestone 0: Repository and contracts

**Goal:** A reproducible monorepo with executable contract tests.

Tasks:

1. Initialize front-end and back-end workspaces, formatting, linting, typing, and test runners.
2. Add CI for front-end tests/build, back-end tests/type checks, schema validation, and dependency scanning.
3. Define JSON Schema for the project envelope and core entities.
4. Generate or validate matching TypeScript and Python types.
5. Define provider descriptors, capabilities, requests, results, and typed errors.
6. Implement a deterministic mock image provider.
7. Add ADR template and record initial stack and coordinate decisions.

Exit criteria:

- Clean checkout runs through documented setup and tests.
- A fixture project round-trips JSON without data loss.
- Type/schema drift fails CI.
- The mock provider passes the shared contract suite.

### Milestone 1: Deterministic editor foundation

**Goal:** Create and edit map geometry without AI.

Tasks:

1. Build canvas viewport, pan, zoom, resize handling, and grid.
2. Implement rectangle and polygon room tools.
3. Implement selection, move, vertex editing, delete, and inspectors.
4. Validate polygons through the backend geometry service.
5. Derive wall segments with stable identifiers.
6. Implement door placement constrained to walls.
7. Add command-based undo/redo.
8. Add project create, save, open, and atomic snapshot storage.

Exit criteria:

- User can create two connected rooms and one door.
- Invalid polygons cannot enter persistent state.
- Save/reopen is visually and structurally identical.
- At least 50 sequential geometry commands can be undone/redone without corruption.

### Milestone 2: Layered raster pipeline and mock generation

**Goal:** Prove localized non-destructive generation independently of a real model.

Tasks:

1. Implement content-addressed assets and raster-layer entities, a base-background target, and undoable ordering of available artwork layers.
2. Implement context crop, polygon mask rasterization, and protected-area compositing.
3. Add generation jobs, states, cancellation, and stale-result handling.
4. Add room prompt and style inspector.
5. Use the mock provider to generate visible room patterns.
6. Add accept, reject, and regenerate flows.
7. Add flatten-to-WebP/PNG export.

Exit criteria:

- Generating Room A does not modify a single pixel outside Room A's mask.
- A generation can be rejected without changing the document.
- Accepted output is undoable and survives reload.
- Background regeneration preserves independent layers; reordering survives undo/redo, save/open and flattened export without changing gameplay geometry.
- A result created against stale geometry cannot auto-apply.

### Milestone 3: First real image provider

**Goal:** Produce useful room imagery through one real backend.

Tasks:

1. Implement provider configuration and secret handling.
2. Implement one hosted image adapter with inpainting or edit support.
3. Add provider health, capability display, dimension normalization, and error mapping.
4. Develop persistent map-style and prompt-wrapper behavior.
5. Record reproducibility metadata and cost/usage data when the provider supplies it.
6. Test continuity across adjacent room generations.

Exit criteria:

- A user can configure the provider without exposing the secret to the browser or project file.
- Two adjacent rooms can be generated independently with preserved geometry.
- Unsupported operations are disabled or explained before invocation.
- Failures do not mutate the project.

### Milestone 4: Foundry vertical slice

**Goal:** Complete the end-to-end MVP success scenario.

Tasks:

1. Select and document the first supported Foundry major version.
2. Define the export-bundle schema.
3. Implement native bottom-left/+y-up/counter-clockwise to Foundry coordinate and document conversion in one version-specific adapter.
4. Build the companion Foundry importer module.
5. Export background image, grid configuration, walls, door, and lights.
6. Add checksums, compatibility errors, and import summary.
7. Test a golden two-room fixture in Foundry.

Exit criteria:

- The MVP fixture imports as a correctly scaled scene.
- Walls block movement and sight as configured.
- The door opens/closes through Foundry.
- Two lights have the correct positions, colors, and radii.
- Reimport behavior is explicit and cannot accidentally duplicate content without warning.

### Milestone 5: Local/open-model backend

**Goal:** Demonstrate true model swappability.

Tasks:

1. Define a versioned reference workflow input/output contract.
2. Implement a ComfyUI-compatible adapter.
3. Supply at least one documented inpainting workflow using a legally redistributable or user-installed model path.
4. Add workflow/model/license metadata.
5. Run the same provider contract suite used by the hosted adapter.
6. Document GPU, memory, installation, and fallback expectations without bundling large weights.

Exit criteria:

- The same room-generation UI works with hosted and local providers.
- Switching providers requires no project conversion.
- Local operation sends no project data to an external AI endpoint.
- Provider differences are isolated to adapter/configuration code.

### Milestone 6: Semantic objects, lights, regions, and AI brush

**Goal:** Expand beyond whole-room rendering.

Tasks:

1. Add semantic object entities and movable transparent raster layers.
2. Add light, hazard, difficult-terrain, and sound tools.
3. Add arbitrary brush masks and regeneration history.
4. Extend Foundry export for supported regions and sounds.
5. Add object/effect layer controls and asset garbage collection.

Exit criteria:

- Moving an object does not alter the base room raster.
- A brush edit changes only its authorized mask.
- Supported semantic metadata exports correctly; unsupported metadata is reported.

### Milestone 7: Natural-language operations

**Goal:** Translate map-level instructions into safe, previewable commands.

Tasks:

1. Define a closed operation schema and language-provider contract.
2. Implement a deterministic mock language provider and validation suite.
3. Implement one real adapter with structured output.
4. Add reference resolution, previews, warnings, and atomic apply.
5. Add adversarial tests for hallucinated IDs, invalid geometry, prompt injection in project content, and excessive operations.

Exit criteria:

- A command such as “add two torches beside the altar” produces a reviewable plan.
- Unknown references cause clarification or a validation failure, never silent guessing.
- Applying the plan is one undoable transaction.
- Model output cannot execute code or bypass project validation.

### Milestone 8: Distribution and hardening

**Goal:** Make installation and recovery reasonable for a non-developer GM.

Tasks:

1. Add migration, backup, autosave, and crash-recovery UX.
2. Profile large maps and optimize rendering, thumbnails, and asset loading.
3. Decide between local service installer and desktop wrapper through an ADR.
4. Define and test the first supported Linux distribution(s), GPU-driver assumptions, and packaging format.
5. Produce the Linux package and installation path before beginning Windows packaging work.
6. Add and test Windows 11 packaging after the Linux release path is stable.
7. Produce signed/reproducible packages where feasible.
8. Create setup diagnostics and a privacy/network activity panel.
9. Run accessibility, security, and Foundry compatibility checks.

Exit criteria:

- A clean machine running the primary supported Linux configuration can install, create, save, reopen, generate, and export using written instructions.
- Windows 11 support, when released, passes the same workflow without weakening Linux support.
- Forced shutdown during save does not destroy the last valid project.
- Upgrade from every released project schema succeeds on fixtures.

## 17. Work decomposition and dependency rules

Safe parallel work areas include:

- schema definitions and fixture creation;
- canvas interaction prototypes against fixed schemas;
- mock provider and contract-test development;
- Foundry API research and isolated importer spikes;
- documentation and threat modeling.

Do not parallelize changes that independently redefine:

- coordinate conventions;
- entity identity or ownership;
- command/history semantics;
- provider request/result contracts;
- export-bundle schemas.

Those require one accepted design change first, followed by coordinated implementation.

## 18. AI-agent operating protocol

An AI agent working on this project MUST follow this sequence:

1. Read `PROJECT_MANIFEST.md`, repository `AGENTS.md`, relevant ADRs, and the files directly involved in the task.
2. State which milestone and acceptance criterion the work advances.
3. Inspect the current implementation and tests; do not assume the manifest describes already-written code.
4. Identify whether the change affects a versioned contract.
5. If it changes a contract or architectural decision, propose or update an ADR before broad implementation.
6. Make the smallest coherent change that delivers a testable vertical outcome.
7. Add or update tests with the implementation.
8. Run focused tests first, then the relevant broader suite.
9. Report changed files, validation performed, remaining risks, and any manifest/implementation discrepancy.

### 18.1 Agent constraints

Agents MUST NOT:

- replace deterministic geometry with AI-inferred geometry without an approved ADR;
- add a model-name conditional to core editor logic when a capability check can be used;
- commit credentials, generated model weights, or private map assets;
- make live paid-provider calls in automated tests;
- silently widen scope beyond the current milestone;
- delete or rewrite user work to resolve a migration or merge problem;
- accept model-generated operations without schema and domain validation;
- declare Foundry compatibility without a recorded test against that version.

### 18.2 Task handoff template

Every substantial agent handoff SHOULD include:

```text
Objective:
Milestone / acceptance criterion:
Implemented:
Files changed:
Contracts changed:
Tests run and results:
Manual verification:
Known limitations or risks:
Recommended next task:
```

## 19. Definition of done

A task is done only when:

- its behavior is implemented, not merely scaffolded;
- relevant tests pass;
- new public data is typed and validated at boundaries;
- persistence or API changes include migrations/versioning as needed;
- error and loading states are handled;
- secrets and private assets are not exposed;
- documentation reflects user-visible or architectural changes;
- no unrelated regressions are known;
- the acceptance criterion can be demonstrated.

A milestone is done only when all exit criteria are demonstrated and the manifest's “Current project state” section is updated.

## 20. Initial Architecture Decision Records

Create these ADRs during Milestone 0:

| ADR | Decision |
|---|---|
| ADR-0001 | Semantic scene graph is authoritative; raster is derived/editable output |
| ADR-0002 | React/Konva front end and FastAPI back end |
| ADR-0003 | Bottom-left, +y-up project space with counter-clockwise angles and explicit target transforms |
| ADR-0004 | Versioned native JSON document plus content-addressed assets |
| ADR-0005 | Capability-based independent image and language providers |
| ADR-0006 | Foundry bundle plus companion importer, not native Foundry persistence |
| ADR-0007 | Command transactions as the undo/redo and AI-operation boundary |

## 21. Open decisions requiring owner input

These questions should be resolved near the stated milestone, not guessed by an implementation agent:

| Decision | Needed by | Default if owner delegates |
|---|---|---|
| First supported Foundry major version | Milestone 4 | Select the latest stable version after compatibility research |
| First hosted image provider | Milestone 3 | Choose based on inpainting quality, API stability, privacy, and cost |
| Minimum supported Linux distribution(s) and packaging format(s) | Milestone 8 | Support Linux first; select an initial tested distribution and portable packaging route, then add Windows 11 |
| Desktop wrapper vs local web service | Milestone 8 | Local web service first; evaluate Tauri |
| Public noncommercial software license | Before the first public release | Choose a license that clearly permits free redistribution while expressing the intended noncommercial restriction; do not describe it as OSI open source unless the selected license qualifies |
| Whether generated raster assets are embedded or stored beside projects | Milestone 0 | Content-addressed shared asset store with portable export/archive |

## 22. Current project state

As of this manifest version:

- Product architecture and staged implementation plan are defined.
- Milestone 0 is complete: strict Python structural models, generated JSON Schema with drift checking, continuous coordinate transforms, two valid project fixtures, and five invalid fixtures are implemented.
- The unreleased structural schema now covers every planned entity category, namespaced metadata, style, and generation provenance. Polygon topology and cross-entity validation for the supported rooms/walls/doors editor profile are implemented before persistence; unsupported future entity profiles are rejected.
- React/TypeScript and FastAPI shells, generated TypeScript declarations, cross-runtime fixture validation, image-provider contracts, an offline mock, Python lint/format/type checks, and an Ubuntu CI workflow are implemented. Dependency auditing is configured but requires network access. See README.md and docs/adr for current scope and limitations.
- No AI provider, Foundry version, or public model is yet committed.
- The project name is **Map-Weaver's Quill**.
- Native geometry uses a bottom-left origin, +y upward, and counter-clockwise angles; target adapters own all coordinate conversion.
- Distribution is planned as a public, free, noncommercial release, with Linux prioritized before Windows 11.
- Node 24 is enforced, frontend lint/format checks are enabled, and Playwright shell tests are included in Ubuntu CI. Clean-checkout CI run 35686075197 passed on code commit 2af87f4, including 20 Python tests, 10 TypeScript tests, 3 browser tests, build, typing, linting, schema drift checks, and dependency audits. Repeated termination signals no longer interrupt service cleanup.
- Provider contracts include versioning, optional references and parameters, namespaced extensions, typed failures, and explicit unsupported cancellation. Python and TypeScript agree on namespace rejection. ADR-0001 through ADR-0007 are recorded. Language operations and asynchronous orchestration remain their scheduled later milestones.
- All Milestone 0 exit criteria are demonstrated by clean Ubuntu CI, cross-runtime project round trips, generated-file drift checks, and mock provider contract tests. Windows 11 and Foundry compatibility remain unverified.
- Milestone 1 is complete for the current editor scope. The React/Konva viewport implements pan/zoom/resize, grid/snapping, rectangle and polygon room proposals, single-room selection, movement, vertex editing, a name/prompt/geometry inspector and deletion. Geometry changes use stateless Shapely validation; accepted additions, edits and deletions support undo/redo. File New/Save/Open now persists native snapshots locally; refresh discards only unsaved session changes, and saved projects can be reopened. Read-only derived walls now split intersections, deduplicate shared boundaries, retain IDs for unchanged endpoints and expose source-room provenance. See ADR-0013 for the versioned API, limits and asynchronous inspection behavior. Constrained doors now support placement, inspection, editing/deletion and atomic room/wall/door undo snapshots. Attachments follow whole-room translations and compatible wall splits; orphaning or ambiguous edits are rejected (ADR-0014). Atomic SQLite persistence and cross-entity validation for the supported rooms/walls/doors profile are implemented (ADR-0015). Unsupported future entity collections and map profiles are explicitly rejected. All Milestone 1 exit criteria are demonstrated by [Ubuntu CI](https://github.com/dylsitarski/Map-Weavers-Quill/actions/runs/36094044452) on code commit `200338f`, including connected rooms plus a door, native and pixel-identical save/reopen, invalid-data rejection, and 50 scene commands through undo/redo. See ADR-0009 and ADR-0011.

- Milestone 2 is in progress. Its first increment adds SHA-256-addressed PNG assets in SQLite, one base-background raster layer, offline mock preview/accept/reject/regenerate, stale-preview rejection, undoable visibility/opacity and native save/reopen with generation provenance (ADR-0016). Cancellation discards the client proposal; persistent jobs/provider cancellation are not claimed. Room crops, binary polygon masks, enforced outside-mask preservation, independent room artwork and validated room/layer bindings are implemented (ADR-0017). Geometry edits clear affected art with undo. Artwork ordering, visibility and opacity controls are implemented with undo/redo and save/open. Persistent job orchestration and flattened export remain unfinished.

## 23. First implementation ticket

**Title:** Bootstrap monorepo and prove schema round trip

**Objective:** Establish the repository foundation without beginning UI feature work.

**Deliverables:**

1. React/TypeScript application shell.
2. FastAPI application shell with `/health`.
3. Root development commands and environment example.
4. Initial project JSON Schema covering map, room, wall, door, light, and raster layer.
5. Generated or checked corresponding Python and TypeScript types.
6. One valid two-room fixture and at least five invalid fixtures.
7. Round-trip and validation tests in both runtimes.
8. Deterministic mock provider contract stub.
9. CI configuration.
10. ADR-0001 through ADR-0004.

**Acceptance test:** From a clean checkout, one documented command starts the development services, one documented command runs all foundation tests, and the valid fixture serializes through both runtimes without semantic change while every invalid fixture is rejected for the intended reason.
