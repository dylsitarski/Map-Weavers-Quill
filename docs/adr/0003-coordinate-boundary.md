# ADR-0003: World coordinates and target transforms

Status: Accepted, following the owner's explicit coordinate decision.

Persist bottom-left, +x-right, +y-up coordinates and counter-clockwise angles
from +x. Renderers own conversion to screen/image space. One world unit currently
maps to one output pixel at scale one. View zoom and device scale never alter
persisted geometry. Continuous points use H-y and rectangles use H-y-height.

The Python transform tests cover corners, round trips, winding and angles.
Discrete pixel rasterization and Foundry-specific offsets remain later work.
