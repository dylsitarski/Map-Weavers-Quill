import { useEffect, useReducer, useRef, useState } from 'react';
import { Layer, Line, Rect, Stage } from 'react-konva';
import type { GeometryResult } from '../../../packages/schema/geometry';
import type { Point } from '../../../packages/schema/project';
import { EditorPanels } from './EditorPanels';
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

export function Editor({ status }: { status: string }) {
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
  const [notice, setNotice] = useState('');
  const [dismissVersion, setDismissVersion] = useState(0);
  const space = useRef(false);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(''), 3500);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    function down(e: KeyboardEvent) {
      if (
        e.target instanceof HTMLElement &&
        (e.target.isContentEditable ||
          ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(e.target.tagName))
      )
        return;
      if (e.code === 'Space') {
        e.preventDefault();
        space.current = true;
      }
      if (e.key === 'Escape') {
        setStart(null);
        setEnd(null);
        pan.current = null;
      }
    }
    function up(e: KeyboardEvent) {
      if (e.code === 'Space') space.current = false;
    }
    function blur() {
      space.current = false;
      pan.current = null;
      setStart(null);
      setEnd(null);
    }
    window.addEventListener('keydown', down);
    window.addEventListener('keyup', up);
    window.addEventListener('blur', blur);
    return () => {
      window.removeEventListener('keydown', down);
      window.removeEventListener('keyup', up);
      window.removeEventListener('blur', blur);
    };
  }, []);
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
  useEffect(() => {
    function wheel(event: WheelEvent) {
      event.preventDefault();
      if (start || pan.current || event.deltaY === 0) return;
      const bounds = container.current?.getBoundingClientRect();
      if (!bounds) return;
      const point = {
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      };
      setView((current) =>
        zoomAt(current, point, event.deltaY < 0 ? 1.1 : 1 / 1.1),
      );
    }
    window.addEventListener('wheel', wheel, { passive: false });
    return () => window.removeEventListener('wheel', wheel);
  }, [start]);
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
      setNotice(`Room ${history.present.length + 1} added.`);
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
      <div ref={container} className="canvas" data-testid="map-canvas">
        <Stage
          width={size.width}
          height={size.height}
          onMouseDown={(e) => {
            setDismissVersion((value) => value + 1);
            if (busy || e.evt.button !== 0) return;
            const pointer = e.target.getStage()?.getPointerPosition();
            if (!pointer) return;
            if (tool === 'pan' || space.current)
              pan.current = { point: pointer, view };
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
      <EditorPanels
        status={status}
        tool={tool}
        setTool={setTool}
        grid={grid}
        setGrid={setGrid}
        snap={snap}
        setSnap={setSnap}
        fit={() => setView(fitView(size.width, size.height))}
        undo={() => dispatch({ type: 'undo' })}
        redo={() => dispatch({ type: 'redo' })}
        canUndo={!!history.past.length}
        canRedo={!!history.future.length}
        busy={busy}
        rooms={history.present}
        zoom={Math.round(view.scale * 100)}
        error={error}
        clearError={() => setError('')}
        notice={notice}
        dismissVersion={dismissVersion}
      />
    </section>
  );
}
