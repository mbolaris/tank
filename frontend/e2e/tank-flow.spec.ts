import { expect, test, type Page } from '@playwright/test';

/**
 * These run against the real backend (see playwright.config.ts), not mocked
 * WebSocket state, so a pass means the application shell, its live connection
 * lifecycle, and the backend command path all work together.
 *
 * The placement test uses its own non-persistent world. The default world at
 * `/` is persistent and auto-saves to data/worlds/, so placing objects there
 * would leak state between runs and make failures order-dependent.
 */

const API = 'http://127.0.0.1:8000';
const CANVAS = 'canvas.tank-canvas';
const WORLD_WIDTH = 1088;
const WORLD_HEIGHT = 612;

interface Entity {
    type: string;
    x: number;
    y: number;
    width: number;
    height: number;
}

/** Create an isolated world and return its id. */
async function createScratchWorld(page: Page): Promise<string> {
    const response = await page.request.post(`${API}/api/worlds`, {
        data: {
            world_type: 'tank',
            name: `e2e-${Date.now()}`,
            persistent: false,
            seed: 42,
            start_paused: false,
        },
    });
    expect(response.ok(), `world creation failed: ${response.status()}`).toBeTruthy();
    const { world_id: worldId } = await response.json();
    expect(worldId, 'backend returned no world_id').toBeTruthy();
    return worldId;
}

/** Records whether the app's own socket has delivered a full-state frame.
 *
 * Installed before any page script runs, so it cannot miss the first frame.
 */
const RECORD_FULL_STATE = `
(() => {
  const Native = window.WebSocket;
  window.__sawFullState = false;
  function Wrapped(...args) {
    const socket = new Native(...args);
    socket.addEventListener('message', (event) => {
      const check = (text) => {
        try {
          const frame = JSON.parse(text);
          const entities = (frame.snapshot || frame).entities;
          if (Array.isArray(entities) && entities.length) window.__sawFullState = true;
        } catch { /* non-JSON frame */ }
      };
      if (typeof event.data === 'string') check(event.data);
      else if (event.data instanceof Blob) event.data.text().then(check);
      else check(new TextDecoder().decode(event.data));
    });
    return socket;
  }
  Wrapped.prototype = Native.prototype;
  Object.assign(Wrapped, Native);
  // The readyState constants are non-enumerable, so Object.assign misses them.
  // Without this the app's \`readyState === WebSocket.OPEN\` guard compares
  // against undefined and every outgoing command is dropped in silence - the
  // socket still receives, so the UI looks perfectly healthy while nothing
  // sent from it ever reaches the backend.
  Wrapped.CONNECTING = Native.CONNECTING;
  Wrapped.OPEN = Native.OPEN;
  Wrapped.CLOSING = Native.CLOSING;
  Wrapped.CLOSED = Native.CLOSED;
  window.WebSocket = Wrapped;
})();
`;

/** Wait for the live WebSocket to deliver actual world state.
 *
 * The command controls enabling only proves the socket opened; the first
 * full-state frame arrives a beat later. That gap matters because
 * Canvas.handleCanvasClick returns early while `state` is null, so a click
 * fired in between is silently swallowed - no error, no placement, and a
 * failure that surfaces much further down. Deliberately not measured by
 * reading canvas pixels: getImageData here can report an all-zero buffer for
 * a canvas that is plainly rendering.
 */
async function waitForLiveConnection(page: Page): Promise<void> {
    await expect(page.getByRole('button', { name: 'Add Food' })).toBeEnabled({ timeout: 30_000 });
    await expect(page.locator(CANVAS)).toBeVisible();
    await expect
        .poll(() => page.evaluate(() => (window as unknown as { __sawFullState: boolean }).__sawFullState), {
            timeout: 30_000,
            message: 'no full-state frame ever reached the app',
        })
        .toBe(true);
}

