import { expect, test } from '@playwright/test';

test('map prompt and defaults save, reopen, undo after save and reach generation', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Map', exact: true }).click();
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  const prompt = page.getByRole('textbox', { name: 'Background prompt' });
  const palette = page.getByRole('textbox', { name: 'Map palette' });
  await prompt.fill('Ancient ruins');
  await palette.fill('ochre and grey');
  await page.getByRole('textbox', { name: 'Map environment' }).fill('desert');
  await expect(
    page.getByRole('button', { name: 'Generate preview', exact: true }),
  ).toBeDisabled();
  await page
    .getByRole('button', { name: 'Apply map prompt and style' })
    .click();
  await expect(
    page.getByRole('button', { name: 'Apply map prompt and style' }),
  ).toBeDisabled();
  await page.getByRole('button', { name: 'File', exact: true }).click();
  const name = `Map authoring ${crypto.randomUUID()}`;
  await page.getByRole('textbox', { name: 'Project name' }).fill(name);
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  await expect(page.getByTestId('save-status')).toHaveText(
    'Saved · revision 1',
  );
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(prompt).toHaveValue('Stone dungeon floor');
  await expect(palette).toHaveValue('');
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(prompt).toHaveValue('Ancient ruins');
  await page.reload();
  await page.getByRole('button', { name: 'File', exact: true }).click();
  await page
    .getByRole('button', { name: `${name} · revision 1`, exact: true })
    .click();
  await page.getByRole('button', { name: 'Map', exact: true }).click();
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  await expect(prompt).toHaveValue('Ancient ruins');
  await expect(palette).toHaveValue('ochre and grey');
  const request = page.waitForRequest('**/api/jobs/*/background');
  await page
    .getByRole('button', { name: 'Generate preview', exact: true })
    .click();
  const body = (await request).postDataJSON();
  expect(body.prompt).toBe('Ancient ruins');
  expect(body.style.palette).toBe('ochre and grey');
  await expect(
    page.getByRole('button', { name: 'Accept background' }),
  ).toBeEnabled();
  await palette.fill('blue');
  await page
    .getByRole('button', { name: 'Apply map prompt and style' })
    .click();
  await expect(
    page.getByRole('button', { name: 'Accept background' }),
  ).toBeDisabled();
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
  await expect(
    page.getByRole('textbox', { name: 'Palette', exact: true }),
  ).toHaveAttribute('placeholder', 'blue');
});
