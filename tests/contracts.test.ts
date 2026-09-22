import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import Ajv from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import type { Project } from '../packages/schema/project';

const ajv = new Ajv({ strict: true, allErrors: true });
addFormats(ajv);
const validate = ajv.compile<Project>(JSON.parse(readFileSync('packages/schema/project.schema.json', 'utf8')));
const raw = readFileSync('fixtures/projects/two-rooms.json', 'utf8');

test('JSON survives Python -> TypeScript -> Python unchanged', () => {
  const value: unknown = JSON.parse(raw);
  assert.ok(validate(value), JSON.stringify(validate.errors));
  const result = spawnSync(process.env.PYTHON ?? '.venv/bin/python', ['-c',
    'import sys; from quill.models import Project; print(Project.model_validate_json(sys.stdin.read()).model_dump_json())'],
    { input: JSON.stringify(value), encoding: 'utf8', env: { ...process.env, PYTHONPATH: 'apps/server' } });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), value);
  assert.ok(validate(JSON.parse(result.stdout)));
});

const errors = JSON.parse(readFileSync('fixtures/projects/invalid/expected-errors.json', 'utf8')) as Record<string, (string | number)[]>;
for (const [name, path] of Object.entries(errors)) {
  test(`reject invalid fixture: ${name}`, () => {
    assert.equal(validate(JSON.parse(readFileSync(`fixtures/projects/invalid/${name}.json`, 'utf8'))), false);
    assert.ok(validate.errors?.some(e => e.instancePath === '/' + path.join('/')));
  });
}

test('reject coercion and unknown fields without mutation', () => {
  for (const change of [{ revision: '0' }, { unknown: true }]) {
    const value = { ...JSON.parse(raw), ...change };
    const before = JSON.stringify(value);
    assert.equal(validate(value), false);
    assert.equal(JSON.stringify(value), before);
  }
});
