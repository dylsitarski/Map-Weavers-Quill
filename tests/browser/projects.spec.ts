import { expect, type Page, test } from '@playwright/test';

async function canvasPixels(page: Page) {
  return page.locator('canvas').evaluate(async (canvas) => {
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    return (canvas as HTMLCanvasElement).toDataURL();
  });
}
async function rectangle(page: Page, left: number, right: number) {
  await page.mouse.move(left, 280);
  await page.mouse.down();
  await page.mouse.move(right, 450);
  await page.mouse.up();
}
test('connected rooms and a door save and reopen with identical geometry and canvas', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .click();
  await rectangle(page, 450, 700);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-wall-count',
    '4',
  );
  await rectangle(page, 700, 868);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-wall-count',
    '7',
  );
  await page
    .getByRole('button', { name: 'Place/edit door', exact: true })
    .click();
  await page.mouse.click(682, 360);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-door-count',
    '1',
  );
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  const geometry = await page
    .locator('[data-room-id]')
    .evaluateAll((nodes) =>
      nodes.map((node) => [
        node.getAttribute('data-room-id'),
        node.getAttribute('data-geometry'),
      ]),
    );
  const before = await canvasPixels(page);
  await page.getByRole('button', { name: 'File', exact: true }).click();
  const name = `Round trip ${crypto.randomUUID()}`;
  await page.getByRole('textbox', { name: 'Project name' }).fill(name);
  const saved = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/projects/save') &&
      response.status() === 200,
  );
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  const document = await (await saved).json();
  await expect(page.getByTestId('save-status')).toHaveText(
    'Saved · revision 1',
  );
  await page.reload();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-door-count',
    '0',
  );
  await page.getByRole('button', { name: 'File', exact: true }).click();
  await page
    .getByRole('button', { name: `${name} · revision 1`, exact: true })
    .click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-door-count',
    '1',
  );
  await expect(page.getByTestId('save-status')).toHaveText(
    'Saved · revision 1',
  );
  await expect(
    page.getByRole('button', { name: 'Undo', exact: true }),
  ).toBeDisabled();
  await page.getByRole('button', { name: 'File', exact: true }).click();
  expect(
    await page
      .locator('[data-room-id]')
      .evaluateAll((nodes) =>
        nodes.map((node) => [
          node.getAttribute('data-room-id'),
          node.getAttribute('data-geometry'),
        ]),
      ),
  ).toEqual(geometry);
  expect(await canvasPixels(page)).toEqual(before);
  const reopened = await page.request.get(
    `/api/projects/${document.projectId}`,
  );
  expect(await reopened.json()).toEqual(document);
});
test('save failure and revision conflict preserve edits; new project can be cancelled', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'File', exact: true }).click();
  const name = `Recovery ${crypto.randomUUID()}`;
  await page.getByRole('textbox', { name: 'Project name' }).fill(name);
  await page.route('**/api/projects/save', (route) =>
    route.fulfill({ status: 503, json: { detail: 'Disk unavailable' } }),
  );
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Disk unavailable');
  await expect(page.getByTestId('save-status')).toHaveText('Unsaved changes');
  await page.unroute('**/api/projects/save');
  const saving = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/projects/save') &&
      response.status() === 200,
  );
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  const project = await (await saving).json();
  await expect(page.getByTestId('save-status')).toHaveText(
    'Saved · revision 1',
  );
  const external = await page.request.post('/api/projects/save', {
    data: {
      expectedRevision: 1,
      project: { ...project, name: 'Other session' },
    },
  });
  expect(external.status()).toBe(200);
  await page
    .getByRole('textbox', { name: 'Project name' })
    .fill('My unsaved edit');
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('another session');
  await expect(page.getByRole('textbox', { name: 'Project name' })).toHaveValue(
    'My unsaved edit',
  );
  await page.route(`**/api/projects/${project.projectId}`, (route) =>
    route.fulfill({ status: 200, json: { broken: true } }),
  );
  page.once('dialog', (dialog) => dialog.accept());
  await page
    .getByRole('button', { name: `${name} · revision 1`, exact: true })
    .click();
  await expect(page.getByRole('alert')).toContainText('invalid project');
  await expect(page.getByRole('textbox', { name: 'Project name' })).toHaveValue(
    'My unsaved edit',
  );
  page.once('dialog', (dialog) => dialog.dismiss());
  await page.getByRole('button', { name: 'New project', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Project name' })).toHaveValue(
    'My unsaved edit',
  );
  page.once('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'New project', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Project name' })).toHaveValue(
    'Untitled map',
  );
  await expect(page.getByTestId('save-status')).toHaveText('Not saved');
});
