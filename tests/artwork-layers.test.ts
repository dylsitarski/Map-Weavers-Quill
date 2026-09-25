import assert from 'node:assert/strict';
import test from 'node:test';
import {
  moveArtwork,
  orderedArtwork,
  reorderArtwork,
} from '../apps/web/src/artworkLayers';
import { type Scene, sceneReducer } from '../apps/web/src/sceneHistory';
import type { RasterLayer } from '../packages/schema/project';

function layer(id: string, zIndex: number): RasterLayer {
  return {
    id,
    zIndex,
    kind: 'raster',
    revision: 0,
    label: id,
    metadata: {},
    assetHash: 'a'.repeat(64),
    bounds: { origin: { x: 0, y: 0 }, width: 1200, height: 800 },
    rotation: 0,
    opacity: 0.5,
    visible: false,
    blendMode: 'normal',
  };
}
test('artwork reordering resolves tied ranks, pins background and preserves content and geometry through undo/redo', () => {
  const layers = [
    layer('background', 0),
    layer('a', 4),
    layer('b', 4),
    layer('c', 9),
  ];
  const before: Scene = { rooms: [], walls: [], doors: [], layers };
  const next = reorderArtwork(layers, 'a', 'up');
  assert.deepEqual(
    orderedArtwork(next).map((item) => item.id),
    ['background', 'b', 'a', 'c'],
  );
  assert.equal(next[0], layers[0]);
  next.forEach((item, i) => {
    assert.deepEqual(
      { ...item, zIndex: layers[i].zIndex, revision: 0 },
      layers[i],
    );
  });
  const changed = sceneReducer(
    { past: [], present: before, future: [] },
    { type: 'commit', before, scene: { ...before, layers: next } },
  );
  assert.equal(changed.present.rooms, before.rooms);
  assert.equal(changed.present.walls, before.walls);
  assert.equal(changed.present.doors, before.doors);
  const undone = sceneReducer(changed, { type: 'undo' });
  assert.equal(undone.present, before);
  assert.deepEqual(sceneReducer(undone, { type: 'redo' }), changed);
  assert.equal(reorderArtwork(layers, 'background', 'up'), layers);
  assert.equal(reorderArtwork(layers, 'a', 'down'), layers);
  assert.equal(reorderArtwork(layers, 'c', 'up'), layers);
  assert.equal(reorderArtwork(layers, 'missing', 'up'), layers);
});

test('drag reordering moves across multiple rows and cannot move the background', () => {
  const layers = [
    layer('background', 0),
    layer('a', 1),
    layer('b', 2),
    layer('c', 3),
  ];
  assert.deepEqual(
    orderedArtwork(moveArtwork(layers, 'a', 'c')).map((item) => item.id),
    ['background', 'b', 'c', 'a'],
  );
  assert.deepEqual(
    orderedArtwork(moveArtwork(layers, 'c', 'a')).map((item) => item.id),
    ['background', 'c', 'a', 'b'],
  );
  assert.equal(moveArtwork(layers, 'background', 'c'), layers);
  assert.equal(moveArtwork(layers, 'c', 'background'), layers);
  assert.equal(moveArtwork(layers, 'a', 'a'), layers);
});
