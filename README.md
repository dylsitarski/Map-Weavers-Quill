# Map-Weaver's Quill

A local-first, AI-assisted 2D battlemap editor. Linux is the primary target;
Windows 11 follows. See [PROJECT_MANIFEST.md](PROJECT_MANIFEST.md).

## Development status

Milestone 0 is **in progress**, not complete. The repository includes React and
FastAPI shells, Python models with generated JSON Schema and TypeScript types,
cross-runtime validation, coordinate transforms, and a deterministic offline
image provider. The web page is a connection-status shell, not a map editor.
There is no project persistence or Foundry importer yet.

### Setup (Linux, Python 3.12 and Node 24)

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
npm ci
make check
```

`make dev` starts the web shell at http://127.0.0.1:5173 and API at
http://127.0.0.1:8000. Ctrl-C stops both. This launcher currently targets Linux.
The API exposes `/health`, `/api/health`, and `/api/providers`.

`make schema` regenerates both schemas and TypeScript declarations. `make test`
runs Python/TypeScript tests and checks generated files for drift. `make check`
also runs Ruff lint/format checks, mypy, TypeScript checks and the Vite build.
`make audit` checks dependencies online; ordinary tests are offline.

The committed Python lockfile pins the full development dependency closure.
GitHub Actions runs `make check` and `make audit` on Ubuntu for pushes and PRs.
Tests use synthetic data, no credentials, paid APIs, or GPUs.

## Next Milestone 0 work

- Complete the remaining project entity fields and provider extension contracts.
- Add browser UI tests, front-end formatting/linting beyond TypeScript, and a
  clean-install development-server smoke test.
- Confirm hosted CI/audit results and document the initial supported toolchain.
- Geometry topology and cross-entity relationship validation before persistence.

The current schema validates structural data, not polygon simplicity or door
attachment geometry. These limitations are explicit; do not use it as a complete
editor validation boundary yet.

## Distribution

Public, free distribution is intended. A software license has not been selected;
this repository does not yet grant a general redistribution license. The owner's
noncommercial release intent does not itself select a legal license. Do not bundle
third-party model weights or private assets.
