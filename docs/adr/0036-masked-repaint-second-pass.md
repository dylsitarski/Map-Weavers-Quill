# ADR-0036: Masked klein rooms repaint pass 1 instead of re-editing it

Status: Implemented; GPU trial pending. Changes the second pass of ADR-0034 when latent
masking (ADR-0035) is on, which is the default. The unmasked comparison mode keeps the
ADR-0034 reference edit.

## Context

Owner trial of ADR-0035 (2026-10-08, cottage map, storeroom twice, bedroom, outhouse):
every room stayed inside its walls, so latent masking fixed the expansion problem. But
the bundle's unclipped pass images showed the second pass now changes almost nothing: in
every room the final image is a near copy of pass 1. The storeroom kept pass 1's
off-white placeholder floor despite "dark wooden floor" in its description, and in one
attempt pass 1 added a door to its top wall that pass 2 kept.

Our reading: pass 2 was an edit whose only reference image is pass 1's result, and under
the mask the fixed surroundings are pass 1 too. An edit model given that reference, with
everything around the room already matching it, reconstructs it; the prompt cannot
outweigh it. Before masking, pass 2 started from an empty latent over the whole window
and did change floors and contents.

## Decision

- With latent masking, pass 2 is a masked repaint with no reference image: it starts from
  pass 1's latent under the same noise mask, re-noised to the tail of a longer schedule.
  `Flux2Scheduler` with 8 steps is split with `SplitSigmas` so that pass 2 runs the last
  `round(8 × denoise)` steps; the default denoise 0.625 runs 5 steps from sigma ≈ 0.94
  (the klein schedule at 1024 × 1024 is 1.0, 0.985, 0.967, 0.942, 0.906, 0.853, 0.763,
  0.58, 0). Pass 1's layout survives in the partly noised latent; the text prompt decides
  floor, contents and character.
- The pass-2 prompt (`flux2-klein-room-repaint-v1`) describes the finished room instead of
  an edit of image 1: an orthographic roof-removed room seen from above, the description
  unchanged, the floor (as described, or clearly textured and never plain or pale),
  furnishings across the whole floor, the described character, style, narrow dark wall
  tops at the edges, closed wooden doors in the walls and no other doors, no text.
- `MWQ_IMAGE_COMFY_FLUX2_REFINE_DENOISE` (0.125 to 1, default 0.625) sets the strength:
  higher repaints more but keeps less of pass 1's layout; 1.0 is a full masked
  generation from noise with pass 1 discarded.
- Workflow `comfy-flux2-klein-edit-repaint-v1`; provenance adds `refineDenoise`,
  `refineSteps` and `refineScheduleSteps`.

## Consequences

- One more sampling step in pass 2 than before (5 instead of 4) and no reference tokens,
  so time should be similar, possibly slightly shorter.
- Doors and walls inside the room now come from pass 1's partly noised latent plus the
  prompt; pass 2 may move or drop doors drawn in pass 1 or, despite the prompt, add some.
  Door placement remains unreliable; exact doors may need to be drawn by Quill.
- The denoise default is a judgement from the schedule, not measured.

## Verification

`tests/test_flux2.py`: the repaint graph (no `ReferenceLatent` in pass 2, masked pass-1
latent, 8-step schedule split at step 3, a full-strength variant), the unmasked mode
keeping the reference edit, configuration and environment parsing, the repaint prompt,
and the queued room job's template and workflow version. `SplitSigmas` and
`Flux2Scheduler` were checked against ComfyUI's source on 2026-10-08.
