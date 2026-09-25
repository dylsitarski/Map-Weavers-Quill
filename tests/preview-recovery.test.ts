import assert from 'node:assert/strict';
import test from 'node:test';
import {
  forgetRecovery,
  previewSignature,
  readRecovery,
  recoveryKey,
  rememberRecovery,
} from '../apps/web/src/previewRecovery';

test('recovery fingerprints and storage preserve target identity and never erase a newer job', async () => {
  const entries = new Map<string, string>();
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => entries.get(key) ?? null,
      setItem: (key: string, value: string) => entries.set(key, value),
      removeItem: (key: string) => entries.delete(key),
    },
  });
  try {
    const key = recoveryKey('project', 'room');
    assert.notEqual(key, recoveryKey('project'));
    const signature = await previewSignature('document');
    assert.equal(signature, await previewSignature('document'));
    assert.notEqual(signature, await previewSignature('changed'));
    const value = {
      id: crypto.randomUUID(),
      signature,
      prompt: 'floor',
      seed: 0,
    };
    assert.equal(rememberRecovery(key, value), true);
    assert.deepEqual(readRecovery(key), value);
    forgetRecovery(key, crypto.randomUUID());
    assert.deepEqual(readRecovery(key), value);
    forgetRecovery(key, value.id);
    assert.equal(readRecovery(key), null);
    entries.set(key, '{broken');
    assert.equal(readRecovery(key), null);
    entries.set(key, JSON.stringify({ ...value, seed: -1 }));
    assert.equal(readRecovery(key), null);
  } finally {
    Reflect.deleteProperty(globalThis, 'localStorage');
  }
});
