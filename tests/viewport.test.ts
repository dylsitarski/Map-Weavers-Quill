import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  emptyHistory,
  historyReducer,
  rectangle,
  screenToWorld,
  worldToScreen,
  zoomAt,
} from '../apps/web/src/viewport';
import type { Room } from '../packages/schema/project';

test('world corners and arbitrary points round trip through zoom and pan', () => {
  for (const scale of [0.1, 0.8, 4]) {
    const view = { x: 41, y: -73, scale };
    for (const point of [
      { x: 0, y: 0 },
      { x: 1200, y: 800 },
      { x: 0, y: 800 },
      { x: 1200, y: 0 },
      { x: 123.4, y: 567.8 },
    ]) {
      const result = screenToWorld(worldToScreen(point, view), view);
      assert.ok(
        Math.abs(result.x - point.x) < 1e-9 &&
          Math.abs(result.y - point.y) < 1e-9,
      );
    }
    assert.equal(worldToScreen({ x: 0, y: 800 }, view).y, view.y);
    const pointer = { x: 331, y: 241 };
    const before = screenToWorld(pointer, view);
    const after = screenToWorld(pointer, zoomAt(view, pointer, 1.1));
    assert.ok(
      Math.abs(before.x - after.x) < 1e-9 &&
        Math.abs(before.y - after.y) < 1e-9,
    );
  }
});

test('rectangle gesture direction does not change native geometry', () => {
  assert.deepEqual(
    rectangle({ x: 100, y: 200 }, { x: 20, y: 10 }),
    rectangle({ x: 20, y: 10 }, { x: 100, y: 200 }),
  );
});

test('50 add commands undo and redo without losing IDs or geometry', () => {
  let state = emptyHistory;
  for (let i = 0; i < 50; i++) {
    const room: Room = {
      id: `room-${i}`,
      kind: 'room',
      revision: 0,
      label: `Room ${i}`,
      metadata: {},
      polygon: rectangle({ x: i, y: i }, { x: i + 10, y: i + 10 }),
      prompt: '',
      styleOverrides: {},
      renderLayerId: null,
    };
    state = historyReducer(state, { type: 'add', room });
  }
  const expected = state.present;
  for (let i = 0; i < 50; i++) state = historyReducer(state, { type: 'undo' });
  assert.deepEqual(state.present, []);
  for (let i = 0; i < 50; i++) state = historyReducer(state, { type: 'redo' });
  assert.deepEqual(state.present, expected);
  state = historyReducer(state, { type: 'undo' });
  state = historyReducer(state, { type: 'add', room: expected[0] });
  assert.equal(state.future.length, 0);
});
