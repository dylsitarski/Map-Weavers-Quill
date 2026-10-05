# Agent instructions

Read PROJECT_MANIFEST.md and relevant docs/adr records before changing contracts.
Keep native coordinates bottom-left, +x right, +y up, angles counter-clockwise
from +x. Never persist screen coordinates as native geometry.

Run `make test` before committing. Regenerate JSON Schema with `make schema`
when models change, then inspect the diff. Do not edit generated schema manually.
Keep milestone status honest in README.md and PROJECT_MANIFEST.md §22. Do not add
credentials, model weights, real user maps, or paid API calls to tests. Preserve
unrelated changes. Contract changes require an ADR and regression tests.

Report tests run, limitations, and the next implementation task at handoff.

Documentation map: README.md describes current behavior only (no change logs);
docs/HISTORY.md records verification evidence and trial results; docs/adr/README.md
indexes ADRs with current status; docs/INTERFACE.md holds interaction rules;
docs/COMFYUI.md covers the local SDXL provider. When behavior changes, update the
current-state docs in place and append history to docs/HISTORY.md. When a later ADR
changes an earlier decision, add a dated update line under the earlier ADR's status.
