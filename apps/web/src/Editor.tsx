import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { Circle, Layer, Line, Rect, Stage } from 'react-konva';
import type { GeometryResult } from '../../../packages/schema/geometry';
import type {
  Door,
  Point,
  Polygon,
  Project,
  Room,
} from '../../../packages/schema/project';
import { BackgroundImage } from './BackgroundImage';
import { BackgroundPanel } from './BackgroundPanel';
import {
  type DoorDrag,
  doorSegment,
  reconcileDoors,
  slideDoor,
  wallPosition,
} from './doorEditing';
import { EditorPanels } from './EditorPanels';
import { initialTools, toolsReducer } from './editorTools';
import { ProjectMenu } from './ProjectMenu';
import {
  newProject,
  openProject,
  projectFingerprint,
  saveProject,
} from './projectFiles';
import {
  containsPoint,
  dragPolygon,
  moveAnchorIndex,
  type RoomDrag,
} from './roomEditing';
import { emptySceneHistory, sceneReducer } from './sceneHistory';
import { useDerivedWalls } from './useDerivedWalls';
import {
  type Command,
  fitView,
  historyReducer,
  mapSize,
  rectangle,
  screenToWorld,
  type View,
  worldToScreen,
  zoomAt,
} from './viewport';
import { nearestWall } from './wallSelection';
import { overScrollablePanel } from './wheelRouting';

