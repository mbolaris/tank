import { expect, test } from '@playwright/test';

test('Board, toast and story consumers reject late world requests and recover polling', async ({ page }) => {
    await page.addInitScript(() => {
        const original = window.fetch;
        const pending: { url: string; resolve: (response: Response) => void }[] = [];
        const requests: string[] = [];
        window.fetch = (input, init) => {
            const url = String(input);
            if (!/commentary|story-events/.test(url)) return original(input, init);
            requests.push(url);
            // Deliberately ignore AbortSignal to prove lifetime checks.
            return new Promise<Response>(resolve => pending.push({ url, resolve }));
        };
        Object.assign(window, {
            activityRequests: requests,
            deliverActivity: (world: string, text: string, id: number) => {
                for (const item of pending.splice(0)) {
                    if (!item.url.includes(`/world/${world}/`)) { pending.push(item); continue; }
                    const data = item.url.includes('story-events')
                        ? { events: [{ id, type: 'generation_milestone', frame: id, title: text, text, entity_ids: [], metrics: {} }] }
                        : { comments: [{ id, frame: id, text, author: 'test', severity: 'info', topic: 'ecosystem', tags: [], metrics: {}, reactions: {} }] };
                    item.resolve(new Response(JSON.stringify(data), { status: 200 }));
                }
            },
        });
    });
    await page.goto('/e2e/fixtures/activity.html');
    const requests = () => page.evaluate(() => (window as unknown as { activityRequests: string[] }).activityRequests);
    const deliver = (world: string, text: string, id: number) => page.evaluate(({ world, text, id }) =>
        (window as unknown as { deliverActivity: (world: string, text: string, id: number) => void }).deliverActivity(world, text, id), { world, text, id });
    await expect.poll(async () => (await requests()).filter(url => url.includes('/world/A/')).length).toBe(5);
    await page.getByText('Switch to B', { exact: true }).click();
    await expect(page.getByTestId('commentary')).toContainText('"loaded":false');
    await expect.poll(async () => (await requests()).filter(url => url.includes('/world/B/')).length).toBe(5);
    await deliver('B', 'B evidence', 20);
    await expect(page.getByTestId('commentary')).toContainText('B evidence');
    await expect(page.getByTestId('story')).toContainText('B evidence');
    await deliver('A', 'A stale evidence', 999);
    await expect(page.locator('body')).not.toContainText('A stale evidence');
    await expect(page.getByTestId('story')).toContainText('"id":20');
    await expect.poll(async () => (await requests()).some(url => url.includes('since_id=20'))).toBe(true);
    await deliver('B', 'B fresh evidence', 21);
    await expect(page.getByTestId('story')).toContainText('B fresh evidence');
    await expect(page.getByRole('status')).toContainText('B fresh evidence');
    await page.getByText('Unmount consumers', { exact: true }).click();
    await deliver('B', 'late unmounted', 22);
    await expect(page.locator('body')).not.toContainText('late unmounted');
});
