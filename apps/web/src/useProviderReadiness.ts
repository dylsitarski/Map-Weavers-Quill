import Ajv2020 from 'ajv/dist/2020';
import { useEffect, useState } from 'react';
import type { ProviderReadiness } from '../../../packages/schema/provider';
import schema from '../../../packages/schema/provider.schema.json';

const validate = new Ajv2020({ strict: false }).compile<ProviderReadiness>({
  $defs: schema.$defs,
  $ref: '#/$defs/ProviderReadiness',
});

export function useProviderReadiness() {
  const [state, setState] = useState<ProviderReadiness | null>(null);
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(true);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    void attempt; // An explicit retry starts a new readiness request.
    const controller = new AbortController();
    setChecking(true);
    setState(null);
    setError('');
    async function check() {
      try {
        const response = await fetch('/api/providers/readiness', {
          signal: AbortSignal.any([
            controller.signal,
            AbortSignal.timeout(35000),
          ]),
        });
        const data: unknown = await response.json();
        if (!response.ok || !validate(data))
          throw new Error(
            'Could not check the image provider. Retry the check.',
          );
        if (!controller.signal.aborted) setState(data);
      } catch {
        if (!controller.signal.aborted)
          setError('Could not check the image provider. Retry the check.');
      } finally {
        if (!controller.signal.aborted) setChecking(false);
      }
    }
    void check();
    return () => controller.abort();
  }, [attempt]);
  return { state, error, checking, refresh: () => setAttempt((n) => n + 1) };
}
