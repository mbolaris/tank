import { expect, test } from '@playwright/test';

test('pending pause cannot double-send or invent acceptance and clears across worlds', async ({ page }) => {
    await page.goto('/e2e/fixtures/activity.html?pause');
    await page.getByRole('button', { name: 'Pause', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Waiting…', exact: true })).toBeDisabled();
    await page.evaluate(() => (window as unknown as { settlePause: (value: { success: boolean; error: string }) => void }).settlePause({ success: false, error: 'Rejected by server' }));
    await expect(page.getByRole('alert')).toContainText('Rejected by server');
    await expect(page.getByRole('button', { name: 'Pause', exact: true })).toBeEnabled();

    await page.getByRole('button', { name: 'Pause', exact: true }).click();
    await page.getByText('Switch pause world', { exact: true }).click();
    await page.evaluate(() => (window as unknown as { failPause: (error: Error) => void }).failPause(new Error('late A failure')));
    await expect(page.getByRole('alert')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Pause', exact: true })).toBeEnabled();

    await page.getByRole('button', { name: 'Pause', exact: true }).click();
    await page.getByText('Disconnect', { exact: true }).click();
    await expect(page.getByRole('button', { name: 'Waiting…', exact: true })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Pause', exact: true })).toBeDisabled();
});
