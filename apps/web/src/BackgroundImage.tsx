import { useEffect, useState } from 'react';
import { Image as CanvasImage, Group } from 'react-konva';
import type { Point, RasterLayer } from '../../../packages/schema/project';
import { type View, worldToScreen } from './viewport';
export function BackgroundImage({
  layer,
  view,
  onError,
  polygon,
}: {
  polygon?: Point[];
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
    <Group
      clipFunc={
        polygon
          ? (context) => {
              context.beginPath();
              polygon.forEach((point, index) => {
                const p = worldToScreen(point, view);
                if (index === 0) context.moveTo(p.x, p.y);
                else context.lineTo(p.x, p.y);
              });
              context.closePath();
            }
          : undefined
      }
    >
      <CanvasImage
        image={loaded.image}
        x={view.x}
        y={view.y}
        width={1200 * view.scale}
        height={800 * view.scale}
        opacity={layer.opacity}
      />
    </Group>
  ) : null;
}
