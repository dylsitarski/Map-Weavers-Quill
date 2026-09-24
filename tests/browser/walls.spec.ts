import { expect, type Page, test } from '@playwright/test';

async function rectangle(page: Page, left: number, right: number) {
  await page.mouse.move(left, 280);
  await page.mouse.down();
  await page.mouse.move(right, 450);
  await page.mouse.up();
}
async function setup(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .click();
}
test('shared wall is deduplicated and retains its ID through undo/redo', async ({
  page,
}) => {
  await setup(page);
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
    .getByRole('button', { name: 'Inspect walls', exact: true })
    .click();
  await page.mouse.click(682, 360);
  const inspector = page.getByRole('region', { name: 'Wall inspector' });
  await expect(inspector).toContainText('Derived from: Room 1, Room 2');
  await expect(inspector).toContainText('Length: 200.00 map units');
  const id = await inspector.getAttribute('data-wall-id');
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-wall-count',
    '4',
  );
  await expect(inspector).toHaveAttribute('data-wall-id', id ?? '');
  await expect(inspector).not.toContainText('Room 2');
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-wall-count',
    '7',
  );
  await expect(inspector).toHaveAttribute('data-wall-id', id ?? '');
  // Canvas selection preserves the active tab; wall controls stay minimal.
  await page.getByRole('tab', { name: 'Layers', exact: true }).click();
  await page.mouse.click(682, 400);
  await expect(
    page.getByRole('combobox', { name: 'Wall segment' }),
  ).toHaveCount(0);
  await expect(page.getByTestId('wall-count')).toHaveCount(0);
  await expect(
    page.getByRole('region', { name: 'Room tools' }).getByRole('button').last(),
  ).toHaveText('Inspect walls');
  await expect(
    page.getByRole('tab', { name: 'Layers', exact: true }),
  ).toHaveAttribute('aria-selected', 'true');
});

test('wall derivation failure leaves rooms intact and can be retried', async ({
  page,
}) => {
  let fail = true;
  await page.route('**/api/geometry/walls', (route) =>
    fail ? route.fulfill({ status: 503, json: {} }) : route.continue(),
  );
  await setup(page);
  await rectangle(page, 450, 700);
  await expect(page.getByRole('alert')).toContainText('Walls unavailable');
  await expect(page.locator('[data-room-id]')).toHaveCount(1);
  const geometry = await page
    .locator('[data-room-id]')
    .getAttribute('data-geometry');
  fail = false;
  await page.getByRole('button', { name: 'Retry walls' }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-wall-count',
    '4',
  );
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.locator('[data-room-id]')).toHaveAttribute(
    'data-geometry',
    geometry ?? '',
  );
});

test('undo discards a delayed wall response', async ({ page }) => {
  let release = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let started = false;
  await page.route('**/api/geometry/walls', async (route) => {
    const response = await route.fetch();
    started = true;
    await held;
    await route.fulfill({ response });
  });
  await setup(page);
  await rectangle(page, 450, 700);
  await expect.poll(() => started).toBe(true);
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-wall-count',
    '0',
  );
  release();
  await expect(page.locator('[data-room-id]')).toHaveCount(0);
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-wall-count',
    '0',
  );
});
