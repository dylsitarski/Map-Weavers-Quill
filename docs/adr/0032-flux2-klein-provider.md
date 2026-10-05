# ADR-0032: Local FLUX.2 [klein] provider through ComfyUI

Status: Implemented with offline protocol and editor tests; image quality and hardware
cost unverified until an owner GPU trial. Adds a second local model family alongside
SDXL (ADR-0025); SDXL remains available and unchanged.

## Context

Owner trials with SDXL (ADR-0028, ADR-0029, ADR-0031) showed that wall *edges* can be
guided, but SDXL does not reliably treat a large enclosed room as indoors: in the fourth
trial half of an enclosed room became an outdoor scene continuing its surroundings.
That is a model-understanding limit rather than a guidance-strength problem.

FLUX.2 [klein] 4B is a newer model with a Qwen3-4B language-model text encoder and native
multi-reference image editing. The 4B weights are Apache-2.0. ComfyUI supports it with
core nodes only: `UNETLoader`, `CLIPLoader` (type `flux2`), `VAELoader`, `ReferenceLatent`,
`EmptyFlux2LatentImage`, `Flux2Scheduler`, `CFGGuider`, `SamplerCustomAdvanced`,
`KSamplerSelect`, `RandomNoise`, `ConditioningZeroOut`. These graphs follow ComfyUI's
official klein text-to-image and image-edit templates.

## Decision

- **Provider `comfyui-flux2-klein`**, selected with `MWQ_IMAGE_PROVIDER`. It shares the
  existing ComfyUI transport, which this ADR factors into `ComfyBase`: loopback-only
  configuration, one submission without retries, polling, bounded responses, safe errors,
  no global interrupt, and exact protection of pixels outside the room mask. The SDXL
  family is `ComfyProvider(ComfyBase)` and is behaviorally unchanged (its tests pass
  without modification).
- **Configuration** (server-only): `MWQ_IMAGE_COMFY_FLUX2_MODEL` (default
  `flux-2-klein-4b-fp8.safetensors`), `MWQ_IMAGE_COMFY_FLUX2_TEXT_ENCODER`
  (`qwen_3_4b.safetensors`), `MWQ_IMAGE_COMFY_FLUX2_VAE` (`flux2-vae.safetensors`),
  `MWQ_IMAGE_COMFY_FLUX2_VARIANT` (`distilled`: 4 steps, CFG 1, zeroed negative; or
  `base`: 20 steps, CFG 5, empty negative), and `MWQ_IMAGE_COMFY_FLUX2_TEXT_ENCODER_DEVICE`
  (`default` or `cpu`, to keep the text encoder off small GPUs). `MWQ_IMAGE_COMFY_URL` and
  `MWQ_IMAGE_COMFY_TIMEOUT` are shared with SDXL.
- **Readiness** checks the core nodes, that `CLIPLoader` offers the `flux2` type (older
  ComfyUI versions do not), and that the three model files are installed.
- **Backgrounds**: text-to-image at 960 × 640 with the same camera-first prompt as SDXL
  (`sdxl-overhead-v2` text; no negative prompt). Layout-aware backgrounds still wait for
  ADR-0023's building/open-air design.
- **Rooms** use the same 1024 × 1024 working transform, clean context, physical scale and
  wall guide as SDXL, but as an image edit with two reference images instead of a mask:
  1. the context crop with the room area filled flat gray (`BLANK`), so the model sees
     the surroundings but not the old content inside the room;
  2. a floor plan (`room-plan-v1`): black outside, gray room floor, white wall lines with
     door gaps, built from the existing wall guide and room mask.
  Both are VAE-encoded and chained with `ReferenceLatent` onto the positive and negative
  conditioning, as in the official multi-reference template. Sampling starts from an
  empty latent. The prompt (`flux2-klein-room-v1`) is an edit instruction naming both
  images, then the user's room description and style, then scale and wall facts. Quill
  still composites only the masked pixels into the room layer, so the room boundary and
  everything outside it stay exact regardless of what the model draws.
- The provider advertises `control_image` because the plan is always sent; no ControlNet
  download is needed. It does not advertise or accept `negative_prompt`.
- **Provenance**: `providerId` `comfyui-flux2-klein`; workflow `comfy-flux2-klein-v1` or
  `comfy-flux2-klein-edit-v1`, model, text encoder and device, VAE, variant, steps, CFG,
  sampler and scheduler, plus `layoutReference` and the plan's source guide hash for
  rooms. Room records keep three input hashes (source, mask, guide), and project
  validation accepts the new provider ID with the same rule as conditioned SDXL rooms.
- The editor shows "Local FLUX.2 klein · ComfyUI", the variant in the readiness message,
  and explains that the floor plan is sent as a reference.

## Consequences

- A second local family with stronger prompt understanding and a reference-image route
  for the room layout, without custom nodes or Quill dependency changes.
- Memory and time: the klein 4B fp8 model, the 4B text encoder and the VAE do not fit
  together in 8 GB of VRAM; ComfyUI offloads between GPU and system RAM. The official
  guide quotes about 8.4 GB VRAM (distilled) and 9.2 GB (base) on a large GPU. On the
  reference RTX 3060 Ti expect slower generation; `text_encoder_device=cpu` or ComfyUI's
  `--lowvram` may be needed. Not measured. GGUF quantizations would fit better but need a
  custom node, which this project avoids.
- Untested: whether an empty-latent edit keeps the surroundings well aligned at the room
  edge (Quill's compositing guarantees the boundary, not the visual join), and how well
  klein reads the plan image. These are the trial's questions.
- Prompt templates are model-specific; changing either family's prompt does not affect
  the other.

## Verification

`tests/test_flux2.py` covers readiness (nodes, files, `flux2` support, no GPU work),
the text-to-image graph against the official template wiring, both reference uploads
(blanked context and plan pixels), the `ReferenceLatent` chain, outside-mask protection,
provenance, the base variant and CPU text encoder, rejection of negative prompts and
invalid requests before any network call, configuration and environment parsing, and an
end-to-end queued background and room job whose result saves and reopens. A browser test
checks the provider label. Existing SDXL tests pass unchanged.

Next: owner trial on the reference hardware with the distilled model (the large octagon
room from the fourth SDXL trial is a good comparison), recording time and peak VRAM.

Sources (checked 2026-10-05): ComfyUI source (`nodes.py` `CLIPLoader`/`UNETLoader`,
`comfy/sd.py` klein text encoders, `comfy_extras/nodes_flux.py`,
`comfy_extras/nodes_edit_model.py`), ComfyUI's klein tutorial and official workflow
templates (`image_flux2_klein_image_edit_4b_distilled.json`,
`image_flux2_klein_image_edit_4b_base.json`, `image_flux2_klein_text_to_image.json` in
Comfy-Org/workflow_templates).
