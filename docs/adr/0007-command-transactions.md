# ADR-0007: Command transactions

Status: Accepted architecture; implementation begins in Milestone 1.

Document mutations enter through validated commands. One user action is one atomic
transaction with enough prior state for undo. Selection and viewport changes are
editor state rather than persistent geometry. Failed validation leaves the document
unchanged. Asset references, not mutable image bytes, participate in history.

Future language providers produce proposals only. Reference resolution, domain
validation, preview and approval precede the same transaction boundary. Generation
acceptance checks captured revisions before applying a command; stale results never
silently replace current content. No command executor is implemented in Milestone 0.
