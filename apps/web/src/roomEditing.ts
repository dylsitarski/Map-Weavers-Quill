import type { Point, Room } from '../../../packages/schema/project';

// Native-coordinate hit test includes edges. Last drawn room wins overlaps.
export function containsPoint(polygon: Point[], point: Point): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const a = polygon[j],
      b = polygon[i];
    const cross = (point.x - a.x) * (b.y - a.y) - (point.y - a.y) * (b.x - a.x);
    if (
      Math.abs(cross) < 1e-7 &&
      point.x >= Math.min(a.x, b.x) &&
      point.x <= Math.max(a.x, b.x) &&
      point.y >= Math.min(a.y, b.y) &&
      point.y <= Math.max(a.y, b.y)
    )
      return true;
    if (
      a.y > point.y !== b.y > point.y &&
      point.x < ((b.x - a.x) * (point.y - a.y)) / (b.y - a.y) + a.x
    )
      inside = !inside;
  }
  return inside;
}
export type RoomDrag = { room: Room; origin: Point; vertex: number | null };
export function dragPolygon(
  drag: RoomDrag,
  point: Point,
  snap: boolean,
): Point[] {
  const quantize = (value: number) =>
    snap ? Math.round(value / 50) * 50 : value;
  if (drag.vertex !== null)
    return drag.room.polygon.map((p, i) =>
      i === drag.vertex ? { x: quantize(point.x), y: quantize(point.y) } : p,
    );
  const dx = quantize(point.x - drag.origin.x),
    dy = quantize(point.y - drag.origin.y);
  return drag.room.polygon.map((p) => ({ x: p.x + dx, y: p.y + dy }));
}
