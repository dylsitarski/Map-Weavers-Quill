# Agent instructions

Read PROJECT_MANIFEST.md and relevant docs/adr records before changing contracts.
Keep native coordinates bottom-left, +x right, +y up, angles counter-clockwise
from +x. Never persist screen coordinates as native geometry.

Run `make test` before committing. Regenerate JSON Schema with `make schema`
when models change, then inspect the diff. Do not edit generated schema manually.
Keep milestone status honest in README.md and PROJECT_MANIFEST.md. Do not add
credentials, model weights, real user maps, or paid API calls to tests. Preserve
unrelated changes. Contract changes require an ADR and regression tests.

Report tests run, limitations, and the next implementation task at handoff.
