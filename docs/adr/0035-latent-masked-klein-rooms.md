# ADR-0035: Latent-masked sampling for FLUX.2 klein rooms

Status: Implemented; GPU trial pending. Changes the room sampling of ADR-0032 and ADR-0034
(klein only). SDXL already samples under its room mask (ADR-0031).

## Context

Klein room edits generated the whole 1024 × 1024 working window from an empty latent,
using the context-plus-sketch image only as a reference. The model was therefore free to
recompose everything: the owner's trials (2026-10-08) showed the 5-ft outhouse redrawn as
an object inside a larger invented hut, and the 10-ft storeroom extended up and sideways
into the forest, with the neighbouring rooms redrawn in its style. Quill's exact clipping
then kept only part of that larger room, so walls were missing on some sides. The smaller
window for tiny rooms (ADR-0034 update) helps size but cannot stop a room of any size from
growing; the cause is that nothing holds the surroundings in place during sampling.

## Decision

- With `MWQ_IMAGE_COMFY_FLUX2_ROOM_MASKING=latent` (default), both klein passes sample
  only inside the room. The first reference image is uploaded with the room mask as
  inverted alpha (the convention the SDXL adapter already uses), so ComfyUI's `LoadImage`
  returns the room as its mask. `GrowMask` expands it by 16 working pixels with tapered
  corners, so the whole wall band can be redrawn and blended. `SetLatentNoiseMask` attaches
  it to the VAE-encoded reference, which becomes pass 1's starting latent instead of an
  empty latent; pass 2 starts from pass 1's latent under the same mask. ComfyUI's
  `SamplerCustomAdvanced` passes the latent's noise mask to the sampler, which re-imposes
  the unmasked latent at every step, so the surroundings stay fixed and the room must be
  composed inside them. Sampling still uses full denoise, and the `ReferenceLatent`
  conditioning is unchanged.
- `none` keeps the previous whole-window generation for comparison.
- Provenance adds `roomMasking` and `maskGrow`; masked room workflows are versioned with a
  `-masked` suffix (`comfy-flux2-klein-edit-v1-masked`,
  `comfy-flux2-klein-edit-2pass-v1-masked`). Readiness requires the two extra core nodes.
- Quill's exact clipping to the room mask is unchanged.

## Consequences

- The model can no longer enlarge the room or redraw its neighbours; its room drawing must
  fit the masked area.
- Risks, untested on GPU: visible seams or lighting mismatch at the mask edge (latent
  masking works at the latent grid's resolution); weaker use of the reference, because the
  sketch now also seeds the starting latent (the off-white floor may persist more in pass 1;
  pass 2 exists to replace it); and small rooms having few latent cells to work with.
- Time should be unchanged: the reference was already encoded, and masking adds no
  sampling steps.

## Verification

`tests/test_flux2.py`: the upload's inverted-alpha mask, the `GrowMask` and
`SetLatentNoiseMask` wiring for both passes, the unmasked alternative (empty latent, RGB
upload), provenance and configuration parsing. Node and input names were checked against
ComfyUI's source (`comfy_extras/nodes_custom_sampler.py` `SamplerCustomAdvanced`,
`nodes.py` `SetLatentNoiseMask`, `comfy_extras/nodes_mask.py` `GrowMask`) on 2026-10-08.
