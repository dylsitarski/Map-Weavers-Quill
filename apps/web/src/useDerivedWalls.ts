import Ajv2020 from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import { useEffect, useState } from 'react';
import type { WallDerivationResult } from '../../../packages/schema/geometry';
import schema from '../../../packages/schema/geometry.schema.json';
import type { Room, Wall } from '../../../packages/schema/project';
import { mapSize } from './viewport';

const ajv = new Ajv2020({ strict: false });
addFormats(ajv);
const validate = ajv.compile<WallDerivationResult>({
  $defs: schema.$defs,
  $ref: '#/$defs/WallDerivationResult',
});

export function useDerivedWalls(rooms: Room[]) {
  const key = JSON.stringify({
    ...mapSize,
    rooms: rooms
      .map(({ id, polygon }) => ({ id, polygon }))
      .sort((a, b) => a.id.localeCompare(b.id)),
  });
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    walls: Wall[];
    error: string;
  } | null>(null);
  useEffect(() => {
    void attempt;
    const controller = new AbortController();
    let current = true;
    const request = JSON.parse(key);
    if (!request.rooms.length) {
      setResult({ key, walls: [], error: '' });
      return;
    }
    setResult(null);
    void (async () => {
      try {
        const response = await fetch('/api/geometry/walls', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: key,
          signal: AbortSignal.any([
            controller.signal,
            AbortSignal.timeout(10000),
          ]),
        });
        if (!response.ok) {
          const error = await response.json().catch(() => null);
          throw new Error(
            typeof error?.detail === 'string'
              ? error.detail
              : 'Check the local server and retry.',
          );
        }
        const data: unknown = await response.json();
        if (!validate(data))
          throw new Error('The server returned invalid wall data.');
        if (current) setResult({ key, walls: data.walls, error: '' });
      } catch (error) {
        if (current)
          setResult({
            key,
            walls: [],
            error: `Walls unavailable. ${error instanceof Error ? error.message : 'Retry wall derivation.'} Room geometry is unchanged.`,
          });
      }
    })();
    return () => {
      current = false;
      controller.abort();
    };
  }, [key, attempt]);
  const fresh = result?.key === key ? result : null;
  return {
    walls: fresh?.walls ?? [],
    loading: !fresh,
    error: fresh?.error ?? '',
    retry: () => setAttempt((value) => value + 1),
  };
}
