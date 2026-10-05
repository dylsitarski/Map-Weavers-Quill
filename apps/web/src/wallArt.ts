import type { WallArtRequest } from '../../../packages/schema/geometry';
import type { Door, Project, Room } from '../../../packages/schema/project';

// Deterministic wall/door artwork settings (ADR-0030). The server renders the
// overlay for both this editor preview and flattened export.
export const wallMaterials = ['stone', 'timber', 'plaster'] as const;
export type WallMaterial = (typeof wallMaterials)[number];
export type WallArtSettings = { visible: boolean; material: WallMaterial };
export const wallArtKey = 'quill.wallArt';
export const defaultWallArt: WallArtSettings = {
  visible: true,
  material: 'stone',
};
export const wallThicknessLimits = { min: 1, max: 50 } as const;
// Sharper than export (2 pixels per native unit) so zoomed previews stay legible.
export const previewSize = { width: 2400, height: 1600 } as const;

export function wallArtSettings(
  settings: Project['settings'],
): WallArtSettings {
  const value = settings[wallArtKey];
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const { visible, material } = value as Record<string, unknown>;
    if (
      typeof visible === 'boolean' &&
      wallMaterials.includes(material as WallMaterial)
    )
      return { visible, material: material as WallMaterial };
  }
  return defaultWallArt;
}

export function validThickness(value: number): boolean {
  return (
    Number.isFinite(value) &&
    value >= wallThicknessLimits.min &&
    value <= wallThicknessLimits.max
  );
}

/** One undoable map-authoring change; other settings and style fields are kept. */
export function changeWallArt(
  authoring: { style: Project['map']['style']; settings: Project['settings'] },
  changes: Partial<WallArtSettings> & { thickness?: number },
) {
  const { thickness, ...settingChanges } = changes;
  return {
    style:
      thickness === undefined
        ? authoring.style
        : { ...authoring.style, wallThicknessPx: thickness },
    settings: {
      ...authoring.settings,
      [wallArtKey]: {
        ...wallArtSettings(authoring.settings),
        ...settingChanges,
      },
    },
  };
}

export function wallArtRequest(
  rooms: Room[],
  doors: Door[],
  thickness: number,
  material: WallMaterial,
): WallArtRequest {
  return {
    ...previewSize,
    thickness,
    material,
    rooms: rooms
      .map(({ id, polygon }) => ({ id, polygon }))
      .sort((a, b) => a.id.localeCompare(b.id)),
    doors,
  };
}
