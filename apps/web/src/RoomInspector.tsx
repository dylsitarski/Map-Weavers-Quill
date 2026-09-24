import { useState } from 'react';
import type { Point, Room } from '../../../packages/schema/project';

export function RoomInspector({
  room,
  busy,
  apply,
  remove,
}: {
  room: Room;
  busy: boolean;
  apply: (points: Point[], label: string, prompt: string) => void;
  remove: () => void;
}) {
  const [label, setLabel] = useState(room.label);
  const [points, setPoints] = useState<Point[]>(room.polygon);
  return (
    <form
      aria-label="Room inspector"
      onSubmit={(event) => {
        event.preventDefault();
        if (points.every((p) => Number.isFinite(p.x) && Number.isFinite(p.y)))
          apply(points, label, room.prompt);
      }}
    >
      <h2>Selected room</h2>
      <fieldset disabled={busy}>
        <div className="inspector-actions">
          <button type="submit" aria-label="Apply room changes">
            Apply
          </button>
          <button
            type="button"
            aria-label="Reset changes"
            onClick={() => {
              setLabel(room.label);
              setPoints(room.polygon);
            }}
          >
            Reset
          </button>
          <button type="button" aria-label="Delete room" onClick={remove}>
            Delete
          </button>
        </div>
        <label>
          Name
          <input value={label} onChange={(e) => setLabel(e.target.value)} />
        </label>
        <p>Coordinates: +y up. Edit the room prompt in the AI tab.</p>
        {points.map((point, index) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: Fully controlled inputs represent ordered vertex slots, with no row-local state.
          <div className="vertex-fields" key={`vertex-${index}`}>
            <span>Vertex {index + 1}</span>
            <div className="vertex-coordinates">
              {(['x', 'y'] as const).map((axis) => (
                <label key={axis}>
                  {axis}
                  <input
                    type="number"
                    step="any"
                    required
                    min={0}
                    max={axis === 'x' ? 1200 : 800}
                    aria-label={`Vertex ${index + 1} ${axis}`}
                    value={Number.isFinite(point[axis]) ? point[axis] : ''}
                    onChange={(e) =>
                      setPoints(
                        points.map((p, i) =>
                          i === index
                            ? { ...p, [axis]: e.target.valueAsNumber }
                            : p,
                        ),
                      )
                    }
                  />
                </label>
              ))}
            </div>
            <button
              type="button"
              disabled={points.length <= 3}
              aria-label={`Remove vertex ${index + 1}`}
              onClick={() => setPoints(points.filter((_, i) => i !== index))}
            >
              Remove
            </button>
            <button
              type="button"
              disabled={points.length >= 2048}
              aria-label={`Insert after vertex ${index + 1}`}
              onClick={() => {
                const next = points[(index + 1) % points.length];
                setPoints([
                  ...points.slice(0, index + 1),
                  { x: (point.x + next.x) / 2, y: (point.y + next.y) / 2 },
                  ...points.slice(index + 1),
                ]);
              }}
            >
              Insert after
            </button>
          </div>
        ))}
      </fieldset>
    </form>
  );
}
