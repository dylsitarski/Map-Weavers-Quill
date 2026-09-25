import { useState } from 'react';
import type { RasterLayer, Room } from '../../../packages/schema/project';
import { orderedArtwork } from './artworkLayers';

type Props = {
  layers: RasterLayer[];
  rooms: Room[];
  busy: boolean;
  selectedId?: string;
  selectRoom: (id: string) => void;
  change: (
    id: string,
    changes: { visible?: boolean; opacity?: number },
  ) => void;
  reorder: (id: string, target: string) => void;
};
export function ArtworkLayers({
  layers,
  rooms,
  busy,
  change,
  reorder,
  selectedId,
  selectRoom,
}: Props) {
  const ordered = orderedArtwork(layers).reverse();
  const [dragged, setDragged] = useState<string | null>(null);
  const [over, setOver] = useState<string | null>(null);
  const [draft, setDraft] = useState<{ id: string; value: number } | null>(
    null,
  );
  return (
    <>
      {ordered.length === 0 && (
        <p>No artwork yet. Generate it in the AI tab.</p>
      )}
      <ul className="artwork-list" aria-label="Artwork layers">
        {ordered.map((layer, index) => {
          const background = layer.zIndex === 0;
          const room = rooms.find((room) => room.renderLayerId === layer.id);
          const label = background
            ? 'Background'
            : (room?.label ?? layer.label);
          return (
            <li
              key={layer.id}
              data-artwork-id={layer.id}
              className={
                over === layer.id
                  ? `artwork-row drop-target ${index < ordered.findIndex((item) => item.id === dragged) ? 'drop-above' : 'drop-below'}`
                  : 'artwork-row'
              }
              onDragOver={(e) => {
                if (!busy && !background && dragged && dragged !== layer.id) {
                  e.preventDefault();
                  setOver(layer.id);
                } else setOver(null);
              }}
              onDragLeave={(e) => {
                if (
                  !(e.relatedTarget instanceof Node) ||
                  !e.currentTarget.contains(e.relatedTarget)
                )
                  setOver(null);
              }}
              onDrop={(e) => {
                e.preventDefault();
                if (!busy && !background && dragged) reorder(dragged, layer.id);
                setDragged(null);
                setOver(null);
              }}
            >
              <button
                type="button"
                className="artwork-handle"
                disabled={busy || background}
                draggable={!busy && !background}
                aria-label={`Reorder ${label}`}
                title={
                  background
                    ? 'Background stays at bottom'
                    : 'Drag to reorder; arrow keys move up/down'
                }
                onDragStart={(e) => {
                  setDragged(layer.id);
                  e.dataTransfer.setData('text/plain', layer.id);
                  e.dataTransfer.effectAllowed = 'move';
                }}
                onDragEnd={() => {
                  setDragged(null);
                  setOver(null);
                }}
                onKeyDown={(e) => {
                  if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;
                  e.preventDefault();
                  const target =
                    ordered[index + (e.key === 'ArrowUp' ? -1 : 1)];
                  if (target && target.zIndex > 0) reorder(layer.id, target.id);
                }}
              >
                ⠿
              </button>
              {room ? (
                <button
                  type="button"
                  className="artwork-name"
                  title={label}
                  disabled={busy}
                  aria-label={`Select ${label}`}
                  aria-pressed={selectedId === room.id}
                  onClick={() => selectRoom(room.id)}
                >
                  {label}
                </button>
              ) : (
                <span className="artwork-name" title={label}>
                  {label}
                </span>
              )}
              <input
                type="checkbox"
                aria-label={background ? 'Show background' : `Show ${label}`}
                disabled={busy}
                checked={layer.visible}
                onChange={(e) =>
                  change(layer.id, { visible: e.target.checked })
                }
              />
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                aria-label={`${label} opacity`}
                disabled={busy}
                value={draft?.id === layer.id ? draft.value : layer.opacity}
                title={`${Math.round((draft?.id === layer.id ? draft.value : layer.opacity) * 100)}%`}
                onChange={(e) =>
                  setDraft({ id: layer.id, value: e.target.valueAsNumber })
                }
                onPointerUp={(e) => {
                  change(layer.id, { opacity: e.currentTarget.valueAsNumber });
                  setDraft(null);
                }}
                onKeyUp={(e) => {
                  change(layer.id, { opacity: e.currentTarget.valueAsNumber });
                  setDraft(null);
                }}
                onBlur={(e) => {
                  if (draft?.id === layer.id)
                    change(layer.id, {
                      opacity: e.currentTarget.valueAsNumber,
                    });
                  setDraft(null);
                }}
                onPointerCancel={() => setDraft(null)}
              />
            </li>
          );
        })}
      </ul>
    </>
  );
}
