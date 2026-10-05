"""Opt-in local GPU test. Saves full-resolution PNG and reproducibility metadata."""

import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from quill.comfyui import MAX_RESPONSE, ComfyConfig, ComfyProvider
from quill.providers import GenerateRequest, InpaintRequest, ProviderFailure


def read_input(path: Path) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(MAX_RESPONSE + 1)
    if len(data) > MAX_RESPONSE:
        raise ValueError("Input PNG exceeds 16 MiB.")
    return data


async def run(args: argparse.Namespace) -> None:
    provider = ComfyProvider(ComfyConfig.from_env())
    await provider.check()
    if not args.generate:
        print("ComfyUI is reachable; required core nodes and configured models are available.")
        print("Readiness only: model loading and GPU execution have not been tested.")
        return
    output: Path = args.output
    sidecar = output.with_suffix(".json")
    if output.suffix.lower() != ".png" or output.exists() or sidecar.exists():
        raise ValueError("Choose a new .png output path; existing outputs will not be overwritten.")
    if bool(args.source) != bool(args.mask):
        raise ValueError("Supply both --source and --mask for inpainting.")
    request = GenerateRequest(
        requestId=str(uuid4()),
        prompt=args.prompt,
        negativePrompt=args.negative_prompt,
        width=args.width,
        height=args.height,
        seed=args.seed,
    )
    inputs = []
    if args.source:
        source = provider.put(read_input(args.source))
        mask = provider.put(read_input(args.mask))
        inputs = [source, mask]
        result = await provider.inpaint(
            InpaintRequest(
                **request.model_dump(),
                sourceRef=source,
                maskRef=mask,
                maskConvention="white-edit-black-preserve",
            )
        )
    else:
        result = await provider.generate(request)
    metadata = {
        "providerId": result.providerId,
        "requestId": request.requestId,
        "prompt": request.prompt,
        "negativePrompt": request.negativePrompt,
        "inputHashes": inputs,
        "outputHash": result.assetHash,
        **provider.last_run,
        "note": "Checkpoint filename is recorded; archive its SHA-256 and ComfyUI version separately. Seed alone does not guarantee identical output across hardware/versions.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(provider.assets[result.assetHash])
    with sidecar.open("x") as stream:
        stream.write(json.dumps(metadata, indent=2) + "\n")
    print(f"Saved {result.width} x {result.height} PNG: {output}")
    print(f"Saved generation metadata: {sidecar}")
    print("No Quill project was modified. ComfyUI also retains its own input/output files.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Readiness only (the default).")
    mode.add_argument(
        "--generate", action="store_true", help="Explicitly queue local GPU generation."
    )
    parser.add_argument("--output", type=Path, default=Path("data/comfy-smoke.png"))
    parser.add_argument(
        "--prompt",
        default="Orthographic top-down fantasy battlemap, stone cottage interior, timber furniture, neutral lighting, no text, no grid.",
    )
    parser.add_argument(
        "--negative-prompt", default="perspective, isometric, text, watermark, grid"
    )
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--mask", type=Path)
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except ProviderFailure as error:
        parser.exit(1, f"{error.error.code}: {error.error.message}\n")
    except (ValueError, OSError):
        parser.exit(
            1, "Invalid configuration, input images, or output path. See docs/COMFYUI.md.\n"
        )


if __name__ == "__main__":
    main()
