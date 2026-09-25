# Milestone 2 acceptance review

The Milestone 2 local mock raster workflow is implemented. Recovery and style checks are
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
| Room prompt and style inspector | test_room_images.py and room-images.spec.ts cover inheritance, prompt/provenance, undo, stale results and persistence |

Limits: 480 × 320 mock rasters, one API worker per data directory, synchronous mock
computation may finish after cancellation, no automatic unsaved-document restoration,
no garbage collection/general job-history UI, and no real provider. Room environment,
render style and palette inherit map defaults until overridden (ADR-0021).

Next implementation task: Milestone 3's first real-provider integration. Confirm the
provider/model, local runtime and available hardware before choosing its deployment;
then extend health/configuration and test one room through the existing safe workflow.
Map-level style editing and provider-specific prompt tuning remain in that milestone.
