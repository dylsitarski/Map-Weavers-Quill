import type { RasterLayer } from '../../../packages/schema/project';

export function orderedArtwork(layers: RasterLayer[]): RasterLayer[] {
  return [...layers].sort(
    (a, b) => a.zIndex - b.zIndex || a.id.localeCompare(b.id),
  );
}

export function reorderArtwork(
  layers: RasterLayer[],
  id: string,
  direction: 'up' | 'down',
): RasterLayer[] {
  const ordered = orderedArtwork(layers).filter((layer) => layer.zIndex > 0);
  const index = ordered.findIndex((layer) => layer.id === id);
  const target = index + (direction === 'up' ? 1 : -1);
  if (index < 0 || target < 0 || target >= ordered.length) return layers;
  [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
  const positions = new Map(ordered.map((layer, i) => [layer.id, i + 1]));
  return layers.map((layer) => {
    const zIndex = positions.get(layer.id) ?? layer.zIndex;
    return zIndex === layer.zIndex
      ? layer
      : { ...layer, zIndex, revision: layer.revision + 1 };
  });
}
