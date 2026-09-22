# ADR-0001: Foundation contract source and coordinate boundary

Status: Accepted for Milestone 0 foundation slice, 2026-09-22.

The owner's manifest establishes deterministic semantic geometry and a
React/Konva + FastAPI target architecture. This slice implements only the
Python contract foundation; it does not change that stack.

Pydantic models are the schema source. Generated JSON Schema is committed and
checked for drift. TypeScript types will be generated from that schema in the
next slice, not maintained independently. Schema 0.1.0 is an unreleased structural
subset (rooms, walls, doors, lights, layers). Unknown fields and non-finite values
are rejected. Entity revision is initial provenance. Topology, foreign keys,
metadata extensions, remaining entity types, and timestamps remain unfinished.

Native coordinates are bottom-left, y-up, CCW from +x. Continuous edge coordinates
use H-y; discrete pixel centers require a separate rasterizer. Screen clockwise
angles sharing +x zero use -angle modulo 360. Foundry field-specific offsets,
padding, and rotation zero axes must be researched and tested in Milestone 4.

Storage remains versioned JSON plus content-addressed assets as planned; neither
persistence nor Foundry conversion is implemented in this slice. The remaining
manifest ADRs will be split into individual records as their components land.
