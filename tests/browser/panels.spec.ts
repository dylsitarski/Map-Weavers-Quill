import { expect, type Page, test } from '@playwright/test';

async function room(page: Page) {
  await page.mouse.move(450, 280);
  await page.mouse.down();
  await page.mouse.move(700, 450);
  await page.mouse.up();
}
async function setup(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .click();
  await room(page);
  await expect(page.locator('[data-room-id]')).toHaveCount(1);
}
async function edit(page: Page) {
  await page
    .getByRole('button', { name: 'Select/edit room', exact: true })
    .click();
  await page.mouse.click(550, 350);
  await expect(
    page.getByRole('textbox', { name: 'Name', exact: true }),
  ).toBeVisible();
}

test('scrolling inspector never zooms; tabs remain fixed and retain form drafts', async ({
  page,
}) => {
  await setup(page);
  await edit(page);
  const zoom = await page.getByTestId('zoom').textContent();
  const body = page.locator('#info-body');
  const tabs = page.getByRole('tablist', { name: 'Right panel' });
  const bounds = await tabs.boundingBox();
  await body.hover();
  await page.mouse.wheel(0, 450);
  await expect
    .poll(() => body.evaluate((el) => el.scrollTop))
    .toBeGreaterThan(0);
  await expect(page.getByTestId('zoom')).toHaveText(zoom ?? '');
  expect(await tabs.boundingBox()).toEqual(bounds);
  await body.evaluate((el) => {
    el.scrollTop = el.scrollHeight;
  });
  await page.mouse.wheel(0, 200);
  await expect(page.getByTestId('zoom')).toHaveText(zoom ?? '');
  await page.mouse.move(550, 350);
  await page.mouse.wheel(0, -120);
  await expect(page.getByTestId('zoom')).not.toHaveText(zoom ?? '');
  await page
    .getByRole('textbox', { name: 'Name', exact: true })
    .fill('Unsaved name');
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  await expect(
    page.getByRole('textbox', { name: 'Room prompt', exact: true }),
  ).toBeVisible();
  await page.getByRole('tab', { name: 'Information', exact: true }).click();
  await expect(
    page.getByRole('textbox', { name: 'Name', exact: true }),
  ).toHaveValue('Unsaved name');
});

test('layer ordering updates stacking and is undoable without changing geometry', async ({
  page,
}) => {
  await setup(page);
  await room(page);
  await expect(page.locator('[data-room-id]')).toHaveCount(2);
  await page.getByRole('tab', { name: 'Layers', exact: true }).click();
  const rows = page.locator('[data-room-id]');
  const geometry = await rows.first().getAttribute('data-geometry');
  await expect(
    rows.first().getByRole('button', { name: 'Room 2', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Lower Room 2', exact: true }).click();
  await expect(
    rows.first().getByRole('button', { name: 'Room 1', exact: true }),
  ).toBeVisible();
  await expect(rows.last()).toHaveAttribute('data-geometry', geometry ?? '');
  // Hit testing follows the newly visible top room.
  await edit(page);
  await expect(
    page.getByRole('textbox', { name: 'Name', exact: true }),
  ).toHaveValue('Room 1');
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await page.getByRole('tab', { name: 'Layers', exact: true }).click();
  await expect(
    rows.first().getByRole('button', { name: 'Room 2', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Room 2', exact: true }).click();
  await expect(
    page.getByRole('tab', { name: 'Information', exact: true }),
  ).toHaveAttribute('aria-selected', 'true');
  await expect(
    page.getByRole('textbox', { name: 'Name', exact: true }),
  ).toHaveValue('Room 2');
});

test('reenabling snap realigns an off-grid room without deforming it', async ({
  page,
}) => {
  await setup(page);
  await edit(page);
  await page.getByRole('checkbox', { name: 'Snap', exact: true }).uncheck();
  await page.mouse.move(550, 350);
  await page.mouse.down();
  await page.mouse.move(567, 361, { steps: 4 });
  await page.mouse.up();
  const layer = page.locator('[data-room-id]');
  await expect
    .poll(async () => {
      const points = JSON.parse(
        (await layer.getAttribute('data-geometry')) ?? '[]',
      );
      return points[0]?.x % 50;
    })
    .not.toBe(0);
  const free = await layer.getAttribute('data-geometry');
  const points = JSON.parse(free ?? '[]') as { x: number; y: number }[];
  await page.getByRole('checkbox', { name: 'Snap', exact: true }).check();
  await page.mouse.move(567, 361);
  await page.mouse.down();
  await page.mouse.move(619, 390, { steps: 4 });
  await page.mouse.up();
  await expect(layer).not.toHaveAttribute('data-geometry', free ?? '');
  const aligned = JSON.parse(
    (await layer.getAttribute('data-geometry')) ?? '[]',
  ) as { x: number; y: number }[];
  aligned.forEach((p, i) => {
    expect(Math.abs(p.x / 50 - Math.round(p.x / 50))).toBeLessThan(1e-9);
    expect(Math.abs(p.y / 50 - Math.round(p.y / 50))).toBeLessThan(1e-9);
    expect(p.x - aligned[0].x).toBeCloseTo(points[i].x - points[0].x);
    expect(p.y - aligned[0].y).toBeCloseTo(points[i].y - points[0].y);
  });
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(layer).toHaveAttribute('data-geometry', free ?? '');
});
