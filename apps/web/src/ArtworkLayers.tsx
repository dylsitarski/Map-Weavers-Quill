import type { RasterLayer, Room } from '../../../packages/schema/project';
import { orderedArtwork } from './artworkLayers';

type Props = {
  layers: RasterLayer[];
  rooms: Room[];
  busy: boolean;
  change: (
    id: string,
    changes: { visible?: boolean; opacity?: number },
  ) => void;
  reorder: (id: string, direction: 'up' | 'down') => void;
};
export function ArtworkLayers({ layers, rooms, busy, change, reorder }: Props) {
  const ordered = orderedArtwork(layers).reverse();
  const art = ordered.filter((layer) => layer.zIndex > 0);
  return (
    <>
      <p>Artwork · front to back</p>
      {ordered.length === 0 && (
        <p>No artwork yet. Generate it in the AI tab.</p>
      )}
      <ul aria-label="Artwork layers">
        {ordered.map((layer) => {
          const background = layer.zIndex === 0;
          const label = background
            ? 'Background'
            : `${rooms.find((room) => room.renderLayerId === layer.id)?.label ?? layer.label} artwork`;
          const index = art.findIndex((item) => item.id === layer.id);
          return (
            <li key={layer.id} data-artwork-id={layer.id}>
              <fieldset disabled={busy}>
                <legend>{label}</legend>
                {!background && (
                  <>
                    <button
                      type="button"
                      aria-label={`Raise ${label}`}
                      disabled={index === 0}
                      onClick={() => reorder(layer.id, 'up')}
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      aria-label={`Lower ${label}`}
                      disabled={index === art.length - 1}
                      onClick={() => reorder(layer.id, 'down')}
                    >
                      ↓
                    </button>
                  </>
                )}
                {background && <p>Fixed at bottom</p>}
                <label>
                  <input
                    type="checkbox"
                    checked={layer.visible}
                    onChange={(e) =>
                      change(layer.id, { visible: e.target.checked })
                    }
                  />
                  {background ? 'Show background' : `Show ${label}`}
                </label>
                <label>
                  {label} opacity
                  <select
                    value={layer.opacity}
                    onChange={(e) =>
                      change(layer.id, { opacity: Number(e.target.value) })
                    }
                  >
                    {[...new Set([0, 0.25, 0.5, 0.75, 1, layer.opacity])]
                      .sort((a, b) => a - b)
                      .map((value) => (
                        <option key={value} value={value}>
                          {Math.round(value * 100)}%
                        </option>
                      ))}
                  </select>
                </label>
              </fieldset>
            </li>
          );
        })}
      </ul>
    </>
  );
}
