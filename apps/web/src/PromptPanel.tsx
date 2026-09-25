import { useState } from 'react';
import type { Room } from '../../../packages/schema/project';

export function PromptPanel({
  room,
  busy,
  save,
}: {
  room: Room;
  busy: boolean;
  save: (prompt: string) => void;
}) {
  const [prompt, setPrompt] = useState(room.prompt);
  return (
    <form
      aria-label="AI prompt"
      onSubmit={(e) => {
        e.preventDefault();
        save(prompt);
      }}
    >
      <h2>{room.label}</h2>
      <p>Apply your room appearance prompt before generating.</p>
      <label>
        Room prompt
        <textarea
          value={prompt}
          disabled={busy}
          onChange={(e) => setPrompt(e.target.value)}
        />
      </label>
      <button type="submit" disabled={busy || prompt === room.prompt}>
        Apply prompt
      </button>
      <p>Save the project to keep applied prompts and accepted artwork.</p>
    </form>
  );
}
