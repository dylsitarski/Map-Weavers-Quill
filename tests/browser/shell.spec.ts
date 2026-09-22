import { expect, test } from '@playwright/test';

test('shell connects through the development proxy', async ({
  page,
  request,
}) => {
  await expect
    .poll(async () => {
      const response = await request.get('/api/health');
      return response.status();
    })
    .toBe(200);
  await page.goto('/');
  await expect(
    page.getByRole('heading', { name: 'Map-Weaver’s Quill', exact: true }),
  ).toBeVisible();
  await expect(page.getByRole('status')).toHaveText('Local server connected');
  const response = await request.get('/api/providers');
  expect(response.ok()).toBeTruthy();
  expect((await response.json())[0].local).toBe(true);
});

test('shell explains a failed connection', async ({ page }) => {
  await page.route('**/api/health', (route) =>
    route.fulfill({ status: 503, body: '{}' }),
  );
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('Server unavailable');
});

test('shell shows loading until health returns', async ({ page }) => {
  let release: () => void = () => {};
  const wait = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route('**/api/health', async (route) => {
    await wait;
    await route.fulfill({ json: { status: 'ok' } });
  });
  await page.goto('/');
  await expect(page.getByRole('status')).toHaveText('Connecting…');
  release();
  await expect(page.getByRole('status')).toHaveText('Local server connected');
});
