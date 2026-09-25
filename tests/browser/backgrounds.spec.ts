import { expect, type Page, test } from '@playwright/test';

async function pixels(page: Page) {
  return page.locator('canvas').evaluate(async (canvas) => {
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    return (canvas as HTMLCanvasElement).toDataURL();
  });
}
async function background(page: Page) {
  await page.getByRole('button', { name: 'Map', exact: true }).click();
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
}
async function generate(page: Page) {
  await page
    .getByRole('button', {
      name: /Generate preview|Regenerate preview/,
      exact: true,
    })
    .click();
  await expect(
    page.getByRole('button', { name: 'Accept background', exact: true }),
  ).toBeEnabled();
}
test('background preview rejection, acceptance, undo, regeneration and save/open', async ({
  page,
}) => {
  await page.goto('/');
  await background(page);
  const blank = await pixels(page);
  await generate(page);
  const preview = await page
    .getByRole('img', { name: 'Generated background preview' })
    .getAttribute('src');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-background-hash',
    '',
  );
  await page.getByRole('button', { name: 'Reject preview' }).click();
  await expect(
    page.getByRole('button', { name: 'Undo', exact: true }),
  ).toBeDisabled();
  await generate(page);
  await page.getByRole('button', { name: 'Accept background' }).click();
  const hash = preview?.split('/').pop() ?? '';
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-background-hash',
    hash,
  );
  await expect.poll(() => pixels(page)).not.toBe(blank);
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-background-hash',
    '',
  );
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-background-hash',
    hash,
  );
  // Artwork survives room creation and remains independent of geometry.
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .click();
  await page.mouse.move(450, 280);
  await page.mouse.down();
  await page.mouse.move(700, 450);
  await page.mouse.up();
  await expect(page.locator('[data-room-id]')).toHaveCount(1);
  const geometry = await page
    .locator('[data-room-id]')
    .getAttribute('data-geometry');
  await page.getByRole('button', { name: 'Map', exact: true }).click();
  await page.getByRole('tab', { name: 'Layers', exact: true }).click();
  await page
    .getByRole('combobox', { name: 'Background opacity' })
    .selectOption('0.5');
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  await page.getByRole('spinbutton', { name: 'Seed', exact: true }).fill('1');
  await generate(page);
  await page.getByRole('button', { name: 'Accept background' }).click();
  await expect(page.getByTestId('map-canvas')).not.toHaveAttribute(
    'data-background-hash',
    hash,
  );
  const nextHash = await page
    .getByTestId('map-canvas')
    .getAttribute('data-background-hash');
  await expect(page.locator('[data-room-id]')).toHaveAttribute(
    'data-geometry',
    geometry ?? '',
  );
  await page.getByRole('button', { name: 'File', exact: true }).click();
  const name = `Background ${crypto.randomUUID()}`;
  await page.getByRole('textbox', { name: 'Project name' }).fill(name);
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  await expect(page.getByTestId('save-status')).toHaveText(
    'Saved · revision 1',
  );
  const savedPixels = await pixels(page);
  await page.reload();
  await page.getByRole('button', { name: 'File', exact: true }).click();
  await page
    .getByRole('button', { name: `${name} · revision 1`, exact: true })
    .click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-background-hash',
    nextHash ?? '',
  );
  await page.getByRole('tab', { name: 'Layers', exact: true }).click();
  await expect(
    page.getByRole('combobox', { name: 'Background opacity' }),
  ).toHaveValue('0.5');
  await expect.poll(() => pixels(page)).toBe(savedPixels);
});
test('geometry changes invalidate previews, including undo to the original scene', async ({
  page,
}) => {
  await page.goto('/');
  await background(page);
  await generate(page);
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .click();
  await page.mouse.move(450, 280);
  await page.mouse.down();
  await page.mouse.move(700, 450);
  await page.mouse.up();
  await expect(page.locator('[data-room-id]')).toHaveCount(1);
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await page.getByRole('button', { name: 'Map', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('project changed');
  await expect(
    page.getByRole('button', { name: 'Accept background' }),
  ).toBeDisabled();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-background-hash',
    '',
  );
});
test('cancel ignores a late response and failures allow retry', async ({
  page,
}) => {
  let release = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let started = false;
  await page.route('**/api/generation/background', async (route) => {
    const response = await route.fetch();
    started = true;
    await gate;
    await route.fulfill({ response });
  });
  await page.goto('/');
  await background(page);
  await page.getByRole('button', { name: 'Generate preview' }).click();
  await expect.poll(() => started).toBe(true);
  await page.getByRole('button', { name: 'Cancel preview' }).click();
  release();
  await expect(
    page.getByRole('button', { name: 'Accept background' }),
  ).toHaveCount(0);
  await page.unroute('**/api/generation/background');
  await page.route('**/api/generation/background', (route) =>
    route.fulfill({ status: 503, json: { detail: 'Mock unavailable' } }),
  );
  await page.getByRole('button', { name: 'Generate preview' }).click();
  await expect(page.getByRole('alert')).toContainText('Mock unavailable');
  await page.unroute('**/api/generation/background');
  await generate(page);
});
