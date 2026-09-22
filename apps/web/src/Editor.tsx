import { useEffect, useReducer, useRef, useState } from 'react';
import { Layer, Line, Rect, Stage } from 'react-konva';
import type { GeometryResult } from '../../../packages/schema/geometry';
import type { Point } from '../../../packages/schema/project';
import {
  emptyHistory,
  fitView,
  historyReducer,
  mapSize,
  rectangle,
  screenToWorld,
  type View,
  worldToScreen,
  zoomAt,
} from './viewport';

export function Editor() {
  const container = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);
  const pending = useRef(false);
  const [size, setSize] = useState({ width: 800, height: 560 });
  const [view, setView] = useState<View>(fitView(800, 560));
  const [tool, setTool] = useState<'pan' | 'room'>('room');
  const [grid, setGrid] = useState(true);
  const [snap, setSnap] = useState(true);
  const [history, dispatch] = useReducer(historyReducer, emptyHistory);
  const [start, setStart] = useState<Point | null>(null);
  const [end, setEnd] = useState<Point | null>(null);
  const pan = useRef<{ point: Point; view: View } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    const node = container.current;
    if (!node) return;
    const observer = new ResizeObserver(([entry]) => {
      const next = {
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      };
      setSize(next);
      if (!initialized.current && next.width > 0) {
        initialized.current = true;
        setView(fitView(next.width, next.height));
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  function world(point: Point) {
    const value = screenToWorld(point, view);
    return snap
      ? { x: Math.round(value.x / 50) * 50, y: Math.round(value.y / 50) * 50 }
      : value;
  }
  function points(polygon: Point[]) {
    return polygon.flatMap((p) => {
      const q = worldToScreen(p, view);
      return [q.x, q.y];
    });
  }
  async function accept(a: Point, b: Point) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    const polygon = rectangle(a, b);
    try {
      const response = await fetch('/api/geometry/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...mapSize, polygon }),
        signal: AbortSignal.timeout(5000),
      });
      if (!response.ok)
        throw new Error(
          'Validation failed. Check the local server and try again.',
        );
      const result: GeometryResult = await response.json();
      if (
        !result ||
        typeof result.valid !== 'boolean' ||
        (result.error !== null && typeof result.error !== 'string')
      ) {
        throw new Error(
          'The server returned an invalid validation response. Try again.',
        );
      }
      if (result.valid !== true)
        throw new Error(result.error || 'Room geometry was rejected.');
      dispatch({
        type: 'add',
        room: {
          id: crypto.randomUUID(),
          kind: 'room',
          revision: 0,
          label: `Room ${history.present.length + 1}`,
          polygon,
          prompt: '',
          metadata: {},
          styleOverrides: {},
          renderLayerId: null,
        },
      });
    } catch (failure) {
      setError(
        `${failure instanceof Error ? failure.message : 'Could not validate room.'} No room was added.`,
      );
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  const gridLines = [];
  if (grid) {
    for (let x = 0; x <= mapSize.width; x += 50)
      gridLines.push([
        { x, y: 0 },
        { x, y: mapSize.height },
      ]);
    for (let y = 0; y <= mapSize.height; y += 50)
      gridLines.push([
        { x: 0, y },
        { x: mapSize.width, y },
      ]);
  }
  return (
    <section className="workshop" aria-label="Map editor">
      <div className="toolbar">
        <button
          type="button"
          aria-pressed={tool === 'room'}
          disabled={busy}
          onClick={() => setTool('room')}
        >
          Rectangle room
        </button>
        <button
          type="button"
          aria-pressed={tool === 'pan'}
          disabled={busy}
          onClick={() => setTool('pan')}
        >
          Pan
        </button>
        <button
          type="button"
          onClick={() => setView(fitView(size.width, size.height))}
        >
          Fit map
        </button>
        <label>
          <input
            type="checkbox"
            checked={grid}
            onChange={(e) => setGrid(e.target.checked)}
          />{' '}
          Grid
        </label>
        <label>
          <input
            type="checkbox"
            checked={snap}
            onChange={(e) => setSnap(e.target.checked)}
          />{' '}
          Snap
        </label>
        <button
          type="button"
          disabled={busy || !history.past.length}
          onClick={() => dispatch({ type: 'undo' })}
        >
          Undo
        </button>
        <button
          type="button"
          disabled={busy || !history.future.length}
          onClick={() => dispatch({ type: 'redo' })}
        >
          Redo
        </button>
        <span data-testid="zoom">{Math.round(view.scale * 100)}%</span>
      </div>
      <p className="hint">
        Drag to draw a room. Choose Pan to move the view; scroll to zoom.
        Session only—refreshing clears rooms.
      </p>
      <div ref={container} className="canvas" data-testid="map-canvas">
        <Stage
          width={size.width}
          height={size.height}
          onWheel={(e) => {
            e.evt.preventDefault();
            if (start || pan.current) return;
            const pointer = e.target.getStage()?.getPointerPosition();
            if (pointer)
              setView(zoomAt(view, pointer, e.evt.deltaY < 0 ? 1.1 : 1 / 1.1));
          }}
          onMouseDown={(e) => {
            if (busy || e.evt.button !== 0) return;
            const pointer = e.target.getStage()?.getPointerPosition();
            if (!pointer) return;
            if (tool === 'pan') pan.current = { point: pointer, view };
            else {
              setStart(world(pointer));
              setEnd(world(pointer));
            }
          }}
          onMouseMove={(e) => {
            const pointer = e.target.getStage()?.getPointerPosition();
            if (!pointer) return;
            if (pan.current)
              setView({
                ...pan.current.view,
                x: pan.current.view.x + pointer.x - pan.current.point.x,
                y: pan.current.view.y + pointer.y - pan.current.point.y,
              });
            else if (start) setEnd(world(pointer));
          }}
          onMouseUp={(e) => {
            pan.current = null;
            const pointer = e.target.getStage()?.getPointerPosition();
            if (start && pointer) void accept(start, world(pointer));
            setStart(null);
            setEnd(null);
          }}
          onMouseLeave={() => {
            pan.current = null;
            setStart(null);
            setEnd(null);
          }}
        >
          <Layer listening={false}>
            <Rect
              x={view.x}
              y={view.y}
              width={mapSize.width * view.scale}
              height={mapSize.height * view.scale}
              fill="#e9e2ce"
              stroke="#b7a578"
            />
            {gridLines.map((line) => (
              <Line
                key={`${line[0].x},${line[0].y}:${line[1].x},${line[1].y}`}
                points={points(line)}
                stroke="#c5bfae"
                strokeWidth={0.7}
              />
            ))}
            {history.present.map((room) => (
              <Line
                key={room.id}
                points={points(room.polygon)}
                closed
                fill="#6f927c99"
                stroke="#234d39"
                strokeWidth={2}
              />
            ))}
            {start && end && (
              <Line
                points={points(rectangle(start, end))}
                closed
                fill="#d9af4d66"
                stroke="#875c18"
                dash={[6, 4]}
              />
            )}
          </Layer>
        </Stage>
      </div>
      <p className="editor-error" role="alert" aria-atomic="true">
        {error}
      </p>
      <div className="room-summary" aria-live="polite">
        {busy ? 'Validating room…' : `${history.present.length} rooms`} · 1200 ×
        800 · origin bottom-left
      </div>
      <ul aria-label="Rooms">
        {history.present.map((room) => (
          <li key={room.id}>
            {room.label} ·{' '}
            {room.polygon
              .map((p) => `(${Math.round(p.x)}, ${Math.round(p.y)})`)
              .join(' ')}
          </li>
        ))}
      </ul>
    </section>
  );
}
