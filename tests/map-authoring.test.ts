import assert from 'node:assert/strict';
import test from 'node:test';
import { backgroundPrompt } from '../apps/web/src/mapAuthoring';
import { newProject } from '../apps/web/src/projectFiles';
import { type SceneHistory, sceneReducer } from '../apps/web/src/sceneHistory';

test('map authoring undo survives saved project replacement and preserves settings', () => {
  const project = newProject();
  const before = {
    rooms: [],
    walls: [],
    doors: [],
    mapAuthoring: { style: project.map.style, settings: project.settings },
  };
  const settings = {
    'quill.background': { prompt: 'Ancient ruins' },
    'other.plugin': true,
  };
  const style = { ...project.map.style, palette: 'ochre' };
  const history: SceneHistory = { past: [], present: before, future: [] };
  const changed = sceneReducer(history, {
    type: 'commit',
    before,
    scene: { ...before, mapAuthoring: { settings, style } },
  });
  project.settings = settings;
  project.map.style = style;
  assert.equal(backgroundPrompt(project), 'Ancient ruins');
  const undone = sceneReducer(changed, { type: 'undo' });
  assert.equal(undone.present.mapAuthoring?.style.palette, '');
  assert.deepEqual(undone.present.mapAuthoring?.settings, {});
  assert.deepEqual(sceneReducer(undone, { type: 'redo' }), changed);
  project.settings = { 'quill.background': { prompt: '' } };
  assert.equal(backgroundPrompt(project), '');
});
