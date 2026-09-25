import { readFile, writeFile } from 'node:fs/promises';
import { compile } from 'json-schema-to-typescript';

for (const name of [
  'project',
  'provider',
  'geometry',
  'persistence',
  'raster',
]) {
  const schema = JSON.parse(
    await readFile(`packages/schema/${name}.schema.json`, 'utf8'),
  );
  const text = await compile(schema, schema.title, {
    bannerComment: '/* Generated. Run make schema; do not edit. */',
  });
  const path = `packages/schema/${name}.d.ts`;
  if (process.argv.includes('--check')) {
    if ((await readFile(path, 'utf8').catch(() => '')) !== text)
      throw Error(`Type drift: ${path}`);
  } else await writeFile(path, text);
}
