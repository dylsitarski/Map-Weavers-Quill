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
// Choose once from the original gesture geometry; never switch anchors mid-drag.
export function moveAnchorIndex(drag: RoomDrag): number {
  let nearest = 0;
  drag.room.polygon.forEach((p, i) => {
    const current = drag.room.polygon[nearest];
    if (
      Math.hypot(p.x - drag.origin.x, p.y - drag.origin.y) <
      Math.hypot(current.x - drag.origin.x, current.y - drag.origin.y)
    )
      nearest = i;
  });
  return nearest;
}
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
  const anchor = drag.room.polygon[moveAnchorIndex(drag)];
  const dx = quantize(anchor.x + point.x - drag.origin.x) - anchor.x,
    dy = quantize(anchor.y + point.y - drag.origin.y) - anchor.y;
  return drag.room.polygon.map((p) => ({ x: p.x + dx, y: p.y + dy }));
}
