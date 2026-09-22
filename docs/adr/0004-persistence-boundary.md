# ADR-0004: Native persistence boundary

Status: Accepted architecture; persistence implementation deferred to Milestone 1.

Versioned JSON holds native scene geometry. Immutable asset bytes are addressed
by SHA-256. SQLite will track local metadata; portable archives will bundle the
document and referenced assets. Persist no absolute machine paths or secrets.

The current mock's in-memory asset dictionary demonstrates hashing only. It is
not a persistence layer and must not be mistaken for one. Atomic snapshots,
migrations and crash recovery need dedicated implementation and tests.
