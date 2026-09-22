import type { Point, Room } from '../../../packages/schema/project';

export type View = { x: number; y: number; scale: number };
export const mapSize = { width: 1200, height: 800 };
export function worldToScreen(p: Point, view: View): Point {
  return {
    x: view.x + p.x * view.scale,
    y: view.y + (mapSize.height - p.y) * view.scale,
  };
}
export function screenToWorld(p: Point, view: View): Point {
  return {
    x: (p.x - view.x) / view.scale,
    y: mapSize.height - (p.y - view.y) / view.scale,
  };
}
export function zoomAt(view: View, point: Point, factor: number): View {
  const scale = Math.max(0.1, Math.min(4, view.scale * factor));
  return {
    x: point.x - ((point.x - view.x) * scale) / view.scale,
    y: point.y - ((point.y - view.y) * scale) / view.scale,
    scale,
  };
}
export function fitView(width: number, height: number): View {
  const scale = Math.max(
    0.1,
    Math.min((width - 48) / mapSize.width, (height - 48) / mapSize.height),
  );
  return {
    x: (width - mapSize.width * scale) / 2,
    y: (height - mapSize.height * scale) / 2,
    scale,
  };
}
export function rectangle(a: Point, b: Point): [Point, Point, Point, Point] {
  const x = Math.min(a.x, b.x),
    y = Math.min(a.y, b.y);
  const right = Math.max(a.x, b.x),
    top = Math.max(a.y, b.y);
  return [
    { x, y },
    { x: right, y },
    { x: right, y: top },
    { x, y: top },
  ];
}
export type History = { past: Room[][]; present: Room[]; future: Room[][] };
export type Command = { type: 'add'; room: Room } | { type: 'undo' | 'redo' };
export const emptyHistory: History = { past: [], present: [], future: [] };
export function historyReducer(state: History, command: Command): History {
  if (command.type === 'add')
    return {
      past: [...state.past, state.present],
      present: [...state.present, command.room],
      future: [],
    };
  if (command.type === 'undo' && state.past.length)
    return {
      past: state.past.slice(0, -1),
      present: state.past[state.past.length - 1],
      future: [state.present, ...state.future],
    };
  if (command.type === 'redo' && state.future.length)
    return {
      past: [...state.past, state.present],
      present: state.future[0],
      future: state.future.slice(1),
    };
  return state;
}
