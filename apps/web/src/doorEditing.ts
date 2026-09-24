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
export function wallPosition(
  wall: Wall,
  point: Point,
  snap: boolean,
  width = 0,
): number {
  const dx = wall.end.x - wall.start.x,
    dy = wall.end.y - wall.start.y;
  const length = Math.hypot(dx, dy);
  const projected =
    ((point.x - wall.start.x) * dx + (point.y - wall.start.y) * dy) /
    length ** 2;
  const half = width / (2 * length);
  if (!snap)
    return half <= 0.5
      ? Math.max(half, Math.min(1 - half, projected))
      : projected;
  // Anchor to the map grid, not a potentially off-grid or split wall endpoint.
  // On diagonals use the dominant axis, keeping the result exactly on the wall.
  const axisStart = Math.abs(dx) >= Math.abs(dy) ? wall.start.x : wall.start.y;
  const axisDelta = Math.abs(dx) >= Math.abs(dy) ? dx : dy;
  const coordinate = axisStart + projected * axisDelta;
  let cell = Math.round((coordinate - 25) / 50);
  const ends = [
    axisStart + half * axisDelta,
    axisStart + (1 - half) * axisDelta,
  ];
  const low = Math.ceil((Math.min(...ends) - 25) / 50 - 1e-10);
  const high = Math.floor((Math.max(...ends) - 25) / 50 + 1e-10);
  if (half <= 0.5 && low <= high) cell = Math.max(low, Math.min(high, cell));
  return (cell * 50 + 25 - axisStart) / axisDelta;
}
export type DoorDrag = { door: Door; wall: Wall; origin: Point };
export function slideDoor(drag: DoorDrag, point: Point, snap: boolean): Door {
  const { door, wall, origin } = drag;
  const center = {
    x:
      wall.start.x +
      door.position * (wall.end.x - wall.start.x) +
      point.x -
      origin.x,
    y:
      wall.start.y +
      door.position * (wall.end.y - wall.start.y) +
      point.y -
      origin.y,
  };
  return { ...door, position: wallPosition(wall, center, snap, door.width) };
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
