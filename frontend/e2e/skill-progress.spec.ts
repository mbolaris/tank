import { expect, test, type Page } from '@playwright/test';

/**
 * The skill-progress panel against a live backend.
 *
 * The verdict logic is pinned in Python (`tests/test_skill_progress.py`,
 * including a captured 35-sample live series). What only a browser confirms is
 * that the panel reaches the endpoint, names all three domains whatever state
 * they are in, and does not squeeze the aquarium - it shares the sidebar with
 * the evolution readout, and an earlier revision of it silently took 350px off
 * the canvas by rendering as a second flex-row sibling.
 */

const CANVAS = 'canvas.tank-canvas';
const PANEL = '[aria-label="Evolution progress by skill domain"]';

async function waitForLiveCanvas(page: Page): Promise<void> {
    await expect(page.getByRole('button', { name: 'Add Food' })).toBeEnabled({ timeout: 30_000 });
    await expect(page.locator(CANVAS)).toBeVisible();
}

test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForLiveCanvas(page);
});

test('every evolving domain is named, whatever its state', async ({ page }) => {
    const panel = page.locator(PANEL);
    await expect(panel).toBeVisible({ timeout: 30_000 });
    // A domain that is switched off must still be listed saying so, rather than
    // disappearing and leaving the reader to wonder whether it was measured.
    for (const domain of ['Foraging', 'Poker', 'Soccer']) {
        await expect(panel.getByText(domain, { exact: true })).toBeVisible({ timeout: 30_000 });
    }
});

test('each domain carries a verdict and the sentence behind it', async ({ page }) => {
    const panel = page.locator(PANEL);
    await expect(panel).toBeVisible({ timeout: 30_000 });
    const text = await panel.innerText();
    expect(text).toMatch(/PROGRESSING|POSSIBLY|STALLED|AT CEILING|NO DATA/);
    // Never a bare verdict: the reason is what stops "Stalled" sending someone
    // to debug a subsystem that simply has not been measured enough yet.
    expect(text).toMatch(/sample/i);
});

test('the panel shares the sidebar without shrinking the tank', async ({ page }) => {
    await expect(page.locator(PANEL)).toBeVisible({ timeout: 30_000 });
    const canvas = await page.locator(CANVAS).first().boundingBox();
    const panelBox = await page.locator(PANEL).boundingBox();
    expect(canvas, 'canvas has no layout box').toBeTruthy();
    expect(panelBox, 'panel has no layout box').toBeTruthy();

    // The sidebar is a 230px column; the tank keeps the rest of the width.
    expect(panelBox!.width).toBeLessThan(280);
    expect(canvas!.width).toBeGreaterThan(700);
    // Side by side, not overlapping.
    expect(panelBox!.x).toBeGreaterThanOrEqual(canvas!.x + canvas!.width - 1);
});
