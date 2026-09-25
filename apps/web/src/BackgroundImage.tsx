import { useEffect, useState } from 'react';
import { Image as CanvasImage } from 'react-konva';
import type { RasterLayer } from '../../../packages/schema/project';
import type { View } from './viewport';
export function BackgroundImage({
  layer,
  view,
  onError,
}: {
  layer: RasterLayer;
  view: View;
  onError: (message: string) => void;
}) {
  const [loaded, setLoaded] = useState<{
    hash: string;
    image: HTMLImageElement;
  } | null>(null);
  useEffect(() => {
    let current = true;
    const image = new window.Image();
    image.onload = () => {
      if (current) setLoaded({ hash: layer.assetHash, image });
    };
    image.onerror = () => {
      if (current)
        onError(
          'The background image could not be loaded. Reopen the project or check the local server.',
        );
    };
    image.src = `/api/assets/${layer.assetHash}`;
    return () => {
      current = false;
      image.onload = null;
      image.onerror = null;
    };
  }, [layer.assetHash, onError]);
  return loaded?.hash === layer.assetHash && layer.visible ? (
    <CanvasImage
      image={loaded.image}
      x={view.x}
      y={view.y}
      width={1200 * view.scale}
      height={800 * view.scale}
      opacity={layer.opacity}
    />
  ) : null;
}
