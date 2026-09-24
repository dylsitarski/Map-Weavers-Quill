import assert from 'node:assert/strict';
import test from 'node:test';
import {
  doorSegment,
  slideDoor,
  wallPosition,
} from '../apps/web/src/doorEditing';
import type { Scene } from '../apps/web/src/sceneHistory';
import { emptySceneHistory, sceneReducer } from '../apps/web/src/sceneHistory';
import fixture from '../fixtures/projects/two-rooms.json';
import type { Door, Wall } from '../packages/schema/project';

const wall: Wall = {
  id: 'wall',
  kind: 'wall',
  revision: 0,
  label: 'Wall',
  metadata: {},
  start: { x: 13, y: 27 },
  end: { x: 313, y: 427 },
  movement: true,
  sight: true,
  sourceRoomId: null,
};
const door: Door = {
  id: 'door',
  kind: 'door',
  revision: 0,
  label: 'Door',
  metadata: {},
  wallId: wall.id,
  position: 0.5,
  width: 50,
  state: 'closed',
  secret: false,
  doorType: 'door',
};
test('door projection and map-cell midpoint snapping work on diagonal off-grid walls', () => {
  assert.equal(wallPosition(wall, { x: 85, y: 123 }, true), 0.245);
  assert.equal(wallPosition(wall, { x: 85, y: 123 }, false), 0.24);
  const [a, b] = doorSegment(door, wall);
  assert.ok(Math.abs(Math.hypot(b.x - a.x, b.y - a.y) - 50) < 1e-10);
  assert.equal((a.x + b.x) / 2, 163);
  assert.equal((a.y + b.y) / 2, 227);
});
test('50 atomic room/wall/door changes undo and redo without dangling attachments', () => {
  let history = emptySceneHistory;
  const snapshots: Scene[] = [history.present];
  for (let i = 0; i < 50; i++) {
    const id = `wall-${i}`;
    const scene: Scene = {
      rooms: fixture.rooms as Scene['rooms'],
      walls: [{ ...wall, id }],
      doors: [{ ...door, wallId: id, revision: i }],
    };
    history = sceneReducer(history, {
      type: 'commit',
      before: history.present,
      scene,
    });
    snapshots.push(history.present);
  }
  const stale = sceneReducer(history, {
    type: 'commit',
    before: snapshots[1],
    scene: snapshots[2],
  });
  assert.equal(stale, history);
  for (let i = 49; i >= 0; i--) {
    history = sceneReducer(history, { type: 'undo' });
    assert.deepEqual(history.present, snapshots[i]);
  }
  for (let i = 1; i <= 50; i++) {
    history = sceneReducer(history, { type: 'redo' });
    assert.deepEqual(history.present, snapshots[i]);
    assert.equal(history.present.doors[0].wallId, history.present.walls[0].id);
  }
});

test('midpoints remain grid anchored and a full-cell door can meet a wall endpoint', () => {
  const vertical = {
    ...wall,
    start: { x: 100, y: 0 },
    end: { x: 100, y: 200 },
  };
  assert.equal(wallPosition(vertical, { x: 100, y: 0 }, true, 50), 0.125);
  const end = doorSegment({ ...door, position: 0.125 }, vertical);
  assert.deepEqual(end, [
    { x: 100, y: 0 },
    { x: 100, y: 50 },
  ]);
  const split = { ...vertical, start: { x: 100, y: 13 } };
  assert.equal(13 + wallPosition(split, { x: 100, y: 76 }, true, 50) * 187, 75);
});
test('sliding preserves grab offset, projects onto parent and clamps the full width', () => {
  const vertical = {
    ...wall,
    start: { x: 100, y: 0 },
    end: { x: 100, y: 200 },
  };
  const initial = { ...door, position: 0.375 };
  const drag = { door: initial, wall: vertical, origin: { x: 100, y: 90 } };
  assert.equal(slideDoor(drag, { x: 400, y: 140 }, true).position, 0.625);
  assert.equal(slideDoor(drag, { x: 400, y: 100 }, false).position, 0.425);
  assert.equal(slideDoor(drag, { x: 100, y: -500 }, true).position, 0.125);
  assert.equal(slideDoor(drag, { x: 100, y: 500 }, false).position, 0.875);
  assert.equal(initial.position, 0.375);
});
