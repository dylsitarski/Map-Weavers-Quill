import { expect, type Page, test } from '@playwright/test';

async function begin(page: Page) {
  await page.goto('/');
  await expect(page.getByRole('status')).toHaveText('Local server connected');
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page.getByRole('button', { name: 'Polygon room', exact: true }).click();
}
async function corners(page: Page, points: number[][]) {
  for (const [x, y] of points) await page.mouse.click(x, y);
}
const rooms = (page: Page) => page.locator('[aria-label="Room layers"]');

test('concave polygon closes at the first point and round trips undo/redo', async ({
  page,
}) => {
  await begin(page);
  await expect(
    page.getByRole('button', { name: 'Finish polygon' }),
  ).toBeDisabled();
  await corners(page, [
    [450, 280],
    [800, 280],
    [800, 500],
    [620, 390],
    [450, 500],
  ]);
  await expect(page.getByTestId('vertex-count')).toHaveText('5 vertices');
  const request = page.waitForRequest('**/api/geometry/validate');
  await page.mouse.click(450, 280);
  const polygon = (await request).postDataJSON().polygon;
  expect(polygon).toHaveLength(5);
  expect(
    polygon.every(
      (p: { x: number; y: number }) => p.x % 50 === 0 && p.y % 50 === 0,
    ),
  ).toBe(true);
  await expect(rooms(page).locator('li')).toHaveCount(1);
  await expect(page.getByTestId('vertex-count')).toHaveText('0 vertices');
  const geometry = await rooms(page).textContent();
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(rooms(page).locator('li')).toHaveCount(0);
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(rooms(page)).toHaveText(geometry ?? '');
});

test('crossed polygon is rejected without history and its draft can be repaired', async ({
  page,
}) => {
  await begin(page);
  await corners(page, [
    [450, 280],
    [800, 500],
    [450, 500],
    [800, 280],
  ]);
  await page.getByRole('button', { name: 'Finish polygon' }).click();
  await expect(page.getByRole('alert')).toContainText('No room was added');
  await expect(page.getByTestId('vertex-count')).toHaveText('4 vertices');
  await expect(
    page.getByRole('button', { name: 'Undo', exact: true }),
  ).toBeDisabled();
  await page.getByRole('button', { name: 'Remove last point' }).click();
  await page.getByRole('button', { name: 'Finish polygon' }).click();
  await expect(rooms(page).locator('li')).toHaveCount(1);
  await expect(page.getByRole('alert')).toHaveCount(0);
});

test('temporary pan preserves polygon draft; scope closure cancels draft but remembers tool', async ({
  page,
}) => {
  await begin(page);
  await corners(page, [
    [450, 280],
    [800, 280],
  ]);
  await page.keyboard.down('Space');
  await page.mouse.move(700, 400);
  await page.mouse.down();
  await page.mouse.move(740, 430, { steps: 4 });
  await page.mouse.up();
  await page.keyboard.up('Space');
  await expect(page.getByTestId('vertex-count')).toHaveText('2 vertices');
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Polygon room', exact: true }),
  ).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByTestId('vertex-count')).toHaveText('0 vertices');
  await corners(page, [
    [450, 280],
    [700, 280],
    [700, 500],
  ]);
  await page.keyboard.press('Escape');
  await expect(rooms(page).locator('li')).toHaveCount(0);
  await expect(
    page.getByRole('button', { name: 'Undo', exact: true }),
  ).toBeDisabled();
});
