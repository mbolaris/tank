import { expect, test } from '@playwright/test';

test('paused reloads and two live clients follow accepted server state', async ({ page, context }) => {
    const response = await page.request.post('http://127.0.0.1:8000/api/worlds', {
        data: { world_type: 'tank', name: `pause-contract-${Date.now()}`, persistent: false, seed: 42, start_paused: true },
    });
    expect(response.ok()).toBeTruthy();
    const { world_id: id } = await response.json();
    const other = await context.newPage();
    try {
        await page.goto(`/tank/${id}`);
        await other.goto(`/tank/${id}`);
        await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeEnabled();
        await expect(other.getByRole('button', { name: 'Resume', exact: true })).toBeEnabled();
        await page.reload();
        await page.getByRole('button', { name: 'Resume', exact: true }).click();
        await expect(page.getByRole('button', { name: 'Pause', exact: true })).toBeEnabled();
        await expect(other.getByRole('button', { name: 'Pause', exact: true })).toBeEnabled();
        await other.getByRole('button', { name: 'Pause', exact: true }).click();
        await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeEnabled();
        await expect(other.getByRole('button', { name: 'Resume', exact: true })).toBeEnabled();
        await page.request.post(`http://127.0.0.1:8000/api/worlds/${id}/resume`);
        await expect(page.getByRole('button', { name: 'Pause', exact: true })).toBeEnabled();
    } finally {
        await other.close();
        await page.request.delete(`http://127.0.0.1:8000/api/worlds/${id}`);
    }
});
