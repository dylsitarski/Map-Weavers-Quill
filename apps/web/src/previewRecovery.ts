export type Recovery = {
  id: string;
  signature: string;
  prompt: string;
  seed: number;
};
export function recoveryKey(projectId: string, roomId?: string): string {
  return `quill.preview.${projectId}.${roomId ?? 'background'}`;
}
export async function previewSignature(fingerprint: string): Promise<string> {
  const bytes = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(fingerprint),
  );
  return Array.from(new Uint8Array(bytes), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
}
export function readRecovery(key: string): Recovery | null {
  try {
    const value = JSON.parse(localStorage.getItem(key) ?? 'null');
    return value &&
      typeof value.id === 'string' &&
      /^[0-9a-f-]{36}$/.test(value.id) &&
      typeof value.signature === 'string' &&
      /^[0-9a-f]{64}$/.test(value.signature) &&
      typeof value.prompt === 'string' &&
      Number.isInteger(value.seed) &&
      value.seed >= 0 &&
      value.seed <= 2147483647
      ? value
      : null;
  } catch {
    return null;
  }
}
export function rememberRecovery(key: string, value: Recovery): boolean {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}
export function forgetRecovery(key: string, id: string): void {
  try {
    if (readRecovery(key)?.id === id) localStorage.removeItem(key);
  } catch {
    /* Storage may be disabled. */
  }
}
