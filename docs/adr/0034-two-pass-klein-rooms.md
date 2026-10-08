# ADR-0034: Two-pass FLUX.2 klein room edits

Status: Implemented; GPU trial pending. Extends ADR-0032 and ADR-0033 (klein only; SDXL and
the mock provider are unchanged).

## Context

After ADR-0033, klein rooms have consistent scale, thin wall tops and correctly placed
closed doors, at about 12 seconds per room. Three problems remained in the owner's trial
(2026-10-08): floors drift toward the sketch's off-white placeholder even when described;
furniture lines the walls and leaves the centre empty; and room character from the
description (an extremely cluttered storeroom, a whimsical bedroom) shows weakly. The
base klein variant (20 steps, CFG 5) gave slightly more character but fixed nothing else
and took about 100 seconds, so it is not a solution. A noise-textured placeholder was
judged unlikely to help, since flat gray and off-white placeholders were both kept.

Our reading (not verified): an edit model keeps what the reference shows unless clearly
told to change it, and the first pass's prompt is mostly about interpreting the sketch,
so the description gets little weight. Changing the floor, adding objects and shifting
the mood of an image that already shows a real room is the kind of edit these models do
best.

## Decision

- Klein room edits run two passes in one ComfyUI job (workflow
  `comfy-flux2-klein-edit-2pass-v1`). Pass 1 is unchanged (ADR-0033). Pass 2 uses pass 1's
  output latent as its only `ReferenceLatent`, starts from an empty latent with the same
  noise seed, sampler, steps and CFG, and has its own prompt; node 7 saves pass 2. Pass 1
  is decoded and saved too, as `quill/pass1_*.png`, for inspection in ComfyUI only; Quill
  does not fetch or store it.
- The pass-2 prompt (`flux2-klein-room-refine-v1`) starts with "Restyle the interior of the
  room near the centre of image 1 to match this description", then the user's description
  unchanged, a floor line (exactly as described, or a clearly textured material that is not
  plain, flat or pale), a request to fill the whole room with fitting objects spread across
  the floor and to give the room its described character, render style and palette, an
  instruction to keep walls, wall tops, doors and the surroundings, then the scale sentence.
- The request carries the pass-2 prompt in a new provider extension, `quill.refine`
  (`{"prompt": text}`), accepted only by klein with two passes and only together with
  `quill.layout`; anything else is refused before contacting ComfyUI.
- `MWQ_IMAGE_COMFY_FLUX2_ROOM_PASSES` (`2` default, or `1`) selects the behavior, for
  comparison and for slower GPUs.
- Generation records add `refinePrompt`, `refineTemplate` and `comfyui.roomPasses`; the
  record's `prompt` stays the pass-1 prompt. Debugging bundles write `refine-prompt.txt`.
- Outside-mask pixels are still copied from the source after the job, so pass 2 cannot
  change anything outside the room.

## Consequences

- About twice the sampling time: roughly 24 seconds per room from the 12-second trial,
  within the 30-second soft limit (not measured). Prompt encoding runs twice.
- Pass 2 may move or soften walls and doors drawn in pass 1. The room boundary is still
  exact, but interior wall faces and door positions depend on pass 2 keeping them.
- "Near the centre" is approximate: the window is clamped at map edges, and neighbouring
  rooms' artwork is also visible. Changes pass 2 makes outside the room are discarded.
- Pass 1's image is not part of provenance; only its ComfyUI output file exists.

## Verification

`tests/test_flux2.py`: the two-pass graph wiring (pass-1 latent as both reference
latents, shared noise, sampler and sigmas, final save from pass 2, pass-1 save prefix),
the base-variant negative, offline refusal of a refine request without layout, with an
empty prompt or with one pass configured, configuration and environment parsing, the
refine prompt's content, and the queued room job recording `refinePrompt` and the
two-pass workflow version.