export function Editor({ status }: { status: string }) {
  const container = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);
  const pending = useRef(false);
  const [size, setSize] = useState({ width: 800, height: 560 });
  const [view, setView] = useState<View>(fitView(800, 560));
  const [tools, changeTools] = useReducer(toolsReducer, initialTools);
  const { tool, scope } = tools;
  const [pointer, setPointer] = useState<Point | null>(null);
  const [temporaryPan, setTemporaryPan] = useState(false);
  const [project, setProject] = useState(newProject);
  const [savedFingerprint, setSavedFingerprint] = useState(() =>
    projectFingerprint(project),
  );
  const [grid, setGrid] = useState(true);
  const [snap, setSnap] = useState(true);
  const [sceneHistory, dispatchScene] = useReducer(
    sceneReducer,
    emptySceneHistory,
  );
  const scene = sceneHistory.present;
  const history = { ...sceneHistory, present: scene.rooms };
  const derived = useDerivedWalls(scene.doors.length ? [] : scene.rooms);
  const wallState = scene.doors.length
    ? { walls: scene.walls, loading: false, error: '', retry: derived.retry }
    : derived;
  const [doorId, setDoorId] = useState<string | null>(null);
  const [doorWidth, setDoorWidth] = useState(50);
  const selectedDoor =
    tool === 'door'
      ? (scene.doors.find((door) => door.id === doorId) ?? null)
      : null;
  const [wallId, setWallId] = useState<string | null>(null);
  const selectedWall =
    tool === 'walls'
      ? (wallState.walls.find((wall) => wall.id === wallId) ?? null)
      : null;
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected =
    tool === 'edit'
      ? (history.present.find((room) => room.id === selectedId) ?? null)
      : null;
  const doorDrag = useRef<DoorDrag | null>(null);
  const [doorPreview, setDoorPreview] = useState<Door | null>(null);
  const editDrag = useRef<RoomDrag | null>(null);
  const [editPreview, setEditPreview] = useState<Point[] | null>(null);
  const cancelEdit = useCallback(() => {
    doorDrag.current = null;
    setDoorPreview(null);
    editDrag.current = null;
    setEditPreview(null);
  }, []);
  const [start, setStart] = useState<Point | null>(null);
  const [end, setEnd] = useState<Point | null>(null);
  const [vertices, setVertices] = useState<Point[]>([]);
  const pan = useRef<{ point: Point; view: View } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [dismissVersion, setDismissVersion] = useState(0);
  const space = useRef(false);
  const currentProject: Project = {
    ...project,
    rooms: scene.rooms,
    doors: scene.doors,
    layers: scene.layers ?? [],
    generations: scene.generations ?? [],
    walls: scene.doors.length ? scene.walls : [],
    map: { ...project.map, grid: { ...project.map.grid, visible: grid, snap } },
  };
  const fingerprint = projectFingerprint(currentProject);
  const dirty = fingerprint !== savedFingerprint;
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);
  function replaceProject(next: Project) {
    cancelEdit();
    setVertices([]);
    setStart(null);
    setEnd(null);
    pan.current = null;
    setDoorId(null);
    setWallId(null);
    setSelectedId(null);
    changeTools({ type: 'close' });
    dispatchScene({
      type: 'load',
      scene: {
        rooms: next.rooms,
        walls: next.walls,
        doors: next.doors,
        layers: next.layers,
        generations: next.generations,
      },
    });
    setProject(next);
    setGrid(next.map.grid.visible);
    setSnap(next.map.grid.snap);
    setSavedFingerprint(projectFingerprint(next));
    setView(fitView(size.width, size.height));
    setError('');
  }
  function createProject() {
    if (
      pending.current ||
      (dirty &&
        !window.confirm('Discard unsaved changes and create a new project?'))
    )
      return;
    replaceProject(newProject());
    setNotice('New project. Save when ready.');
  }
  async function fileAction(id?: string) {
    if (pending.current) return;
    if (
      id &&
      dirty &&
      !window.confirm('Discard unsaved changes and open this project?')
    )
      return;
    pending.current = true;
    setBusy(true);
    setError('');
    cancelEdit();
    try {
      if (id) {
        const loaded = await openProject(id);
        if (loaded.projectId !== id)
          throw new Error('The server returned a different project.');
        replaceProject(loaded);
        setNotice('Project opened.');
      } else {
        const saved = await saveProject(currentProject);
        setProject(saved);
        setSavedFingerprint(projectFingerprint(saved));
        setNotice('Project saved on this computer.');
      }
    } catch (failure) {
      setError(
        `${failure instanceof Error ? failure.message : 'Project operation failed.'} Current work is still in the editor.`,
      );
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }

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
          ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName))
      )
        return;
      if (e.code === 'Space') {
        e.preventDefault();
        space.current = true;
        setTemporaryPan(true);
      }
      if (e.key === 'Escape') {
        cancelEdit();
        setVertices([]);
        setStart(null);
        setEnd(null);
        pan.current = null;
      }
    }
    function up(e: KeyboardEvent) {
      if (e.code === 'Space' && space.current) {
        e.preventDefault();
        space.current = false;
        setTemporaryPan(false);
      }
    }
    function blur() {
      cancelEdit();
      space.current = false;
      setTemporaryPan(false);
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
  }, [cancelEdit]);
  useEffect(() => {
    // A scope/tool transition cancels a draft without changing document history.
    void tool;
    void scope;
    setStart(null);
    setEnd(null);
    setVertices([]);
    cancelEdit();
    if (tool !== 'edit') setSelectedId(null);
    if (tool !== 'walls') setWallId(null);
    if (tool !== 'door') setDoorId(null);
    pan.current = null;
  }, [tool, scope, cancelEdit]);
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
      if (overScrollablePanel(event.target)) return;
      event.preventDefault();
      if (
        start ||
        pan.current ||
        editDrag.current ||
        doorDrag.current ||
        event.deltaY === 0
      )
        return;
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
  async function commitRoom(command: Command) {
    const next = historyReducer(
      { past: [], present: scene.rooms, future: [] },
      command,
    ).present;
    if (next === scene.rooms) return;
    const attachments = scene.doors.length
      ? await reconcileDoors(scene.rooms, next, scene.doors)
      : { doors: scene.doors, walls: scene.walls };
    dispatchScene({
      type: 'commit',
      before: scene,
      scene: {
        ...scene,
        rooms: next,
        walls: attachments.walls,
        doors: attachments.doors,
      },
    });
  }
  async function changeDoors(doors: Door[]) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      const attachments = await reconcileDoors(scene.rooms, scene.rooms, doors);
      dispatchScene({
        type: 'commit',
        before: scene,
        scene: {
          ...scene,
          rooms: scene.rooms,
          walls: attachments.walls,
          doors: attachments.doors,
        },
      });
      setNotice('Door changes applied.');
    } catch (failure) {
      setError(
        `${failure instanceof Error ? failure.message : 'Could not validate doors.'} Nothing was changed.`,
      );
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  function placeDoor(point: Point) {
    const native = screenToWorld(point, view);
    const openings = scene.doors.flatMap((door) => {
      const wall = wallState.walls.find((wall) => wall.id === door.wallId);
      if (!wall) return [];
      const [start, end] = doorSegment(door, wall);
      return [{ ...wall, id: door.id, start, end }];
    });
    const hit = nearestWall(openings, native, 10 / view.scale);
    if (hit) {
      setDoorId(hit.id);
      const door = scene.doors.find((door) => door.id === hit.id);
      const wall = wallState.walls.find((wall) => wall.id === door?.wallId);
      if (door && wall) doorDrag.current = { door, wall, origin: native };
      return;
    }
    setDoorId(null);
    if (wallState.loading || wallState.error) {
      setError('Wait for valid walls before placing a door.');
      return;
    }
    const wall = nearestWall(wallState.walls, native, 8 / view.scale);
    if (!wall) return;
    if (!Number.isFinite(doorWidth) || doorWidth <= 0) {
      setError('Enter a positive door width.');
      return;
    }
    const door: Door = {
      id: crypto.randomUUID(),
      kind: 'door',
      revision: 0,
      label: 'Door',
      metadata: {},
      wallId: wall.id,
      position: wallPosition(wall, native, snap, doorWidth),
      width: doorWidth,
      state: 'closed',
      secret: false,
      doorType: 'door',
    };
    setDoorId(door.id);
    void changeDoors([...scene.doors, door]);
  }
  async function accept(
    proposal: Point[],
    before?: Room,
    details?: { label: string; prompt: string },
  ) {
    if (pending.current || proposal.length < 3) return;
    if (
      before &&
      JSON.stringify(proposal) === JSON.stringify(before.polygon) &&
      (!details ||
        (details.label === before.label && details.prompt === before.prompt))
    )
      return;
    const polygon: Polygon = [
      proposal[0],
      proposal[1],
      proposal[2],
      ...proposal.slice(3),
    ];
    pending.current = true;
    setBusy(true);
    setError('');
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
      if (before) {
        await commitRoom({
          type: 'update',
          before,
          room: { ...before, ...details, polygon },
        });
        setNotice('Room updated.');
      } else {
        await commitRoom({
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
        setVertices([]);
      }
    } catch (failure) {
      setError(
        `${failure instanceof Error ? failure.message : 'Could not validate room.'} ${before ? 'The room was not changed. Adjust the edit and try again.' : 'No room was added.'}`,
      );
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  const gridLines = [];
  function beginEdit(point: Point) {
    const native = screenToWorld(point, view);
    const vertex =
      selected?.polygon.findIndex((p) => {
        const screen = worldToScreen(p, view);
        return Math.hypot(screen.x - point.x, screen.y - point.y) <= 8;
      }) ?? -1;
    const room =
      vertex >= 0
        ? selected
        : [...history.present]
            .reverse()
            .find((r) => containsPoint(r.polygon, native));
    setSelectedId(room?.id ?? null);
    if (room)
      editDrag.current = {
        room,
        origin: native,
        vertex: vertex >= 0 ? vertex : null,
      };
  }
  function selectRoom(id: string) {
    if (busy) return;
    changeTools({ type: 'selectRoom' });
    cancelEdit();
    setSelectedId(id);
  }
  async function deleteRoom() {
    if (!selected || pending.current) return;
    cancelEdit();
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      await commitRoom({ type: 'delete', id: selected.id });
      setNotice('Room deleted. Undo restores it.');
    } catch (failure) {
      setError(
        `${failure instanceof Error ? failure.message : 'Could not delete room.'} Nothing was changed.`,
      );
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  function finishPolygon() {
    if (vertices.length >= 3) void accept(vertices);
  }
  function addVertex(point: Point) {
    const value = world(point);
    const first = vertices[0];
    const screenFirst = first && worldToScreen(first, view);
    if (
      first &&
      ((value.x === first.x && value.y === first.y) ||
        (screenFirst &&
          Math.hypot(point.x - screenFirst.x, point.y - screenFirst.y) <= 8))
    ) {
      finishPolygon();
      return;
    }
    if (vertices.some((p) => p.x === value.x && p.y === value.y)) return;
    if (vertices.length >= 2048) {
      setError(
        'A room can contain at most 2048 vertices. Finish the polygon or remove its last point.',
      );
      return;
    }
    setVertices([...vertices, value]);
  }
  const snapWorld =
    pointer &&
    snap &&
    tool !== 'pan' &&
    tool !== 'edit' &&
    tool !== 'walls' &&
    tool !== 'door' &&
    !temporaryPan &&
    !pan.current &&
    !busy
      ? world(pointer)
      : null;
  const snapPoint =
    snapWorld &&
    snapWorld.x >= 0 &&
    snapWorld.y >= 0 &&
    snapWorld.x <= mapSize.width &&
    snapWorld.y <= mapSize.height
      ? worldToScreen(snapWorld, view)
      : null;
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
      <div
        ref={container}
        className="canvas"
        data-testid="map-canvas"
        data-wall-count={wallState.walls.length}
        data-walls-loading={wallState.loading}
        data-door-count={scene.doors.length}
        data-background-hash={scene.layers?.[0]?.assetHash ?? ''}
      >
        <Stage
          width={size.width}
          height={size.height}
          onMouseDown={(e) => {
            setDismissVersion((value) => value + 1);
            if (busy || e.evt.button !== 0) return;
            const pointer = e.target.getStage()?.getPointerPosition();
            if (!pointer) return;
            setPointer(pointer);
            if (tool === 'pan' || space.current)
              pan.current = { point: pointer, view };
            else if (tool === 'polygon') addVertex(pointer);
            else if (tool === 'edit') beginEdit(pointer);
            else if (tool === 'door') placeDoor(pointer);
            else if (tool === 'walls')
              setWallId(
                nearestWall(
                  wallState.walls,
                  screenToWorld(pointer, view),
                  8 / view.scale,
                )?.id ?? null,
              );
            else {
              setStart(world(pointer));
              setEnd(world(pointer));
            }
          }}
          onMouseMove={(e) => {
            const pointer = e.target.getStage()?.getPointerPosition();
            if (!pointer) return;
            setPointer(pointer);
            if (pan.current)
              setView({
                ...pan.current.view,
                x: pan.current.view.x + pointer.x - pan.current.point.x,
                y: pan.current.view.y + pointer.y - pan.current.point.y,
              });
            else if (doorDrag.current) {
              const native = screenToWorld(pointer, view);
              if (
                Math.hypot(
                  native.x - doorDrag.current.origin.x,
                  native.y - doorDrag.current.origin.y,
                ) *
                  view.scale >
                2
              )
                setDoorPreview(slideDoor(doorDrag.current, native, snap));
            } else if (editDrag.current)
              setEditPreview(
                dragPolygon(
                  editDrag.current,
                  screenToWorld(pointer, view),
                  snap,
                ),
              );
            else if (start) setEnd(world(pointer));
          }}
          onMouseUp={(e) => {
            pan.current = null;
            const pointer = e.target.getStage()?.getPointerPosition();
            if (doorDrag.current && pointer) {
              const drag = doorDrag.current;
              const native = screenToWorld(pointer, view);
              if (
                Math.hypot(native.x - drag.origin.x, native.y - drag.origin.y) *
                  view.scale >
                2
              ) {
                const proposed = slideDoor(drag, native, snap);
                if (Math.abs(proposed.position - drag.door.position) > 1e-10)
                  void changeDoors(
                    scene.doors.map((door) =>
                      door.id === proposed.id
                        ? { ...proposed, revision: door.revision + 1 }
                        : door,
                    ),
                  );
              }
            }
            if (editDrag.current && pointer) {
              const drag = editDrag.current;
              const native = screenToWorld(pointer, view);
              if (
                Math.hypot(native.x - drag.origin.x, native.y - drag.origin.y) *
                  view.scale >
                2
              )
                void accept(dragPolygon(drag, native, snap), drag.room);
            }
            cancelEdit();
            if (start && pointer) void accept(rectangle(start, world(pointer)));
            setStart(null);
            setEnd(null);
          }}
          onMouseLeave={() => {
            cancelEdit();
            setPointer(null);
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
            {scene.layers?.[0] && (
              <BackgroundImage
                layer={scene.layers[0]}
                view={view}
                onError={setError}
              />
            )}
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
            {wallState.walls.map((wall) => (
              <Line
                key={wall.id}
                points={points([wall.start, wall.end])}
                stroke={selectedWall?.id === wall.id ? '#efc766' : '#25362b'}
                strokeWidth={selectedWall?.id === wall.id ? 5 : 2.5}
              />
            ))}
            {scene.doors.map((door) => {
              const wall = wallState.walls.find(
                (wall) => wall.id === door.wallId,
              );
              if (!wall) return null;
              const segment = points(
                doorSegment(
                  doorPreview?.id === door.id ? doorPreview : door,
                  wall,
                ),
              );
              return (
                <Line
                  key={door.id}
                  points={segment}
                  stroke={door.id === selectedDoor?.id ? '#efc766' : '#78472b'}
                  strokeWidth={7}
                  dash={
                    door.state === 'open'
                      ? [3, 5]
                      : door.state === 'locked'
                        ? [10, 3, 2, 3]
                        : undefined
                  }
                />
              );
            })}
            {start && end && (
              <Line
                points={points(rectangle(start, end))}
                closed
                fill="#d9af4d66"
                stroke="#875c18"
                dash={[6, 4]}
              />
            )}
            {selected && (
              <>
                <Line
                  points={points(editPreview ?? selected.polygon)}
                  closed
                  stroke="#efc766"
                  strokeWidth={3}
                  dash={[6, 3]}
                />
                {(editPreview ?? selected.polygon).map((p, i) => {
                  const screen = worldToScreen(p, view);
                  return (
                    <Circle
                      // biome-ignore lint/suspicious/noArrayIndexKey: Stateless handles track vertex slots during dragging.
                      key={`handle-${i}`}
                      x={screen.x}
                      y={screen.y}
                      radius={
                        snap &&
                        editDrag.current?.vertex === null &&
                        moveAnchorIndex(editDrag.current) === i
                          ? 8
                          : 5
                      }
                      fill="#fff0be"
                      stroke="#875c18"
                      strokeWidth={1.5}
                    />
                  );
                })}
              </>
            )}
            {vertices.length > 0 && (
              <>
                <Line
                  points={points(
                    pointer && !temporaryPan && !pan.current
                      ? [...vertices, world(pointer)]
                      : vertices,
                  )}
                  closed={vertices.length >= 2}
                  fill="#d9af4d33"
                  stroke="#875c18"
                  dash={[6, 4]}
                />
                {vertices.map((p, index) => {
                  const screen = worldToScreen(p, view);
                  return (
                    <Circle
                      key={`${p.x},${p.y}`}
                      x={screen.x}
                      y={screen.y}
                      radius={index === 0 ? 5 : 3}
                      fill="#e9e2ce"
                      stroke="#875c18"
                    />
                  );
                })}
              </>
            )}
          </Layer>
        </Stage>
        {snapPoint && (
          <span
            className="snap-point"
            data-testid="snap-point"
            aria-hidden="true"
            style={{ left: snapPoint.x, top: snapPoint.y }}
          />
        )}
      </div>
      <EditorPanels
        status={status}
        backgroundControls={
          <BackgroundPanel
            context={sceneHistory}
            fingerprint={fingerprint}
            projectId={project.projectId}
            revision={project.revision}
            busy={busy}
            count={scene.generations?.length ?? 0}
            accept={(result) => {
              if (pending.current) return;
              const previous = scene.layers?.[0];
              const layer = previous
                ? {
                    ...previous,
                    assetHash: result.layer.assetHash,
                    revision: previous.revision + 1,
                  }
                : result.layer;
              dispatchScene({
                type: 'commit',
                before: scene,
                scene: {
                  ...scene,
                  layers: [layer],
                  generations: [
                    ...(scene.generations ?? []),
                    result.generation,
                  ],
                },
              });
              setNotice('Background accepted. Save to keep it.');
            }}
          />
        }
        background={scene.layers?.[0] ?? null}
        changeBackground={(changes) => {
          if (pending.current || !scene.layers?.[0]) return;
          const layer = scene.layers[0];
          dispatchScene({
            type: 'commit',
            before: scene,
            scene: {
              ...scene,
              layers: [{ ...layer, ...changes, revision: layer.revision + 1 }],
            },
          });
        }}
        fileControls={
          <ProjectMenu
            name={project.name}
            revision={project.revision}
            dirty={dirty}
            busy={busy}
            rename={(name) => setProject((current) => ({ ...current, name }))}
            save={() => void fileAction()}
            create={createProject}
            open={(id) => void fileAction(id)}
          />
        }
        tool={tool}
        setTool={(tool) => changeTools({ type: 'tool', tool })}
        scope={scope}
        toggleScope={(scope) => changeTools({ type: 'scope', scope })}
        closeScope={() => changeTools({ type: 'close' })}
        grid={grid}
        setGrid={setGrid}
        snap={snap}
        setSnap={setSnap}
        fit={() => setView(fitView(size.width, size.height))}
        undo={() => {
          cancelEdit();
          if (!pending.current) dispatchScene({ type: 'undo' });
        }}
        redo={() => {
          cancelEdit();
          if (!pending.current) dispatchScene({ type: 'redo' });
        }}
        canUndo={!!history.past.length}
        canRedo={!!history.future.length}
        busy={busy}
        vertexCount={vertices.length}
        finishPolygon={finishPolygon}
        removeVertex={() => setVertices(vertices.slice(0, -1))}
        cancelPolygon={() => setVertices([])}
        rooms={history.present}
        selected={selected}
        selectedWall={selectedWall}
        selectedDoor={selectedDoor}
        doorWidth={doorWidth}
        setDoorWidth={setDoorWidth}
        applyDoor={(door) => {
          if (
            !selectedDoor ||
            JSON.stringify(door) === JSON.stringify(selectedDoor)
          )
            return;
          if (
            !Number.isFinite(door.width) ||
            door.width <= 0 ||
            !Number.isFinite(door.position) ||
            door.position < 0 ||
            door.position > 1
          ) {
            setError(
              'Enter a positive width and a position between 0 and 100%.',
            );
            return;
          }
          void changeDoors(
            scene.doors.map((current) =>
              current.id === door.id
                ? { ...door, revision: current.revision + 1 }
                : current,
            ),
          );
        }}
        deleteDoor={() => {
          if (selectedDoor)
            void changeDoors(
              scene.doors.filter((door) => door.id !== selectedDoor.id),
            );
        }}
        wallsError={wallState.error}
        retryWalls={wallState.retry}
        selectRoom={selectRoom}
        applyRoom={(points, label, prompt) => {
          if (selected) void accept(points, selected, { label, prompt });
        }}
        deleteRoom={() => void deleteRoom()}
        reorderRoom={(id, direction) => {
          if (pending.current) return;
          cancelEdit();
          const rooms = historyReducer(
            { past: [], present: scene.rooms, future: [] },
            { type: 'reorder', id, direction },
          ).present;
          dispatchScene({
            type: 'commit',
            before: scene,
            scene: { ...scene, rooms },
          });
        }}
        zoom={Math.round(view.scale * 100)}
        error={error}
        clearError={() => setError('')}
        notice={notice}
        dismissVersion={dismissVersion}
      />
    </section>
  );
}
