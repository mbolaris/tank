import { expect, test, type Page } from '@playwright/test';

/**
 * The Cinematic Director, exercised in a real browser.
 *
 * `cinematicDirector.test.ts` pins the shot-selection rules; what only a live
 * tank can confirm is that the toggle is reachable over the canvas, and — the
 * rule most likely to regress silently — that switching the director on does
 * **not** immediately replay the story-event backlog. `useStoryEvents`
 * backfills up to 200 past events, so a cursor bug would show up here as a
 * caption for something that happened long before the viewer pressed the
 * button, and nowhere else.
 *
 * Deliberately not asserted: that a shot eventually fires. Story events are
 * produced by detectors on world state, so waiting for one would make this
 * test a coin flip on how the simulation happens to be going.
 */

const CANVAS = 'canvas.tank-canvas';
const CAPTION = '[role="status"]';

async function waitForLiveCanvas(page: Page): Promise<void> {
    await expect(page.getByRole('button', { name: 'Add Food' })).toBeEnabled({ timeout: 30_000 });
    await expect(page.locator(CANVAS)).toBeVisible();
}

function directorToggle(page: Page) {
    return page.getByRole('button', { name: /Director/i });
}

test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForLiveCanvas(page);
});

test('the director is offered over the tank and starts switched off', async ({ page }) => {
    const toggle = directorToggle(page);
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAttribute('aria-pressed', 'false');
});

test('the toggle reports its state rather than signalling by colour alone', async ({ page }) => {
    const toggle = directorToggle(page);
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-pressed', 'true');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-pressed', 'false');
});

test('switching it on does not replay the backfilled story-event history', async ({ page }) => {
    // The backlog is fetched before the toggle is pressed, so a cursor bug cuts
    // to a stale moment within a poll tick or two. Five seconds is many ticks.
    await directorToggle(page).click();
    await page.waitForTimeout(5_000);
    await expect(page.locator(CAPTION).filter({ hasText: /Generation|Lineage|Population/ })).toHaveCount(0);
});

test('switching it off ends any shot and leaves the tank alone', async ({ page }) => {
    const toggle = directorToggle(page);
    await toggle.click();
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-pressed', 'false');
    await expect(page.locator(CAPTION).filter({ hasText: /Generation|Lineage|Population/ })).toHaveCount(0);
    await expect(page.locator(CANVAS)).toBeVisible();
});
