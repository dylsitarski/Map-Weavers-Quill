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
nvm install
nvm use
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

Node 24 is declared in `.nvmrc` and enforced by npm and `make doctor`. The nvm
commands assume nvm is installed; another Node manager may also select Node 24.
For real-browser checks, run `npx playwright install --with-deps chromium`, then
`make browser`. On Linux, installing browser system dependencies may require sudo.
Browser tests cover loading, API connectivity through Vite, and failure messaging.
They start and stop the same launcher as `make dev`, with no external AI calls.

The committed Python lockfile pins the full development dependency closure.
GitHub Actions runs `make check`, `make browser`, and `make audit` on Ubuntu for pushes and PRs.
Tests use synthetic data, no credentials, paid APIs, or GPUs.

## Next Milestone 0 work

- Resolve the pending browser CI run and verify clean-install checks against the latest commit.
- Confirm all Milestone 0 exit criteria before starting the editor.

Provider contracts now include version tags, capability vocabulary, reference
images, negative prompts, neutral parameters, namespaced extensions and normalized
errors. The mock rejects unsupported options and cancellation explicitly. All
seven initial architecture decisions are recorded. Geometry topology and
cross-entity relationship validation belong to Milestone 1, before persistence.

The schema now covers every planned entity category, including namespaced
metadata, object transforms, sounds, regions, and generation provenance. The
all-entities fixture is checked across Python and TypeScript. This unreleased
schema was expanded in place; old synthetic fixtures were updated together.
The current schema validates structural data, not polygon simplicity or door
attachment geometry. These limitations are explicit; do not use it as a complete
editor validation boundary yet.

## Distribution

Public, free distribution is intended. A software license has not been selected;
this repository does not yet grant a general redistribution license. The owner's
noncommercial release intent does not itself select a legal license. Do not bundle
third-party model weights or private assets.
