import { expect, type Page, test } from '@playwright/test';

async function setup(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .click();
  await page.mouse.move(450, 280);
  await page.mouse.down();
  await page.mouse.move(700, 450);
  await page.mouse.up();
  await expect(page.locator('[data-room-id]')).toHaveCount(1);
  await page
    .getByRole('button', { name: 'Select/edit room', exact: true })
    .click();
  await page.mouse.click(550, 350);
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  await page
    .getByRole('textbox', { name: 'Room prompt', exact: true })
    .fill('Stone tiles');
  await page.getByRole('button', { name: 'Apply prompt' }).click();
  await expect(
    page.getByRole('button', { name: 'Apply prompt' }),
  ).toBeDisabled();
}
async function generate(page: Page) {
  await page
    .getByRole('button', {
      name: /Generate preview|Regenerate preview/,
      exact: true,
    })
    .click();
  await expect(
    page.getByRole('button', { name: 'Accept room artwork' }),
  ).toBeEnabled();
}
test('room artwork accepts separately, survives background generation and save/open, clears on reshape with undo', async ({
  page,
}) => {
  await setup(page);
  const geometry = await page
    .locator('[data-room-id]')
    .getAttribute('data-geometry');
  await generate(page);
  await page.getByRole('button', { name: 'Reject preview' }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-room-art-count',
    '0',
  );
  await generate(page);
  await page.getByRole('button', { name: 'Accept room artwork' }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-room-art-count',
    '1',
  );
  await expect(page.locator('[data-room-id]')).toHaveAttribute(
    'data-geometry',
    geometry ?? '',
  );
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-room-art-count',
    '0',
  );
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-room-art-count',
    '1',
  );
  await page.getByRole('spinbutton', { name: 'Seed', exact: true }).fill('1');
  await generate(page);
  await page.getByRole('button', { name: 'Accept room artwork' }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-room-art-count',
    '1',
  );
  await page.getByRole('button', { name: 'Map', exact: true }).click();
  await page
    .getByRole('button', { name: 'Generate preview', exact: true })
    .click();
  await expect(
    page.getByRole('button', { name: 'Accept background' }),
  ).toBeEnabled();
  await page.getByRole('button', { name: 'Accept background' }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-room-art-count',
    '1',
  );
  await page.getByRole('button', { name: 'File', exact: true }).click();
  const name = `Room art ${crypto.randomUUID()}`;
  await page.getByRole('textbox', { name: 'Project name' }).fill(name);
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  await expect(page.getByTestId('save-status')).toHaveText(
    'Saved · revision 1',
  );
  await page.reload();
  await page.getByRole('button', { name: 'File', exact: true }).click();
  await page
    .getByRole('button', { name: `${name} · revision 1`, exact: true })
    .click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-room-art-count',
    '1',
  );
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page
    .getByRole('button', { name: 'Select/edit room', exact: true })
    .click();
  await page.mouse.move(550, 350);
  await page.mouse.down();
  await page.mouse.move(592, 350, { steps: 4 });
  await page.mouse.up();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-room-art-count',
    '0',
  );
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-room-art-count',
    '1',
  );
});
test('editing geometry while a room preview is open makes acceptance unavailable', async ({
  page,
}) => {
  await setup(page);
  await generate(page);
  await page.getByRole('tab', { name: 'Information', exact: true }).click();
  await page
    .getByRole('spinbutton', { name: 'Vertex 1 x', exact: true })
    .fill('400');
  await page.getByRole('button', { name: 'Apply room changes' }).click();
  await expect(
    page.getByRole('spinbutton', { name: 'Vertex 1 x', exact: true }),
  ).toHaveValue('400');
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('project changed');
  await expect(
    page.getByRole('button', { name: 'Accept room artwork' }),
  ).toBeDisabled();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-room-art-count',
    '0',
  );
});
