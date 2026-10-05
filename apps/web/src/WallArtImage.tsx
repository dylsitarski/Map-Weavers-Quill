import { useEffect, useState } from 'react';
import { Image as CanvasImage } from 'react-konva';
import type { WallArtRequest } from '../../../packages/schema/geometry';
import { mapSize, type View } from './viewport';

/**
 * Fetch the server-rendered wall/door overlay. While a newer render is pending the
 * previous image stays visible, avoiding flicker; failed renders show nothing.
 */
export function useWallArt(request: WallArtRequest | null) {
  const key = request ? JSON.stringify(request) : '';
  const [result, setResult] = useState<{
    key: string;
    image: HTMLImageElement | null;
    error: string;
  } | null>(null);
  useEffect(() => {
    if (!key) return;
    const controller = new AbortController();
    let current = true;
    // Debounce bursts (typing a thickness, repeated undo) into one render.
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch('/api/render/walls', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: key,
          signal: AbortSignal.any([
            controller.signal,
            AbortSignal.timeout(15000),
          ]),
        });
        if (!response.ok) {
          const error = await response.json().catch(() => null);
          throw new Error(
            typeof error?.detail === 'string'
              ? error.detail
              : 'Check the local server.',
          );
        }
        const url = URL.createObjectURL(await response.blob());
        const image = new window.Image();
        try {
          await new Promise((resolve, reject) => {
            image.onload = resolve;
            image.onerror = () => reject(new Error('Invalid wall art image.'));
            image.src = url;
          });
        } finally {
          URL.revokeObjectURL(url);
        }
        if (current) setResult({ key, image, error: '' });
      } catch (error) {
        if (current && !controller.signal.aborted)
          setResult({
            key,
            image: null,
            error: `Wall art preview unavailable. ${error instanceof Error ? error.message : ''} Room geometry is unchanged.`,
          });
      }
    }, 120);
    return () => {
      current = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [key]);
  return {
    image: key ? (result?.image ?? null) : null,
    loading: !!key && result?.key !== key,
    error: key && result?.key === key ? result.error : '',
  };
}

export function WallArtImage({
  image,
  view,
}: {
  image: HTMLImageElement | null;
  view: View;
}) {
  return image ? (
    <CanvasImage
      image={image}
      x={view.x}
      y={view.y}
      width={mapSize.width * view.scale}
      height={mapSize.height * view.scale}
    />
  ) : null;
}
