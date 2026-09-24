import assert from 'node:assert/strict';
import test from 'node:test';
import { initialTools, toolsReducer } from '../apps/web/src/editorTools';

test('whole-map context suspends room tools and restores their remembered choice', () => {
  let state = toolsReducer(initialTools, { type: 'scope', scope: 'Room' });
  state = toolsReducer(state, { type: 'tool', tool: 'polygon' });
  state = toolsReducer(state, { type: 'scope', scope: 'Map' });
  assert.equal(state.scope, 'Map');
  assert.equal(state.tool, 'pan');
  assert.deepEqual(toolsReducer(state, { type: 'tool', tool: 'room' }), state);
  state = toolsReducer(state, { type: 'scope', scope: 'Map' });
  assert.equal(state.scope, null);
  state = toolsReducer(state, { type: 'scope', scope: 'Room' });
  assert.equal(state.tool, 'polygon');
});

test('scope closure suspends tools and reopening restores the remembered choice', () => {
  assert.equal(initialTools.tool, 'pan');
  let state = toolsReducer(initialTools, { type: 'scope', scope: 'Room' });
  assert.equal(state.tool, 'pan');
  state = toolsReducer(state, { type: 'tool', tool: 'room' });
  state = toolsReducer(state, { type: 'scope', scope: 'Room' });
  assert.equal(state.scope, null);
  assert.equal(state.tool, 'pan');
  state = toolsReducer(state, { type: 'scope', scope: 'Room' });
  assert.equal(state.tool, 'room');
  state = toolsReducer(state, { type: 'close' });
  state = toolsReducer(state, { type: 'scope', scope: 'Room' });
  assert.equal(state.tool, 'room');
  state = toolsReducer(state, { type: 'tool', tool: 'room' });
  assert.equal(state.tool, 'pan');
  state = toolsReducer(state, { type: 'close' });
  state = toolsReducer(state, { type: 'scope', scope: 'Room' });
  assert.equal(state.tool, 'pan');
});
