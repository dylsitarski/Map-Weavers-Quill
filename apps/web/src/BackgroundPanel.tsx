import Ajv2020 from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import { useEffect, useRef, useState } from 'react';
import type {
  Project,
  RasterLayer,
  Room,
} from '../../../packages/schema/project';
import type {
  BackgroundResult,
  GenerationJob,
} from '../../../packages/schema/raster';
import schema from '../../../packages/schema/raster.schema.json';

import {
  forgetRecovery,
  previewSignature,
  type Recovery,
  readRecovery,
  recoveryKey,
  rememberRecovery,
} from './previewRecovery';

const ajv = new Ajv2020({ strict: false });
addFormats(ajv);
const valid = ajv.compile<BackgroundResult>({
  $defs: schema.$defs,
  $ref: '#/$defs/BackgroundResult',
});
const validJob = ajv.compile<GenerationJob>({
  $defs: schema.$defs,
  $ref: '#/$defs/GenerationJob',
});
function cancelJob(id: string) {
  void fetch(`/api/jobs/${id}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
    keepalive: true,
  }).catch(() => {});
}
export function BackgroundPanel(p: {
  preview: (layer: RasterLayer | null) => void;
  active: boolean;
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
  const key = recoveryKey(p.projectId, p.room?.id);
  const [recovery, setRecovery] = useState<{
    key: string;
    value: Recovery;
  } | null>(null);
  const remembered = useRef<{ key: string; value: Recovery } | null>(null);
  const [storageWarning, setStorageWarning] = useState('');
  useEffect(() => {
    sequence.current++;
    controller.current?.abort();
    jobId.current = null;
    remembered.current = null;
    setProposal(null);
    setWorking(false);
    setError('');
    const value = readRecovery(key);
    setRecovery(value ? { key, value } : null);
  }, [key]);
  const [prompt, setPrompt] = useState('Stone dungeon floor');
  const [seed, setSeed] = useState(0);
  const [working, setWorking] = useState(false);
  const [jobStatus, setJobStatus] = useState('queued');
  const jobId = useRef<string | null>(null);
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
    if (remembered.current) {
      forgetRecovery(remembered.current.key, remembered.current.value.id);
      remembered.current = null;
    }
    setRecovery(null);
    sequence.current++;
    controller.current?.abort();
    if (jobId.current) cancelJob(jobId.current);
    jobId.current = null;
    setProposal(null);
    setWorking(false);
    setError('');
    setLoaded(false);
  }
  async function generate(resume?: Recovery) {
    if (
      resume &&
      resume.signature !== (await previewSignature(p.fingerprint))
    ) {
      setError(
        'This preview belongs to a different project state. Reopen the matching saved project or discard it and generate again.',
      );
      return;
    }
    if (!resume) {
      const previous = readRecovery(key);
      if (previous) {
        cancelJob(previous.id);
        forgetRecovery(key, previous.id);
      }
    }
    reject();
    const attempt = sequence.current;
    const abort = new AbortController();
    controller.current = abort;
    setWorking(true);
    setJobStatus('queued');
    const id = resume?.id ?? crypto.randomUUID();
    jobId.current = id;
    try {
      const value = resume ?? {
        id,
        signature: await previewSignature(p.fingerprint),
        prompt: p.room?.prompt ?? prompt,
        seed,
      };
      if (attempt !== sequence.current) return;
      remembered.current = { key, value };
      setRecovery({ key, value });
      setStorageWarning(
        rememberRecovery(key, value)
          ? ''
          : 'Browser storage is unavailable. This preview cannot be recovered after reload.',
      );
      if (resume) {
        setPrompt(resume.prompt);
        setSeed(resume.seed);
      }
      const response = resume
        ? await fetch(`/api/jobs/${id}`, { signal: abort.signal })
        : await fetch(`/api/jobs/${id}/${target}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(
              p.room
                ? { project: p.project, roomId: p.room.id, seed }
                : { prompt, seed, baseRevision: p.revision },
            ),
            signal: AbortSignal.any([abort.signal, AbortSignal.timeout(15000)]),
          });
      let data = await response.json().catch(() => null);
      if (!response.ok)
        throw new Error(
          typeof data?.detail === 'string'
            ? data.detail
            : 'Background generation failed. Retry.',
        );
      if (!validJob(data) || data.id !== id)
        throw new Error('The server returned an invalid job.');
      while (data.status === 'queued' || data.status === 'running') {
        if (abort.signal.aborted) return;
        if (attempt === sequence.current) setJobStatus(data.status);
        await new Promise<void>((resolve, reject) => {
          const cancel = () => {
            window.clearTimeout(timer);
            reject(new Error('Cancelled'));
          };
          const timer = window.setTimeout(() => {
            abort.signal.removeEventListener('abort', cancel);
            resolve();
          }, 250);
          abort.signal.addEventListener('abort', cancel, { once: true });
        });
        const poll = await fetch(`/api/jobs/${id}`, {
          signal: AbortSignal.any([abort.signal, AbortSignal.timeout(15000)]),
        });
        data = await poll.json().catch(() => null);
        if (!poll.ok || !validJob(data) || data.id !== id)
          throw new Error(`Could not read job ${id}. Retry generation.`);
      }
      if (data.status !== 'succeeded')
        throw new Error(data.error ?? `Generation ${data.status}.`);
      data = data.result;
      if (!valid(data))
        throw new Error('The server returned an invalid background proposal.');
      if (attempt === sequence.current) jobId.current = null;
      if (attempt === sequence.current)
        setProposal({
          result: data,
          context: p.context,
          fingerprint: p.fingerprint,
          projectId: p.projectId,
          roomId: p.room?.id,
        });
    } catch (failure) {
      if (attempt === sequence.current) jobId.current = null;
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
  useEffect(() => {
    setLoaded(false);
    if (!proposal || stale) return;
    const image = new window.Image();
    image.onload = () => setLoaded(true);
    image.onerror = () =>
      setError('Could not load the preview image. Regenerate to retry.');
    image.src = `/api/assets/${proposal.result.layer.assetHash}`;
    return () => {
      image.onload = null;
      image.onerror = null;
    };
  }, [proposal, stale]);
  useEffect(() => {
    p.preview(
      proposal && !stale && loaded && p.active ? proposal.result.layer : null,
    );
    return () => p.preview(null);
  }, [proposal, stale, loaded, p.active, p.preview]);
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
      {recovery?.key === key && !working && !proposal && (
        <div>
          <button
            type="button"
            disabled={p.busy || p.count >= 128}
            onClick={() => void generate(recovery.value)}
          >
            Recover preview
          </button>
          <button
            type="button"
            disabled={p.busy}
            onClick={() => {
              cancelJob(recovery.value.id);
              forgetRecovery(key, recovery.value.id);
              setRecovery(null);
              setError('');
            }}
          >
            Discard recoverable preview
          </button>
        </div>
      )}
      {storageWarning && <p role="alert">{storageWarning}</p>}
      {p.count >= 128 && <p>Generation history limit reached (128 records).</p>}
      {working && (
        <>
          <p>
            {jobStatus === 'queued'
              ? 'Queued for generation…'
              : 'Generating preview…'}
          </p>
          <button type="button" onClick={reject}>
            Cancel preview
          </button>
        </>
      )}
      {error && <p role="alert">{error}</p>}
      {proposal && (
        <>
          <p>
            Preview:{' '}
            {String(
              proposal.result.generation.parameters.roomPrompt ??
                proposal.result.generation.prompt,
            )}{' '}
            · seed {String(proposal.result.generation.parameters.seed)}
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
