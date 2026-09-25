# ADR-0004: Native persistence boundary

Status: Native JSON and SQLite snapshots implemented in ADR-0015; asset archives remain planned.

Versioned JSON holds native scene geometry. Immutable asset bytes are addressed
by SHA-256. SQLite will track local metadata; portable archives will bundle the
document and referenced assets. Persist no absolute machine paths or secrets.

The mock provider keeps request-local assets in memory. ADR-0016 now stores generated
background PNGs persistently in SQLite by SHA-256; the dictionary is not the durable store. Atomic snapshots and interruption recovery are implemented in ADR-0015. Migration
execution, portable asset archives and a recovery UI remain future work.
