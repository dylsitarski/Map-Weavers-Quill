import Ajv2020 from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import type { DoorResult } from '../../../packages/schema/geometry';
import schema from '../../../packages/schema/geometry.schema.json';
import type { Door, Point, Room, Wall } from '../../../packages/schema/project';
import { mapSize } from './viewport';

const ajv = new Ajv2020({ strict: false });
addFormats(ajv);
const validate = ajv.compile<DoorResult>({
  $defs: schema.$defs,
  $ref: '#/$defs/DoorResult',
});
export async function reconcileDoors(
  before: Room[],
  rooms: Room[],
  doors: Door[],
): Promise<DoorResult> {
  const boundaries = (values: Room[]) =>
    values.map(({ id, polygon }) => ({ id, polygon }));
  const response = await fetch('/api/geometry/doors', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...mapSize,
      beforeRooms: boundaries(before),
      rooms: boundaries(rooms),
      doors,
    }),
    signal: AbortSignal.timeout(10000),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok)
    throw new Error(
      typeof data?.detail === 'string'
        ? data.detail
        : 'Could not validate door attachments. Check the local server and retry.',
    );
  if (!validate(data))
    throw new Error('The server returned invalid door data.');
  return data;
}
export function wallPosition(wall: Wall, point: Point, snap: boolean): number {
  const dx = wall.end.x - wall.start.x,
    dy = wall.end.y - wall.start.y;
  const length = Math.hypot(dx, dy);
  let distance =
    ((point.x - wall.start.x) * dx + (point.y - wall.start.y) * dy) / length;
  if (snap) distance = Math.round(distance / 50) * 50;
  return Math.max(0, Math.min(1, distance / length));
}
export function doorSegment(door: Door, wall: Wall): [Point, Point] {
  const dx = wall.end.x - wall.start.x,
    dy = wall.end.y - wall.start.y;
  const half = door.width / (2 * Math.hypot(dx, dy));
  return [door.position - half, door.position + half].map((t) => ({
    x: wall.start.x + t * dx,
    y: wall.start.y + t * dy,
  })) as [Point, Point];
}
