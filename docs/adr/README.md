# Architecture decision records

Each ADR records one decision and why it was made. ADRs are historical: when a later
ADR changes a decision, the earlier record stays and gets a dated update line under
its status, rather than being rewritten. Start new ADRs from [template.md](template.md)
and add them to this table. Contract changes require an ADR (see AGENTS.md).

Status as of 2026-10-05.

| ADR | Decision | Current status | Related |
| --- | --- | --- | --- |
| [0001](0001-foundation-contracts.md) | Pydantic models are the single contract source; coordinate boundary | Accepted (M0) | 0003, 0008 |
| [0002](0002-application-shells.md) | React/TypeScript and FastAPI shells; contract tooling | Accepted (M0) | |
| [0003](0003-coordinate-boundary.md) | Bottom-left, +y-up, counter-clockwise world space; target adapters convert | Accepted | 0001 |
| [0004](0004-persistence-boundary.md) | Versioned native JSON plus content-addressed assets | Snapshots implemented (0015); archives planned | 0015 |
| [0005](0005-provider-contracts.md) | Capability-based provider contract; offline mock | Accepted (M0) | 0024 |
| [0006](0006-foundry-export-boundary.md) | Foundry export bundle plus importer module | Accepted; implementation in M4 | |
| [0007](0007-command-transactions.md) | Command transactions as the undo/redo boundary | Implemented (M1); language operations in M7 | |
| [0008](0008-foundation-completion.md) | Milestone 0 verification and contract completion | Accepted (M0) | |
| [0009](0009-editor-foundation.md) | First editor slice: viewport, rectangle rooms, undo | Implemented (M1) | 0015 |
| [0010](0010-scope-and-layer-semantics.md) | Scope targets and visual layer ordering | Implemented for background and rooms; objects planned | 0016–0018 |
| [0011](0011-room-editing.md) | Validated room editing | Implemented (M1); snapping superseded by 0012 | 0012 |
| [0012](0012-snapping-and-sidebar.md) | Anchor snapping and tabbed sidebar | Implemented (M1) | 0011 |
| [0013](0013-derived-walls.md) | Deterministic derived walls and inspection | Implemented (M1) | 0014 |
| [0014](0014-door-attachments.md) | Constrained doors and atomic geometry snapshots | Implemented (M1) | 0013 |
| [0015](0015-local-project-snapshots.md) | Local SQLite project snapshots and File workflow | Implemented; M1 verified | 0004 |
| [0016](0016-mock-background-raster.md) | Persistent mock background raster | Implemented (M2); sizes extended by 0026 | 0026 |
| [0017](0017-masked-room-artwork.md) | Context-cropped room artwork with enforced masks | Implemented (M2) | 0026, 0028 |
| [0018](0018-flattened-artwork-export.md) | Flattened PNG and lossless WebP export | Implemented (M2); resolution from 0026 | 0026 |
| [0019](0019-durable-generation-jobs.md) | Durable local generation jobs | Implemented; provider interruption not implemented | 0027 |
| [0020](0020-preview-recovery.md) | Explicit preview recovery after reload | Implemented (mock and SDXL) | |
| [0021](0021-room-style-inspector.md) | Room style overrides and prompt assembly | Implemented; SDXL prompts per 0028 | 0022, 0028 |
| [0022](0022-map-authoring.md) | Persistent map prompt and style defaults | Implemented (M2) | 0021 |
| [0023](0023-exterior-background-and-room-interiors.md) | Geometry-aware exterior background under interior layers | **Accepted design, not implemented** (M3) | 0029 |
| [0024](0024-server-provider-configuration.md) | Server-only provider configuration and secrets | Implemented (M3); sequencing superseded by 0025 | 0025 |
| [0025](0025-local-sdxl-first.md) | Local ComfyUI/SDXL as first real provider | Implemented; GPU acceptance pending | 0026, 0027 |
| [0026](0026-resolution-aware-raster-assets.md) | Resolution-aware raster assets (480 × 320 and 960 × 640) | Implemented (M3) | 0016–0018 |
| [0027](0027-queued-sdxl-editor.md) | Queued SDXL generation in the editor | Implemented; visual acceptance pending | 0019, 0025 |
| [0028](0028-sdxl-room-working-resolution.md) | SDXL 1024 × 1024 room working transform and prompts | Implemented; GPU trial pending | 0027 |
| [0029](0029-scale-and-room-layout-conditioning.md) | Physical scale prompts and optional ControlNet wall guidance | Implemented; GPU trial pending | 0028, 0023 |
| 0030 | Deterministic wall/door overlay drawn by Quill | **Parked**; exists only on the PR #1 branch, not on main | |
| [0031](0031-sdxl-inpainting-model.md) | `InpaintModelConditioning` and optional dedicated SDXL inpainting UNet for rooms | Implemented; first trial done; needs a full ControlNet for walls (Control-LoRA incompatible) | 0025, 0029 |

M0–M8 refer to milestones in [PROJECT_MANIFEST.md](../../PROJECT_MANIFEST.md) §16.
