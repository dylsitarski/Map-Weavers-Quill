import type {
  Door,
  GenerationRecord,
  Project,
  RasterLayer,
  Room,
  Wall,
} from '../../../packages/schema/project';

export type Scene = {
  mapAuthoring?: {
    style: Project['map']['style'];
    settings: Project['settings'];
  };
  rooms: Room[];
  doors: Door[];
  walls: Wall[];
  layers?: RasterLayer[];
  generations?: GenerationRecord[];
};
export type SceneHistory = { past: Scene[]; present: Scene; future: Scene[] };
export const emptySceneHistory: SceneHistory = {
  past: [],
  present: { rooms: [], doors: [], walls: [] },
  future: [],
};
export type SceneAction =
  | { type: 'commit'; before: Scene; scene: Scene }
  | { type: 'load'; scene: Scene }
  | { type: 'undo' | 'redo' };
export function sceneReducer(
  state: SceneHistory,
  action: SceneAction,
): SceneHistory {
  if (action.type === 'load')
    return { past: [], present: action.scene, future: [] };
  if (action.type === 'commit') {
    if (
      action.before !== state.present ||
      JSON.stringify(action.scene) === JSON.stringify(state.present)
    )
      return state;
    return {
      past: [...state.past, state.present],
      present: action.scene,
      future: [],
    };
  }
  if (action.type === 'undo' && state.past.length)
    return {
      past: state.past.slice(0, -1),
      present: state.past[state.past.length - 1],
      future: [state.present, ...state.future],
    };
  if (action.type === 'redo' && state.future.length)
    return {
      past: [...state.past, state.present],
      present: state.future[0],
      future: state.future.slice(1),
    };
  return state;
}
