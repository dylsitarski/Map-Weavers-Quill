"""Generate JSON Schema from the single-source Pydantic contracts."""

import argparse
import json
from pathlib import Path

from quill.models import Project

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "packages/schema/project.schema.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    schema = Project.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    output = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not TARGET.exists() or TARGET.read_text() != output:
            raise SystemExit("Schema drift: run make schema and commit the result")
        print("Schema is current")
    else:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(output)


if __name__ == "__main__":
    main()
