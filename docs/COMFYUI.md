# Local image generation with ComfyUI

Quill's real image providers run on a local [ComfyUI](https://docs.comfy.org) server.
Two model families are supported: **SDXL** (`comfyui-sdxl`, ADR-0025) and
**FLUX.2 [klein]** (`comfyui-flux2-klein`, ADR-0032); choose one with
`MWQ_IMAGE_PROVIDER`. Sections 1–4 set up ComfyUI and SDXL; section 5 covers klein.
ComfyUI runs as a separate process with its own Python
environment, and Quill talks to it over loopback HTTP. No API key, account, custom
nodes or paid partner nodes are needed, and nothing leaves your machine. Quill bundles
no model weights: you download them yourself under their own licenses.

The default provider is still the offline mock. Design records: ADR-0025 (adapter),
ADR-0026 (resolution), ADR-0027 (editor integration), ADR-0028 (room working resolution
and prompts), ADR-0029 (scale and wall guidance), ADR-0031 (dedicated inpainting model),
ADR-0032 (FLUX.2 klein).

Reference hardware: Linux, NVIDIA RTX 3060 Ti (8 GB VRAM), about 32 GB RAM. This is the
owner's test machine, not a measured requirement.

## 1. Install ComfyUI

Follow the [official manual install guide](https://docs.comfy.org/installation/manual_install)
for its current Python/PyTorch requirements. Install it outside the Map-Weavers-Quill
directory, in its own virtual environment; never install ComfyUI dependencies into
Quill's venv. Start it on loopback from the ComfyUI directory:

```sh
python main.py --listen 127.0.0.1 --port 8188
```

If GPU memory runs out, stop other GPU workloads first, then try ComfyUI's documented
`--lowvram` option. That trades speed for capacity.

## 2. Install models

Required: download `sd_xl_base_1.0.safetensors` from the
[SDXL base repository](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/tree/main)
into `ComfyUI/models/checkpoints/`.

Optional, recommended for room artwork: the dedicated SDXL inpainting UNet
([SD-XL Inpainting 0.1](https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1),
openrail++). Download `unet/diffusion_pytorch_model.fp16.safetensors` (5.14 GB) into
`ComfyUI/models/diffusion_models/` and rename it to something recognizable, for
example `sdxl-inpainting-0.1.fp16.safetensors`. It replaces only the room sampler model;
the base checkpoint above is still required for text encoding, the VAE and backgrounds.

Optional, for room wall/door guidance, put one SDXL canny control model in
`ComfyUI/models/controlnet/` (not checkpoints or loras) and restart ComfyUI. Use an SDXL
model, not an SD 1.5 one. Which kind depends on the room model:

- **With the dedicated inpainting UNet, use a full ControlNet.** Recommended for 8 GB
  GPUs: [diffusers/controlnet-canny-sdxl-1.0-small](https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0-small)
  (about 320 MB in fp16). Download its fp16 `.safetensors` file and rename it, for example
  `controlnet-canny-sdxl-1.0-small.fp16.safetensors`. Higher quality but 5 GB:
  [xinsir/controlnet-canny-sdxl-1.0](https://huggingface.co/xinsir/controlnet-canny-sdxl-1.0)
  (Apache-2.0).
- **Control-LoRA works only with base SDXL rooms:**
  [control-lora-canny-rank128.safetensors](https://huggingface.co/stabilityai/control-lora/blob/main/control-LoRAs-rank128/control-lora-canny-rank128.safetensors).
  A Control-LoRA is built from the active UNet's weights and cannot adapt to the inpainting
  UNet's 9-channel input; ComfyUI fails with `shape '[320, 9, 3, 3]' is invalid`. Quill's
  readiness check refuses this combination (detected by the `control-lora` filename).

Check each model's published license and access terms before use or redistribution.

## 3. Configure and check from Quill

Configuration is read from the environment of the Quill API process. `.env` is not
loaded automatically, so export variables before running commands:

| Variable | Default | Meaning |
| --- | --- | --- |
| `MWQ_IMAGE_PROVIDER` | `mock` | Set to `comfyui-sdxl` to use ComfyUI in the editor |
| `MWQ_IMAGE_COMFY_URL` | `http://127.0.0.1:8188` | Loopback HTTP URL with an explicit port; credentials, paths, queries and non-local hosts are rejected |
| `MWQ_IMAGE_COMFY_CHECKPOINT` | `sd_xl_base_1.0.safetensors` | Checkpoint filename (not a path) |
| `MWQ_IMAGE_COMFY_TIMEOUT` | `600` | Overall generation deadline in seconds |
| `MWQ_IMAGE_COMFY_CONTROLNET` | unset | Optional ControlNet filename that enables wall/door guidance |
| `MWQ_IMAGE_COMFY_INPAINT_UNET` | unset | Optional dedicated SDXL inpainting UNet filename (in `models/diffusion_models`) used for room artwork |

With ComfyUI running, from the Quill directory:

```sh
make comfy-check
```

This checks connectivity, the core nodes and that the configured files exist. It does
not load weights, queue an image or test GPU memory, and it cannot verify that a file
really is an SDXL model.

## 4. Use SDXL in the editor

Stop any running `make dev`, then:

```sh
export MWQ_IMAGE_PROVIDER=comfyui-sdxl
export MWQ_IMAGE_COMFY_CHECKPOINT=sd_xl_base_1.0.safetensors
# optional dedicated inpainting model for rooms:
# export MWQ_IMAGE_COMFY_INPAINT_UNET=sdxl-inpainting-0.1.fp16.safetensors
# optional wall/door guidance (a full ControlNet when using the inpainting UNet):
# export MWQ_IMAGE_COMFY_CONTROLNET=controlnet-canny-sdxl-1.0-small.fp16.safetensors
make dev
```

Open Map → AI. The panel identifies Local SDXL / ComfyUI and its readiness. If it is not
ready, fix the setup and click **Check provider**; generation stays disabled until the
check passes, and each job re-checks before submitting. With the inpainting UNet
configured, the readiness message reads "Ready · dedicated SDXL inpainting model for
rooms". With ControlNet configured, a
selected room's AI panel reports that wall and door guidance is enabled. A configured
but missing model or node fails readiness instead of silently falling back.

Then use the normal workflow: apply a background prompt and style, Generate preview,
Accept; select a room, apply its prompt, generate and accept. Accepting is undoable and
File → Save keeps accepted art with its provenance. To switch back, set
`MWQ_IMAGE_PROVIDER=mock` and restart Quill. Save/Open and export keep working with
either provider.

## 5. Use FLUX.2 klein instead

FLUX.2 [klein] 4B follows prompts better than SDXL and edits images from reference
pictures. By default Quill sends each room as one reference: the surroundings with a
floor-plan sketch of the room drawn in (off-white floor, thin dark walls, floor-plan door
symbols). It needs a
ComfyUI version recent enough to offer the `flux2` text-encoder type; update ComfyUI if
readiness says so. No ControlNet is needed. The 4B model is Apache-2.0; check each model
card for the text encoder and VAE.

Download these files (the links are from ComfyUI's official klein guide):

| File | Folder | Source |
| --- | --- | --- |
| `flux-2-klein-4b-fp8.safetensors` (distilled, recommended) | `models/diffusion_models/` | [black-forest-labs/FLUX.2-klein-4b-fp8](https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8/blob/main/flux-2-klein-4b-fp8.safetensors) |
| `qwen_3_4b.safetensors` (text encoder) | `models/text_encoders/` | [Comfy-Org/flux2-klein-4B](https://huggingface.co/Comfy-Org/flux2-klein-4B/blob/main/split_files/text_encoders/qwen_3_4b.safetensors) |
| `flux2-vae.safetensors` | `models/vae/` | [Comfy-Org/flux2-dev](https://huggingface.co/Comfy-Org/flux2-dev/blob/main/split_files/vae/flux2-vae.safetensors) |
| optional: `flux-2-klein-base-4b-fp8.safetensors` (base) | `models/diffusion_models/` | [black-forest-labs/FLUX.2-klein-base-4b-fp8](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4b-fp8/blob/main/flux-2-klein-base-4b-fp8.safetensors) |

Restart ComfyUI, stop Quill, then:

```sh
export MWQ_IMAGE_PROVIDER=comfyui-flux2-klein
# defaults shown; set only what differs
# export MWQ_IMAGE_COMFY_FLUX2_MODEL=flux-2-klein-4b-fp8.safetensors
# export MWQ_IMAGE_COMFY_FLUX2_TEXT_ENCODER=qwen_3_4b.safetensors
# export MWQ_IMAGE_COMFY_FLUX2_VAE=flux2-vae.safetensors
# export MWQ_IMAGE_COMFY_FLUX2_VARIANT=distilled   # or base (with the base model file)
# export MWQ_IMAGE_COMFY_FLUX2_TEXT_ENCODER_DEVICE=cpu   # keep the encoder off an 8 GB GPU
# export MWQ_IMAGE_COMFY_FLUX2_ROOM_REFERENCE=plan   # or sketch (default)
make dev
```

| Variable | Default | Meaning |
| --- | --- | --- |
| `MWQ_IMAGE_COMFY_FLUX2_MODEL` | `flux-2-klein-4b-fp8.safetensors` | Diffusion model file in `models/diffusion_models` |
| `MWQ_IMAGE_COMFY_FLUX2_TEXT_ENCODER` | `qwen_3_4b.safetensors` | Text encoder file in `models/text_encoders` |
| `MWQ_IMAGE_COMFY_FLUX2_VAE` | `flux2-vae.safetensors` | VAE file in `models/vae` |
| `MWQ_IMAGE_COMFY_FLUX2_VARIANT` | `distilled` | `distilled`: 4 steps, CFG 1. `base`: 20 steps, CFG 5; needs the base model file |
| `MWQ_IMAGE_COMFY_FLUX2_TEXT_ENCODER_DEVICE` | `default` | `cpu` runs the text encoder on the CPU to save GPU memory |
| `MWQ_IMAGE_COMFY_FLUX2_ROOM_REFERENCE` | `sketch` | `sketch`: one image with the room sketched in. `plan`: blanked context plus a separate floor plan (see ADR-0032) |

The AI panel shows "Local FLUX.2 klein · ComfyUI" and "Ready · distilled model" (or
base). Backgrounds are text-to-image at 960 × 640 with the same camera-first prompt as
SDXL. Rooms use the same working window, context and scale data as SDXL, but as an image
edit (ADR-0032, ADR-0033). The sketch is drawn at the working scale, so walls are the
project's wall thickness (about 13 px of 1024) in every room. Doors use floor-plan
symbols: a closed or locked door is a brown leaf across the opening; an open door is a
leaf swung into the room with a thin quarter-circle arc; secret doors and windows are
plain wall. The prompt starts with your room description, adds a default floor line if
the description does not mention a floor (so the off-white placeholder is not read as
the floor colour), lists the doors by wall side and state, adds render style and
palette, then gives the edit instruction and the scale. Pixels outside the room are
always protected exactly. The smoke command in this document tests
SDXL only.

Memory: the model, its 4B text encoder and the VAE do not fit in 8 GB of VRAM at once.
ComfyUI swaps them between GPU and system RAM, so expect slower generation; try
`MWQ_IMAGE_COMFY_FLUX2_TEXT_ENCODER_DEVICE=cpu` or ComfyUI's `--lowvram` if it runs out of
memory. Not yet measured on the reference hardware.

## What Quill sends to SDXL

- **Resolution.** The native map is 1200 × 800 units. SDXL backgrounds and room layers
  are stored at 960 × 640 (3:2, multiples of 64). Older 480 × 320 mock layers keep
  their original bytes and are only resampled for composition and context.
- **Rooms.** Quill takes a square window of real map context, 8 grid cells (40 ft) on a
  side, centred on the room and kept inside the map, and generates it at 1024 × 1024, so
  every room has the same working scale (25.6 px/ft, 128 px per 5-ft square). A room
  wider than about 36 ft gets a larger window and a smaller scale. The result is scaled
  back and clipped to the exact room mask, so pixels outside the room never change
  (ADR-0028, ADR-0033).
- **Context.** The source image for a room excludes that room's previous artwork and
  any known mock output (identified by provenance, not appearance). Real neighbouring
  artwork is kept.
- **Prompts.** Both backgrounds and rooms use camera-first, plain-language prompts
  (template `sdxl-overhead-v3`) with negative prompts against perspective, horizons,
  text, grids and abstract patterns. Backgrounds ask for terrain and roofs from above;
  rooms ask for roof-removed interiors and furniture from above. Your own prompts and
  the render style and palette are included unchanged. The map Environment field is no
  longer used: describe the setting in the background and room prompts (ADR-0033).
- **Scale.** Room prompts state the working window (for example "the image shows 40 by 40
  ft; one 5-ft grid square is 128 pixels wide"), the room's dimensions, and ask for
  life-size furniture and no interior partitions (ADR-0029, ADR-0033). Background
  prompts state the map's 120 × 80 ft size and pixels per 5-ft square. This is
  guidance, not a guarantee.
- **Wall/door guidance (optional).** When ControlNet is configured, Quill draws a
  white-on-black guide of the actual walls, with gaps at doors, transforms it with the
  room window, and passes it through core ControlNet nodes at strength 1 for the whole
  sampling run. No preprocessor or custom nodes are needed. Backgrounds remain
  text-only.
- **Masked editing (rooms).** The source and mask go through `InpaintModelConditioning`
  (ADR-0031). With the dedicated inpainting UNet, the model receives the masked image and
  mask as extra inputs and is trained to continue the surroundings. Without it, base SDXL
  ignores those inputs and sees the context only through the latent noise mask.
  Backgrounds always use the base model.
- **Sampler.** 20 Euler/normal steps, CFG 7, denoise 1, batch one. These are fixed
  reference settings, not UI controls.

## Behavior and limits

- With the dedicated inpainting UNet, ComfyUI holds it (5.14 GB) as well as the base
  checkpoint. On an 8 GB GPU this relies on ComfyUI's offloading and may need
  `--lowvram`; time and memory are not yet measured. Combined with a full ControlNet
  the pairing is supported by ComfyUI but not yet run here; Control-LoRA is refused.
- Jobs run one at a time through Quill's durable queue. Cancel preview stops the result
  from being published but does not stop ComfyUI's GPU work; the worker stays busy
  until completion or the timeout, and server shutdown may wait for it.
- Submissions are never retried automatically, and Quill never calls ComfyUI's global
  interrupt (it could stop another application's work). After a timeout, check
  ComfyUI's queue before retrying.
- ComfyUI keeps its own copies of uploaded inputs and outputs, and may embed workflow
  metadata in its PNGs. Quill re-encodes returned images without that metadata.
  Cleanup is manual.
- Accepted generation records include workflow version and hash, checkpoint and
  control-model filenames, ComfyUI prompt ID, seed, sampler settings, prompts, crop and
  transform details, scale data and input/output hashes. They contain no endpoint URL
  or credentials. A filename is not a checkpoint hash, so record hashes separately
  for reproducibility.
- Responses are capped at 16 MiB and checked before decoding; errors omit server
  payloads and tracebacks.
- Offline tests simulate ComfyUI. They do not establish image quality, GPU performance,
  adjacent-room continuity or building alignment.

## Standalone smoke command

`scripts/comfy_smoke.py` exercises the adapter directly, without the editor. It never
changes a Quill project and refuses to overwrite existing output files.

```sh
# one 1024 x 1024 image, seed 42, 20 steps
PYTHONPATH=apps/server .venv/bin/python scripts/comfy_smoke.py \
  --generate --output data/comfy-smoke.png

# lower-memory trial
PYTHONPATH=apps/server .venv/bin/python scripts/comfy_smoke.py \
  --generate --width 768 --height 768 --output data/comfy-smoke-768.png

# full-map size used by the editor
PYTHONPATH=apps/server .venv/bin/python scripts/comfy_smoke.py \
  --generate --width 960 --height 640 --output data/comfy-map-960.png

# masked edit: same-size grayscale mask, white edits, black preserves
PYTHONPATH=apps/server .venv/bin/python scripts/comfy_smoke.py \
  --generate --source data/comfy-smoke.png --mask data/room-mask.png \
  --prompt 'Orthographic top-down cottage bedroom, wooden bed and stone floor, no grid or labels' \
  --output data/comfy-room-edit.png
```

Dimensions must be multiples of 64 between 64 and 1024. Source and mask must match
`--width`/`--height` exactly; nothing is resized. Black-mask pixels are copied back from
the source after generation. Each run writes the PNG and a JSON sidecar with provider,
workflow version and hash, checkpoint filename, prompts, seed, sampler settings,
dimensions, ComfyUI prompt ID and input/output hashes. Treat the sidecar as project
content when sharing. The smoke command does not build a project wall guide; test
guidance through the editor.

## Trial results and pending checks

Recorded 2026-10-05 on the reference hardware (details in docs/HISTORY.md): the dedicated
inpainting UNet without guidance connected well to neighbouring rooms, but continued the
outdoor background into the room and invented its own layout instead of walls at the
boundary. With Control-LoRA guidance it failed as described above. With the small full
canny ControlNet, walls were followed in part, but the right half of a large enclosed room
became outdoors, continuing the surrounding scene. SDXL guidance tuning has stopped here
in favour of a FLUX.2 klein provider.

To share a trial, run `make debug-bundle PROJECT="Your project name"` (README) and attach the
zip. If possible also include the matching ComfyUI files: `ComfyUI/input/quill-*.png` (the
exact images sent to the model) and `ComfyUI/output/quill/` (raw model output before
Quill clips it to the room).

Still to record (SDXL items 1–3, then FLUX.2 klein):

1. Generate a background and two adjacent room interiors. Check top-down perspective,
   furniture scale, invented partitions, seams and that pixels outside each room are
   untouched. Accept, undo/redo, save/reopen and export.
2. Generate the same room and seed with wall guidance on and off; compare door
   clearance, partitions and object size.
3. Record elapsed time, peak VRAM, whether `--lowvram` was needed, the ComfyUI commit
   (`git rev-parse HEAD`) and checkpoint SHA-256
   (`sha256sum models/checkpoints/sd_xl_base_1.0.safetensors`).
4. FLUX.2 klein (distilled), first trial done with the `plan` reference: the room was fully
   indoors and walls followed the plan, but the gray placeholder floor and white plan
   walls stayed in the image and doors were drawn closed; about 20 seconds. Next: the
   default `sketch` reference on the same room with one open and one closed door, then
   `plan` for comparison. Check that no placeholder colors remain, walls follow the
   sketch, door states match, and record time (soft limit about 30 seconds).
5. FLUX.2 klein `sketch` trial done (2026-10-06, see docs/HISTORY.md): rooms indoors, but
   scale varied by room size, floors had to be described, doors were not always
   honoured, and rooms looked alike. Next, after ADR-0033: regenerate the bedroom,
   storeroom and main room with unlocked seeds. Check that furniture scale matches
   across rooms, wall tops are thin and even, open doors are drawn open where the
   sketch shows them, undescribed floors are not off-white, and each room's own
   description (clutter, whimsy) shows through. Record time.
