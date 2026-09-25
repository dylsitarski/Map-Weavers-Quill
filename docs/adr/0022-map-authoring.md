# ADR-0022: Persistent map-level prompt and style authoring

Status: Implemented.

Map → AI exposes Background prompt and Map environment, render style and palette.
Apply map prompt and style commits one scene-history transaction; Save project writes
the applied values. Draft changes disable background generation until applied. Form
drafts are not saved. A new project starts with the existing Stone dungeon floor prompt
and empty style defaults. Room blanks inherit these map values; map defaults are not
inferred from a prompt and changing a map default never rewrites room overrides.

Persist the prompt at Project.settings["quill.background"].prompt, retaining unrelated
settings/namespace fields. The project schema's existing extension slot is used; no
native version migration is needed. Save/Open validates this known namespace as an
object containing a string prompt up to 4000 characters. Persist map defaults in the
existing map.style fields. Existing projects lacking a stored prompt display the latest
background generation's raw backgroundPrompt (or legacy prompt), otherwise the default.
An explicitly stored empty prompt remains empty.

Map authoring snapshots live in the same undo history as geometry and artwork, with
initial/load baselines captured explicitly so undo after Save cannot fall back to the
new saved values. Apply/Undo/Redo invalidate pending previews through the normal context
and fingerprint guards. Existing artwork and historical generation records are preserved.

BackgroundRequest gains optional MapStyle; old callers without it retain the raw-prompt
behavior. The editor supplies applied defaults. Assemble the raw prompt plus sorted style
JSON and fixed map camera/neutral-lighting constraints. Style fields have a 512-character
generation limit. Generation provenance retains the assembled prompt, raw backgroundPrompt,
mapStyle and template version map-style-v1. Room generation uses these same persisted
map defaults through ADR-0021. A style is a prompt instruction, not a filter on existing art.

Tests cover native persistence, immutable provenance, style changes reaching generation,
undo after Save, prompt/default restoration after Open, inherited room placeholders,
draft generation gating, stale previews and preservation of unrelated settings. Mock
imagery remains deterministic test patterns; real-provider integration is separate.

Planned extension: ADR-0023 specifies layout-aware background context and complete building
exteriors beneath interior layers. The prompt/style-only request implemented here does
not yet carry room footprints or guarantee exterior alignment.
