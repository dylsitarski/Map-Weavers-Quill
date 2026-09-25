import Ajv2020 from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import type { ProjectList } from '../../../packages/schema/persistence';
import schema from '../../../packages/schema/persistence.schema.json';
import type { Project } from '../../../packages/schema/project';

const ajv = new Ajv2020({ strict: false });
addFormats(ajv);
const projectValid = ajv.compile<Project>({
  $defs: schema.$defs,
  $ref: '#/$defs/Project',
});
const listValid = ajv.compile<ProjectList>({
  $defs: schema.$defs,
  $ref: '#/$defs/ProjectList',
});
async function json(url: string, options?: RequestInit): Promise<unknown> {
  const response = await fetch(url, {
    ...options,
    signal: AbortSignal.timeout(10000),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok)
    throw new Error(
      typeof data?.detail === 'string'
        ? data.detail
        : 'Project request failed. Check the local server and retry.',
    );
  return data;
}
export async function listProjects(): Promise<ProjectList> {
  const data = await json('/api/projects');
  if (!listValid(data))
    throw new Error('The server returned an invalid project list.');
  return data;
}
export async function openProject(id: string): Promise<Project> {
  const data = await json(`/api/projects/${encodeURIComponent(id)}`);
  if (!projectValid(data))
    throw new Error('The server returned an invalid project.');
  return data;
}
export async function saveProject(project: Project): Promise<Project> {
  const data = await json('/api/projects/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contractVersion: '0.1.0',
      expectedRevision: project.revision || null,
      project,
    }),
  });
  if (
    !projectValid(data) ||
    data.projectId !== project.projectId ||
    data.revision !== project.revision + 1
  )
    throw new Error(
      'Save confirmation was invalid. Reopen the saved project before retrying.',
    );
  return data;
}
export function newProject(): Project {
  return {
    schemaVersion: '0.1.0',
    projectId: crypto.randomUUID(),
    revision: 0,
    name: 'Untitled map',
    map: {
      width: 1200,
      height: 800,
      coordinateSystem: 'bottom-left-y-up-ccw',
      grid: {
        type: 'square',
        sizePx: 50,
        distance: 5,
        units: 'ft',
        visible: true,
        snap: true,
      },
      style: {
        camera: 'strict orthographic top-down',
        environment: '',
        renderStyle: '',
        palette: '',
        wallThicknessPx: 5,
        bakedLighting: 'neutral',
      },
    },
    rooms: [],
    walls: [],
    doors: [],
    lights: [],
    layers: [],
    objects: [],
    regions: [],
    sounds: [],
    generations: [],
    settings: {},
  };
}
export function projectFingerprint(project: Project): string {
  // Wall geometry is deterministic; saved revision is metadata, not a local edit.
  const { revision: _revision, walls: _walls, ...content } = project;
  function canonical(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(canonical);
    if (value && typeof value === 'object')
      return Object.fromEntries(
        Object.entries(value)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([key, item]) => [key, canonical(item)]),
      );
    return value;
  }
  return JSON.stringify(canonical(content));
}
