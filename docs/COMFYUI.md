# Local SDXL / ComfyUI test

Milestone 3 uses a local backend first to avoid per-image API charges. This increment
provides a standalone adapter and GPU smoke test; the editor still uses mock.
Full-resolution editor storage/integration is next. See ADR-0025.

## Install separately on Linux

Use the [official ComfyUI installation guide](https://docs.comfy.org/installation/manual_install)
for its current Python/PyTorch requirements. Install outside Map-Weavers-Quill, with
its own virtual environment. Do not install ComfyUI's dependencies into Quill's venv.
No custom nodes, paid partner nodes, account, or API key is needed for this workflow.

The first target is the owner's RTX 3060 Ti (8 GB VRAM), 32 GB RAM, Linux desktop.
A real run on that hardware is still required. No generation timing is promised.

Download `sd_xl_base_1.0.safetensors` from the
[SDXL base model repository](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/tree/main)
into ComfyUI's `models/checkpoints/` directory. Follow the model's published license
and access terms. Quill does not bundle weights or change their license. The initial
graph uses SDXL base for both generation and masked editing; it does not yet use the
separate Diffusers SDXL inpainting fine-tune. A dedicated inpainting comparison is
planned after the baseline works.

From the ComfyUI directory, using its Python environment, start it on loopback:

```sh
python main.py --listen 127.0.0.1 --port 8188
```

Use batch one (fixed by our graph). Start with default memory management. If GPU
memory is exhausted, stop other GPU workloads, try 768x768, or restart ComfyUI with
its documented `--lowvram` option. These affect capacity/speed; reduced resolution
also affects quality. Do not install a refiner or ControlNet for this initial test.

## Check from Quill

Pull the latest repository changes and activate Quill's existing dependencies.
In a second terminal, from Map-Weavers-Quill:

```sh
make comfy-check
```

This checks core node availability and the configured checkpoint filename. It does
not queue an image, load the model, or test GPU memory. If it fails, verify ComfyUI
is running and the checkpoint is installed. Optional environment overrides:

```sh
export MWQ_IMAGE_COMFY_URL=http://127.0.0.1:8188
export MWQ_IMAGE_COMFY_CHECKPOINT=sd_xl_base_1.0.safetensors
export MWQ_IMAGE_COMFY_TIMEOUT=600
```

Only HTTP loopback hosts with an explicit port are accepted. The checkpoint must
be a filename, not a directory. `.env` is not loaded automatically. Leave
`MWQ_IMAGE_PROVIDER=mock` for the editor; `comfyui` is not an editor option yet.
The standalone command constructs the adapter directly using the variables above.

## Run one real generation

```sh
PYTHONPATH=apps/server .venv/bin/python scripts/comfy_smoke.py \
  --generate --output data/comfy-smoke.png
```

This queues one local 1024x1024 image, seed 42, 20 steps. The default prompt asks for
a top-down cottage interior. It writes the original-resolution PNG plus
`data/comfy-smoke.json` metadata and never changes a Quill project. Existing files
are not overwritten; choose a fresh output name for another run. The default data
directory is ignored by git. Generation uses your GPU/electricity, with no hosted
image API call or per-image fee.

For the 8 GB card, a lower-memory trial is:

```sh
PYTHONPATH=apps/server .venv/bin/python scripts/comfy_smoke.py \
  --generate --width 768 --height 768 --output data/comfy-smoke-768.png
```

For masked editing, create a same-size grayscale PNG mask (white edits, black
preserves) in an image editor and supply both inputs:

```sh
PYTHONPATH=apps/server .venv/bin/python scripts/comfy_smoke.py \
  --generate --source data/comfy-smoke.png --mask data/room-mask.png \
  --prompt 'Orthographic top-down cottage bedroom, wooden bed and stone floor, no grid or labels' \
  --output data/comfy-room-edit.png
```

Source and mask dimensions must exactly match --width/--height (1024x1024 defaults).
The adapter does not resize them. Black-mask RGB pixels are copied from the original
source after generation. White-mask content quality and border continuity need
visual review; a mask does not guarantee exact furniture/door placement.

## Evidence to capture

- PNG and JSON sidecar; inspect top-down perspective, room borders and continuity.
- ComfyUI version/commit (`git rev-parse HEAD` in its repository).
- Checkpoint file SHA-256 (`sha256sum models/checkpoints/sd_xl_base_1.0.safetensors`).
- Actual elapsed time and peak VRAM, plus whether low-VRAM mode was needed.

The sidecar contains prompts, asset hashes and local model/workflow details; treat
it as project content when sharing. No credentials or endpoint URL are recorded.
ComfyUI retains its own input and output copies, and may store workflow metadata
in its output PNG. Quill's returned PNG is re-encoded without that metadata.

Timeouts do not automatically resubmit. ComfyUI may still finish after a timeout
or Ctrl-C; inspect its queue before retrying. The adapter never calls the global
interrupt endpoint. The command returns a safe summary; consult ComfyUI's local
console for GPU errors. No automatic history/asset cleanup is implemented.

Protocol tests run offline as part of `make check`; they do not demonstrate actual
GPU performance, adjacent-room visual continuity or geometry-aware roof generation.
