import { expect, type Page, test } from '@playwright/test';

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
  await draw(page);
  const rooms = page.getByRole('list', { name: 'Rooms' });
  await expect(rooms.getByRole('listitem')).toHaveCount(1);
  const geometry = await rooms.innerText();
  const zoom = await page.getByTestId('zoom').innerText();
  await page.mouse.wheel(0, -120);
  await expect(page.getByTestId('zoom')).not.toHaveText(zoom);
  await expect(rooms).toHaveText(geometry);
  await page.getByRole('button', { name: 'Pan', exact: true }).click();
  await draw(page);
  await expect(rooms).toHaveText(geometry);
  await page.setViewportSize({ width: 900, height: 700 });
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
  await draw(page);
  await expect(page.getByRole('alert')).toContainText('No room was added');
  await expect(
    page.getByRole('list', { name: 'Rooms' }).getByRole('listitem'),
  ).toHaveCount(0);
  await expect(
    page.getByRole('button', { name: 'Undo', exact: true }),
  ).toBeDisabled();
});
