import { expect, type Page, test } from '@playwright/test';

async function activateRectangle(page: Page) {
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .click();
}

async function draw(page: Page) {
  const box = await page.getByTestId('map-canvas').boundingBox();
  if (!box) throw new Error('No drawing surface');
  await page.mouse.move(
    box.x + box.width / 2 - 80,
    box.y + box.height / 2 - 60,
  );
  await page.mouse.down();
  await page.mouse.move(
    box.x + box.width / 2 + 80,
    box.y + box.height / 2 + 60,
    { steps: 5 },
  );
  await page.mouse.up();
}
test('draw validated room, zoom without mutation, undo and redo', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByRole('status')).toHaveText('Local server connected');
  await activateRectangle(page);
  await draw(page);
  const rooms = page.getByRole('list', { name: 'Rooms' });
  await expect(rooms.getByRole('listitem')).toHaveCount(1);
  const geometry = (await rooms.textContent()) ?? '';
  const zoom = await page.getByTestId('zoom').innerText();
  await page.mouse.wheel(0, -120);
  await expect(page.getByTestId('zoom')).not.toHaveText(zoom);
  await expect(rooms).toHaveText(geometry);
  await page.getByRole('button', { name: 'Pan', exact: true }).click();
  await draw(page);
  await expect(rooms).toHaveText(geometry);
  await page.setViewportSize({ width: 900, height: 700 });
  await page.getByRole('button', { name: 'View', exact: true }).click();
  await page.getByRole('button', { name: 'Fit map', exact: true }).click();
  await expect(rooms).toHaveText(geometry);
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(rooms.getByRole('listitem')).toHaveCount(0);
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(rooms).toHaveText(geometry);
  await page.getByRole('checkbox', { name: 'Grid', exact: true }).uncheck();
  await expect(rooms).toHaveText(geometry);
});
test('failed validation adds no room or history', async ({ page }) => {
  await page.route('**/api/geometry/validate', (route) =>
    route.fulfill({ status: 503, body: '{}' }),
  );
  await page.goto('/');
  await activateRectangle(page);
  await draw(page);
  await expect(page.getByRole('alert')).toContainText('No room was added');
  await expect(
    page.getByRole('list', { name: 'Rooms' }).getByRole('listitem'),
  ).toHaveCount(0);
  await expect(
    page.getByRole('button', { name: 'Undo', exact: true }),
  ).toBeDisabled();
  const before = await page.getByTestId('map-canvas').boundingBox();
  await page.getByRole('button', { name: 'Dismiss error' }).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
  expect(await page.getByTestId('map-canvas').boundingBox()).toEqual(before);
});

test('scope persists while drawing and remembers tools after closing', async ({
  page,
}) => {
  await page.goto('/');
  const canvas = page.getByTestId('map-canvas');
  const before = await canvas.boundingBox();
  const roomScope = page.getByRole('button', { name: 'Room', exact: true });
  const pan = page.getByRole('button', { name: 'Pan', exact: true });
  await expect(pan).toHaveAttribute('aria-pressed', 'true');
  await roomScope.click();
  await expect(page.getByRole('region', { name: 'Room tools' })).toBeVisible();
  expect(await canvas.boundingBox()).toEqual(before);
  await page.keyboard.press('Escape');
  await expect(roomScope).toBeFocused();
  await expect(roomScope).toHaveAttribute('aria-expanded', 'false');
  await roomScope.click();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .click();
  await draw(page);
  await expect(roomScope).toHaveAttribute('aria-expanded', 'true');
  await expect(
    page.getByRole('list', { name: 'Rooms' }).getByRole('listitem'),
  ).toHaveCount(1);
  await roomScope.click();
  await expect(pan).toHaveAttribute('aria-pressed', 'true');
  await roomScope.click();
  const rectangle = page.getByRole('button', {
    name: 'Rectangle room',
    exact: true,
  });
  await expect(rectangle).toHaveAttribute('aria-pressed', 'true');
  // Focus is still on the scope button: Space must not activate it or draw.
  const beforePan = await page
    .locator('canvas')
    .evaluate((canvas) => (canvas as HTMLCanvasElement).toDataURL());
  await page.keyboard.down('Space');
  await draw(page);
  await page.keyboard.up('Space');
  await expect(roomScope).toHaveAttribute('aria-expanded', 'true');
  await expect(rectangle).toHaveAttribute('aria-pressed', 'true');
  expect(
    await page
      .locator('canvas')
      .evaluate((canvas) => (canvas as HTMLCanvasElement).toDataURL()),
  ).not.toEqual(beforePan);
  await expect(
    page.getByRole('list', { name: 'Rooms' }).getByRole('listitem'),
  ).toHaveCount(1);
  await rectangle.click();
  await expect(pan).toHaveAttribute('aria-pressed', 'true');
  await roomScope.click();
  await roomScope.click();
  await expect(rectangle).toHaveAttribute('aria-pressed', 'false');
  expect(
    await page.evaluate(
      () => document.documentElement.scrollHeight <= window.innerHeight,
    ),
  ).toBe(true);
});

test('snap point matches the submitted corner and hides when snapping or drawing is off', async ({
  page,
}) => {
  await page.goto('/');
  await expect(
    page.getByRole('checkbox', { name: 'Snap', exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Map', exact: true }),
  ).toHaveCount(0);
  await activateRectangle(page);
  await page.mouse.move(613, 377);
  const marker = page.getByTestId('snap-point');
  await expect(marker).toBeVisible();
  const box = await marker.boundingBox();
  if (!box) throw new Error('No snap marker');
  const request = page.waitForRequest('**/api/geometry/validate');
  await page.mouse.down();
  await page.mouse.move(800, 500);
  await page.mouse.up();
  const polygon = (await request).postDataJSON().polygon as {
    x: number;
    y: number;
  }[];
  // Initial fit: 24px margin, centered 1200 × 800 map.
  const viewport = page.viewportSize();
  if (!viewport) throw new Error('No viewport');
  const { width, height } = viewport;
  const scale = Math.min((width - 48) / 1200, (height - 48) / 800);
  const x = (width - 1200 * scale) / 2;
  const y = (height - 800 * scale) / 2;
  expect(
    polygon.some(
      (p) =>
        Math.abs(x + p.x * scale - (box.x + box.width / 2)) < 1 &&
        Math.abs(y + (800 - p.y) * scale - (box.y + box.height / 2)) < 1,
    ),
  ).toBe(true);
  await page.getByRole('checkbox', { name: 'Snap', exact: true }).uncheck();
  await page.mouse.move(613, 377);
  await expect(marker).toHaveCount(0);
  await page.getByRole('checkbox', { name: 'Snap', exact: true }).check();
  await page.mouse.move(613, 377);
  await expect(marker).toBeVisible();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .focus();
  await page.keyboard.down('Space');
  await expect(marker).toHaveCount(0);
  await page.keyboard.up('Space');
  await expect(marker).toBeVisible();
});
