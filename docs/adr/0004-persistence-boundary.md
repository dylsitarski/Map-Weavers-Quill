# ADR-0004: Native persistence boundary

Status: Native JSON and SQLite snapshots implemented in ADR-0015; asset archives remain planned.

Versioned JSON holds native scene geometry. Immutable asset bytes are addressed
by SHA-256. SQLite will track local metadata; portable archives will bundle the
document and referenced assets. Persist no absolute machine paths or secrets.

The current mock's in-memory asset dictionary demonstrates hashing only. It is
not a persistence layer and must not be mistaken for one. Atomic snapshots and interruption recovery are implemented in ADR-0015. Migration
execution, portable asset archives and a recovery UI remain future work.
