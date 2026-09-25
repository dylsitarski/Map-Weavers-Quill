# Milestone 2 acceptance review

The core mock raster workflow is implemented. The final browser recovery checks are
part of Ubuntu CI; real AI image quality and Windows 11 remain unverified.

| Exit criterion | Evidence |
| --- | --- |
| Room A cannot change pixels outside its mask | test_room_images.py checks exact pixels, concavity/orientation and a deliberately noncompliant provider |
| Reject leaves the document unchanged | backgrounds.spec.ts and room-images.spec.ts exercise preview/reject and history |
| Accepted output supports undo and reload | background/room browser tests and persisted asset/binding tests |
| Layer order survives undo/save/export without geometry changes | artwork-layers.test.ts, room-images.spec.ts, test_exports.py and exports.spec.ts |
| Stale geometry cannot auto-apply | in-session stale-preview tests and recovery.spec.ts mismatch refusal |
| Durable jobs and cancellation | test_jobs.py covers success, duplicate IDs, cancellation races, failure and restart recovery |
| Recover an unaccepted preview after reload | recovery.spec.ts covers background and room retrieval without regeneration |

Limits: 480 × 320 mock rasters, one API worker per data directory, synchronous mock
computation may finish after cancellation, no automatic unsaved-document restoration,
no garbage collection/general job-history UI, and no real provider. Per-room prompts
are editable. A dedicated style-override inspector is not yet implemented; styleOverrides
remain preserved schema data. This outstanding planned task keeps the full milestone
open even though the listed core raster exit criteria have test coverage.

Next implementation task: define and expose the minimal provider-neutral room style
controls, with applied changes captured in generation inputs/provenance, before moving
to the first real provider. Do not label the mock output as rendered fantasy artwork.
