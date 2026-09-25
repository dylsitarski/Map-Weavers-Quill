# ADR-0020: Explicit preview recovery after reload

Status: Implemented for the local mock workflow.

Store one small browser-local recovery record per project/target (background or room
UUID): durable job ID, SHA-256 of the canonical project fingerprint, prompt and seed.
No full project or image is stored in browser storage. A storage failure is reported;
generation can still work but recovery is unavailable. Records share the normal browser
origin, so use the same localhost/127.0.0.1 address and browser profile when recovering.

After reload, reopen the saved project, select Map or the same room, open AI and choose
Recover preview. Fetch/poll the existing job; never resubmit or implicitly accept it.
Compare the current document fingerprint before retrieval. Saved revision and derived
wall serialization do not affect the canonical fingerprint; project identity, geometry,
layer settings, prompts and other document content do. Changed or lost unsaved work
blocks recovery until the matching document is restored or the record is discarded.
Unapplied field drafts are not recovered. Results remain subject to the normal in-session
history/selection stale guards and explicit Accept/Reject controls.

Acceptance, rejection and explicit discard remove the matching recovery record.
Regeneration cancels/replaces the previous target job. Compare job IDs before deleting
records so an old panel cannot remove a newer record. Selection changes/unmount/reload
abort local polling without cancelling server jobs, making recovery possible. Network
polling failures retain the record for retry. Explicit Cancel still requests server
cancellation. Restart-interrupted jobs report the durable failure; discard/regenerate
rather than silently rerunning them. Cross-tab coordination and a general job-history
browser are not implemented; the UI offers the latest record for each target only.

Regression tests cover fingerprints, storage validation, deletion identity, background
and room recovery with submission blocked, normal acceptance/undo, and refusal after a
changed saved snapshot. Existing job tests cover interrupted/failed/cancelled outcomes.
