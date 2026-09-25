import { type ReactNode, useEffect, useRef, useState } from 'react';
import type {
  Door,
  MapStyle,
  Point,
  RasterLayer,
  Room,
  Wall,
} from '../../../packages/schema/project';
import { ArtworkLayers } from './ArtworkLayers';
import { DoorInspector } from './DoorInspector';
import type { Scope, Tool } from './editorTools';
import { PromptPanel } from './PromptPanel';
import { RoomInspector } from './RoomInspector';

type Props = {
  status: string;
  mapStyle: MapStyle;
  fileControls: ReactNode;
  backgroundControls: ReactNode;
  roomGenerationControls: ReactNode;
  layers: RasterLayer[];
  changeArtwork: (
    id: string,
    changes: { visible?: boolean; opacity?: number },
  ) => void;
  reorderArtwork: (id: string, target: string) => void;
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
  selected: Room | null;
  selectedWall: Wall | null;
  selectedDoor: Door | null;
  applyDoor: (door: Door) => void;
  deleteDoor: () => void;
  doorWidth: number;
  setDoorWidth: (width: number) => void;
  wallsError: string;
  retryWalls: () => void;
  selectRoom: (id: string) => void;
  applyRoom: (
    points: Point[],
    label: string,
    prompt: string,
    styleOverrides?: Room['styleOverrides'],
  ) => void;
  deleteRoom: () => void;
  zoom: number;
  error: string;
  clearError: () => void;
  notice: string;
  dismissVersion: number;
};
export function EditorPanels(p: Props) {
  const [panel, setPanel] = useState<string | null>(null);
  const [infoOpen, setInfoOpen] = useState(window.innerWidth >= 900);
  const [tab, setTab] = useState('Information');
  const selectedId = p.selected?.id ?? p.selectedWall?.id ?? p.selectedDoor?.id;
  useEffect(() => {
    if (selectedId) {
      setInfoOpen(true);
    }
  }, [selectedId]);
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
        <span className="connection-status" title={p.status}>
          <span aria-hidden="true">●</span>
          <span className="sr-only" role="status">
            {p.status}
          </span>
        </span>
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
          {panel === 'File' && p.fileControls}
          {panel === 'View' && (
            <>
              <p>1200 × 800 map units · 50-unit grid</p>
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
            <>
              <p>{p.status}</p>
              <p>
                Drag to draw a rectangle. Use Pan or hold Space to move the
                view. Scroll over the canvas to zoom, or over a scrollable panel
                to scroll it. Escape cancels a draft or closes a menu. Use Enter
                to activate focused buttons; Space temporarily pans.
              </p>
            </>
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
                ? 'Select the base background. Open AI for a mock preview.'
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
                aria-pressed={p.tool === 'edit'}
                onClick={() => p.setTool('edit')}
              >
                Select/edit room
              </button>
              {p.tool === 'edit' && (
                <p>
                  Click a room to select it. Drag inside to move; drag a corner
                  to reshape. Use Information for exact edits.
                </p>
              )}
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
              <button
                type="button"
                disabled={p.busy}
                aria-pressed={p.tool === 'door'}
                onClick={() => p.setTool('door')}
              >
                Place/edit door
              </button>
              {p.tool === 'door' && (
                <>
                  <label>
                    New door width
                    <input
                      type="number"
                      min="0.01"
                      step="any"
                      value={Number.isFinite(p.doorWidth) ? p.doorWidth : ''}
                      onChange={(e) => p.setDoorWidth(e.target.valueAsNumber)}
                    />
                  </label>
                  <p>
                    Click a wall to place a door, or an existing door to edit
                    it. Drag a door along its wall. Snap aligns to grid-cell
                    midpoints.
                  </p>
                </>
              )}
              <button
                type="button"
                disabled={p.busy}
                aria-pressed={p.tool === 'walls'}
                onClick={() => p.setTool('walls')}
              >
                Inspect walls
              </button>
            </>
          )}
        </section>
      )}
      <aside className="info-panel surface" aria-label="Inspector and layers">
        <div className="panel-header">
          <div role="tablist" aria-label="Right panel">
            {['Information', 'Layers', 'AI'].map((name, index, tabs) => (
              <button
                key={name}
                type="button"
                role="tab"
                id={`tab-${name}`}
                aria-selected={tab === name}
                aria-controls={`panel-${name}`}
                tabIndex={tab === name ? 0 : -1}
                onClick={() => {
                  setTab(name);
                  setInfoOpen(true);
                }}
                onKeyDown={(event) => {
                  let next = index;
                  if (event.key === 'ArrowRight')
                    next = (index + 1) % tabs.length;
                  else if (event.key === 'ArrowLeft')
                    next = (index + tabs.length - 1) % tabs.length;
                  else if (event.key === 'Home') next = 0;
                  else if (event.key === 'End') next = tabs.length - 1;
                  else return;
                  event.preventDefault();
                  event.stopPropagation();
                  setTab(tabs[next]);
                  setInfoOpen(true);
                  document.getElementById(`tab-${tabs[next]}`)?.focus();
                }}
              >
                {name}
              </button>
            ))}
          </div>
          <button
            type="button"
            aria-label={
              infoOpen ? 'Collapse right panel' : 'Expand right panel'
            }
            aria-expanded={infoOpen}
            aria-controls="info-body"
            onClick={() => setInfoOpen(!infoOpen)}
          >
            {infoOpen ? '−' : '+'}
          </button>
        </div>
        <div id="info-body" hidden={!infoOpen}>
          <section
            role="tabpanel"
            id="panel-Information"
            aria-labelledby="tab-Information"
            hidden={tab !== 'Information'}
          >
            {p.selectedDoor ? (
              <DoorInspector
                key={JSON.stringify(p.selectedDoor)}
                door={p.selectedDoor}
                busy={p.busy}
                apply={p.applyDoor}
                remove={p.deleteDoor}
              />
            ) : p.selectedWall ? (
              <section
                aria-label="Wall inspector"
                data-wall-id={p.selectedWall.id}
              >
                <h2>Selected wall</h2>
                <p>
                  Start: ({p.selectedWall.start.x}, {p.selectedWall.start.y})
                </p>
                <p>
                  End: ({p.selectedWall.end.x}, {p.selectedWall.end.y})
                </p>
                <p>
                  Length:{' '}
                  {Math.hypot(
                    p.selectedWall.end.x - p.selectedWall.start.x,
                    p.selectedWall.end.y - p.selectedWall.start.y,
                  ).toFixed(2)}{' '}
                  map units
                </p>
                <p>
                  Blocks movement: {p.selectedWall.movement ? 'Yes' : 'No'} ·
                  Blocks sight: {p.selectedWall.sight ? 'Yes' : 'No'}
                </p>
                <p>
                  Derived from:{' '}
                  {p.rooms
                    .filter((room) => {
                      const source = p.selectedWall?.metadata['quill.geometry'];
                      return (
                        source &&
                        typeof source === 'object' &&
                        !Array.isArray(source) &&
                        'sourceRoomIds' in source &&
                        Array.isArray(source.sourceRoomIds) &&
                        source.sourceRoomIds.includes(room.id)
                      );
                    })
                    .map((room) => room.label)
                    .join(', ')}
                </p>
                <p>
                  Edit the source room to change its walls. Use Place/edit door
                  to add an opening. Standalone wall tools are not available
                  yet.
                </p>
              </section>
            ) : p.selected ? (
              <RoomInspector
                key={JSON.stringify(p.selected)}
                room={p.selected}
                busy={p.busy}
                apply={p.applyRoom}
                remove={p.deleteRoom}
              />
            ) : (
              <p>
                {p.scope === 'Map'
                  ? 'Base background selected. Open AI to generate a mock background preview.'
                  : 'Select an item to inspect it.'}
              </p>
            )}
          </section>
          <section
            role="tabpanel"
            id="panel-Layers"
            aria-labelledby="tab-Layers"
            hidden={tab !== 'Layers'}
          >
            <ArtworkLayers
              selectedId={p.selected?.id}
              selectRoom={p.selectRoom}
              layers={p.layers}
              rooms={p.rooms}
              busy={p.busy}
              change={p.changeArtwork}
              reorder={p.reorderArtwork}
            />
          </section>
          <section
            role="tabpanel"
            id="panel-AI"
            aria-labelledby="tab-AI"
            hidden={tab !== 'AI'}
          >
            <div hidden={p.scope !== 'Map'}>{p.backgroundControls}</div>
            {p.selected ? (
              <>
                <PromptPanel
                  key={JSON.stringify(p.selected)}
                  mapStyle={p.mapStyle}
                  room={p.selected}
                  busy={p.busy}
                  save={(prompt, styleOverrides) => {
                    if (p.selected)
                      p.applyRoom(
                        p.selected.polygon,
                        p.selected.label,
                        prompt,
                        styleOverrides,
                      );
                  }}
                />
                {p.roomGenerationControls}
              </>
            ) : (
              <p>
                {p.scope === 'Map'
                  ? 'Accepting a preview changes only the base background.'
                  : 'Select a room to edit its prompt, or Map to target the base background. Apply a room prompt, then generate a mock preview.'}
              </p>
            )}
          </section>
        </div>
      </aside>
      <div className="feedback">
        {p.wallsError && (
          <div className="error surface">
            <p role="alert">{p.wallsError}</p>
            <button type="button" onClick={p.retryWalls}>
              Retry walls
            </button>
          </div>
        )}
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
          {p.busy ? 'Working…' : p.notice}
        </p>
      </div>
      <div className="view-status surface">
        {p.scope === 'Map' && 'Map background selected · '}
        {p.tool === 'room'
          ? 'Rectangle room'
          : p.tool === 'polygon'
            ? 'Polygon room'
            : p.tool === 'edit'
              ? 'Select/edit room'
              : p.tool === 'walls'
                ? 'Inspect walls'
                : p.tool === 'door'
                  ? 'Place/edit door'
                  : 'Pan'}{' '}
        · <span data-testid="zoom">{p.zoom}%</span>
      </div>
    </>
  );
}
