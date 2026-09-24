import { expect, type Page, test } from '@playwright/test';

async function setup(page: Page, connected = false) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .click();
  await page.mouse.move(450, 280);
  await page.mouse.down();
  await page.mouse.move(700, 450);
  await page.mouse.up();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-wall-count',
    '4',
  );
  if (connected) {
    await page.mouse.move(700, 280);
    await page.mouse.down();
    await page.mouse.move(868, 450);
    await page.mouse.up();
    await expect(page.getByTestId('map-canvas')).toHaveAttribute(
      'data-wall-count',
      '7',
    );
  }
  await page
    .getByRole('button', { name: 'Place/edit door', exact: true })
    .click();
  await page.mouse.click(682, 360);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-door-count',
    '1',
  );
}
test('place, inspect, reject overlap, edit and undo doors', async ({
  page,
}) => {
  await setup(page, true);
  const inspector = page.getByRole('region', { name: 'Door inspector' });
  const id = await inspector.getAttribute('data-door-id');
  await expect(
    inspector.getByRole('spinbutton', { name: 'Width', exact: true }),
  ).toHaveValue('50');
  await inspector
    .getByRole('combobox', { name: 'State', exact: true })
    .selectOption('open');
  await page.getByRole('button', { name: 'Apply door', exact: true }).click();
  await expect(inspector.getByRole('combobox')).toHaveValue('open');
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(inspector.getByRole('combobox')).toHaveValue('closed');
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(inspector.getByRole('combobox')).toHaveValue('open');
  await inspector
    .getByRole('spinbutton', { name: 'Width', exact: true })
    .fill('1000');
  await page.getByRole('button', { name: 'Apply door', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('full door opening');
  await page.getByRole('button', { name: 'Reset door', exact: true }).click();
  await expect(
    inspector.getByRole('spinbutton', { name: 'Width', exact: true }),
  ).toHaveValue('50');
  await page.getByRole('button', { name: 'Dismiss error' }).click();
  // Click outside the existing opening, with a wider proposed overlapping door.
  await page.getByRole('spinbutton', { name: 'New door width' }).fill('100');
  await page.mouse.click(682, 402);
  await expect(page.getByRole('alert')).toContainText('overlap');
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-door-count',
    '1',
  );
  await page.getByRole('button', { name: 'Dismiss error' }).click();
  await page.getByRole('tab', { name: 'Layers', exact: true }).click();
  await page.mouse.click(682, 360);
  await expect(
    page.getByRole('tab', { name: 'Layers', exact: true }),
  ).toHaveAttribute('aria-selected', 'true');
  await page.getByRole('tab', { name: 'Information', exact: true }).click();
  await expect(inspector).toHaveAttribute('data-door-id', id ?? '');
  await page.getByRole('button', { name: 'Delete door', exact: true }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-door-count',
    '0',
  );
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(inspector).toHaveAttribute('data-door-id', id ?? '');
});
test('room movement and door remapping form one undoable transaction; deletion is protected', async ({
  page,
}) => {
  await setup(page);
  const inspector = page.getByRole('region', { name: 'Door inspector' });
  const original = await inspector.getAttribute('data-wall-id');
  await page
    .getByRole('button', { name: 'Select/edit room', exact: true })
    .click();
  await page.mouse.move(550, 350);
  await page.mouse.down();
  await page.mouse.move(592, 350, { steps: 4 });
  await page.mouse.up();
  await expect(
    page.getByRole('spinbutton', { name: 'Vertex 1 x', exact: true }),
  ).toHaveValue('400');
  await page.getByRole('button', { name: 'Delete room', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Delete the door first');
  await expect(page.locator('[data-room-id]')).toHaveCount(1);
  await page.getByRole('button', { name: 'Dismiss error' }).click();
  await page
    .getByRole('button', { name: 'Place/edit door', exact: true })
    .click();
  await page.mouse.click(724, 360);
  await expect(inspector).toBeVisible();
  await expect(inspector).not.toHaveAttribute('data-wall-id', original ?? '');
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(inspector).toHaveAttribute('data-wall-id', original ?? '');
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(inspector).not.toHaveAttribute('data-wall-id', original ?? '');
});

test('failed door validation preserves the scene and allows retry', async ({
  page,
}) => {
  await setup(page);
  const inspector = page.getByRole('region', { name: 'Door inspector' });
  await page.route('**/api/geometry/doors', (route) =>
    route.fulfill({ status: 503, json: {} }),
  );
  await inspector
    .getByRole('spinbutton', { name: 'Width', exact: true })
    .fill('75');
  await page.getByRole('button', { name: 'Apply door', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Nothing was changed');
  await page.getByRole('button', { name: 'Reset door', exact: true }).click();
  await expect(
    inspector.getByRole('spinbutton', { name: 'Width', exact: true }),
  ).toHaveValue('50');
  await page.unroute('**/api/geometry/doors');
  await inspector
    .getByRole('spinbutton', { name: 'Width', exact: true })
    .fill('75');
  await page.getByRole('button', { name: 'Apply door', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(
    inspector.getByRole('spinbutton', { name: 'Width', exact: true }),
  ).toHaveValue('50');
});

test('midpoint doors slide on their parent wall, clamp at endpoints and undo once', async ({
  page,
}) => {
  await setup(page);
  const inspector = page.getByRole('region', { name: 'Door inspector' });
  const wall = await inspector.getAttribute('data-wall-id');
  await expect(inspector).toHaveAttribute('data-position', '0.625');
  await page.mouse.move(682, 339);
  await page.mouse.down();
  await page.mouse.move(730, 381, { steps: 5 });
  await page.mouse.up();
  await expect(inspector).toHaveAttribute('data-position', '0.375');
  await expect(inspector).toHaveAttribute('data-wall-id', wall ?? '');
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(inspector).toHaveAttribute('data-position', '0.625');
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(inspector).toHaveAttribute('data-position', '0.375');
  await page.mouse.move(682, 381);
  await page.mouse.down();
  await page.mouse.move(682, 500, { steps: 5 });
  await page.mouse.up();
  await expect(inspector).toHaveAttribute('data-position', '0.125');
  await expect(
    inspector.getByRole('spinbutton', { name: 'Width', exact: true }),
  ).toHaveValue('50');
  // Unsnapped sliding is continuous and keeps the same parent.
  await page.getByRole('checkbox', { name: 'Snap', exact: true }).uncheck();
  await page.mouse.move(682, 423);
  await page.mouse.down();
  await page.mouse.move(700, 413, { steps: 4 });
  await page.mouse.up();
  await expect
    .poll(async () => Number(await inspector.getAttribute('data-position')))
    .toBeGreaterThan(0.18);
  const position = await inspector.getAttribute('data-position');
  await expect(inspector).toHaveAttribute('data-wall-id', wall ?? '');
  // Leaving the canvas cancels the preview, rather than committing it.
  await page.mouse.move(682, 413);
  await page.mouse.down();
  await page.mouse.move(682, 350);
  await page.mouse.move(-1, 350);
  await page.mouse.up();
  await expect(inspector).toHaveAttribute('data-position', position ?? '');
});
