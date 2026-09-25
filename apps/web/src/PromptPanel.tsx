import { useState } from 'react';
import type { MapStyle, Room } from '../../../packages/schema/project';

export function PromptPanel({
  room,
  busy,
  mapStyle,
  save,
}: {
  room: Room;
  busy: boolean;
  mapStyle: MapStyle;
  save: (prompt: string, styleOverrides: Room['styleOverrides']) => void;
}) {
  const [prompt, setPrompt] = useState(room.prompt);
  const [style, setStyle] = useState(room.styleOverrides);
  return (
    <form
      aria-label="AI prompt"
      onSubmit={(e) => {
        e.preventDefault();
        save(prompt, style);
      }}
    >
      <h2>{room.label}</h2>
      <p>Apply your room prompt and style before generating.</p>
      <label>
        Room prompt
        <textarea
          value={prompt}
          maxLength={4000}
          disabled={busy}
          onChange={(e) => setPrompt(e.target.value)}
        />
      </label>
      <p>Room style · leave blank to inherit the map style.</p>
      {(
        [
          ['environment', 'Environment'],
          ['renderStyle', 'Render style'],
          ['palette', 'Palette'],
        ] as const
      ).map(([key, label]) => (
        <label key={key}>
          {label}
          <input
            value={style[key] ?? ''}
            placeholder={mapStyle[key]}
            maxLength={512}
            disabled={busy}
            onChange={(e) =>
              setStyle((current) => {
                const next = { ...current };
                if (e.target.value.trim()) next[key] = e.target.value;
                else delete next[key];
                return next;
              })
            }
          />
        </label>
      ))}
      <button
        type="submit"
        disabled={
          busy ||
          (prompt === room.prompt &&
            JSON.stringify(style) === JSON.stringify(room.styleOverrides))
        }
      >
        Apply prompt and style
      </button>
      <p>
        Save the project to keep applied prompts, styles and accepted artwork.
      </p>
    </form>
  );
}
