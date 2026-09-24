import { useEffect, useRef, useState } from 'react';
import type { Room } from '../../../packages/schema/project';
import type { Scope, Tool } from './editorTools';

type Props = {
  status: string;
  tool: Tool;
  setTool: (tool: Tool) => void;
  scope: Scope | null;
  toggleScope: (scope: Scope) => void;
  closeScope: () => void;
  grid: boolean;
  setGrid: (value: boolean) => void;
  snap: boolean;
  setSnap: (value: boolean) => void;
  fit: () => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  busy: boolean;
  vertexCount: number;
  finishPolygon: () => void;
  removeVertex: () => void;
  cancelPolygon: () => void;
  rooms: Room[];
  zoom: number;
  error: string;
  clearError: () => void;
  notice: string;
  dismissVersion: number;
};
export function EditorPanels(p: Props) {
  const [panel, setPanel] = useState<string | null>(null);
  const [infoOpen, setInfoOpen] = useState(window.innerWidth >= 900);
  const opener = useRef<HTMLButtonElement | null>(null);
  const scopeOpener = useRef<HTMLButtonElement | null>(null);
  const previousDismiss = useRef(p.dismissVersion);
  const escapeState = useRef({
    panel,
    scope: p.scope,
    closeScope: p.closeScope,
  });
  escapeState.current = { panel, scope: p.scope, closeScope: p.closeScope };
  useEffect(() => {
    if (previousDismiss.current !== p.dismissVersion) setPanel(null);
    previousDismiss.current = p.dismissVersion;
  }, [p.dismissVersion]);
  useEffect(() => {
    function closeOnEscape(e: KeyboardEvent) {
      const current = escapeState.current;
      if (e.key === 'Escape' && current.panel) {
        setPanel(null);
        opener.current?.focus();
      } else if (e.key === 'Escape' && current.scope) {
        current.closeScope();
        scopeOpener.current?.focus();
      }
    }
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, []);
  function open(name: string, button: HTMLButtonElement) {
    opener.current = button;
    setPanel(panel === name ? null : name);
    if (window.innerWidth < 900) setInfoOpen(false);
  }
  return (
    <>
      <h1 className="brand" title="Map-Weaver’s Quill">
        <span aria-hidden="true">MQ</span>
        <span className="sr-only">Map-Weaver’s Quill</span>
      </h1>
      <nav className="topbar surface" aria-label="Global actions">
        {['File', 'View', 'Settings', 'Help'].map((name) => (
          <button
            key={name}
            type="button"
            aria-expanded={panel === name}
            aria-controls="global-panel"
            onClick={(e) => open(name, e.currentTarget)}
          >
            {name}
          </button>
        ))}
        <span className="separator" />
        <label>
          <input
            type="checkbox"
            checked={p.snap}
            onChange={(e) => p.setSnap(e.target.checked)}
          />
          Snap
        </label>
        <button
          type="button"
          aria-pressed={p.tool === 'pan'}
          disabled={p.busy}
          onClick={() => p.setTool('pan')}
        >
          Pan
        </button>
        <button type="button" disabled={!p.canUndo || p.busy} onClick={p.undo}>
          Undo
        </button>
        <button type="button" disabled={!p.canRedo || p.busy} onClick={p.redo}>
          Redo
        </button>
      </nav>
      {panel && ['File', 'View', 'Settings', 'Help'].includes(panel) && (
        <section
          id="global-panel"
          className="global-panel surface"
          aria-label={`${panel} options`}
        >
          <h2>{panel}</h2>
          {panel === 'File' && (
            <p>
              Session only. Saving and opening projects are not available yet.
              Refreshing clears rooms.
            </p>
          )}
          {panel === 'View' && (
            <>
              <button type="button" onClick={p.fit}>
                Fit map
              </button>
              <label>
                <input
                  type="checkbox"
                  checked={p.grid}
                  onChange={(e) => p.setGrid(e.target.checked)}
                />
                Grid
              </label>
            </>
          )}
          {panel === 'Settings' && <p>Grid spacing: 50 map units.</p>}
          {panel === 'Help' && (
            <p>
              Drag to draw a rectangle. Use Pan or hold Space to move the view.
              Scroll to zoom. Escape cancels a draft or closes a menu. Use Enter
              to activate focused buttons; Space temporarily pans.
            </p>
          )}
        </section>
      )}
      <nav className="scope-rail surface" aria-label="Editing scopes">
        {(['Map', 'Room'] as const).map((name) => (
          <button
            key={name}
            type="button"
            aria-pressed={p.scope === name}
            aria-expanded={name === 'Room' ? p.scope === name : undefined}
            aria-controls={name === 'Room' ? 'scope-panel' : undefined}
            title={
              name === 'Map'
                ? 'Select the whole map. AI prompting is planned.'
                : undefined
            }
            onClick={(e) => {
              scopeOpener.current = e.currentTarget;
              p.toggleScope(name);
              setPanel(null);
              if (window.innerWidth < 900) setInfoOpen(false);
            }}
          >
            {name}
          </button>
        ))}
        {['Region', 'Object', 'Light', 'Sound'].map((name) => (
          <button
            key={name}
            type="button"
            disabled
            title={`${name} tools are planned for a later milestone`}
          >
            {name}
          </button>
        ))}
      </nav>
      {p.scope === 'Room' && (
        <section
          id="scope-panel"
          className="scope-panel surface"
          aria-label={`${p.scope} tools`}
        >
          <h2>{p.scope}</h2>
          {p.scope === 'Room' && (
            <>
              <button
                type="button"
                disabled={p.busy}
                aria-pressed={p.tool === 'room'}
                onClick={() => p.setTool('room')}
              >
                Rectangle room
              </button>
              <button
                type="button"
                disabled={p.busy}
                aria-pressed={p.tool === 'polygon'}
                onClick={() => p.setTool('polygon')}
              >
                Polygon room
              </button>
              {p.tool === 'room' && <p>Drag opposite corners on the map.</p>}
              {p.tool === 'polygon' && (
                <>
                  <p>
                    Click corners, then the first point or Finish polygon.
                    Escape cancels.
                  </p>
                  <p data-testid="vertex-count">{p.vertexCount} vertices</p>
                  <button
                    type="button"
                    disabled={p.busy || p.vertexCount < 3}
                    onClick={p.finishPolygon}
                  >
                    Finish polygon
                  </button>
                  <button
                    type="button"
                    disabled={p.busy || !p.vertexCount}
                    onClick={p.removeVertex}
                  >
                    Remove last point
                  </button>
                  <button
                    type="button"
                    disabled={p.busy || !p.vertexCount}
                    onClick={p.cancelPolygon}
                  >
                    Cancel polygon
                  </button>
                </>
              )}
            </>
          )}
        </section>
      )}
      <aside className="info-panel surface" aria-label="Persistent information">
        <button
          className="info-toggle"
          type="button"
          aria-expanded={infoOpen}
          aria-controls="info-body"
          onClick={() => {
            setInfoOpen(!infoOpen);
            if (window.innerWidth < 900) setPanel(null);
          }}
        >
          Information {infoOpen ? '−' : '+'}
        </button>
        <div id="info-body" hidden={!infoOpen}>
          <p className="session-note">Session only · not saved</p>
          <p className="connection-status" role="status">
            {p.status}
          </p>
          <h2>Map</h2>
          <p>1200 × 800 · 50-unit grid</p>
          <h2>Rooms ({p.rooms.length})</h2>
          {p.rooms.length === 0 && <p>No rooms yet.</p>}
          <ul aria-label="Rooms">
            {p.rooms.map((room) => (
              <li key={room.id}>
                <strong>{room.label}</strong>
                <br />
                {room.polygon
                  .map(
                    (point) =>
                      `(${Math.round(point.x)}, ${Math.round(point.y)})`,
                  )
                  .join(' ')}
              </li>
            ))}
          </ul>
        </div>
      </aside>
      <div className="feedback">
        {p.error && (
          <div className="error surface">
            <p role="alert">{p.error}</p>
            <button
              type="button"
              onClick={p.clearError}
              aria-label="Dismiss error"
            >
              Dismiss
            </button>
          </div>
        )}
        <p className="notice surface" aria-live="polite">
          {p.busy ? 'Validating room…' : p.notice}
        </p>
      </div>
      <div className="view-status surface">
        {p.scope === 'Map' && 'Whole map selected · '}
        {p.tool === 'room'
          ? 'Rectangle room'
          : p.tool === 'polygon'
            ? 'Polygon room'
            : 'Pan'}{' '}
        · <span data-testid="zoom">{p.zoom}%</span>
      </div>
    </>
  );
}
