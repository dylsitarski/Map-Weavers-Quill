import { useState } from 'react';
import type { Door } from '../../../packages/schema/project';
export function DoorInspector({
  door,
  busy,
  apply,
  remove,
}: {
  door: Door;
  busy: boolean;
  apply: (door: Door) => void;
  remove: () => void;
}) {
  const [draft, setDraft] = useState(door);
  return (
    <section
      aria-label="Door inspector"
      data-door-id={door.id}
      data-wall-id={door.wallId}
      data-position={door.position}
    >
      <h2>Selected door</h2>
      <div className="actions">
        <button type="button" disabled={busy} onClick={() => apply(draft)}>
          Apply door
        </button>
        <button type="button" disabled={busy} onClick={() => setDraft(door)}>
          Reset door
        </button>
        <button type="button" disabled={busy} onClick={remove}>
          Delete door
        </button>
      </div>
      <label>
        Name
        <input
          value={draft.label}
          onChange={(e) => setDraft({ ...draft, label: e.target.value })}
        />
      </label>
      <label>
        Width
        <input
          type="number"
          min="0.01"
          step="any"
          value={Number.isFinite(draft.width) ? draft.width : ''}
          onChange={(e) =>
            setDraft({ ...draft, width: e.target.valueAsNumber })
          }
        />
      </label>
      <label>
        Position along wall (%)
        <input
          type="number"
          min="0"
          max="100"
          step="any"
          value={Number.isFinite(draft.position) ? draft.position * 100 : ''}
          onChange={(e) =>
            setDraft({ ...draft, position: e.target.valueAsNumber / 100 })
          }
        />
      </label>
      <label>
        State
        <select
          value={draft.state}
          onChange={(e) =>
            setDraft({ ...draft, state: e.target.value as Door['state'] })
          }
        >
          {['closed', 'open', 'locked'].map((state) => (
            <option key={state}>{state}</option>
          ))}
        </select>
      </label>
      <label>
        <input
          type="checkbox"
          checked={draft.secret}
          onChange={(e) => setDraft({ ...draft, secret: e.target.checked })}
        />
        Secret
      </label>
      <p>
        Exact position follows the wall's canonical start → end. The full
        opening must fit on one segment.
      </p>
    </section>
  );
}
