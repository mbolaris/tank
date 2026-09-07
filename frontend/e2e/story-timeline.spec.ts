import { expect, test, type Page } from '@playwright/test';

/**
 * Browser-level contract for the Living History timeline (U7/E4).
 *
 * Runs against the real backend, so a pass means the E3 detectors, the
 * story-events REST endpoint, the polling hook, and the rendered timeline all
 * line up — not merely that the component compiles.
 */

const API = 'http://127.0.0.1:8000';

/** An isolated, non-persistent world so this never leaks into data/worlds/. */
async function createScratchWorld(page: Page): Promise<string> {
    const response = await page.request.post(`${API}/api/worlds`, {
        data: {
            world_type: 'tank',
            name: `e2e-story-${Date.now()}`,
            persistent: false,
            seed: 42,
            start_paused: false,
        },
    });
    expect(response.ok(), `world creation failed: ${response.status()}`).toBeTruthy();
    const { world_id: worldId } = await response.json();
    return worldId;
}

test('the timeline renders under the canvas and explains itself when empty', async ({ page }) => {
    const worldId = await createScratchWorld(page);
    await page.goto(`/tank/${worldId}`);

    const timeline = page.getByTestId('story-timeline');
    await expect(timeline).toBeVisible();
    await expect(timeline).toContainText('Living history');
});

test('the story-events endpoint backs the timeline with a real contract', async ({ page }) => {
    const worldId = await createScratchWorld(page);
    const response = await page.request.get(`${API}/api/world/${worldId}/story-events`);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('schema_version');
    expect(body).toHaveProperty('events');
    expect(Array.isArray(body.events)).toBeTruthy();
    // The closed detector set U7 renders. If this drifts, the feed's icons and
    // labels silently fall back to a generic "World event".
    expect(new Set(body.event_types)).toEqual(
        new Set([
            'population_danger',
            'population_recovered',
            'generation_milestone',
            'lineage_dominant',
        ]),
    );
});

test('the Board offers a World events filter next to the topics', async ({ page }) => {
    const worldId = await createScratchWorld(page);
    await page.goto(`/tank/${worldId}`);

    // The Board lives behind the Analyze-mode panel toggles.
    const boardToggle = page.getByRole('button', { name: /board/i }).first();
    await boardToggle.click();

    await expect(page.getByRole('button', { name: /world events/i })).toBeVisible();
});
