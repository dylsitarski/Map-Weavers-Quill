import { expect, type Page, test } from '@playwright/test';

async function setup(page: Page) {
  await page.goto('/');
  await expect(page.getByRole('status')).toHaveText('Local server connected');
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .click();
  await page.mouse.move(450, 280);
  await page.mouse.down();
  await page.mouse.move(700, 450);
  await page.mouse.up();
  await expect(
    page.locator('[data-testid="room-geometry"]').locator('[data-room-id]'),
  ).toHaveCount(1);
  await page
    .getByRole('button', { name: 'Select/edit room', exact: true })
    .click();
  await page.mouse.click(550, 350);
  await expect(
    page.getByRole('form', { name: 'Room inspector' }),
  ).toBeVisible();
}
test('move, reshape, inspect and delete are undoable room edits', async ({
  page,
}) => {
  await setup(page);
  const x = page.getByRole('spinbutton', { name: 'Vertex 1 x', exact: true });
  const initial = Number(await x.inputValue());
  await page.mouse.move(550, 350);
  await page.mouse.down();
  await page.mouse.move(592, 350, { steps: 4 });
  await page.mouse.up();
  await expect(x).toHaveValue(String(initial + 50));
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(x).toHaveValue(String(initial));
  // First corner: derive screen location from inspector's native coordinates.
  const y = Number(
    await page
      .getByRole('spinbutton', { name: 'Vertex 1 y', exact: true })
      .inputValue(),
  );
  const screen = { x: 136 + initial * 0.84, y: 24 + (800 - y) * 0.84 };
  await page.mouse.move(screen.x, screen.y);
  await page.mouse.down();
  await page.mouse.move(screen.x + 42, screen.y, { steps: 4 });
  await page.mouse.up();
  await expect(x).toHaveValue(String(initial + 50));
  await page.getByRole('textbox', { name: 'Name', exact: true }).fill('Hall');
  await page
    .getByRole('button', { name: 'Insert after vertex 1', exact: true })
    .click();
  await page.getByRole('button', { name: 'Apply room changes' }).click();
  await expect(
    page.getByRole('textbox', { name: 'Name', exact: true }),
  ).toHaveValue('Hall');
  await expect(
    page.getByRole('spinbutton', { name: 'Vertex 5 x', exact: true }),
  ).toHaveCount(1);
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  await page
    .getByRole('textbox', { name: 'Room prompt', exact: true })
    .fill('Stone floor');
  await page.getByRole('button', { name: 'Apply prompt and style' }).click();
  await expect(
    page.getByRole('button', { name: 'Apply prompt and style' }),
  ).toBeDisabled();
  await page.getByRole('tab', { name: 'Information', exact: true }).click();
  await page.getByRole('button', { name: 'Delete room', exact: true }).click();
  await expect(
    page.locator('[data-testid="room-geometry"]').locator('[data-room-id]'),
  ).toHaveCount(0);
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(
    page.getByRole('textbox', { name: 'Name', exact: true }),
  ).toHaveValue('Hall');
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  await expect(
    page.getByRole('textbox', { name: 'Room prompt', exact: true }),
  ).toHaveValue('Stone floor');
});
test('invalid edits leave geometry and history unchanged; Escape cancels a drag', async ({
  page,
}) => {
  await setup(page);
  const rooms = page.locator('[data-testid="room-geometry"]');
  const before = await rooms.textContent();
  const x2 = await page
    .getByRole('spinbutton', { name: 'Vertex 2 x', exact: true })
    .inputValue();
  await page
    .getByRole('spinbutton', { name: 'Vertex 1 x', exact: true })
    .fill(x2);
  await page.getByRole('button', { name: 'Apply room changes' }).click();
  await expect(page.getByRole('alert')).toContainText(
    'The room was not changed',
  );
  await expect(rooms).toHaveText(before ?? '');
  await page.mouse.move(550, 350);
  await page.mouse.down();
  await page.mouse.move(650, 400);
  await page.keyboard.press('Escape');
  await page.mouse.up();
  await expect(rooms).toHaveText(before ?? '');
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(rooms.locator('[data-room-id]')).toHaveCount(0);
});
