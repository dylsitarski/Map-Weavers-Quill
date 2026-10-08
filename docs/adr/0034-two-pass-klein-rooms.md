# ADR-0034: Two-pass FLUX.2 klein room edits

Status: Implemented; first trial done (below). Extends ADR-0032 and ADR-0033 (klein only; SDXL and
the mock provider are unchanged).

Update 2026-10-08: after the first trial, rooms under 10 ft get a smaller window (at least
20 ft) so they span a quarter of it; both prompts say to add no doors other than the brown
bands (pass 2: `flux2-klein-room-refine-v2`, pass 1: `flux2-klein-room-sketch-v4`); and
both passes' unclipped images are kept for debugging bundles. Details below.

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
  is decoded and saved too, as `quill/pass1_*.png`; since the first trial Quill fetches it
  for diagnostics (below).
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

## First trial and follow-up (2026-10-08)

Owner trial on the cottage map, about 24 seconds per room as estimated. Room character
improved markedly: the main room's floor became the described wood and the room filled
with furniture and clutter across the floor. Remaining problems, with the owner's pass-1
and final images from ComfyUI's output folder:

- **Tiny rooms expand.** The 5-ft outhouse was drawn as a large hut about 20 ft across,
  with the sketched square as a box in its middle, already in pass 1. Clipping to the
  room then left floor only, or walls on some sides. At the fixed 40-ft window the room
  was 64 px of 1024; 10-ft rooms (256 px) stayed inside their walls. Pass 2 kept pass 1's
  walls closely (main room), so the second pass is not the cause; giving pass 2 the sketch
  as a second reference was tried in code and dropped before trial on this evidence.
- **Doors.** Brown door bands survived as flat strips in both passes, and pass 1 invented
  extra doors (main room top wall, bedroom top wall). Exterior bottom door of the main
  room stayed a strip.

Follow-up:

- `RoomWindow.around` takes a minimum: the window is `min(40 ft, max(20 ft, 4 × room
  extent))`, still growing for large rooms. Rooms 10 ft and larger are unchanged; a 5-ft
  room gets a 20-ft window (256 px wide, 51.2 px/ft). Scale now differs by at most 2× and
  only for rooms under 10 ft; the prompt states the actual scale.
- Pass 1 asks for "no other doors"; pass 2 says any flat brown strip in a wall is a closed
  door to draw as a wooden door, and to add no other doors.
- Diagnostics: for every ComfyUI room edit, the provider keeps the unclipped final image
  and (two-pass klein) the pass-1 image; Quill restores both to map size and stores them,
  recorded as `diagnosticImages` (`raw`, `firstPass`). Debugging bundles write
  `pass-1-unclipped` and `final-unclipped`. This adds two image assets per room
  generation, including unaccepted previews.

Verification: tiny-room window sizes (`test_sdxl_authoring.py`), diagnostics fetched,
unclipped and stored at map size (`test_flux2.py`), and exported
(`test_debug_bundle.py`).

