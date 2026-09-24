import assert from 'node:assert/strict';
import test from 'node:test';
import { nearestWall } from '../apps/web/src/wallSelection';
import type { Wall } from '../packages/schema/project';

test('wall hit testing measures distance to finite segments with zoom-adjusted tolerance', () => {
  const wall: Wall = {
    id: 'wall',
    kind: 'wall',
    revision: 0,
    label: 'Wall',
    metadata: {},
    sourceRoomId: null,
    start: { x: 0, y: 0 },
    end: { x: 100, y: 0 },
    movement: true,
    sight: true,
  };
  assert.equal(nearestWall([wall], { x: 50, y: 7 }, 8), wall);
  assert.equal(nearestWall([wall], { x: 50, y: 7 }, 4), null);
  assert.equal(nearestWall([wall], { x: 110, y: 0 }, 8), null);
  assert.equal(nearestWall([wall], { x: 103, y: 3 }, 8), wall);
});
