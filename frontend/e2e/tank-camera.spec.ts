import { expect, test, type Page } from '@playwright/test';

/**
 * The free-look camera, exercised through real input rather than unit-level
 * maths. camera.test.ts already pins the transforms; what only a browser can
 * confirm is that a wheel gesture reaches the canvas without scrolling the
 * page, that a drag pans instead of selecting a fish, and that the controls
 * stay in step with the view.
 */

const CANVAS = 'canvas.tank-canvas';
const CONTROLS = '[data-testid="camera-controls"]';

async function waitForLiveCanvas(page: Page): Promise<void> {
    await expect(page.getByRole('button', { name: 'Add Food' })).toBeEnabled({ timeout: 30_000 });
    await expect(page.locator(CANVAS)).toBeVisible();
    await expect(page.locator(CONTROLS)).toBeVisible({ timeout: 30_000 });
}

/** The zoom readout, as a number ("2.5×" -> 2.5). */
async function readZoom(page: Page): Promise<number> {
    const label = await page.locator(`${CONTROLS} span`).innerText();
    return Number.parseFloat(label.replace('×', '').trim());
}

async function canvasBox(page: Page) {
    const box = await page.locator(CANVAS).first().boundingBox();
    expect(box, 'canvas has no layout box').toBeTruthy();
    return box!;
}

test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForLiveCanvas(page);
});

test('the view starts showing the whole tank', async ({ page }) => {
    expect(await readZoom(page)).toBe(1);
    await expect(page.getByRole('button', { name: 'Reset view' })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Zoom out' })).toBeDisabled();
});

test('the wheel zooms the tank without scrolling the page', async ({ page }) => {
    const box = await canvasBox(page);
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.wheel(0, -300);

    await expect.poll(() => readZoom(page), { timeout: 5_000 }).toBeGreaterThan(1);
    // The canvas must swallow the gesture; a scrolled page means the listener
    // was registered passively and preventDefault never took effect.
    expect(await page.evaluate(() => window.scrollY)).toBe(0);
});

test('zoom is bounded at both ends', async ({ page }) => {
    const box = await canvasBox(page);
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    for (let i = 0; i < 12; i += 1) await page.mouse.wheel(0, -300);
    await expect.poll(() => readZoom(page), { timeout: 5_000 }).toBeLessThanOrEqual(4);
    await expect(page.getByRole('button', { name: 'Zoom in' })).toBeDisabled();

    for (let i = 0; i < 20; i += 1) await page.mouse.wheel(0, 300);
    await expect.poll(() => readZoom(page), { timeout: 5_000 }).toBe(1);
    await expect(page.getByRole('button', { name: 'Zoom out' })).toBeDisabled();
});

test('the buttons zoom and reset the view', async ({ page }) => {
    await page.getByRole('button', { name: 'Zoom in' }).click();
    await expect.poll(() => readZoom(page), { timeout: 5_000 }).toBeGreaterThan(1);

    await page.getByRole('button', { name: 'Reset view' }).click();
    await expect.poll(() => readZoom(page), { timeout: 5_000 }).toBe(1);
    await expect(page.getByRole('button', { name: 'Reset view' })).toBeDisabled();
});

test('dragging pans the view rather than selecting a fish', async ({ page }) => {
    const box = await canvasBox(page);
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.wheel(0, -600);
    await expect.poll(() => readZoom(page), { timeout: 5_000 }).toBeGreaterThan(1);

    const cx = box.x + box.width / 2;
    const cy = box.y + box.height / 2;
    await page.mouse.move(cx, cy);
    await page.mouse.down();
    await page.mouse.move(cx - 200, cy - 80, { steps: 12 });
    await page.mouse.up();

    // A pan must not double as a click: the inspector drawer stays shut.
    await expect(page.getByRole('complementary', { name: /inspector/i })).toHaveCount(0);
    // Zoom is unchanged by panning.
    expect(await readZoom(page)).toBeGreaterThan(1);
});

test('panning cannot leave the tank', async ({ page }) => {
    const box = await canvasBox(page);
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.wheel(0, -600);
    await expect.poll(() => readZoom(page), { timeout: 5_000 }).toBeGreaterThan(1);

    // Shove the view hard into a corner, repeatedly.
    for (let i = 0; i < 6; i += 1) {
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.mouse.down();
        await page.mouse.move(box.x + box.width, box.y + box.height, { steps: 6 });
        await page.mouse.up();
    }

    // Still a live, sane canvas rather than a blank or detached one.
    await expect(page.locator(CANVAS)).toBeVisible();
    expect(await readZoom(page)).toBeGreaterThan(1);
});
