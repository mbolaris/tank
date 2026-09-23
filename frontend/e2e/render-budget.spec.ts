import { expect, test } from '@playwright/test';

/**
 * TankView re-renders on every WebSocket payload (~15 a second). Its children
 * whose props rarely change - the controls, the mode switch, the canvas
 * overlays, the evolution sidebar - are memoized, which only works while
 * TankView hands them stable props: one inline `() => ...` callback silently
 * puts a child back on the per-message path (IMPROVEMENT_PROPOSALS 13.9
 * measured that at ~30% of dev-mode React time per message).
 *
 * This counts real renders through a minimal React DevTools hook. After each
 * commit it walks the fiber tree and, for each render of a watched component,
 * shallow-compares its props with the previous render's. A render is *wasted*
 * when no prop changed, or only function props changed identity - exactly
 * what an unmemoized child or an inline callback produces. Renders driven by
 * data (a new metrics sample, a connection-status change) are not counted, so
 * the budget of zero holds however loaded the backend is.
 */

const MEMOIZED_CHILDREN = ['ControlPanel', 'ModeSwitch', 'CanvasOverlays', 'EvolutionSidebar'];

test('memoized TankView children skip per-message renders', async ({ page }) => {
    await page.addInitScript(() => {
        type Fiber = {
            type: unknown;
            child: Fiber | null;
            sibling: Fiber | null;
            alternate: Fiber | null;
            memoizedProps: unknown;
            memoizedState: unknown;
        };
        const counts: Record<string, number> = {};
        const wasted: Record<string, number> = {};
        const seen = new WeakMap<Fiber, [unknown, unknown]>();
        // Vite renames `memo(function ControlPanel ...)`'s inner function to
        // ControlPanel2 (it shadows the const), so trailing digits are dropped.
        const nameOf = (fiber: Fiber) =>
            typeof fiber.type === 'function'
                ? (fiber.type as { name?: string }).name?.replace(/\d+$/, '')
                : undefined;
        const onlyCallbacksChanged = (prev: unknown, next: unknown) => {
            if (!prev || !next || typeof prev !== 'object' || typeof next !== 'object') return false;
            const a = prev as Record<string, unknown>;
            const b = next as Record<string, unknown>;
            const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
            for (const key of keys) {
                if (!Object.is(a[key], b[key]) && typeof b[key] !== 'function') return false;
            }
            return true;
        };
        const w = window as unknown as {
            __renderCounts: Record<string, number>;
            __wastedRenders: Record<string, number>;
            __REACT_DEVTOOLS_GLOBAL_HOOK__: unknown;
        };
        w.__wastedRenders = wasted;
        w.__renderCounts = counts;
        let nextId = 1;
        w.__REACT_DEVTOOLS_GLOBAL_HOOK__ = {
            supportsFiber: true,
            renderers: new Map(),
            inject(renderer: unknown) {
                const id = nextId++;
                this.renderers.set(id, renderer);
                return id;
            },
            checkDCE() {},
            onScheduleFiberRoot() {},
            onCommitFiberUnmount() {},
            onPostCommitFiberRoot() {},
            onCommitFiberRoot(_id: number, root: { current: Fiber }) {
                const stack: Fiber[] = [root.current];
                while (stack.length > 0) {
                    const fiber = stack.pop()!;
                    const name = nameOf(fiber);
                    if (name) {
                        const before =
                            seen.get(fiber) ?? (fiber.alternate ? seen.get(fiber.alternate) : undefined);
                        if (
                            before !== undefined &&
                            (before[0] !== fiber.memoizedProps || before[1] !== fiber.memoizedState)
                        ) {
                            counts[name] = (counts[name] ?? 0) + 1;
                            if (
                                before[1] === fiber.memoizedState &&
                                onlyCallbacksChanged(before[0], fiber.memoizedProps)
                            ) {
                                wasted[name] = (wasted[name] ?? 0) + 1;
                            }
                        }
                        seen.set(fiber, [fiber.memoizedProps, fiber.memoizedState]);
                    }
                    if (fiber.sibling) stack.push(fiber.sibling);
                    if (fiber.child) stack.push(fiber.child);
                }
            },
        };
    });

    await page.goto('/');
    await expect(page.getByRole('button', { name: 'Add Food' })).toBeEnabled({ timeout: 30_000 });
    await expect(page.locator('canvas.tank-canvas')).toBeVisible();
    await page.waitForTimeout(2_000);

    type Counts = Record<string, number>;
    const read = () =>
        page.evaluate(() => {
            const w = window as unknown as { __renderCounts: Counts; __wastedRenders: Counts };
            return { renders: { ...w.__renderCounts }, wasted: { ...w.__wastedRenders } };
        });
    const before = await read();
    // A window of payloads rather than of seconds: the message rate depends on
    // how loaded the shared backend is.
    await expect
        .poll(async () => ((await read()).renders.TankView ?? 0) - (before.renders.TankView ?? 0), {
            message: 'TankView should re-render with the live stream',
            timeout: 60_000,
        })
        .toBeGreaterThanOrEqual(20);
    const after = await read();

    for (const name of MEMOIZED_CHILDREN) {
        const wastedRenders = (after.wasted[name] ?? 0) - (before.wasted[name] ?? 0);
        expect(wastedRenders, `${name}: renders with no data prop changed`).toBe(0);
    }
});
