export type Scope = 'Map' | 'Room';
export type Tool = 'pan' | 'room' | 'polygon' | 'edit' | 'walls';
export type ToolState = {
  scope: Scope | null;
  tool: Tool;
  remembered: Partial<Record<Scope, Tool>>;
};
export const initialTools: ToolState = {
  scope: null,
  tool: 'pan',
  remembered: {},
};
export type ToolAction =
  | { type: 'selectRoom' }
  | { type: 'scope'; scope: Scope }
  | { type: 'close' }
  | { type: 'tool'; tool: Tool };

export function toolsReducer(state: ToolState, action: ToolAction): ToolState {
  if (action.type === 'selectRoom')
    return {
      scope: 'Room',
      tool: 'edit',
      remembered: { ...state.remembered, Room: 'edit' },
    };
  if (action.type === 'close') return { ...state, scope: null, tool: 'pan' };
  if (action.type === 'scope') {
    const scope = state.scope === action.scope ? null : action.scope;
    return {
      ...state,
      scope,
      tool: scope ? (state.remembered[scope] ?? 'pan') : 'pan',
    };
  }
  if (state.scope !== 'Room') return state;
  const tool = state.tool === action.tool ? 'pan' : action.tool;
  return {
    ...state,
    tool,
    remembered: { ...state.remembered, [state.scope]: tool },
  };
}
