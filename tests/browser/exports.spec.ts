import { expect, test } from '@playwright/test';

test('image downloads use accepted artwork, retain unsaved state and report failures', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'File', exact: true }).click();
  await page.getByRole('textbox', { name: 'Project name' }).fill('Export test');
  await page.getByRole('button', { name: 'File', exact: true }).click();
  await page.getByRole('button', { name: 'Map', exact: true }).click();
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  await page
    .getByRole('button', { name: 'Generate preview', exact: true })
    .click();
  await expect(
    page.getByRole('button', { name: 'Accept background' }),
  ).toBeEnabled();
  await page.getByRole('button', { name: 'File', exact: true }).click();

  const request = page.waitForRequest('**/api/export/image');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export PNG', exact: true }).click();
  expect((await request).postDataJSON().project.layers).toEqual([]);
  const file = await download;
  expect(file.suggestedFilename()).toBe('Export-test.png');
  expect(await file.failure()).toBeNull();
  await expect(page.getByTestId('save-status')).toHaveText('Unsaved changes');
  await page.getByRole('button', { name: 'Accept background' }).click();
  const nextRequest = page.waitForRequest('**/api/export/image');
  const webp = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export WebP', exact: true }).click();
  expect((await nextRequest).postDataJSON().project.layers).toHaveLength(1);
  expect((await webp).suggestedFilename()).toBe('Export-test.webp');
  await page.route('**/api/export/image', (route) =>
    route.fulfill({ status: 503, json: { detail: 'Export unavailable' } }),
  );
  await page.getByRole('button', { name: 'Export PNG', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Export unavailable');
  await expect(
    page.getByRole('button', { name: 'Export PNG', exact: true }),
  ).toBeEnabled();
});
