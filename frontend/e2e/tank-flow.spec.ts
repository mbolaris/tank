import { expect, test } from '@playwright/test';

test('a viewer can enter and leave the live build workspace', async ({ page }, testInfo) => {
    await page.goto('/');

    const build = page.getByRole('button', { name: 'Build' });
    await expect(build).toBeVisible();

    // The command controls are disabled until the real WebSocket connection
    // has arrived, so this is not a mocked component-level interaction.
    await expect(page.getByRole('button', { name: 'Add Food' })).toBeEnabled();
    await build.click();
    await page.getByRole('button', { name: /Algae Reef/ }).click();
    await expect(page.getByText('Algae Reef selected — click the aquarium to place it.')).toBeVisible();

    await page.getByRole('button', { name: 'Watch' }).click();
    await expect(page.getByRole('button', { name: 'Build' })).toHaveAttribute('aria-pressed', 'false');
    await expect(page.getByText('DECORATE YOUR WORLD')).toHaveCount(0);

    await testInfo.attach('tank-flow-url', { body: page.url(), contentType: 'text/plain' });
});