/** Fetch the full entity list through a throwaway WebSocket.
 *
 * Deliberately not `GET /snapshot`: the runner keeps one shared "last sent"
 * cursor, so once the app's own socket has taken delivery that route returns
 * a delta with no `entities` array, despite passing `force_full=True`. Every
 * *new* socket is sent full state on connect, which is reliable and repeatable.
 * Frames arrive as binary, so they need decoding before JSON.parse.
 */
async function fetchEntities(page: Page, worldId: string): Promise<Entity[]> {
    const entities = await page.evaluate(
        ({ id, timeoutMs }) =>
            new Promise<Entity[]>((resolve, reject) => {
                const socket = new WebSocket(`ws://127.0.0.1:8000/ws/world/${id}`);
                socket.binaryType = 'arraybuffer';
                const timer = setTimeout(() => {
                    socket.close();
                    reject(new Error('no full-state frame arrived'));
                }, timeoutMs);
                socket.onmessage = (event: MessageEvent) => {
                    const text =
                        typeof event.data === 'string'
                            ? event.data
                            : new TextDecoder().decode(event.data as ArrayBuffer);
                    let frame: { snapshot?: { entities?: Entity[] }; entities?: Entity[] };
                    try {
                        frame = JSON.parse(text);
                    } catch {
                        return;
                    }
                    const list = frame.snapshot?.entities ?? frame.entities;
                    if (Array.isArray(list)) {
                        clearTimeout(timer);
                        socket.close();
                        resolve(list);
                    }
                };
                socket.onerror = () => {
                    clearTimeout(timer);
                    reject(new Error('websocket error'));
                };
            }),
        { id: worldId, timeoutMs: 15_000 },
    );
    expect(entities.length, 'world reported no entities at all').toBeGreaterThan(0);
    return entities;
}

/** Click a point given in world coordinates.
 *
 * Mirrors screenPointToWorld in canvasGeometry.ts: the canvas maps the world
 * linearly onto its CSS box, with no letterboxing.
 *
 * Uses locator.click({position}) rather than page.mouse.click(viewportX, ...)
 * on purpose. The canvas can sit partly above the viewport while the layout
 * settles, so absolute coordinates computed from an earlier boundingBox() go
 * stale and the click silently lands somewhere harmless. A positioned locator
 * click scrolls the element in, waits for it to be stable, and takes
 * element-relative coordinates.
 */
async function clickWorldPoint(page: Page, worldX: number, worldY: number): Promise<void> {
    const canvas = page.locator(CANVAS);
    await canvas.scrollIntoViewIfNeeded();
    const box = await canvas.boundingBox();
    expect(box, 'tank canvas has no layout box').not.toBeNull();
    await canvas.click({
        position: {
            x: worldX * (box!.width / WORLD_WIDTH),
            y: worldY * (box!.height / WORLD_HEIGHT),
        },
    });
}

/** A point inside `target` that no other clickable entity covers.
 *
 * The canvas hit-test returns the first entity containing the point and does
 * not prefer tank objects, so a fish resting over the reef would be selected
 * instead and the inspector would never appear.
 */
function unobstructedPoint(target: Entity, entities: Entity[]): { x: number; y: number } {
    const covers = (e: Entity, x: number, y: number) =>
        x >= e.x && x <= e.x + e.width && y >= e.y && y <= e.y + e.height;
    const others = entities.filter(
        (e) => e !== target && e.type !== 'food' && e.type !== 'plant_nectar',
    );
    for (const fx of [0.5, 0.3, 0.7, 0.15, 0.85]) {
        for (const fy of [0.5, 0.3, 0.7, 0.15, 0.85]) {
            const x = target.x + target.width * fx;
            const y = target.y + target.height * fy;
            if (!others.some((e) => covers(e, x, y))) return { x, y };
        }
    }
    throw new Error('every candidate point on the placed object is covered by another entity');
}

test.beforeEach(async ({ page }) => {
    await page.addInitScript(RECORD_FULL_STATE);
});

