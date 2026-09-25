# ADR-0019: Durable local generation jobs

Status: Implemented mock workflow increment; real-provider interruption and a job-history
recovery UI remain future work. Run one API process/worker against this data directory.

The editor creates a UUID before submitting POST /api/jobs/{id}/background or /room,
using the existing strict request contract and a 4 MiB JSON/local-origin guard. The
202 response and GET /api/jobs/{id} return GenerationJob: id, status (queued, running,
succeeded, failed, cancelled), optional BackgroundResult and safe user-facing error.
POST /api/jobs/{id}/cancel requests cancellation. Older synchronous generation endpoints
remain for compatibility; the editor now uses jobs exclusively.

SQLite stores the immutable request, target, state and completed proposal alongside
native snapshots/assets. A single worker consumes a bounded queue (16 queued/running
jobs). Duplicate ID plus identical request returns the existing job; reuse for another
request is a conflict. Queued-to-running and running-to-terminal transitions use SQL
conditional updates. Cancellation is idempotent; an unknown UUID creates a tombstone,
so cancellation can precede a delayed submit. A cancelled queued job never invokes the
provider; a cancelled running job cannot publish a result. Completion/cancellation race
is resolved by the first terminal transition. Already completed jobs remain completed.

The mock provider is synchronous and explicitly lacks remote cancellation. Its active
short computation may finish and create unreferenced assets after cancellation, but
its result is discarded. This is cancellation of job publication, not a claim that CPU
work or a future paid provider can be forcibly stopped. Actual provider cancellation
must be implemented with that adapter in Milestone 3. Asset/job garbage collection is
not implemented. Raw exceptions and filesystem details are not returned to the UI.

On startup, leftover queued/running jobs become failed with an interruption message;
completed and cancelled jobs remain queryable. Graceful shutdown marks unfinished jobs
failed and drains the short active mock computation. Jobs are not silently retried.
Browser polling displays queued/running states; Cancel, replacing a request, component
unmount and polling failure send cancellation using the already-known UUID. Client
sequence/abort guards discard late responses. Cancellation delivery during network
failure is best effort. A browser reload does not auto-resume a proposal; durable results
remain available through the job API. Existing stale-context and explicit acceptance
checks remain mandatory. Jobs never change the project or undo history by themselves.

Tests cover persisted success, idempotent submission, conflicting requests, cancellation
before submit, queued/running cancellation, late completion, failure, restart recovery,
API guards and browser cancellation/late responses. Room interiors no longer receive a
green fill; wall/selection/draft guides remain.
