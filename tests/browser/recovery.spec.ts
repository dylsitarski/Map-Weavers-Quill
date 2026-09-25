import { expect, type Page, test } from '@playwright/test';

async function save(page: Page, name: string, revision: number) {
  await page.getByRole('button', { name: 'File', exact: true }).click();
  await page.getByRole('textbox', { name: 'Project name' }).fill(name);
  await page.getByRole('button', { name: 'Save project', exact: true }).click();
  await expect(page.getByTestId('save-status')).toHaveText(
    `Saved · revision ${revision}`,
  );
  await page.getByRole('button', { name: 'File', exact: true }).click();
}
async function reopen(page: Page, name: string, revision: number) {
  await page.reload();
  await page.getByRole('button', { name: 'File', exact: true }).click();
  await page
    .getByRole('button', {
      name: `${name} · revision ${revision}`,
      exact: true,
    })
    .click();
  await page.getByRole('button', { name: 'File', exact: true }).click();
}
for (const room of [false, true]) {
  test(`${room ? 'room' : 'background'} preview recovers after reload without regenerating`, async ({
    page,
  }) => {
    await page.goto('/');
    if (room) {
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
    } else await page.getByRole('button', { name: 'Map', exact: true }).click();
    const name = `Recovery ${crypto.randomUUID()}`;
    await save(page, name, 1);
    await page.getByRole('tab', { name: 'AI', exact: true }).click();
    await page
      .getByRole('button', { name: 'Generate preview', exact: true })
      .click();
    const accept = page.getByRole('button', {
      name: room ? 'Accept room artwork' : 'Accept background',
      exact: true,
    });
    await expect(accept).toBeEnabled();
    const hash = await page
      .getByTestId('map-canvas')
      .getAttribute('data-preview-hash');
    await reopen(page, name, 1);
    if (room) {
      await page.getByRole('button', { name: 'Room', exact: true }).click();
      await page
        .getByRole('button', { name: 'Select/edit room', exact: true })
        .click();
      await page.mouse.click(550, 350);
    } else await page.getByRole('button', { name: 'Map', exact: true }).click();
    await page.getByRole('tab', { name: 'AI', exact: true }).click();
    await page.route('**/api/jobs/*/background', (route) => route.abort());
    await page.route('**/api/jobs/*/room', (route) => route.abort());
    await page
      .getByRole('button', { name: 'Recover preview', exact: true })
      .click();
    await expect(accept).toBeEnabled();
    await expect(page.getByTestId('map-canvas')).toHaveAttribute(
      'data-preview-hash',
      hash ?? '',
    );
    await accept.click();
    expect(
      await page.evaluate(() =>
        Object.keys(localStorage).filter((key) =>
          key.startsWith('quill.preview.'),
        ),
      ),
    ).toHaveLength(0);
    await expect(
      page.getByRole('button', { name: 'Undo', exact: true }),
    ).toBeEnabled();
  });
}

test('recovery refuses a changed saved document and can be discarded', async ({
  page,
}) => {
  await page.goto('/');
  const name = `Stale recovery ${crypto.randomUUID()}`;
  await save(page, name, 1);
  await page.getByRole('button', { name: 'Map', exact: true }).click();
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  await page
    .getByRole('button', { name: 'Generate preview', exact: true })
    .click();
  await expect(
    page.getByRole('button', { name: 'Accept background' }),
  ).toBeEnabled();
  await save(page, `${name} edited`, 2);
  await reopen(page, `${name} edited`, 2);
  await page.getByRole('button', { name: 'Map', exact: true }).click();
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  await page
    .getByRole('button', { name: 'Recover preview', exact: true })
    .click();
  await expect(page.getByRole('alert')).toContainText(
    'different project state',
  );
  await expect(
    page.getByRole('button', { name: 'Accept background' }),
  ).toHaveCount(0);
  await page
    .getByRole('button', { name: 'Discard recoverable preview' })
    .click();
  await expect(
    page.getByRole('button', { name: 'Recover preview' }),
  ).toHaveCount(0);
});
