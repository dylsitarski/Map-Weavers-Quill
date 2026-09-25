import Ajv2020 from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import { useEffect, useRef, useState } from 'react';
import type { Project, Room } from '../../../packages/schema/project';
import type { BackgroundResult } from '../../../packages/schema/raster';
import schema from '../../../packages/schema/raster.schema.json';

const ajv = new Ajv2020({ strict: false });
addFormats(ajv);
const valid = ajv.compile<BackgroundResult>({
  $defs: schema.$defs,
  $ref: '#/$defs/BackgroundResult',
});
export function BackgroundPanel(p: {
  room?: Room | null;
  project?: Project;
  context: object;
  fingerprint: string;
  projectId: string;
  revision: number;
  busy: boolean;
  count: number;
  accept: (result: BackgroundResult) => void;
}) {
  const target = p.room ? 'room' : 'background';
  const [prompt, setPrompt] = useState('Stone dungeon floor');
  const [seed, setSeed] = useState(0);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState(false);
  const [proposal, setProposal] = useState<{
    result: BackgroundResult;
    context: object;
    fingerprint: string;
    projectId: string;
    roomId?: string;
  } | null>(null);
  const controller = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  useEffect(
    () => () => {
      sequence.current++;
      controller.current?.abort();
    },
    [],
  );
  function reject() {
    sequence.current++;
    controller.current?.abort();
    setProposal(null);
    setWorking(false);
    setError('');
    setLoaded(false);
  }
  async function generate() {
    reject();
    const attempt = sequence.current;
    const abort = new AbortController();
    controller.current = abort;
    setWorking(true);
    try {
      const response = await fetch(`/api/generation/${target}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(
          p.room
            ? { project: p.project, roomId: p.room.id, seed }
            : { prompt, seed, baseRevision: p.revision },
        ),
        signal: AbortSignal.any([abort.signal, AbortSignal.timeout(15000)]),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok)
        throw new Error(
          typeof data?.detail === 'string'
            ? data.detail
            : 'Background generation failed. Retry.',
        );
      if (!valid(data))
        throw new Error('The server returned an invalid background proposal.');
      if (attempt === sequence.current)
        setProposal({
          result: data,
          context: p.context,
          fingerprint: p.fingerprint,
          projectId: p.projectId,
          roomId: p.room?.id,
        });
    } catch (failure) {
      if (attempt === sequence.current)
        setError(
          failure instanceof Error ? failure.message : 'Generation failed.',
        );
    } finally {
      if (attempt === sequence.current) setWorking(false);
    }
  }
  const stale =
    proposal &&
    (proposal.context !== p.context ||
      proposal.fingerprint !== p.fingerprint ||
      proposal.projectId !== p.projectId ||
      proposal.roomId !== p.room?.id);
  return (
    <section aria-label={p.room ? 'Room generation' : 'Background generation'}>
      <h2>{p.room ? 'Room artwork' : 'Map background'}</h2>
      <p>
        Offline mock: generates a deterministic test pattern, not AI artwork.
      </p>
      {p.room ? (
        <p>Uses the applied room prompt: {p.room.prompt || '(empty)'}</p>
      ) : (
        <label>
          Background prompt
          <textarea
            maxLength={4000}
            value={prompt}
            disabled={working}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </label>
      )}
      <label>
        Seed
        <input
          type="number"
          min="0"
          max="2147483647"
          step="1"
          value={Number.isFinite(seed) ? seed : ''}
          disabled={working}
          onChange={(e) => setSeed(e.target.valueAsNumber)}
        />
      </label>
      <button
        type="button"
        disabled={
          working ||
          p.busy ||
          p.count >= 128 ||
          !Number.isInteger(seed) ||
          seed < 0 ||
          seed > 2147483647
        }
        onClick={() => void generate()}
      >
        {proposal ? 'Regenerate preview' : 'Generate preview'}
      </button>
      {p.count >= 128 && <p>Generation history limit reached (128 records).</p>}
      {working && (
        <>
          <p>Generating preview…</p>
          <button type="button" onClick={reject}>
            Cancel preview
          </button>
        </>
      )}
      {error && <p role="alert">{error}</p>}
      {proposal && (
        <>
          <img
            className="background-preview"
            src={`/api/assets/${proposal.result.layer.assetHash}`}
            alt={
              p.room ? 'Generated room preview' : 'Generated background preview'
            }
            onLoad={() => setLoaded(true)}
            onError={() => {
              setLoaded(false);
              setError(
                'Could not load the preview image. Regenerate to retry.',
              );
            }}
          />
          <p>
            Preview: {proposal.result.generation.prompt} · seed{' '}
            {String(proposal.result.generation.parameters.seed)}
          </p>
          {stale && (
            <p role="alert">
              The project changed. Regenerate the preview before accepting.
            </p>
          )}
          <button
            type="button"
            disabled={p.busy || !!stale || !loaded}
            onClick={() => {
              p.accept(proposal.result);
              reject();
            }}
          >
            {p.room ? 'Accept room artwork' : 'Accept background'}
          </button>
          <button type="button" onClick={reject}>
            Reject preview
          </button>
        </>
      )}
    </section>
  );
}
