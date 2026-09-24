import assert from 'node:assert/strict';
import test from 'node:test';
import { containsPoint, dragPolygon } from '../apps/web/src/roomEditing';
import {
  emptyHistory,
  historyReducer,
  rectangle,
} from '../apps/web/src/viewport';
import type { Room } from '../packages/schema/project';

const room: Room = {
  id: 'test-room',
  kind: 'room',
  revision: 0,
  label: 'Room',
  polygon: rectangle({ x: 13, y: 27 }, { x: 113, y: 127 }),
  prompt: '',
  metadata: {},
  styleOverrides: {},
  renderLayerId: null,
};

test('concave hit testing includes boundaries and excludes the notch', () => {
  const polygon = [
    { x: 0, y: 0 },
    { x: 100, y: 0 },
    { x: 100, y: 40 },
    { x: 40, y: 40 },
    { x: 40, y: 100 },
    { x: 0, y: 100 },
  ];
  assert.equal(containsPoint(polygon, { x: 20, y: 90 }), true);
  assert.equal(containsPoint(polygon, { x: 70, y: 70 }), false);
  assert.equal(containsPoint(polygon, { x: 40, y: 60 }), true);
});
test('moving snaps an off-grid anchor to the actual grid without deforming the room', () => {
  const moved = dragPolygon(
    { room, origin: { x: 25, y: 40 }, vertex: null },
    { x: 85, y: 130 },
    true,
  );
  assert.deepEqual(
    moved,
    room.polygon.map((p) => ({ x: p.x + 37, y: p.y + 73 })),
  );
  const reshaped = dragPolygon(
    { room, origin: room.polygon[0], vertex: 0 },
    { x: 42, y: 65 },
    true,
  );
  assert.deepEqual(reshaped[0], { x: 50, y: 50 });
  assert.deepEqual(reshaped.slice(1), room.polygon.slice(1));
  assert.deepEqual(room.polygon[0], { x: 13, y: 27 });
});

test('an irregular room keeps its shape and fixed nearest-grab anchor when snapping resumes', () => {
  const irregular: Room = {
    ...room,
    polygon: [
      { x: 13, y: 27 },
      { x: 126, y: 32 },
      { x: 93, y: 147 },
    ],
  };
  const origin = { x: 100, y: 50 };
  const free = dragPolygon(
    { room: irregular, origin, vertex: null },
    { x: 107, y: 59 },
    false,
  );
  const moved = { ...irregular, polygon: free as Room['polygon'] };
  const points = dragPolygon(
    { room: moved, origin: { x: 107, y: 59 }, vertex: null },
    { x: 190, y: 172 },
    true,
  );
  // Vertex 2 was nearest the initial grab and stays the anchor even as the pointer travels.
  assert.equal(points[1].x % 50, 0);
  assert.equal(points[1].y % 50, 0);
  for (let i = 0; i < points.length; i++) {
    assert.equal(points[i].x - points[1].x, free[i].x - free[1].x);
    assert.equal(points[i].y - points[1].y, free[i].y - free[1].y);
  }
});

test('reordering changes drawing order only and is undoable', () => {
  const other = { ...room, id: 'second' };
  let state = historyReducer(
    historyReducer(emptyHistory, { type: 'add', room }),
    { type: 'add', room: other },
  );
  const before = state;
  state = historyReducer(state, {
    type: 'reorder',
    id: room.id,
    direction: 'up',
  });
  assert.deepEqual(state.present, [other, room]);
  assert.equal(state.present[1], room);
  assert.equal(
    historyReducer(state, { type: 'reorder', id: room.id, direction: 'up' }),
    state,
  );
  state = historyReducer(state, { type: 'undo' });
  assert.deepEqual(state.present, before.present);
  state = historyReducer(state, { type: 'redo' });
  assert.deepEqual(state.present, [other, room]);
});
test('mixed edit/delete history restores full room data and rejects stale edits', () => {
  let state = historyReducer(emptyHistory, { type: 'add', room });
  const initial = state.present;
  for (let i = 0; i < 50; i++) {
    const before = state.present[0];
    state = historyReducer(state, {
      type: 'update',
      before,
      room: {
        ...before,
        label: `Room ${i}`,
        prompt: `Prompt ${i}`,
        polygon: rectangle({ x: i, y: 0 }, { x: i + 100, y: 100 }),
      },
    });
  }
  const edited = state.present;
  assert.equal(edited[0].revision, 50);
  assert.equal(
    historyReducer(state, {
      type: 'update',
      before: room,
      room: { ...room, label: 'stale' },
    }),
    state,
  );
  state = historyReducer(state, { type: 'delete', id: room.id });
  assert.deepEqual(state.present, []);
  state = historyReducer(state, { type: 'undo' });
  assert.deepEqual(state.present, edited);
  for (let i = 0; i < 50; i++) state = historyReducer(state, { type: 'undo' });
  assert.deepEqual(state.present, initial);
  for (let i = 0; i < 51; i++) state = historyReducer(state, { type: 'redo' });
  assert.deepEqual(state.present, []);
});
