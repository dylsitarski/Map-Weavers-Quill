import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import Ajv from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import { newProject } from '../apps/web/src/projectFiles';
import { type SceneHistory, sceneReducer } from '../apps/web/src/sceneHistory';
import {
  changeWallArt,
  defaultWallArt,
  validThickness,
  wallArtKey,
  wallArtRequest,
  wallArtSettings,
} from '../apps/web/src/wallArt';
import type { WallArtRequest } from '../packages/schema/geometry';
import type { Project } from '../packages/schema/project';

const fixture: Project = JSON.parse(
  readFileSync('fixtures/projects/two-rooms.json', 'utf8'),
);

test('wall art defaults to visible stone and ignores malformed settings', () => {
  assert.deepEqual(wallArtSettings({}), defaultWallArt);
  for (const value of [
    'stone',
    [],
    { visible: 'yes', material: 'stone' },
    { visible: true, material: 'glass' },
    { visible: true },
  ])
    assert.deepEqual(wallArtSettings({ [wallArtKey]: value }), defaultWallArt);
  assert.deepEqual(
    wallArtSettings({ [wallArtKey]: { visible: false, material: 'timber' } }),
    { visible: false, material: 'timber' },
  );
  assert.equal(newProject().map.style.wallThicknessPx, 10);
});

test('thickness limits match the server contract', () => {
  for (const value of [1, 10, 50]) assert.ok(validThickness(value));
  for (const value of [0, 0.5, 51, Number.NaN, Number.POSITIVE_INFINITY])
    assert.ok(!validThickness(value));
});

test('wall art changes are one undoable map-authoring edit preserving other data', () => {
  const project = newProject();
  const authoring = {
    style: { ...project.map.style, palette: 'ochre' },
    settings: { 'quill.background': { prompt: 'Ruins' } },
  };
  const material = changeWallArt(authoring, { material: 'plaster' });
  assert.deepEqual(material.settings, {
    'quill.background': { prompt: 'Ruins' },
    [wallArtKey]: { visible: true, material: 'plaster' },
  });
  assert.equal(material.style, authoring.style);
  const thicker = changeWallArt(material, { thickness: 24, visible: false });
  assert.equal(thicker.style.wallThicknessPx, 24);
  assert.equal(thicker.style.palette, 'ochre');
  assert.deepEqual(wallArtSettings(thicker.settings), {
    visible: false,
    material: 'plaster',
  });

  const before = { rooms: [], walls: [], doors: [], mapAuthoring: authoring };
  const history: SceneHistory = { past: [], present: before, future: [] };
  const changed = sceneReducer(history, {
    type: 'commit',
    before,
    scene: { ...before, mapAuthoring: thicker },
  });
  const undone = sceneReducer(changed, { type: 'undo' });
  assert.equal(undone.present.mapAuthoring, authoring);
  assert.deepEqual(sceneReducer(undone, { type: 'redo' }), changed);
});

test('render requests are order-independent and satisfy the generated schema', () => {
  const schema = JSON.parse(
    readFileSync('packages/schema/geometry.schema.json', 'utf8'),
  );
  const ajv = new Ajv({ strict: false });
  addFormats(ajv);
  const validate = ajv.compile<WallArtRequest>({
    $defs: schema.$defs,
    $ref: '#/$defs/WallArtRequest',
  });
  const request = wallArtRequest(fixture.rooms, fixture.doors, 10, 'stone');
  assert.ok(validate(request), JSON.stringify(validate.errors));
  assert.deepEqual(
    wallArtRequest([...fixture.rooms].reverse(), fixture.doors, 10, 'stone'),
    request,
  );
  assert.deepEqual(Object.keys(request.rooms[0]).sort(), ['id', 'polygon']);
  assert.equal(request.width, 2400);
  assert.equal(request.height, 1600);
  assert.ok(!validate({ ...request, thickness: 0 }));
  assert.ok(!validate({ ...request, material: 'glass' }));
});
