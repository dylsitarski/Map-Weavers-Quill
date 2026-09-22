# Map-Weaver's Quill

A local-first, AI-assisted 2D battlemap editor. Linux is the primary target;
Windows 11 follows. See [PROJECT_MANIFEST.md](PROJECT_MANIFEST.md).

## Development status

Milestone 0 is **in progress**, not complete. This first slice provides strict
Python project models, generated JSON Schema, coordinate conversions, a two-room
fixture, and offline unit tests. There is no editor, generation service, or
Foundry importer yet.

### Run foundation tests (Linux, Python 3.12)

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
make test PYTHON=.venv/bin/python
```

`make schema` regenerates the checked-in schema. `make test` detects schema drift.
Tests use synthetic data, no credentials, paid APIs, GPUs, or network calls.

## Next Milestone 0 work

- React/TypeScript and FastAPI shells, with a one-command development launcher.
- Generated TypeScript types and cross-runtime round-trip validation.
- Provider contracts and a deterministic mock image provider.
- Formatting, linting, type checking, dependency scanning, and broader CI.
- Geometry topology and cross-entity relationship validation before persistence.

The current schema validates structural data, not polygon simplicity or door
attachment geometry. These limitations are explicit; do not use it as a complete
editor validation boundary yet.

## Distribution

Public, free distribution is intended. A software license has not been selected;
this repository does not yet grant a general redistribution license. The owner's
noncommercial release intent does not itself select a legal license. Do not bundle
third-party model weights or private assets.
