# ADR-0021: Room style overrides and deterministic prompt assembly

Status: Implemented for the mock provider profile.

The room AI panel edits Environment, Render style and Palette alongside its prompt.
Blank fields remove that room override and inherit the current MapStyle value, shown
as the field placeholder. Apply prompt and style commits all draft values in one
undoable room edit. The existing string-valued Room.styleOverrides schema is retained;
unrelated stored keys are preserved, never silently discarded by the editor. Supported
keys are environment, renderStyle and palette. Unknown keys cause generation to fail
explicitly until their semantics are implemented. Each resolved style value is limited
to 512 characters; the existing raw room prompt limit is 4000. No schema migration.

Generation resolves each supported field against map.style, strips surrounding
whitespace and assembles a stable prompt: raw description, a sorted JSON style object,
map camera and neutral baked-lighting constraints. Room overrides cannot change camera
or baked lighting. This is provider-neutral text input, not model-specific parameters.
The mock uses the assembled text in its deterministic pattern hash; it demonstrates
that style changes reach the provider but does not paint semantic fantasy artwork.

GenerationRecord.prompt is the exact assembled provider prompt. Parameters additionally
store promptTemplate=room-style-v1, roomPrompt, styleOverrides, effectiveStyle and mapStyle,
alongside seed/crop/dimensions. Already recorded generations are never rewritten.
Existing artwork remains unchanged when styles/prompts are edited; regenerate explicitly
to replace it. Applied style changes invalidate outstanding previews and recovery
fingerprints. Inspector drafts alone do not mutate the project or generation inputs.

Tests verify inheritance, override precedence, deterministic output, changed output for
changed style, exact provenance, invalid values/keys, and browser apply/undo/redo,
stale-preview refusal, existing-art preservation, clearing overrides and save/reopen.
Map-level style editing and real-provider prompt tuning remain Milestone 3 work.
