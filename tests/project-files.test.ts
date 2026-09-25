import assert from 'node:assert/strict';
import test from 'node:test';
import { newProject, projectFingerprint } from '../apps/web/src/projectFiles';
import { emptySceneHistory, sceneReducer } from '../apps/web/src/sceneHistory';

test('save comparison ignores serialization key order and saved revision but detects document edits', () => {
  const project = newProject();
  const reordered = Object.fromEntries(
    Object.entries(project).reverse(),
  ) as typeof project;
  assert.equal(
    projectFingerprint(project),
    projectFingerprint({ ...reordered, revision: 3 }),
  );
  assert.notEqual(
    projectFingerprint(project),
    projectFingerprint({ ...project, name: 'Changed' }),
  );
  assert.notEqual(
    projectFingerprint(project),
    projectFingerprint({
      ...project,
      map: { ...project.map, grid: { ...project.map.grid, snap: false } },
    }),
  );
});
test('opening replaces history so undo cannot restore the previous project', () => {
  const old = { rooms: [], doors: [], walls: [] };
  const loaded = { rooms: [], doors: [], walls: [] };
  const state = sceneReducer(
    { past: [old], present: old, future: [old] },
    { type: 'load', scene: loaded },
  );
  assert.equal(state.present, loaded);
  assert.deepEqual(state.past, []);
  assert.equal(sceneReducer(state, { type: 'undo' }), state);
  assert.equal(emptySceneHistory.past.length, 0);
});
