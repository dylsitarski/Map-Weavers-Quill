import { useEffect, useRef, useState } from 'react';
import type { Project } from '../../../packages/schema/project';
import type { ExportRequest } from '../../../packages/schema/raster';

export function ExportPanel({
  project,
  busy,
}: {
  project: Project;
  busy: boolean;
}) {
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function download(format: 'png' | 'webp') {
    const abort = new AbortController();
    controller.current = abort;
    setWorking(true);
    setError('');
    const request: ExportRequest = {
      contractVersion: '0.1.0',
      project,
      format,
    };
    try {
      const response = await fetch('/api/export/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: AbortSignal.any([abort.signal, AbortSignal.timeout(30000)]),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(
          typeof data?.detail === 'string'
            ? data.detail
            : 'Export failed. Retry.',
        );
      }
      if (
        response.headers.get('content-type')?.split(';')[0] !==
        `image/${format}`
      )
        throw new Error('The server returned an invalid image export.');
      const blob = await response.blob();
      if (abort.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${
        project.name
          .replace(/[^a-zA-Z0-9_-]+/g, '-')
          .replace(/^-|-$/g, '')
          .slice(0, 100) || 'map'
      }.${format}`;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (failure) {
      if (!abort.signal.aborted)
        setError(
          failure instanceof Error ? failure.message : 'Export failed. Retry.',
        );
    } finally {
      if (!abort.signal.aborted) setWorking(false);
    }
  }
  return (
    <section aria-label="Export artwork">
      <h3>Export artwork</h3>
      <p>
        480 × 320 pixels. Accepted artwork only, with current layer settings. No
        grid or editing guides.
      </p>
      <button
        type="button"
        disabled={busy || working}
        onClick={() => void download('png')}
      >
        Export PNG
      </button>
      <button
        type="button"
        disabled={busy || working}
        onClick={() => void download('webp')}
      >
        Export WebP
      </button>
      {working && <p>Preparing download…</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
