import type { Point, Wall } from '../../../packages/schema/project';

export function nearestWall(
  walls: Wall[],
  point: Point,
  tolerance: number,
): Wall | null {
  let selected: Wall | null = null;
  let distance = tolerance;
  for (const wall of walls) {
    const dx = wall.end.x - wall.start.x,
      dy = wall.end.y - wall.start.y;
    const lengthSquared = dx * dx + dy * dy;
    if (!lengthSquared) continue;
    const t = Math.max(
      0,
      Math.min(
        1,
        ((point.x - wall.start.x) * dx + (point.y - wall.start.y) * dy) /
          lengthSquared,
      ),
    );
    const next = Math.hypot(
      point.x - wall.start.x - t * dx,
      point.y - wall.start.y - t * dy,
    );
    if (next < distance) {
      distance = next;
      selected = wall;
    }
  }
  return selected;
}