test('a viewer can enter and leave the live build workspace', async ({ page }, testInfo) => {
    await page.goto('/');

    const build = page.getByRole('button', { name: 'Build' });
    await expect(build).toBeVisible();

    await waitForLiveConnection(page);
    await build.click();
    await page.getByRole('button', { name: /Algae Reef/ }).click();
    await expect(page.getByText('Algae Reef selected — click the aquarium to place it.')).toBeVisible();

    await page.getByRole('button', { name: 'Watch' }).click();
    await expect(page.getByRole('button', { name: 'Build' })).toHaveAttribute('aria-pressed', 'false');
    await expect(page.getByText('DECORATE YOUR WORLD')).toHaveCount(0);

    await testInfo.attach('tank-flow-url', { body: page.url(), contentType: 'text/plain' });
});

test('a placed object survives a full page reload and WebSocket reconnect', async ({ page }) => {
    // Two full connect-and-render cycles plus a real simulation step, so this
    // needs more than the default per-test budget.
    test.setTimeout(150_000);

    // The regression this guards: placement travels over the WebSocket as a
    // `place_tank_object` command, so a break anywhere along
    // client -> socket -> backend -> world state -> re-broadcast leaves the
    // object visible in the session that placed it but gone after a reload.
    const worldId = await createScratchWorld(page);
    await page.goto(`/tank/${worldId}`);
    await waitForLiveConnection(page);

    await page.getByRole('button', { name: 'Build' }).click();
    const card = page.getByRole('button', { name: /Algae Reef/ });
    await card.click();
    await expect(page.getByText('Algae Reef selected — click the aquarium to place it.')).toBeVisible();

    // Mid-tank, clear of the corners the world seeds its own objects into.
    await clickWorldPoint(page, 544, 300);

    // Placement clears the selected card (TankView.handleBuildPlace) - the
    // client-side signal that the command was actually dispatched, rather than
    // the click having landed somewhere that did nothing.
    await expect(card, 'the canvas click never reached handleBuildPlace').toHaveClass(
        /_card_/,
        { timeout: 10_000 },
    );

    // Confirm the command reached world state before the reload, so a failure
    // below can only mean the state did not survive the reconnect.
    let placed: Entity[] = [];
    await expect
        .poll(
            async () => {
                const entities = await fetchEntities(page, worldId);
                placed = entities.filter(
                    (candidate) =>
                        candidate.type === 'algae_reef' &&
                        candidate.x > 100 &&
                        candidate.x < WORLD_WIDTH - 200,
                );
                return placed.length;
            },
            {
                timeout: 20_000,
                message: 'the placed reef never reached world state - the command path is broken',
            },
        )
        .toBe(1);

    // Full reload: new document, new WebSocket, state rebuilt from the backend.
    await page.reload();
    await waitForLiveConnection(page);
    await page.getByRole('button', { name: 'Build' }).click();

    // Re-resolve the reef inside the post-reload entity list. Reusing the
    // object from the earlier fetch would be a different reference, so the
    // reef would count as an obstruction covering itself.
    const afterReload = await fetchEntities(page, worldId);
    const reef = afterReload.find(
        (candidate) =>
            candidate.type === 'algae_reef' &&
            Math.abs(candidate.x - placed[0].x) < 1 &&
            Math.abs(candidate.y - placed[0].y) < 1,
    );
    expect(reef, 'the placed reef was gone after the reload and reconnect').toBeDefined();

    const target = unobstructedPoint(reef!, afterReload);

    // No card is selected now, so a canvas click hit-tests entities rather
    // than placing - it resolves to the object only if it really persisted.
    // Retried because the hit-test returns whichever entity is on top, and a
    // fish swimming over the reef would be selected instead; fish keep moving,
    // so a later attempt lands on the reef itself.
    await expect
        .poll(
            async () => {
                await clickWorldPoint(page, target.x, target.y);
                return page.getByText(/placed object #\d+/).count();
            },
            {
                timeout: 20_000,
                message: 'the placed object did not survive the reload and reconnect',
            },
        )
        .toBeGreaterThan(0);

    await expect(page.getByRole('button', { name: 'Delete' })).toBeVisible();
});
