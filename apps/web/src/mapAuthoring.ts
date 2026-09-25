import type { Project } from '../../../packages/schema/project';
export function backgroundPrompt(project: Project): string {
  const saved = project.settings['quill.background'];
  if (
    saved &&
    typeof saved === 'object' &&
    !Array.isArray(saved) &&
    'prompt' in saved &&
    typeof saved.prompt === 'string'
  )
    return saved.prompt;
  const previous = [...project.generations]
    .reverse()
    .find((item) => item.capability === 'text_to_image');
  return typeof previous?.parameters.backgroundPrompt === 'string'
    ? previous.parameters.backgroundPrompt
    : (previous?.prompt ?? 'Stone dungeon floor');
}
