import Ajv2020 from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import { useEffect, useRef, useState } from 'react';
import type {
  MapStyle,
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
import { useProviderReadiness } from './useProviderReadiness';

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
const MAX_SEED = 2147483647;
export function randomSeed(): number {
  const value = new Uint32Array(1);
  crypto.getRandomValues(value);
  return value[0] % (MAX_SEED + 1);
}
function cancelJob(id: string) {
  void fetch(`/api/jobs/${id}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
    keepalive: true,
  }).catch(() => {});
}
export function BackgroundPanel(p: {
  mapPrompt?: string;
  mapStyle?: MapStyle;
  saveMap?: (prompt: string, style: MapStyle) => void;
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
  const provider = useProviderReadiness();
  const canGenerate =
    provider.state?.ready &&
    provider.state.descriptor.capabilities.includes(
      p.room ? 'inpainting' : 'text_to_image',
    );
  const providerId = provider.state?.descriptor.id;
  const klein = providerId === 'comfyui-flux2-klein';
  const localComfy = providerId === 'comfyui-sdxl' || klein;
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
  const [prompt, setPrompt] = useState(p.mapPrompt ?? 'Stone dungeon floor');
  const [styleDraft, setStyleDraft] = useState(p.mapStyle);
  useEffect(() => {
    void p.projectId;
    setPrompt(p.mapPrompt ?? 'Stone dungeon floor');
    setStyleDraft(p.mapStyle);
  }, [p.mapPrompt, p.mapStyle, p.projectId]);
  const mapDraftDirty =
    !p.room &&
    (prompt !== p.mapPrompt ||
      JSON.stringify(styleDraft) !== JSON.stringify(p.mapStyle));
  // A new random seed per generation unless the seed is locked (typing one locks it).
  const [seed, setSeed] = useState(randomSeed);
  const [seedLocked, setSeedLocked] = useState(false);
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
    const used = resume?.seed ?? (seedLocked ? seed : randomSeed());
    setSeed(used);
    try {
      const value = resume ?? {
        id,
        signature: await previewSignature(p.fingerprint),
        prompt: p.room?.prompt ?? p.mapPrompt ?? prompt,
        seed: used,
      };
      if (attempt !== sequence.current) return;
      remembered.current = { key, value };
      setRecovery({ key, value });
      setStorageWarning(
        rememberRecovery(key, value)
          ? ''
          : 'Browser storage is unavailable. This preview cannot be recovered after reload.',
      );
      const response = resume
        ? await fetch(`/api/jobs/${id}`, { signal: abort.signal })
        : await fetch(`/api/jobs/${id}/${target}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(
              p.room
                ? { project: p.project, roomId: p.room.id, seed: used }
                : {
                    prompt: p.mapPrompt ?? prompt,
                    style: p.mapStyle,
                    seed: used,
                    baseRevision: p.revision,
                  },
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
      <div>
        <p>
          {provider.checking
            ? 'Checking image provider…'
            : provider.state?.descriptor.id === 'mock'
              ? 'Offline mock: generates a deterministic test pattern, not AI artwork.'
              : klein
                ? 'Local FLUX.2 klein · ComfyUI'
                : localComfy
                  ? 'Local SDXL · ComfyUI'
                  : 'Image provider unavailable'}
        </p>
        {provider.state && (
          <p>
            {provider.state.message} ·{' '}
            {provider.state.descriptor.capabilities
              .filter((c) => c === 'text_to_image' || c === 'inpainting')
              .map((c) =>
                c === 'text_to_image'
                  ? 'Background generation'
                  : 'Room editing',
              )
              .join(' · ')}
          </p>
        )}
        {provider.error && <p role="alert">{provider.error}</p>}
        <button
          type="button"
          disabled={provider.checking || working}
          onClick={provider.refresh}
        >
          Check provider
        </button>
        {localComfy && !p.room && (
          <p>Backgrounds do not yet follow drawn buildings or entrances.</p>
        )}
        {localComfy && p.room && (
          <p>
            {klein
              ? 'The room is sent as a floor-plan sketch; doors are drawn closed and secret doors as wall. Every room uses the same physical scale; describe the floor and contents, then inspect the preview.'
              : provider.state?.descriptor.capabilities.includes(
                    'control_image',
                  )
                ? 'Wall and door guidance enabled. Physical scale is included; inspect the preview for accuracy.'
                : 'Wall and door guidance is not enabled. Configure the SDXL ControlNet model to use the drawn layout.'}
          </p>
        )}
        {localComfy && (
          <p>
            960 × 640 map artwork. Cancelling discards the preview; ComfyUI may
            continue working.
          </p>
        )}
      </div>
      {p.room ? (
        <p>Uses the applied room prompt: {p.room.prompt || '(empty)'}</p>
      ) : (
        <form
          aria-label="Map authoring"
          onSubmit={(e) => {
            e.preventDefault();
            if (styleDraft) p.saveMap?.(prompt, styleDraft);
          }}
        >
          <label>
            Background prompt
            <textarea
              value={prompt}
              maxLength={4000}
              disabled={working || p.busy}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </label>
          <p>
            Map defaults · inherited by rooms unless overridden. Describe the
            setting in the background and room prompts.
          </p>
          {styleDraft?.environment && (
            <p>
              Map environment "{styleDraft.environment}" is no longer used.{' '}
              <button
                type="button"
                disabled={working || p.busy}
                onClick={() =>
                  styleDraft &&
                  setStyleDraft({ ...styleDraft, environment: '' })
                }
              >
                Clear unused environment
              </button>
            </p>
          )}
          {styleDraft &&
            (
              [
                ['renderStyle', 'Map render style'],
                ['palette', 'Map palette'],
              ] as const
            ).map(([key, label]) => (
              <label key={key}>
                {label}
                <input
                  value={styleDraft[key]}
                  maxLength={512}
                  disabled={working || p.busy}
                  onChange={(e) =>
                    setStyleDraft({ ...styleDraft, [key]: e.target.value })
                  }
                />
              </label>
            ))}
          <button type="submit" disabled={working || p.busy || !mapDraftDirty}>
            Apply map prompt and style
          </button>
          <p>Apply, then save the project to keep these settings.</p>
        </form>
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
          onChange={(e) => {
            setSeed(e.target.valueAsNumber);
            setSeedLocked(true);
          }}
        />
      </label>
      <label>
        <input
          type="checkbox"
          checked={seedLocked}
          disabled={working}
          onChange={(e) => setSeedLocked(e.target.checked)}
        />
        Lock seed
      </label>
      <button
        type="button"
        disabled={
          working ||
          !canGenerate ||
          p.busy ||
          mapDraftDirty ||
          p.count >= 128 ||
          (seedLocked &&
            (!Number.isInteger(seed) || seed < 0 || seed > MAX_SEED))
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
                proposal.result.generation.parameters.backgroundPrompt ??
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
