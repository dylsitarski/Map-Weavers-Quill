import { expect, test } from '@playwright/test';

test('SDXL readiness gates generation, supports retry, and explains cancellation', async ({
  page,
}) => {
  let ready = false;
  await page.route('**/api/providers/readiness', async (route) => {
    await route.fulfill({
      json: {
        descriptor: {
          contractVersion: '0.1.0',
          id: 'comfyui-sdxl',
          capabilities: ['text_to_image', 'inpainting', 'seed'],
          maxWidth: 1024,
          maxHeight: 1024,
          local: true,
        },
        ready,
        message: ready
          ? 'Ready'
          : 'Cannot connect to the local ComfyUI server.',
      },
    });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Map', exact: true }).click();
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  await expect(
    page.getByText('Local SDXL · ComfyUI', { exact: true }),
  ).toBeVisible();
  const generate = page.getByRole('button', {
    name: 'Generate preview',
    exact: true,
  });
  await expect(generate).toBeDisabled();
  await expect(
    page.getByText(/Cannot connect to the local ComfyUI/),
  ).toBeVisible();
  await expect(page.getByText(/ComfyUI may continue working/)).toBeVisible();
  ready = true;
  await page.getByRole('button', { name: 'Check provider' }).click();
  await expect(generate).toBeEnabled();
  await expect(page.getByText(/Room editing/)).toBeVisible();
});
