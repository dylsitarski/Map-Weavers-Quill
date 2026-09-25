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
  await page.getByRole('button', { name: 'Apply prompt and style' }).click();
  await expect(
    page.getByRole('button', { name: 'Apply prompt and style' }),
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
  await page.getByRole('tab', { name: 'Layers', exact: true }).click();
  const artwork = page.getByRole('list', { name: 'Artwork layers' });
  const roomArt = artwork.locator('li').first();
  await roomArt.getByRole('checkbox').uncheck();
  await roomArt.getByRole('slider').click();
  await page.getByRole('tab', { name: 'Layers', exact: true }).focus();
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(roomArt.getByRole('slider')).toHaveValue('1');
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(roomArt.getByRole('slider')).toHaveValue('0.5');
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
  await page.getByRole('tab', { name: 'Layers', exact: true }).click();
  await expect(roomArt.getByRole('checkbox')).not.toBeChecked();
  await expect(roomArt.getByRole('slider')).toHaveValue('0.5');
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
test('artwork order survives undo/redo and native save/open without reordering room geometry', async ({
  page,
}) => {
  await setup(page);
  await generate(page);
  await page.getByRole('button', { name: 'Accept room artwork' }).click();
  await page
    .getByRole('button', { name: 'Rectangle room', exact: true })
    .click();
  await page.mouse.move(480, 320);
  await page.mouse.down();
  await page.mouse.move(740, 500);
  await page.mouse.up();
  await page
    .getByRole('button', { name: 'Select/edit room', exact: true })
    .click();
  await page.mouse.click(650, 430);
  await generate(page);
  await page.getByRole('button', { name: 'Accept room artwork' }).click();
  await page.getByRole('tab', { name: 'Layers', exact: true }).click();
  const list = page.getByRole('list', { name: 'Artwork layers' });
  const rows = list.locator('li');
  await expect(rows).toHaveCount(2);
  await rows
    .last()
    .getByRole('button', { name: /^Select/ })
    .click();
  await expect(
    rows.last().getByRole('button', { name: /^Select/ }),
  ).toHaveAttribute('aria-pressed', 'true');
  await expect(
    page.getByRole('tab', { name: 'Layers', exact: true }),
  ).toHaveAttribute('aria-selected', 'true');
  const transfer = await page.evaluateHandle(() => new DataTransfer());
  await rows
    .first()
    .getByRole('button', { name: /^Reorder/ })
    .dispatchEvent('dragstart', { dataTransfer: transfer });
  await rows.last().dispatchEvent('dragover', { dataTransfer: transfer });
  await expect(rows.last()).toHaveClass(/drop-below/);
  await rows.first().dispatchEvent('dragover', { dataTransfer: transfer });
  await expect(list.locator('.drop-target')).toHaveCount(0);
  await rows.last().dispatchEvent('dragover', { dataTransfer: transfer });
  await rows.last().dispatchEvent('dragleave', { relatedTarget: null });
  await expect(list.locator('.drop-target')).toHaveCount(0);
  await rows
    .first()
    .getByRole('button', { name: /^Reorder/ })
    .dispatchEvent('dragend');
  await rows
    .last()
    .getByRole('button', { name: /^Reorder/ })
    .dispatchEvent('dragstart', { dataTransfer: transfer });
  await rows.first().dispatchEvent('dragover', { dataTransfer: transfer });
  await expect(rows.first()).toHaveClass(/drop-above/);
  await rows
    .last()
    .getByRole('button', { name: /^Reorder/ })
    .dispatchEvent('dragend');
  await expect(list.locator('.drop-target')).toHaveCount(0);
  await transfer.dispose();
  const front = await rows.first().getAttribute('data-artwork-id');
  const back = await rows.last().getAttribute('data-artwork-id');
  const geometry = await page
    .locator('[data-room-id]')
    .evaluateAll((elements) =>
      elements.map((element) => element.getAttribute('data-geometry')),
    );
  await rows
    .first()
    .getByRole('button', { name: /^Reorder/ })
    .dragTo(rows.last());
  await expect(rows.first()).toHaveAttribute('data-artwork-id', back ?? '');
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(rows.first()).toHaveAttribute('data-artwork-id', front ?? '');
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(rows.first()).toHaveAttribute('data-artwork-id', back ?? '');
  expect(
    await page
      .locator('[data-room-id]')
      .evaluateAll((elements) =>
        elements.map((element) => element.getAttribute('data-geometry')),
      ),
  ).toEqual(geometry);
  await page.getByRole('button', { name: 'File', exact: true }).click();
  const name = `Art order ${crypto.randomUUID()}`;
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
  await page.getByRole('tab', { name: 'Layers', exact: true }).click();
  await expect(rows.first()).toHaveAttribute('data-artwork-id', back ?? '');
});

test('room style edits undo, preserve art, invalidate previews and survive save/open', async ({
  page,
}) => {
  await setup(page);
  const palette = page.getByRole('textbox', { name: 'Palette', exact: true });
  await palette.fill('icy blue');
  await page
    .getByRole('textbox', { name: 'Render style', exact: true })
    .fill('ink drawing');
  await page.getByRole('button', { name: 'Apply prompt and style' }).click();
  await expect(
    page.getByRole('button', { name: 'Apply prompt and style' }),
  ).toBeDisabled();
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(palette).toHaveValue('');
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(palette).toHaveValue('icy blue');
  await generate(page);
  await page.getByRole('button', { name: 'Accept room artwork' }).click();
  await generate(page);
  await palette.fill('warm gold');
  await page.getByRole('button', { name: 'Apply prompt and style' }).click();
  await expect(page.getByRole('alert')).toContainText('project changed');
  await expect(
    page.getByRole('button', { name: 'Accept room artwork' }),
  ).toBeDisabled();
  await expect(page.getByTestId('map-canvas')).toHaveAttribute(
    'data-room-art-count',
    '1',
  );
  await page.getByRole('button', { name: 'File', exact: true }).click();
  const name = `Style ${crypto.randomUUID()}`;
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
  await page.getByRole('button', { name: 'Room', exact: true }).click();
  await page
    .getByRole('button', { name: 'Select/edit room', exact: true })
    .click();
  await page.mouse.click(550, 350);
  await page.getByRole('tab', { name: 'AI', exact: true }).click();
  await expect(palette).toHaveValue('warm gold');
  await expect(
    page.getByRole('textbox', { name: 'Render style', exact: true }),
  ).toHaveValue('ink drawing');
  await palette.fill('');
  await page.getByRole('button', { name: 'Apply prompt and style' }).click();
  await expect(palette).toHaveValue('');
  await expect(
    page.getByRole('button', { name: 'Apply prompt and style' }),
  ).toBeDisabled();
});
