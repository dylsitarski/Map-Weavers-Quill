"""Generate JSON Schema from the single-source Pydantic contracts."""

import argparse
import json
from pathlib import Path

from pydantic import BaseModel
from quill.doors import DoorRequest, DoorResult
from quill.geometry import GeometryRequest, GeometryResult
from quill.models import Project
from quill.projects import ProjectList, SaveRequest
from quill.providers import (
    GenerateRequest,
    GenerationResult,
    InpaintRequest,
    ProviderDescriptor,
    ProviderError,
)
from quill.walls import WallDerivationRequest, WallDerivationResult


class ProviderContracts(BaseModel):
    descriptor: ProviderDescriptor
    generate: GenerateRequest
    inpaint: InpaintRequest
    result: GenerationResult
    error: ProviderError


class PersistenceContracts(BaseModel):
    save: SaveRequest
    result: Project
    listing: ProjectList


class GeometryContracts(BaseModel):
    request: GeometryRequest
    result: GeometryResult
    wallRequest: WallDerivationRequest
    wallResult: WallDerivationResult
    doorRequest: DoorRequest
    doorResult: DoorResult


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "packages/schema/project.schema.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, model in [
        ("project", Project),
        ("provider", ProviderContracts),
        ("geometry", GeometryContracts),
        ("persistence", PersistenceContracts),
    ]:
        target = ROOT / f"packages/schema/{name}.schema.json"
        schema = model.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        output = json.dumps(schema, indent=2, sort_keys=True) + "\n"
        if args.check:
            if not target.exists() or target.read_text() != output:
                raise SystemExit(f"Schema drift: {name}; run make schema")
            print(f"{name} schema is current")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(output)


if __name__ == "__main__":
    main()
