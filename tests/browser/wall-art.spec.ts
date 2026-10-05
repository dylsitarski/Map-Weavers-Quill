import { expect, type Page, test } from '@playwright/test';

// Count wall-top pixels of one material in a strip across the room's left wall.
async function wallPixels(page: Page, material: 'stone' | 'timber') {
  await expect(page.getByTestId('map-canvas')).not.toHaveAttribute(
    'data-wall-art',
    'loading',
  );
  return page.locator('canvas').evaluate(async (canvas, material) => {
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
    const element = canvas as HTMLCanvasElement;
    const scale = element.width / element.getBoundingClientRect().width;
    const context = element.getContext('2d');
    if (!context) throw new Error('Canvas context unavailable');
    const data = context.getImageData(
      Math.round(420 * scale),
      Math.round(365 * scale),
      Math.round(60 * scale),
      1,
    ).data;
    let count = 0;
    for (let i = 0; i < data.length; i += 4) {
      const [r, g, b] = [data[i], data[i + 1], data[i + 2]];
      const stone = Math.abs(r - g) < 14 && Math.abs(g - b) < 18 && r > 70;
      const timber = r - b > 40 && r < 160 && g < 110;
      if ((material === 'stone' ? stone : timber) && r < 150) count += 1;
    }
    return count;
  }, material);
}

test('walls and doors render from geometry, toggle with undo and save their style', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByRole('status')).toHaveText('Local server connected');
  const canvas = page.getByTestId('map-canvas');
  await expect(canvas).toHaveAttribute('data-wall-art', 'ready');
  expect(await wallPixels(page, 'stone')).toBe(0);
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .click();
  await page.mouse.move(450, 280);
  await page.mouse.down();
  await page.mouse.move(700, 450);
  await page.mouse.up();
  await expect(page.locator('[data-room-id]')).toHaveCount(1);
  await expect.poll(() => wallPixels(page, 'stone')).toBeGreaterThan(2);

  await page.getByRole('tab', { name: 'Layers', exact: true }).click();
  const show = page.getByRole('checkbox', { name: 'Show walls and doors' });
  await expect(show).toBeChecked();
  await show.uncheck();
  await expect(canvas).toHaveAttribute('data-wall-art', 'hidden');
  expect(await wallPixels(page, 'stone')).toBe(0);
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(show).toBeChecked();
  await expect.poll(() => wallPixels(page, 'stone')).toBeGreaterThan(2);
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(show).not.toBeChecked();
  await page.getByRole('button', { name: 'Undo', exact: true }).click();

  await page.getByLabel('Material').selectOption('timber');
  await expect.poll(() => wallPixels(page, 'timber')).toBeGreaterThan(2);
  expect(await wallPixels(page, 'stone')).toBe(0);

  const thickness = page.getByRole('spinbutton', {
    name: 'Thickness (map units)',
  });
  await expect(thickness).toHaveValue('10');
  const thin = await wallPixels(page, 'timber');
  await thickness.fill('30');
  await thickness.press('Enter');
  await expect.poll(() => wallPixels(page, 'timber')).toBeGreaterThan(thin);
  await thickness.fill('0');
  await expect(page.getByText('Enter 1–50 map units.')).toBeVisible();
  await thickness.blur();
  await expect(thickness).toHaveValue('30');

  await page.getByRole('button', { name: 'File', exact: true }).click();
  await page
    .getByRole('textbox', { name: 'Project name' })
    .fill(`Walls ${crypto.randomUUID()}`);
  const saved = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/projects/save') &&
      response.status() === 200,
  );
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  const document = await (await saved).json();
  expect(document.settings['quill.wallArt']).toEqual({
    visible: true,
    material: 'timber',
  });
  expect(document.map.style.wallThicknessPx).toBe(30);
});
